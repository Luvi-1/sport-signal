"""Frozen ACB release-context experiment, with separately gated phases.

Only ``prepare`` is runnable before review. All estimator fits fail closed unless
shared gates authorize the exact frozen inputs. Tests replace estimators with
invented-data doubles; they never need to fit a real estimator.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from . import basketball as parser
from . import gates
from .metrics import classification_summary, per_case_scores
from .shot_sources import sha256_file

ROOT = Path(__file__).resolve().parents[2]
DEVELOPMENT_GAMES = parser.DEVELOPMENT_GAMES
EVALUATION_GAMES = parser.QA_GAMES
ALL_GAMES = DEVELOPMENT_GAMES + EVALUATION_GAMES
CANDIDATES = ("A", "B", "C", "D")
PROTOCOL = "docs/tactical/BASKETBALL_PROTOCOL_DRAFT.md"
CONTEXT_PATH = "data/tactical/basketball/contexts.jsonl"
TARGET_PATH = "data/tactical/basketball/development_targets.jsonl"
SOURCE_MANIFEST = "data/tactical/basketball/source_manifest.json"
PARSER_SUMMARY = "reports/tactical/basketball/summary.json"
ARTIFACT_DIRECTORY = "artifacts/tactical/basketball"
REPORT_DIRECTORY = "reports/tactical/basketball/model"
LOG_EPSILON = 1e-6
BIN_EDGES = (0., .2, .4, .6, .8, 1.)
CELL_EDGES = (6., 14., 22.)
FIT_LIMITS = {"development": 8, "evaluation": 10}
BASE_FEATURES = (
    "log1p_distance_ft", "three", "absolute_hoop_bearing_rad",
    "shot_clock_seconds", "shot_clock_missing", "bearing_missing",
)
CONTEXT_FEATURES = BASE_FEATURES + ("log1p_nearest_defender_distance_ft", "defender_log_distance_x_three")
BINARY_FEATURES = frozenset(("three", "shot_clock_missing", "bearing_missing"))
PARSER_FEATURES = frozenset(("x_ft", "y_ft", "distance_ft", "absolute_hoop_bearing_rad",
                           "three", "shot_clock_seconds", "nearest_defender_distance_ft"))
QUALITY_MASKS = ("raw_consistent_0p1ft", "raw_consistent_1ft", "raw_consistent_and_directly_detected_0p1ft")
LOGISTIC_CONFIG = {"C": 1., "fit_intercept": True, "solver": "lbfgs", "penalty": "l2",
                   "max_iter": 2000, "tol": 1e-8, "class_weight": None}
CODE_PATHS = (
    "experiments/tactical/basketball_model.py", "experiments/tactical/basketball.py",
    "experiments/tactical/shot_sources.py", "experiments/tactical/metrics.py",
    "experiments/tactical/gates.py", "pyproject.toml",
)


class ProtocolError(RuntimeError):
    """An integrity, timing, numerical or measurement failure. Never auto-retry."""


class GateClosed(ProtocolError):
    pass


class TargetValidityError(ProtocolError):
    def __init__(self, affected):
        self.affected = affected
        super().__init__(f"Binary target validity stop: {len(affected)} affected releases; no rows dropped")


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _digest(value):
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _read_json(path):
    return json.loads(Path(path).read_text())


def _write_once(path, value):
    """Exclusive, durable write: existing results are never replaced by a rerun."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _json_bytes(value)
    with path.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    return sha256_file(path)


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _environment():
    return {"python": platform.python_version(), "platform": platform.platform(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("numpy", "scipy", "pandas", "scikit-learn", "joblib")}}


def _relative(root, path):
    path = Path(path)
    resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        return resolved, str(resolved.relative_to(root))
    except ValueError as error:
        raise ProtocolError("Source path escapes project root") from error


def _source_event_path(game):
    return f"data/research/SkillCorner_opendata-basketball/data/matches/{game}/{game}_dynamic_events.json"


def _require_gate(runner, phase):
    """Require a lead-recorded permit for these exact frozen inputs; never self-approve."""
    stage = "evaluation" if phase == "scoring" else phase
    try:
        permit = gates.require_stage(runner.root, "basketball", stage)
    except (PermissionError, FileNotFoundError) as error:
        raise GateClosed(str(error)) from error
    if (permit["binding_sha256"] != runner.manifest["binding_sha256"]
            or permit["binding"]["metadata"].get("artifact_id") != runner.artifact_id):
        raise GateClosed("Shared stage permit belongs to another immutable runner artifact")
    return permit


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid_clock(value):
    return _finite(value) and 0 <= value <= 24


def _eligible(row):
    if type(row.get("event_geometry_eligible")) is not bool:
        raise ProtocolError("Geometry eligibility must be an explicit parser boolean")
    return row["event_geometry_eligible"]


def _validate_contexts(rows):
    """Validate the parser contract, without consulting labels or inferring new exclusions."""
    seen = set()
    for row in rows:
        shot = row.get("shot_id")
        if not isinstance(shot, str) or not shot or shot in seen:
            raise ProtocolError("Missing or duplicate release ID")
        seen.add(shot)
        if row.get("game_id") not in ALL_GAMES:
            raise ProtocolError("Undeclared game in context artifact")
        f = row.get("features", {})
        if set(f) != PARSER_FEATURES:
            raise ProtocolError("Parser feature allowlist differs from the frozen contract")
        eligible = _eligible(row)
        q = row.get("quality", {})
        keys = ("location_valid", "nearest_defender_distance_valid", "three_flag_valid", "period_valid", "release_frame_valid")
        if any(type(q.get(key)) is not bool for key in keys) or eligible != all(q[key] for key in keys):
            raise ProtocolError("Eligibility disagrees with parser quality flags")
        if eligible:
            if not parser.valid_xy([f["x_ft"], f["y_ft"]]) or type(f["three"]) is not bool:
                raise ProtocolError("Eligible geometry contains malformed location/three")
            if not _finite(f["distance_ft"]) or f["distance_ft"] < 0 or not _finite(f["nearest_defender_distance_ft"]) or f["nearest_defender_distance_ft"] < 0:
                raise ProtocolError("Eligible geometry contains malformed distance")
            expected = parser.court_geometry([f["x_ft"], f["y_ft"]])
            if not math.isclose(expected["distance_ft"], f["distance_ft"], rel_tol=0, abs_tol=1e-10):
                raise ProtocolError("Event distance is not the declared feet/hoop geometry")
            bearing = f["absolute_hoop_bearing_rad"]
            if expected["absolute_hoop_bearing_rad"] is None:
                if bearing is not None:
                    raise ProtocolError("Exact-hoop bearing must be explicitly missing")
            elif not _finite(bearing) or not math.isclose(bearing, expected["absolute_hoop_bearing_rad"], rel_tol=0, abs_tol=1e-10):
                raise ProtocolError("Event bearing disagrees with normalized geometry")
        raw = row.get("raw_quality", {})
        if any(type(raw.get(key)) is not bool for key in QUALITY_MASKS):
            raise ProtocolError("Prespecified raw-quality masks must be explicit booleans")
        if raw[QUALITY_MASKS[0]] and (not eligible or not raw[QUALITY_MASKS[1]]):
            raise ProtocolError("Raw agreement masks violate nested geometry support")
        if raw[QUALITY_MASKS[2]] and not raw[QUALITY_MASKS[0]]:
            raise ProtocolError("Direct-detection sensitivity is not nested")
    return rows


def _binary_targets(rows, labels):
    """Validate ALL recorded releases, including the A-fallback cohort."""
    expected = {row["shot_id"] for row in rows}
    if set(labels) != expected:
        affected = [{"shot_id": shot, "reason": "missing_target"} for shot in sorted(expected - set(labels))]
        affected += [{"shot_id": shot, "reason": "unexpected_target"} for shot in sorted(set(labels) - expected)]
        raise TargetValidityError(affected)
    affected = [{"shot_id": row["shot_id"], "game_id": row["game_id"], "reason": "nonfinite_nonbinary_or_unknown_target"}
                for row in rows if type(labels[row["shot_id"]]) is not int or labels[row["shot_id"]] not in (0, 1)]
    if affected:
        raise TargetValidityError(affected)
    return np.asarray([labels[row["shot_id"]] for row in rows], dtype=np.int64)


def _raw_matrix(rows, candidate, clock_median):
    if candidate not in ("C", "D"):
        raise ProtocolError("Only fixed logistic candidates C and D have design matrices")
    features = BASE_FEATURES if candidate == "C" else CONTEXT_FEATURES
    values = []
    for row in rows:
        if not _eligible(row):
            raise ProtocolError("Do not impute geometry for unsupported releases")
        f = row["features"]
        clock = f["shot_clock_seconds"]
        bearing = f["absolute_hoop_bearing_rad"]
        v = [math.log1p(f["distance_ft"]), float(f["three"]), 0. if bearing is None else bearing,
             clock if _valid_clock(clock) else clock_median, float(not _valid_clock(clock)), float(bearing is None)]
        if candidate == "D":
            defender = math.log1p(f["nearest_defender_distance_ft"])
            v.extend((defender, defender * float(f["three"])))
        values.append(v)
    matrix = np.asarray(values, dtype=np.float64).reshape((-1, len(features)))
    if not np.isfinite(matrix).all():
        raise ProtocolError("Nonfinite design matrix; no clipping or row dropping")
    return matrix


@dataclass(frozen=True)
class Preprocessor:
    candidate: str
    feature_names: tuple
    shot_clock_median: float
    no_valid_training_clock: bool
    means: tuple
    scales: tuple
    training_ids_sha256: str

    @classmethod
    def from_training(cls, rows, candidate):
        if not rows or any(not _eligible(row) for row in rows):
            raise ProtocolError("Preprocessing requires the common nonempty eligible training cohort")
        clocks = [row["features"]["shot_clock_seconds"] for row in rows if _valid_clock(row["features"]["shot_clock_seconds"])]
        median = float(np.median(clocks)) if clocks else 12.
        matrix = _raw_matrix(rows, candidate, median)
        names = BASE_FEATURES if candidate == "C" else CONTEXT_FEATURES
        means = np.zeros(len(names), dtype=np.float64)
        scales = np.ones(len(names), dtype=np.float64)
        for index, name in enumerate(names):
            if name not in BINARY_FEATURES:
                means[index] = matrix[:, index].mean()
                deviation = matrix[:, index].std(ddof=0)
                scales[index] = deviation if deviation > 0 else 1.
        return cls(candidate, names, median, not clocks, tuple(means.tolist()), tuple(scales.tolist()),
                   _digest([row["shot_id"] for row in rows]))

    def transform(self, rows):
        matrix = _raw_matrix(rows, self.candidate, self.shot_clock_median)
        result = (matrix - np.asarray(self.means, dtype=np.float64)) / np.asarray(self.scales, dtype=np.float64)
        if not np.isfinite(result).all():
            raise ProtocolError("Nonfinite standardized matrix")
        return result

    def to_dict(self):
        return {"candidate": self.candidate, "feature_names": list(self.feature_names),
                "shot_clock_median": self.shot_clock_median, "no_valid_training_clock": self.no_valid_training_clock,
                "means": list(self.means), "scales": list(self.scales), "training_ids_sha256": self.training_ids_sha256,
                "continuous_std_ddof": 0, "binary_columns_standardized": False}

    @classmethod
    def from_dict(cls, value):
        return cls(value["candidate"], tuple(value["feature_names"]), value["shot_clock_median"],
                   value["no_valid_training_clock"], tuple(value["means"]), tuple(value["scales"]), value["training_ids_sha256"])


def _cell(row):
    f = row["features"]
    return f"{int(f['three'])}:{sum(f['distance_ft'] >= edge for edge in CELL_EDGES)}"


def _sigmoid(values):
    values = np.asarray(values, dtype=np.float64)
    output = np.empty_like(values)
    positive = values >= 0
    output[positive] = 1 / (1 + np.exp(-values[positive]))
    exponential = np.exp(values[~positive])
    output[~positive] = exponential / (1 + exponential)
    return output


def predict(model_artifact, contexts):
    """Pure, label-free inference from an already saved model; no fit or scoring.

    Raw tracking diagnostics only copy subgroup membership; neither orientations,
    player IDs nor quality residuals are used in the numeric design matrix.
    """
    model = _read_json(model_artifact) if isinstance(model_artifact, (str, Path)) else model_artifact
    rows = _validate_contexts(list(contexts))
    prior = model["A"]["probability"]
    eligible = [row for row in rows if _eligible(row)]
    probabilities = {candidate: np.full(len(rows), prior, dtype=np.float64) for candidate in CANDIDATES}
    indexes = [i for i, row in enumerate(rows) if _eligible(row)]
    for index in indexes:
        row = rows[index]
        probabilities["B"][index] = model["B"]["cells"].get(_cell(row), {"probability": prior})["probability"]
    for candidate in ("C", "D"):
        stream = model[candidate]
        if stream["status"] == "fitted" and eligible:
            prep = Preprocessor.from_dict(stream["preprocessing"])
            logits = prep.transform(eligible) @ np.asarray(stream["coef"], dtype=np.float64) + stream["intercept"]
            probabilities[candidate][indexes] = _sigmoid(logits)
        elif stream["status"] not in ("fitted", "pooled_fallback_single_class", "pooled_fallback_no_eligible_training"):
            raise ProtocolError("Unknown model stream status")
    if any(not np.isfinite(p).all() or (p < 0).any() or (p > 1).any() for p in probabilities.values()):
        raise ProtocolError("Saved model produced invalid probabilities")
    results = []
    for index, row in enumerate(rows):
        support = _eligible(row)
        three = row["features"]["three"]
        point_value = 3 if three is True else 2 if three is False else None
        results.append({"shot_id": row["shot_id"], "game_id": row["game_id"],
                        "event_geometry_eligible": support, "geometry_fallback": not support,
                        **{key: row["raw_quality"][key] for key in QUALITY_MASKS},
                        "probabilities": {candidate: float(probabilities[candidate][index]) for candidate in CANDIDATES},
                        "fallback": {candidate: (not support or (candidate in ("C", "D") and model[candidate]["status"] != "fitted"))
                                     for candidate in CANDIDATES},
                        "immediate_field_goal_points": {candidate: point_value * float(probabilities[candidate][index]) if point_value else None
                                                       for candidate in CANDIDATES}})
    return {"artifact_id": model["artifact_id"], "training_game_ids": model["training_game_ids"],
            "training_ids_sha256": model["training_ids_sha256"],
            "preprocessing_sha256": {candidate: _digest(model[candidate].get("preprocessing")) for candidate in ("C", "D")},
            "rows": results, "interpretation": "Immediate field-goal points conditional on release only; no foul, rebound, turnover or continuation reward"}


def prepare(root=ROOT, *, run_dir=None):
    """Hash and freeze sources/code/environment, without parsing ANY target file."""
    root = Path(root).resolve()
    source = _read_json(root / SOURCE_MANIFEST)
    if source.get("commit") != parser.COMMIT:
        raise ProtocolError("Basketball source commit mismatch")
    expected_paths = {f"data/research/SkillCorner_opendata-basketball/data/matches/{game}/{game}_{suffix}"
                      for game in ALL_GAMES for suffix in ("dynamic_events.json", "game_data.json", "tracking_data.jsonl.gz")}
    if len(source.get("files", [])) != len(expected_paths) or {record["path"] for record in source["files"]} != expected_paths:
        raise ProtocolError("Source manifest must bind the exact 30 files for the ten fixed games")
    sources = {}
    for record in source["files"]:
        path, relative = _relative(root, record["path"])
        if f"/{parser.COMMIT}/" not in record["url"] or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise ProtocolError(f"Pinned source integrity failure: {relative}")
        sources[relative] = {"sha256": record["sha256"], "bytes": record["bytes"]}
    summary = _read_json(root / PARSER_SUMMARY)
    if summary.get("source_commit") != parser.COMMIT:
        raise ProtocolError("Reviewed parser summary source mismatch")
    for relative, expected in summary.get("parser_dependencies_sha256", {}).items():
        if sha256_file(root / relative) != expected:
            raise ProtocolError(f"Parser source changed after the reviewed context build: {relative}")
    if summary.get("parser_sha256") != sha256_file(root / "experiments/tactical/basketball.py"):
        raise ProtocolError("Context artifact was produced by a different parser")
    contract_path = "docs/research/TACTICAL_MEASUREMENT_CONTRACT.json"
    if summary.get("contract_sha256") != sha256_file(root / contract_path):
        raise ProtocolError("Measurement contract changed after parser build")
    files = list(CODE_PATHS) + [PROTOCOL, contract_path, CONTEXT_PATH, TARGET_PATH, SOURCE_MANIFEST,
                               PARSER_SUMMARY, "data/tactical/basketball/orientation_qa.json",
                               "data/tactical/basketball/SKILLCORNER_BASKETBALL_MIT.txt"]
    frozen = {}
    for relative in files:
        path = root / relative
        # Absence of the shared gate is itself frozen and never authorizes execution.
        if not path.exists() and relative == "experiments/tactical/gates.py":
            frozen[relative] = {"sha256": None, "bytes": None}
        else:
            frozen[relative] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    contexts = _validate_contexts([json.loads(line) for line in (root / CONTEXT_PATH).read_text().splitlines()])
    counts = Counter(row["game_id"] for row in contexts)
    if set(counts) != set(ALL_GAMES):
        raise ProtocolError("Missing fixed game in context artifact")
    summary_counts = {item["game_id"]: item["recorded_releases"] for item in summary["cohorts"]}
    if dict(counts) != summary_counts:
        raise ProtocolError("Context population differs from the reviewed parser summary")
    content = {"schema_version": 1, "sport": "basketball", "task": "recorded_field_goal_release_context",
               "source_commit": parser.COMMIT, "files": frozen, "sources": sources, "environment": _environment(),
               "development_game_ids": list(DEVELOPMENT_GAMES), "evaluation_game_ids": list(EVALUATION_GAMES),
               "candidates": list(CANDIDATES), "designated_comparison": "D minus C", "fit_limits": FIT_LIMITS,
               "logistic_config": LOGISTIC_CONFIG, "C_features": list(BASE_FEATURES), "D_features": list(CONTEXT_FEATURES),
               "target_policy": "Every recorded release must have an explicit binary label; unknown labels stop",
               "recalibrator_fits": 0, "context_game_counts": dict(counts),
               "release_ids_sha256": _digest([row["shot_id"] for row in contexts]),
               "publication": "local_only_pending_specific_release_review",
               "orientation": "Parser raw rotations are retrospective QA metadata only, never model features"}
    artifact_id = _digest(content)
    binding = gates.prepare_binding(
        root, "basketball", PROTOCOL, list(CODE_PATHS) + [contract_path],
        {relative: value["sha256"] for relative, value in (sources | frozen).items()
         if relative not in CODE_PATHS and relative not in (PROTOCOL, contract_path)},
        metadata={"artifact_id": artifact_id, "fit_limits": FIT_LIMITS,
                  "fixed_candidates": list(CANDIDATES), "designated_comparison": "D minus C"})
    manifest = {"artifact_id": artifact_id, "binding_sha256": binding["binding_sha256"],
                "created_at": _utc(), "freeze": content}
    run_dir = Path(run_dir) if run_dir is not None else root / ARTIFACT_DIRECTORY / artifact_id
    if not run_dir.is_absolute():
        run_dir = root / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_once(run_dir / "manifest.json", manifest)
    journal = Journal(run_dir)
    journal.append("prepared", artifact_id=artifact_id, targets_read=False, fits=0)
    return {"artifact_id": artifact_id, "run_dir": str(run_dir), "manifest": str(run_dir / "manifest.json"),
            "phase": "prepared", "fit_gate": "closed_pending_exact_frozen_approval"}


class Journal:
    def __init__(self, run_dir):
        self.path = Path(run_dir) / "journal.jsonl"

    def read(self):
        if not self.path.exists():
            return []
        events = []
        previous = None
        for line in self.path.read_text().splitlines():
            event = json.loads(line)
            digest = event.pop("entry_sha256")
            if event.get("sequence") != len(events) or event.get("previous_sha256") != previous or _digest(event) != digest:
                raise ProtocolError("Journal hash chain failed; no resume permitted")
            event["entry_sha256"] = digest
            events.append(event)
            previous = digest
        return events

    def append(self, kind, **details):
        events = self.read()
        event = {"sequence": len(events), "previous_sha256": events[-1]["entry_sha256"] if events else None,
                 "at": _utc(), "kind": kind, **details}
        event["entry_sha256"] = _digest(event)
        with self.path.open("ab") as output:
            output.write(_json_bytes(event))
            output.flush()
            os.fsync(output.fileno())
        return event


class Runner:
    def __init__(self, root, run_dir):
        self.root = Path(root).resolve()
        self.run_dir = Path(run_dir).resolve()
        self.manifest = _read_json(self.run_dir / "manifest.json")
        self.artifact_id = self.manifest["artifact_id"]
        if _digest(self.manifest["freeze"]) != self.artifact_id:
            raise ProtocolError("Manifest artifact identity mismatch")
        self.journal = Journal(self.run_dir)
        self.contexts = None

    @contextmanager
    def _lock(self):
        with (self.run_dir / "execution.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ProtocolError("Another process holds this experiment's execution lock") from error
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def verify_freeze(self):
        frozen = self.manifest["freeze"]
        if frozen["environment"] != _environment():
            raise ProtocolError("Frozen package/runtime environment changed")
        for relative, expected in (frozen["files"] | frozen["sources"]).items():
            path, _ = _relative(self.root, relative)
            if expected["sha256"] is None:
                if path.exists():
                    raise ProtocolError(f"A previously absent frozen dependency appeared: {relative}")
            elif not path.exists() or path.stat().st_size != expected["bytes"] or sha256_file(path) != expected["sha256"]:
                raise ProtocolError(f"Frozen input changed: {relative}")
        self.journal.read()

    def _load_contexts(self):
        self.contexts = _validate_contexts([json.loads(line) for line in (self.root / CONTEXT_PATH).read_text().splitlines()])
        if _digest([row["shot_id"] for row in self.contexts]) != self.manifest["freeze"]["release_ids_sha256"]:
            raise ProtocolError("Release population identity changed")
        return self.contexts

    def _rows(self, games):
        rows = self.contexts if self.contexts is not None else self._load_contexts()
        return [row for game in games for row in rows if row["game_id"] == game]

    def _events(self, kind=None):
        events = self.journal.read()
        return [event for event in events if kind is None or event["kind"] == kind]

    def _forbid_reexecution(self, phase):
        if any(event.get("phase") == phase for event in self._events("phase_started")):
            raise ProtocolError(f"{phase} already started; never restart, reuse a consumed budget, or overwrite predictions")

    def _verify_file(self, relative, expected):
        path = self.run_dir / relative
        if not path.exists() or sha256_file(path) != expected:
            raise ProtocolError(f"Immutable artifact integrity failure: {relative}")
        return path

    def _verified_predictions(self):
        saved = self._events("prediction_saved")
        for event in saved:
            self._verify_file(event["path"], event["sha256"])
        return saved

    def _assert_label_access(self, games, phase):
        if phase == "development":
            if any(game not in DEVELOPMENT_GAMES for game in games):
                raise GateClosed("Future targets cannot enter development")
        elif phase in ("evaluation", "scoring"):
            saved = self._verified_predictions()
            predicted = [event["game_id"] for event in saved]
            if predicted != list(EVALUATION_GAMES[:len(predicted)]):
                raise ProtocolError("Outer prediction order differs from frozen schedule")
            if phase == "scoring" and predicted != list(EVALUATION_GAMES):
                raise GateClosed("No outer performance until all five prediction files are saved and verified")
            if any(game not in DEVELOPMENT_GAMES and game not in predicted for game in games):
                raise GateClosed("Target access requires an immutable prior prediction for that game")
        else:
            raise GateClosed("Unknown label-read phase")

    def _targets(self, games, phase):
        _require_gate(self, phase)
        self._assert_label_access(games, phase)
        labels = {}
        rows = self._rows(games)
        for game in games:
            relative = _source_event_path(game)
            expected = self.manifest["freeze"]["sources"][relative]
            path = self.root / relative
            if sha256_file(path) != expected["sha256"]:
                raise ProtocolError("Event source changed before authorized label read")
            self.journal.append("label_read", phase=phase, game_id=game, source_path=relative, source_sha256=expected["sha256"])
            shots = _read_json(path)["shots"]
            game_rows = self._rows([game])
            source_labels = {}
            source_contexts = {}
            for shot in shots:
                target = parser.extract_target(shot)
                sid = target["shot_id"]
                if sid in source_labels:
                    raise ProtocolError("Duplicate source release ID; no implicit target collapse")
                source_labels[sid] = target["make"]
                source_contexts[sid] = parser.extract_context(shot)
            try:
                _binary_targets(game_rows, source_labels)
            except TargetValidityError as error:
                self.journal.append("target_validity_stop", phase=phase, game_id=game, affected_count=len(error.affected), affected=error.affected,
                                    source_path=relative, source_sha256=expected["sha256"])
                raise
            for row in game_rows:
                extracted = source_contexts[row["shot_id"]]
                if any(extracted[key] != row[key] for key in extracted):
                    raise ProtocolError("Staged release context disagrees with its hashed event source")
            labels.update(source_labels)
        try:
            _binary_targets(rows, labels)
            if set(games) == set(DEVELOPMENT_GAMES):
                # The separately staged development label file is bound, validated and
                # cross-checked, rather than silently ignored in favor of a newer source.
                staged = [json.loads(line) for line in (self.root / TARGET_PATH).read_text().splitlines()]
                staged_map = {}
                for row in staged:
                    if row["shot_id"] in staged_map:
                        raise ProtocolError("Duplicate staged development target")
                    staged_map[row["shot_id"]] = row.get("make")
                _binary_targets(rows, staged_map)
                if staged_map != labels:
                    raise ProtocolError("Staged development targets disagree with pinned event sources")
        except TargetValidityError as error:
            self.journal.append("target_validity_stop", phase=phase, affected_count=len(error.affected), affected=error.affected,
                                staged_target_sha256=self.manifest["freeze"]["files"][TARGET_PATH]["sha256"])
            raise
        return labels

    def _reserve_slot(self, phase, validation_game, candidate, training_games):
        if phase not in FIT_LIMITS or candidate not in ("C", "D"):
            raise ProtocolError("Undeclared fit")
        schedule = DEVELOPMENT_GAMES[1:] if phase == "development" else EVALUATION_GAMES
        expected_training = list(ALL_GAMES[:ALL_GAMES.index(validation_game)])
        if validation_game not in schedule or list(training_games) != expected_training:
            raise ProtocolError("Training must be the exact strictly earlier fixed games")
        slots = [event for event in self._events("fit_slot_reserved") if event["phase"] == phase]
        expected_slot = [(game, stream) for game in schedule for stream in ("C", "D")]
        if len(slots) >= FIT_LIMITS[phase] or (validation_game, candidate) != expected_slot[len(slots)]:
            raise ProtocolError("Fixed fit order/budget exhausted or violated")
        gates.record_operation(self.root, "basketball", phase, f"{validation_game}:{candidate}",
                               {"candidate": candidate, "validation_game": validation_game,
                                "training_game_ids": list(training_games), "logistic": LOGISTIC_CONFIG,
                                "artifact_id": self.artifact_id}, FIT_LIMITS[phase], kind="fixed_logistic_slot")
        return self.journal.append("fit_slot_reserved", phase=phase, validation_game=validation_game,
                                   candidate=candidate, training_game_ids=list(training_games), slot=len(slots)+1)

    def _train(self, training_games, validation_game, labels, phase):
        _require_gate(self, phase)
        rows = self._rows(training_games)
        selected_labels = {row["shot_id"]: labels[row["shot_id"]] for row in rows if row["shot_id"] in labels}
        y_all = _binary_targets(rows, selected_labels)
        eligible = [row for row in rows if _eligible(row)]
        y = np.asarray([labels[row["shot_id"]] for row in eligible], dtype=np.int64)
        prior = float((int(y_all.sum()) + 1) / (len(y_all) + 2))
        cells = {}
        for three in (0, 1):
            for distance_bin in range(4):
                cell = f"{three}:{distance_bin}"
                ys = [labels[row["shot_id"]] for row in eligible if _cell(row) == cell]
                cells[cell] = {"n": len(ys), "makes": sum(ys), "probability": (sum(ys) + 20 * prior) / (len(ys) + 20)}
        model = {"artifact_id": self.artifact_id, "phase": phase, "validation_game": validation_game,
                 "training_game_ids": list(training_games), "training_ids_sha256": _digest([row["shot_id"] for row in rows]),
                 "eligible_training_ids_sha256": _digest([row["shot_id"] for row in eligible]),
                 "training_targets_sha256": _digest(selected_labels), "recorded_training_releases": len(rows),
                 "eligible_training_releases": len(eligible), "A": {"probability": prior, "n": len(y_all), "makes": int(y_all.sum())},
                 "B": {"cells": cells, "prior_concentration": 20, "distance_edges_ft": list(CELL_EDGES)}}
        for candidate in ("C", "D"):
            _require_gate(self, phase)
            self._reserve_slot(phase, validation_game, candidate, training_games)
            prep = Preprocessor.from_training(eligible, candidate) if eligible else None
            if not eligible or len(np.unique(y)) < 2:
                status = "pooled_fallback_single_class" if eligible else "pooled_fallback_no_eligible_training"
                model[candidate] = {"status": status, "preprocessing": prep.to_dict() if prep else None,
                                    "probability": prior, "actual_estimator_fits": 0}
                self.journal.append("fit_skipped", phase=phase, validation_game=validation_game, candidate=candidate, reason=status)
                continue
            matrix = prep.transform(eligible)
            self.journal.append("estimator_fit_started", phase=phase, validation_game=validation_game, candidate=candidate,
                                preprocessing_sha256=_digest(prep.to_dict()), training_ids_sha256=model["eligible_training_ids_sha256"],
                                training_targets_sha256=_digest(y.tolist()))
            try:
                estimator = LogisticRegression(**LOGISTIC_CONFIG)
                with warnings.catch_warnings():
                    warnings.simplefilter("error", ConvergenceWarning)
                    estimator.fit(matrix, y)
                coef = np.asarray(estimator.coef_, dtype=np.float64)
                intercept = np.asarray(estimator.intercept_, dtype=np.float64)
                iterations = np.asarray(estimator.n_iter_)
                if estimator.classes_.tolist() != [0, 1] or coef.shape != (1, matrix.shape[1]) or intercept.shape != (1,) or not np.isfinite(coef).all() or not np.isfinite(intercept).all():
                    raise ProtocolError("Invalid fitted logistic parameters")
                if (iterations >= LOGISTIC_CONFIG["max_iter"]).any():
                    raise ProtocolError("Iteration cap reached; do not silently restart optimization")
                model[candidate] = {"status": "fitted", "preprocessing": prep.to_dict(), "config": LOGISTIC_CONFIG,
                                    "coef": coef[0].tolist(), "intercept": float(intercept[0]), "class_order": [0, 1],
                                    "n_iter": iterations.tolist(), "actual_estimator_fits": 1}
                self.journal.append("estimator_fit_completed", phase=phase, validation_game=validation_game,
                                    candidate=candidate, n_iter=iterations.tolist())
            except Exception as error:
                self.journal.append("estimator_fit_failed", phase=phase, validation_game=validation_game,
                                    candidate=candidate, error_type=type(error).__name__, error=str(error))
                raise
        relative = f"models/{phase}_{validation_game}.json"
        digest = _write_once(self.run_dir / relative, model)
        self.journal.append("model_saved", phase=phase, validation_game=validation_game, path=relative, sha256=digest)
        return model, relative, digest

    def develop(self):
        with self._lock():
            self.verify_freeze()
            _require_gate(self, "development")
            self._forbid_reexecution("development")
            self.journal.append("phase_started", phase="development")
            self._load_contexts()
            labels = self._targets(DEVELOPMENT_GAMES, "development")
            reports = []
            for index, game in enumerate(DEVELOPMENT_GAMES[1:], start=1):
                model, model_path, model_hash = self._train(DEVELOPMENT_GAMES[:index], game, labels, "development")
                prediction = predict(model, self._rows([game]))
                prediction.update(model_path=model_path, model_sha256=model_hash)
                relative = f"development_predictions/{game}.json"
                digest = _write_once(self.run_dir / relative, prediction)
                self.journal.append("development_prediction_saved", phase="development", game_id=game, path=relative, sha256=digest)
                reports.append({"game_id": game, "training_game_ids": list(DEVELOPMENT_GAMES[:index]),
                                "diagnostics": score_predictions(prediction["rows"], labels, require_five_games=False)})
            report = {"artifact_id": self.artifact_id, "phase": "development_complete", "folds": reports,
                      "candidates_fixed_before_diagnostics": list(CANDIDATES), "model_selection": "none; D remains designated",
                      "fit_budget": self._budget("development"), "recalibrator_fits": 0,
                      "evaluation": "still closed; requires separate approval of exact development report"}
            digest = _write_once(self.run_dir / "development_report.json", report)
            self.journal.append("development_complete", phase="development", report_path="development_report.json", report_sha256=digest)
            selection = {"schema_version": 1, "task": "basketball", "binding_sha256": self.manifest["binding_sha256"],
                         "artifact_id": self.artifact_id, "status": "fixed_design_development_complete",
                         "candidates": list(CANDIDATES), "designated_model": "D", "comparison": "D minus C",
                         "selection_performed": False, "hyperparameter_search": False, "recalibrator_fits": 0,
                         "development_report_path": str((self.run_dir / "development_report.json").relative_to(self.root)),
                         "development_report_sha256": digest, "fit_budget": self._budget("development"),
                         "outer_fit_limit": FIT_LIMITS["evaluation"]}
            selection_hash = _write_once(self.root / ARTIFACT_DIRECTORY / "SELECTION_FREEZE.json", selection)
            self.journal.append("selection_frozen", phase="development", sha256=selection_hash)
            _write_once(self.root / REPORT_DIRECTORY / self.artifact_id / "development_report.json", report)
            return report

    def _budget(self, phase):
        return {"limit": FIT_LIMITS[phase],
                "slots_consumed": sum(event.get("phase") == phase for event in self._events("fit_slot_reserved")),
                "estimator_fit_calls": sum(event.get("phase") == phase for event in self._events("estimator_fit_started")),
                "completed_estimator_fits": sum(event.get("phase") == phase for event in self._events("estimator_fit_completed")),
                "skipped_single_class_or_empty": sum(event.get("phase") == phase for event in self._events("fit_skipped"))}

    def evaluate(self):
        with self._lock():
            self.verify_freeze()
            _require_gate(self, "evaluation")
            completed = self._events("development_complete")
            if len(completed) != 1 or self._budget("development")["slots_consumed"] != FIT_LIMITS["development"]:
                raise GateClosed("All four fixed development folds must complete before evaluation")
            self._verify_file(completed[0]["report_path"], completed[0]["report_sha256"])
            self._forbid_reexecution("evaluation")
            self.journal.append("phase_started", phase="evaluation")
            self._load_contexts()
            labels = self._targets(DEVELOPMENT_GAMES, "evaluation")
            training_games = list(DEVELOPMENT_GAMES)
            for game in EVALUATION_GAMES:
                model, model_path, model_hash = self._train(training_games, game, labels, "evaluation")
                prediction = predict(model, self._rows([game]))
                prediction.update(model_path=model_path, model_sha256=model_hash)
                relative = f"evaluation_predictions/{game}.json"
                digest = _write_once(self.run_dir / relative, prediction)
                self._verify_file(relative, digest)
                self.journal.append("prediction_saved", phase="evaluation", game_id=game, path=relative, sha256=digest,
                                    model_sha256=model_hash, training_game_ids=training_games.copy())
                # No losses, residuals or candidate comparisons are computed here.
                self._verified_predictions()
                labels.update(self._targets([game], "evaluation"))
                self.journal.append("target_admitted", phase="evaluation", game_id=game,
                                    prediction_sha256=digest, targets_sha256=_digest({row["shot_id"]: labels[row["shot_id"]] for row in self._rows([game])}))
                training_games.append(game)
            self.journal.append("all_predictions_saved", phase="evaluation", prediction_hashes={str(event["game_id"]): event["sha256"] for event in self._verified_predictions()})
            return self._score_outer()

    def _score_outer(self):
        self._assert_label_access(EVALUATION_GAMES, "scoring")
        if self._budget("evaluation")["slots_consumed"] != FIT_LIMITS["evaluation"]:
            raise ProtocolError("Outer fit-slot schedule incomplete")
        saved = self._verified_predictions()
        self.journal.append("scoring_started", phase="scoring", prediction_hashes={str(event["game_id"]): event["sha256"] for event in saved})
        # Fresh label join only AFTER every immutable prediction has been verified.
        labels = self._targets(EVALUATION_GAMES, "scoring")
        rows = []
        for event in saved:
            prediction = _read_json(self._verify_file(event["path"], event["sha256"]))
            rows.extend(prediction["rows"])
        report = {"artifact_id": self.artifact_id, "phase": "evaluation_complete",
                  "prediction_sha256": {str(event["game_id"]): event["sha256"] for event in saved},
                  "diagnostics": score_predictions(rows, labels, require_five_games=True),
                  "fit_budget": self._budget("evaluation"), "development_fit_budget": self._budget("development"),
                  "recalibrator_fits": 0, "designated_model": "D regardless of result", "new_model_selection": False,
                  "claims": ["Five sampled evaluation games; exploratory, not league-wide superiority",
                             "Prior source QA inspected some later aggregate outcomes; not human-blind or prospective",
                             "Raw agreement is representation consistency, not independent physical accuracy",
                             "Retrospective release context only; no preceding-choice, player-skill or causal claim"],
                  "publication": "local_only_pending_specific_release_review"}
        digest = _write_once(self.run_dir / "evaluation_report.json", report)
        self.journal.append("evaluation_complete", phase="evaluation", report_path="evaluation_report.json", report_sha256=digest)
        destination = self.root / REPORT_DIRECTORY / self.artifact_id / "evaluation_report.json"
        _write_once(destination, report)
        return report


def _stream_scores(y, probabilities):
    """Shared implementation plus an independent direct recomputation from saved p."""
    shared = per_case_scores(y, probabilities, epsilon=LOG_EPSILON)
    p = np.asarray(probabilities, dtype=np.float64)
    clipped = np.minimum(np.maximum(p, LOG_EPSILON), 1 - LOG_EPSILON)
    independent_log = -(y * np.log(clipped) + (1 - y) * np.log(1 - clipped))
    independent_brier = np.square(p - y)
    if not np.allclose(shared["log_loss"], independent_log, rtol=0, atol=1e-12) or not np.array_equal(shared["brier"], independent_brier):
        raise ProtocolError("Independent score recomputation disagrees with shared metric implementation")
    return shared


def _candidate_summary(y, p):
    summary = classification_summary(y, p, epsilon=LOG_EPSILON, bin_edges=BIN_EDGES)
    summary['accuracy_tie_rule'] = 'argmax with class order [0,1]; exact p=0.5 ties choose class 0'
    # Report exactly five make-probability reliability bins, with low-support marks.
    summary["reliability"] = [{**item, "low_support": item["n"] < 30} for item in summary["reliability"] if item["class"] == 1]
    summary["auroc"] = float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None
    summary["auroc_status"] = "defined" if len(np.unique(y)) == 2 else "undefined_single_label_class"
    return summary


def score_predictions(prediction_rows, labels, *, require_five_games):
    """Score immutable prediction rows; caller owns phase/label-access enforcement."""
    if not prediction_rows:
        raise ProtocolError("No saved predictions to score")
    ids = [row["shot_id"] for row in prediction_rows]
    if len(ids) != len(set(ids)):
        raise ProtocolError("Duplicate saved prediction IDs")
    games = list(dict.fromkeys(row["game_id"] for row in prediction_rows))
    if require_five_games and games != list(EVALUATION_GAMES):
        raise GateClosed("Outer report requires all five fixed games in order")
    y_all = _binary_targets(prediction_rows, {shot: labels[shot] for shot in ids if shot in labels})
    masks = {"event_geometry": np.asarray([row["event_geometry_eligible"] for row in prediction_rows], dtype=bool),
             "all_releases_with_A_fallback": np.ones(len(prediction_rows), dtype=bool)}
    masks.update({key: np.asarray([row[key] for row in prediction_rows], dtype=bool) for key in QUALITY_MASKS})
    result = {"primary_cohort": "event_geometry", "primary_comparison": "D minus C", "log_loss_units": "nats per release",
              "brier": "mean squared error of saved unclipped make probability", "cohorts": {},
              "headline_confidence_interval": None, "p_value": None, "uncertainty": "Per-game and exactly five leave-one-game-out sensitivities; no refits"}
    game_array = np.asarray([row["game_id"] for row in prediction_rows])
    for cohort, mask in masks.items():
        selected = [row for row, include in zip(prediction_rows, mask) if include]
        y = y_all[mask]
        support = {"n": len(y), "makes": int(y.sum()), "excluded_from_all_releases": int((~mask).sum()),
                   "geometry_fallback_count": sum(row["geometry_fallback"] for row in selected)}
        if not len(y):
            result["cohorts"][cohort] = {**support, "status": "no_support", "candidates": {},
                                        "per_game": [{"game_id": game, "n": 0, "makes": 0, "geometry_fallback_count": 0,
                                                      "excluded": int((game_array == game).sum()), "D_minus_C": None} for game in games],
                                        "leave_one_game_out": [{"omitted_game_id": game, "n": 0, "log_loss": None, "brier": None} for game in games] if require_five_games else []}
            continue
        probabilities = {candidate: np.asarray([row["probabilities"][candidate] for row in selected], dtype=np.float64) for candidate in CANDIDATES}
        scores = {candidate: _stream_scores(y, p) for candidate, p in probabilities.items()}
        differences = {metric: scores["D"][metric] - scores["C"][metric] for metric in ("log_loss", "brier")}
        grouped = game_array[mask]
        per_game = []
        for game in games:
            gm = grouped == game
            game_rows = [row for row in selected if row["game_id"] == game]
            per_game.append({"game_id": game, "n": int(gm.sum()), "makes": int(y[gm].sum()),
                             "geometry_fallback_count": sum(row["geometry_fallback"] for row in game_rows),
                             "excluded": int(((game_array == game) & ~mask).sum()),
                             "D_minus_C": {metric: float(values[gm].mean()) for metric, values in differences.items()} if gm.any() else None,
                             "candidates": {candidate: {**{metric: float(values[gm].mean()) for metric, values in scores[candidate].items()},
                                                         "auroc": float(roc_auc_score(y[gm], probabilities[candidate][gm])) if len(np.unique(y[gm])) == 2 else None,
                                                         "fallback_count": sum(row["fallback"][candidate] for row in game_rows)} for candidate in CANDIDATES} if gm.any() else {}})
        paired = {metric: float(values.mean()) for metric, values in differences.items()}
        # If any game's support is empty, do not silently change the equal-game denominator.
        equal_game = {metric: float(np.mean([item["D_minus_C"][metric] for item in per_game])) for metric in differences} if all(item["n"] for item in per_game) else None
        leave_out = []
        if require_five_games:
            for game in EVALUATION_GAMES:
                keep = grouped != game
                leave_out.append({"omitted_game_id": game, "n": int(keep.sum()),
                                  **{metric: float(values[keep].mean()) if keep.any() else None for metric, values in differences.items()}})
        result["cohorts"][cohort] = {**support, "status": "scored", "candidates": {candidate: _candidate_summary(y, p) for candidate, p in probabilities.items()},
                                    "D_minus_C_shot_weighted": paired, "D_minus_C_equal_game_weighted": equal_game,
                                    "equal_game_status": "defined" if equal_game is not None else "undefined_at_least_one_game_has_no_support",
                                    "per_game": per_game, "leave_one_game_out": leave_out}
    primary = result["cohorts"]["event_geometry"]
    if require_five_games and primary["status"] == "scored":
        favorable = sum(item["D_minus_C"] is not None and item["D_minus_C"]["log_loss"] < 0 for item in primary["per_game"])
        paired = primary["D_minus_C_shot_weighted"]
        result["exploratory_practical_yardstick"] = {"minimum_log_loss_improvement": .005, "no_brier_worsening": True,
                                                   "minimum_games_with_negative_log_loss_difference": 4,
                                                   "games_with_negative_difference": favorable,
                                                   "met": paired["log_loss"] <= -.005 and paired["brier"] <= 0 and favorable >= 4,
                                                   "population_effect_established": False}
    return result


def develop(root=ROOT, *, run_dir):
    return Runner(root, run_dir).develop()


def evaluate(root=ROOT, *, run_dir):
    return Runner(root, run_dir).evaluate()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("phase", choices=("prepare", "develop", "evaluate", "predict"))
    cli.add_argument("--root", type=Path, default=ROOT)
    cli.add_argument("--run-dir", type=Path)
    cli.add_argument("--model", type=Path)
    cli.add_argument("--contexts", type=Path)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    if args.phase == "prepare":
        result = prepare(args.root, run_dir=args.run_dir)
    elif args.phase == "predict":
        if not args.model or not args.contexts or not args.output:
            cli.error("predict requires --model, --contexts and --output")
        result = predict(args.model, [json.loads(line) for line in args.contexts.read_text().splitlines()])
        digest = _write_once(args.output, result)
        result = {"prediction_path": str(args.output), "sha256": digest, "rows": len(result["rows"])}
    else:
        if not args.run_dir:
            cli.error("develop/evaluate requires an immutable --run-dir from prepare")
        report = develop(args.root, run_dir=args.run_dir) if args.phase == "develop" else evaluate(args.root, run_dir=args.run_dir)
        result = {"artifact_id": report["artifact_id"], "phase": report["phase"], "fit_budget": report["fit_budget"]}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
