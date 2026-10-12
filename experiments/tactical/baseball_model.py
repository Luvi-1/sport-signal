"""Fixed, role-gated Retrosheet pitch-sequence experiment.

Importing this module does not read source rows. Preparation projects only
metadata, eligibility and prefix features. Labels are decoded by one private,
role-checked reader, after the exact source/code approval has been verified.
No command grants approval or overwrites an existing run.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import csv
from dataclasses import dataclass
from datetime import datetime
import fcntl
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import time
import uuid
import warnings
import zipfile

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.sparse import csr_matrix
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

from . import baseball as parser
from . import gates
from .metrics import classification_summary, per_case_scores

ROOT = Path(__file__).resolve().parents[2]
TASK = "baseball"
PROTOCOL = "docs/tactical/BASEBALL_PROTOCOL_DRAFT.md"
BASE = "artifacts/tactical/baseball"
SUMMARY = "reports/tactical/baseball/summary.json"
VALIDATION = "reports/tactical/baseball/validation.json"
ADJUDICATION = "reports/tactical/baseball/reference_adjudication.json"
ADJUDICATION_SHA256 = "9854b5876623fe45f183b2ebf4402092b711d234162873e43b22bdf7bba6f3a1"
SAMPLE = "data/tactical/baseball/reference_sample"
MEMBERSHIP_SHA256 = "3d5b30035926ad1c9c94e319de1dfdd9f120a270c76a65b38f5bddf4f7b421c9"
CODE_PATHS = (
    "experiments/tactical/baseball_model.py", "experiments/tactical/baseball.py",
    "experiments/tactical/baseball_reference_sample.py", "experiments/tactical/gates.py",
    "experiments/tactical/metrics.py",
)
TARGETS = ("swing", "contact_given_swing")
ROLES = ("initial", "selection", "calibration", "test")
PROCEDURES = ("constant", "context_table", "history_table", "context_logistic", "sequence_logistic")
CS = (.03, .3, 3.)
SEED = 20261011
RELIABILITY_EDGES = tuple(np.arange(11, dtype=np.float64) / 10)
FIT_LIMIT = 38
EXPECTED_GAMES = {"initial": 2430, "selection": 1261, "calibration": 1167, "boundary_exclusion": 1, "test": 2430}
EXPECTED_ROWS = {2023: (717944, 713338, 338840), 2024: (709510, 704671, 337665), 2025: (710079, 705223, 336314)}
CONTEXT = ("count", "hand_pair", "hand_method", "outs", "bases", "batting_side", "inning_band", "score_band")
SEQUENCE = CONTEXT + ("delivery_band", "lag1", "lag2", "lag3")
LOGISTIC_CONFIG = dict(penalty="l2", solver="lbfgs", fit_intercept=True, class_weight=None,
                       max_iter=1000, tol=1e-8, warm_start=False, random_state=SEED)
CALIBRATION_CONFIG = {"method": "L-BFGS-B", "start": [1., 0.], "bounds": [[0., 10.], [-10., 10.]],
                      "maxiter": 200, "ftol": 1e-12, "penalty": 1e-4, "logit_clip": 1e-6}
METRIC_DEFINITION = {"log_loss": "mean -[y log(p)+(1-y) log(1-p)]; natural logarithms",
                     "log_loss_clip_epsilon": 1e-12, "brier": "mean((original_probability-y)^2)",
                     "brier_units": "dimensionless", "accuracy": "predict 1 when p >= 0.5",
                     "reliability": "10 equal-width bins; left-closed/right-open; final bin includes 1"}


class ProtocolError(ValueError):
    """A changed contract, cohort or numerical operation must stop the run."""


class ResourceLimitError(RuntimeError):
    pass


def _digest(value):
    return hashlib.sha256(gates.canonical_bytes(value)).hexdigest()


def _read_json(path):
    return json.loads(Path(path).read_text())


def _path(root, name):
    return gates.resolve(Path(root), f"{BASE}/{name}")


def _write_once(path, value):
    """Atomic no-clobber publication; even equal existing output is not rewritten."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    try:
        with temporary.open("xb") as stream:
            stream.write(gates.canonical_bytes(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return gates.digest_file(path)


@contextmanager
def _gzip_once(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    try:
        with temporary.open("xb") as binary:
            with gzip.GzipFile(filename="", mode="wb", fileobj=binary, mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8") as stream:
                    yield stream
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _json_spans(text):
    """Locate top-level value spans without decoding any value (including targets)."""
    decoder = json.JSONDecoder()
    pos = 0
    length = len(text)
    def whitespace(i):
        while i < length and text[i].isspace():
            i += 1
        return i
    pos = whitespace(pos)
    if pos >= length or text[pos] != "{":
        raise ProtocolError("Derivative row must be an object")
    pos += 1
    spans = {}
    while True:
        pos = whitespace(pos)
        if pos < length and text[pos] == "}":
            pos = whitespace(pos + 1)
            if pos != length:
                raise ProtocolError("Trailing derivative bytes")
            return spans
        key, end = decoder.raw_decode(text, pos)
        if not isinstance(key, str) or key in spans:
            raise ProtocolError("Duplicate/nonstring derivative field")
        pos = whitespace(end)
        if pos >= length or text[pos] != ":":
            raise ProtocolError("Invalid derivative object")
        start = pos = whitespace(pos + 1)
        depth = 0
        quoted = escaped = False
        while pos < length:
            ch = text[pos]
            if quoted:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    quoted = False
            elif ch == '"':
                quoted = True
            elif ch in "[{":
                depth += 1
            elif ch in "]}":
                if depth == 0:
                    break
                depth -= 1
            elif ch == "," and depth == 0:
                break
            pos += 1
        if pos == start or quoted or depth != 0 or pos >= length:
            raise ProtocolError("Truncated derivative value")
        spans[key] = (start, pos)
        if text[pos] == ",":
            pos += 1
        elif text[pos] != "}":
            raise ProtocolError("Invalid derivative delimiter")


def _project(text, fields):
    spans = _json_spans(text)
    if not set(fields).issubset(spans):
        raise ProtocolError("Missing projected derivative field")
    return {name: json.loads(text[slice(*spans[name])]) for name in fields}


def _date(value):
    if not isinstance(value, str):
        raise ProtocolError("Date must be explicit")
    normalized = value.replace("/", "").replace("-", "")
    if not re.fullmatch(r"\d{8}", normalized):
        raise ProtocolError("Date must have an explicit four-digit year, month and day")
    datetime.strptime(normalized, "%Y%m%d")
    return normalized


def _role(year, minimum, maximum):
    if year not in (2023, 2024, 2025):
        raise ProtocolError("Unapproved season")
    minimum, maximum = _date(minimum), _date(maximum)
    if minimum > maximum or minimum[:4] != str(year) or maximum[:4] != str(year):
        raise ProtocolError("Game date span is reversed or outside its declared source season")
    if year == 2023:
        return "initial"
    if year == 2025:
        return "test"
    if year != 2024:
        raise ProtocolError("Unapproved season")
    if maximum <= "20240630":
        return "selection"
    if minimum >= "20240701":
        return "calibration"
    return "boundary_exclusion"


def _union(spans, gid, minimum, maximum):
    minimum, maximum = _date(minimum), _date(maximum)
    if minimum > maximum:
        raise ProtocolError("Reversed event-date interval")
    old = spans.get(gid, (minimum, maximum))
    spans[gid] = (min(old[0], minimum), max(old[1], maximum))


def _game_spans(root, year):
    """Read only source game/date columns and raw date/suspension headers."""
    spans = {}
    with zipfile.ZipFile(parser.source_path(root, year, "plays")) as archive:
        with archive.open(f"{year}plays.csv") as stream:
            for chunk in pd.read_csv(stream, usecols=["gid", "date", "gametype"], dtype=str, chunksize=100000):
                for row in chunk.loc[chunk.gametype.eq("regular")].itertuples(index=False):
                    # Named attributes avoid depending on source column ordering.
                    _union(spans, row.gid, row.date, row.date)
    raw_spans = {}
    with zipfile.ZipFile(parser.source_path(root, year, "eve")) as archive:
        for name in sorted(archive.namelist()):
            if not re.search(r"\.EV[ANFR]$", name.upper()):
                continue
            gid = None
            with archive.open(name) as raw:
                for line in io.TextIOWrapper(raw, encoding="utf-8-sig"):
                    # Never hand play strings, actors or outcomes to the CSV decoder.
                    if line.startswith("id,"):
                        gid = next(csv.reader([line]))[1]
                    elif line.startswith("info,date,"):
                        date = next(csv.reader([line]))[2]
                        _union(raw_spans, gid, date, date)
                    elif line.startswith("com,") and "suspended," in line:
                        comment = next(csv.reader([line]))[1]
                        if comment.startswith("suspended,"):
                            date = comment.split(",")[1]
                            _union(raw_spans, gid, date, date)
    if set(raw_spans) != set(spans):
        raise ProtocolError("Raw/parsed source game-date coverage differs")
    for gid, interval in raw_spans.items():
        _union(spans, gid, *interval)
    with gzip.open(root / f"data/tactical/baseball/{year}_pitches.jsonl.gz", "rt") as stream:
        for line in stream:
            lineage = _project(line, ("lineage",))["lineage"]
            if lineage["gid"] not in spans:
                raise ProtocolError("Derivative has a game absent from source dates")
            _union(spans, lineage["gid"], lineage["event_date_min"], lineage["event_date_max"])
    return spans


def _features(features):
    if set(features) != set(parser.FEATURE_FIELDS):
        raise ProtocolError("Parser prefix-feature allowlist changed")
    f = features
    if type(f["balls"]) is not int or type(f["strikes"]) is not int or not 0 <= f["balls"] <= 3 or not 0 <= f["strikes"] <= 2:
        raise ProtocolError("Eligible count is invalid; never clip counts")
    if f["batter_hand"] not in ("L", "R") or f["pitcher_hand"] not in ("L", "R"):
        raise ProtocolError("Eligible hand is unknown; never fill from future rows")
    methods = {"roster": "roster", "raw_adjustment": "adjusted", "switch_hitter_opposite_pitcher_inference": "switch"}
    if f["batter_hand_method"] not in methods:
        raise ProtocolError("Unrecognized hand-method flag")
    if f["outs"] not in (0, 1, 2) or f["batting_side"] not in (0, 1) or type(f["inning"]) is not int or f["inning"] < 1:
        raise ProtocolError("Invalid eligible game context")
    if any(type(f[key]) is not bool for key in ("on_first", "on_second", "on_third")):
        raise ProtocolError("Base occupancy must be boolean")
    score = f["batting_score_difference"]
    index = f["pa_delivered_pitch_index"]
    if type(score) is not int or type(index) is not int or index < 1:
        raise ProtocolError("Invalid score/index context")
    history = list(f["previous_three_pitch_outcomes"])
    allowed = (parser.PITCH_CODES - parser.ADMIN) | {"BUNT_IN_PLAY"}
    if len(history) != min(index - 1, 3) or any(value not in allowed for value in history):
        raise ProtocolError("Delivery lags violate the prefix contract")
    lags = list(reversed(history)) + ["START"] * (3 - len(history))
    if f["previous_pitch_outcome"] != lags[0]:
        raise ProtocolError("Immediately preceding outcome disagrees with suffix")
    inning = f["inning"]
    return (f"{f['balls']}-{f['strikes']}", f["batter_hand"] + f["pitcher_hand"], methods[f["batter_hand_method"]],
            str(f["outs"]), "".join(str(int(f[key])) for key in ("on_first", "on_second", "on_third")),
            str(f["batting_side"]), "1-3" if inning <= 3 else "4-6" if inning <= 6 else "7-9" if inning <= 9 else "10+",
            "<=-5" if score <= -5 else ">=5" if score >= 5 else str(score), str(index) if index < 7 else "7+", *lags)


def _identity(row):
    l, f = row["lineage"], row["features"]
    if not isinstance(l["gid"], str) or not re.fullmatch(r"[A-Z]{3}\d{8}\d", l["gid"]):
        raise ProtocolError("Invalid game identity")
    if type(l["pa"]) is not int or l["pa"] < 1 or type(f["pa_delivered_pitch_index"]) is not int or f["pa_delivered_pitch_index"] < 1:
        raise ProtocolError("Invalid PA/delivery identity")
    return f"{l['gid']}|{l['pa']}|{f['pa_delivered_pitch_index']}"


def _source_contract(root):
    """Reconcile pinned sources and accepted QA, without reading target rows."""
    root = Path(root).resolve()
    if gates.digest_file(root / ADJUDICATION) != ADJUDICATION_SHA256:
        raise PermissionError("The exact accepted reference adjudication is missing or changed")
    accepted = _read_json(root / ADJUDICATION)
    if (accepted.get("status") != "accepted_for_frozen_source_representation" or accepted.get("selected_pas") != 133
            or accepted.get("reviewed_deliveries") != 641 or accepted.get("unexplained_discrepancies") != 0
            or accepted.get("independent_adjudication_completed") is not True):
        raise PermissionError("Reference acceptance does not satisfy the frozen prerequisite")
    summary = _read_json(root / SUMMARY)
    validation = _read_json(root / VALIDATION)
    expected = {"parser_sha256": gates.digest_file(root / "experiments/tactical/baseball.py"),
                "protocol_sha256": gates.digest_file(root / PROTOCOL), "summary_sha256": gates.digest_file(root / SUMMARY)}
    if any(accepted["provenance"].get(key) != value or validation.get(key) != value for key, value in expected.items()):
        raise ProtocolError("Parser/protocol/summary differs from accepted source review")
    if summary.get("parser_sha256") != expected["parser_sha256"] or validation.get("tests_passed") != 35:
        raise ProtocolError("Parser validation prerequisite changed")
    if accepted["provenance"]["selection_code_sha256"] != gates.digest_file(root / "experiments/tactical/baseball_reference_sample.py"):
        raise ProtocolError("Frozen reference-selection implementation changed")
    data = {ADJUDICATION: ADJUDICATION_SHA256, SUMMARY: expected["summary_sha256"], VALIDATION: gates.digest_file(root / VALIDATION)}
    evidence = {"membership.json": MEMBERSHIP_SHA256, "packet_manifest.json": accepted["packet_manifest_sha256"],
                "machine_checks.json": accepted["mechanical_checks_sha256"], "independent_adjudication.json": accepted["local_adjudication_record_sha256"]}
    for name, digest in evidence.items():
        relative = f"{SAMPLE}/{name}"
        if gates.digest_file(root / relative) != digest:
            raise ProtocolError("Frozen reference evidence changed")
        data[relative] = digest
    if accepted["membership_sha256"] != MEMBERSHIP_SHA256:
        raise ProtocolError("Reference sample membership changed")
    packet = _read_json(root / SAMPLE / "packet_manifest.json")
    for item in packet["files"]:
        for kind in ("json", "markdown"):
            filename = Path(item[kind]).name
            relative = f"{SAMPLE}/windows/{filename}"
            # The accepted packet may contain its original absolute workspace;
            # source identity is the fixed relative window and its pinned bytes.
            if not str(item[kind]).endswith(relative) or not re.fullmatch(r"[A-Z]{3}\d{9}_pa\d+\.(json|md)", filename):
                raise ProtocolError("Unexpected reference-window identity")
            if gates.digest_file(root / relative) != item[f"{kind}_sha256"]:
                raise ProtocolError("Frozen reference window changed")
            data[relative] = item[f"{kind}_sha256"]
    seasons = {item["season"]: item for item in summary["seasons"]}
    validations = {item["season"]: item for item in validation["seasons"]}
    if set(seasons) != {2023, 2024, 2025} or set(validations) != set(seasons):
        raise ProtocolError("All three pinned seasons and validation records are required")
    for year in (2023, 2024, 2025):
        d = seasons[year]["denominators"]
        if tuple(d[key] for key in ("delivered_pitch_symbols", "eligible_swing", "eligible_contact_given_swing")) != EXPECTED_ROWS[year] or validations[year]["status"] != "passed":
            raise ProtocolError("Reviewed source eligibility denominators changed")
        for kind in ("eve", "plays"):
            source = parser.source_path(root, year, kind)
            parser.validate_source(source, year, kind)
            data[gates.relative_path(root, source)] = parser.SOURCE_PINS[source.name]
            sidecar = source.with_suffix(".zip.source.json")
            data[gates.relative_path(root, sidecar)] = gates.digest_file(sidecar)
        for kind, record in seasons[year]["local_derivatives"].items():
            relative = f"data/tactical/baseball/{year}_{kind}.jsonl.gz"
            if gates.digest_file(root / relative) != record["sha256"]:
                raise ProtocolError("Source-derived input bytes changed")
            data[relative] = record["sha256"]
    return data


@dataclass(frozen=True)
class Cohort:
    target: str
    roles: tuple
    ids: np.ndarray
    games: np.ndarray
    values: np.ndarray
    role_labels: np.ndarray

    def __len__(self):
        return len(self.ids)


@dataclass(frozen=True)
class Labels:
    target: str
    roles: tuple
    cohort_sha256: str
    binding_sha256: str
    values: np.ndarray


def _checked_labels(root, labels, cohort, permit):
    if (not isinstance(labels, Labels) or labels.target != cohort.target or labels.roles != cohort.roles
            or labels.cohort_sha256 != _cohort_hash(cohort) or labels.binding_sha256 != permit["binding_sha256"]):
        raise PermissionError("Labels do not belong to this authorized binding/role/cohort")
    return _binary(labels.values, len(cohort))


def _cohort_hash(cohort):
    h = hashlib.sha256()
    for array in (cohort.ids, cohort.games, cohort.role_labels, *cohort.values.T):
        strings = np.asarray(array, dtype=str)
        if np.any(np.char.str_len(strings) > 48):
            raise ProtocolError("Unexpectedly long frozen context field")
        h.update(np.asarray(strings, dtype="S48").tobytes())
    return h.hexdigest()


def _load_role_file(path, role, target):
    ids, games, values = [], [], []
    with gzip.open(path, "rt") as stream:
        for line in stream:
            row = json.loads(line)  # prepared contexts contain no target namespace
            if set(row) != {"id", "game", "values", "eligible"}:
                raise ProtocolError("Prepared context schema differs")
            if row["eligible"][target]:
                ids.append(row["id"])
                games.append(row["game"])
                values.append(row["values"])
    matrix = np.asarray(values, dtype=object).reshape((-1, len(SEQUENCE)))
    return Cohort(target, (role,), np.asarray(ids), np.asarray(games), matrix, np.full(len(ids), role))


def prepare(root=ROOT):
    """Freeze label-free contexts/membership and source fingerprints; no approval."""
    root = Path(root).resolve()
    if _path(root, "run_binding.json").exists():
        return gates.verify_binding(root, TASK, include_data=True)
    data = _source_contract(root)
    _write_once(_path(root, "prepare_started.json"), {"task": TASK, "labels_decoded": False})
    game_manifest = []
    game_roles = {}
    for year in (2023, 2024, 2025):
        for gid, (minimum, maximum) in sorted(_game_spans(root, year).items()):
            role = _role(year, minimum, maximum)
            game_roles[gid] = role
            game_manifest.append({"gid": gid, "season": year, "date_min": minimum, "date_max": maximum, "role": role})
    if dict(Counter(item["role"] for item in game_manifest)) != EXPECTED_GAMES:
        raise ProtocolError("Conservative whole-game fold counts differ from the protocol")
    if [item["gid"] for item in game_manifest if item["role"] == "boundary_exclusion"] != ["BOS202406260"]:
        raise ProtocolError("Unexpected boundary-excluded game")
    from contextlib import ExitStack
    counts = Counter()
    with ExitStack() as stack:
        outputs = {role: stack.enter_context(_gzip_once(_path(root, f"prepared/{role}.jsonl.gz"))) for role in ROLES}
        membership = stack.enter_context(_gzip_once(_path(root, "prepared/membership.jsonl.gz")))
        for year in (2023, 2024, 2025):
            seen = set()
            with gzip.open(root / f"data/tactical/baseball/{year}_pitches.jsonl.gz", "rt") as stream:
                for line in stream:
                    row = _project(line, ("lineage", "features", "eligibility", "qa_exclusions"))
                    identity = _identity(row)
                    if identity in seen:
                        raise ProtocolError("Duplicate pitch identity")
                    seen.add(identity)
                    eligibility = row["eligibility"]
                    if set(eligibility) != set(TARGETS) or any(type(v) is not bool for v in eligibility.values()) or (eligibility[TARGETS[1]] and not eligibility[TARGETS[0]]):
                        raise ProtocolError("Target-specific eligibility schema changed")
                    l = row["lineage"]
                    role = game_roles[l["gid"]]
                    meta = {"id": identity, "gid": l["gid"], "pa": l["pa"], "delivery_index": row["features"]["pa_delivered_pitch_index"],
                            "event_date_min": l["event_date_min"], "event_date_max": l["event_date_max"], "event_date": l["event_date"],
                            "role": role, "eligible": eligibility, "qa_exclusions": row["qa_exclusions"]}
                    membership.write(gates.canonical_bytes(meta).decode() + "\n")
                    counts[year, "delivered"] += 1
                    for target in TARGETS:
                        counts[year, target] += int(eligibility[target])
                    if eligibility["swing"]:
                        if row["qa_exclusions"] or l["event_date"] is None:
                            raise ProtocolError("An excluded/undated delivery is marked eligible")
                        values = _features(row["features"])
                        if role in outputs:
                            context = {"id": identity, "game": l["gid"], "values": values, "eligible": eligibility}
                            outputs[role].write(gates.canonical_bytes(context).decode() + "\n")
            if tuple(counts[year, key] for key in ("delivered", *TARGETS)) != EXPECTED_ROWS[year]:
                raise ProtocolError("Projected eligibility denominators changed")
    prepared = {"schema_version": 1, "task": TASK, "game_membership": game_manifest, "roles": {}, "notice": parser.NOTICE, "source_hashes": dict(parser.SOURCE_PINS),
                "features": list(SEQUENCE), "operation_budget": FIT_LIMIT, "labels_decoded": False}
    for role in ROLES:
        relative = f"{BASE}/prepared/{role}.jsonl.gz"
        data[relative] = gates.digest_file(root / relative)
        prepared["roles"][role] = {"path": relative, "sha256": data[relative], "targets": {}}
        for target in TARGETS:
            cohort = _load_role_file(root / relative, role, target)
            prepared["roles"][role]["targets"][target] = {"n": len(cohort), "games": len(np.unique(cohort.games)), "cohort_sha256": _cohort_hash(cohort)}
            del cohort
    membership_path = f"{BASE}/prepared/membership.jsonl.gz"
    data[membership_path] = gates.digest_file(root / membership_path)
    prepared["membership_sha256"] = data[membership_path]
    prepared_path = f"{BASE}/PREPARED.json"
    data[prepared_path] = _write_once(root / prepared_path, prepared)
    return gates.prepare_binding(root, TASK, PROTOCOL, CODE_PATHS, data,
                                 {"operation_budget": FIT_LIMIT, "game_counts": EXPECTED_GAMES,
                                  "membership_sha256": prepared["membership_sha256"], "adjudication_sha256": ADJUDICATION_SHA256})


def _guard(root, phase):
    if phase not in ("develop", "calibrate", "predict", "evaluate"):
        raise PermissionError("Unsupported runner phase")
    return gates.require_stage(Path(root), TASK, "evaluation" if phase in ("predict", "evaluate") else "development")


def _prepared(root):
    return _read_json(_path(root, "PREPARED.json"))


def _load_cohort(root, roles, target):
    if target not in TARGETS or not roles or any(role not in ROLES for role in roles):
        raise ProtocolError("Undeclared target/role")
    prepared = _prepared(root)
    pieces = []
    for role in roles:
        item = prepared["roles"][role]
        if gates.digest_file(Path(root) / item["path"]) != item["sha256"]:
            raise ProtocolError("Prepared prefix contexts changed")
        pieces.append(_load_role_file(Path(root) / item["path"], role, target))
    cohort = Cohort(target, tuple(roles), np.concatenate([p.ids for p in pieces]), np.concatenate([p.games for p in pieces]),
                    np.concatenate([p.values for p in pieces]), np.concatenate([p.role_labels for p in pieces]))
    _assert_cohort(root, cohort, target, tuple(roles))
    return cohort


def _assert_cohort(root, cohort, target, roles):
    if cohort.target != target or cohort.roles != tuple(roles) or len(set(cohort.ids)) != len(cohort) or not len(cohort):
        raise ProtocolError("Wrong/empty/duplicate target-specific cohort")
    prepared = _prepared(root)
    start = 0
    for role in roles:
        expected = prepared["roles"][role]["targets"][target]
        stop = start + expected["n"]
        part = Cohort(target, (role,), cohort.ids[start:stop], cohort.games[start:stop], cohort.values[start:stop], cohort.role_labels[start:stop])
        if not np.all(part.role_labels == role) or _cohort_hash(part) != expected["cohort_sha256"]:
            raise ProtocolError("Features, identities, ordering or source role differ from frozen membership")
        start = stop
    if start != len(cohort):
        raise ProtocolError("Extra target rows beyond the frozen cohort")


def _verified_artifact(root, name, expected):
    path = _path(root, name)
    if gates.digest_file(path) != expected:
        raise PermissionError(f"Frozen artifact changed: {name}")
    return _read_json(path)


def _development(root):
    complete = _read_json(_path(root, "DEVELOPMENT.json"))
    _verified_artifact(root, "SELECTED.json", complete["selection_sha256"])
    for target in TARGETS:
        for name in PROCEDURES:
            _verified_artifact(root, f"models/{target}/{name}.json", complete["models"][target][name])
    return complete


def _selection_freeze(root):
    freeze = _read_json(_path(root, "SELECTION_FREEZE.json"))
    if freeze["binding_sha256"] != gates.verify_binding(root, TASK, include_data=True)["binding_sha256"]:
        raise PermissionError("Selection freeze belongs to a different binding")
    _verified_artifact(root, "DEVELOPMENT.json", freeze["development_sha256"])
    _development(root)
    for target in TARGETS:
        for name in PROCEDURES:
            _verified_artifact(root, f"calibration/{target}/{name}.json", freeze["calibrators"][target][name])
    return freeze


def _prediction_evidence(root):
    sealed = _read_json(_path(root, "PREDICTIONS_SEALED.json"))
    if sealed["selection_freeze_sha256"] != gates.digest_file(_path(root, "SELECTION_FREEZE.json")):
        raise PermissionError("Predictions were made under a different selection freeze")
    if set(sealed["targets"]) != set(TARGETS):
        raise PermissionError("Both target prediction sets must be complete before target access")
    for target in TARGETS:
        item = sealed["targets"][target]
        if set(item["procedures"]) != set(PROCEDURES) or item["file"] != f"predictions/{target}.npz" or gates.digest_file(_path(root, item["file"])) != item["sha256"]:
            raise PermissionError("Incomplete/changed prediction set")
        expected_keys = {"ids", "games"} | {f"{name}__{kind}" for name in PROCEDURES for kind in ("raw", "calibrated")
                                          if item["procedures"][name][f"{kind}_available"]}
        with np.load(_path(root, item["file"]), allow_pickle=False) as saved:
            if set(saved.files) != expected_keys or len(saved["ids"]) != item["n"] or saved["games"].shape != (item["n"],):
                raise PermissionError("Sealed prediction columns/denominators are incomplete")
            for key in expected_keys - {"ids", "games"}:
                values = saved[key]
                if values.shape != (item["n"],) or not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
                    raise PermissionError("Invalid sealed prediction probabilities")
    return sealed


def _labels(root, cohort, phase):
    """Only this function may deserialize current-pitch labels from row sources."""
    permit = _guard(root, phase)
    allowed = {"develop": {("initial",), ("selection",), ("initial", "selection")},
               "calibrate": {("calibration",)}, "evaluate": {("test",)}}
    if cohort.roles not in allowed.get(phase, set()):
        raise PermissionError("Target-reader role is not authorized for this phase")
    _assert_cohort(root, cohort, cohort.target, cohort.roles)
    if phase == "calibrate":
        _development(root)  # all finalists have been fixed and refitted first
    if phase == "evaluate":
        _selection_freeze(root)
        _prediction_evidence(root)  # all ten procedures sealed before any 2025 target
    years = {"initial": 2023, "selection": 2024, "calibration": 2024, "test": 2025}
    wanted = {identity: i for i, identity in enumerate(cohort.ids)}
    y = np.full(len(cohort), -1, dtype=np.int64)
    for year in sorted({years[role] for role in cohort.roles}):
        with gzip.open(Path(root) / f"data/tactical/baseball/{year}_pitches.jsonl.gz", "rt") as stream:
            for line in stream:
                metadata = _project(line, ("lineage", "features"))
                identity = _identity(metadata)
                if identity not in wanted:
                    continue  # rejected role/row never reaches target JSON decoder
                index = wanted[identity]
                if y[index] != -1:
                    raise ProtocolError("Duplicate source label identity")
                value = _project(line, ("target",))["target"][cohort.target]
                if type(value) is not int or value not in (0, 1):
                    raise ProtocolError("Eligible target is unknown/nonbinary; do not drop or impute")
                y[index] = value
    if (y < 0).any():
        raise ProtocolError("Missing target from frozen row membership")
    y.setflags(write=False)
    return Labels(cohort.target, cohort.roles, _cohort_hash(cohort), permit["binding_sha256"], y)


def candidates():
    return [{"name": name, "family": name} for name in PROCEDURES[:3]] + [
        {"name": f"{family}_C{c:g}", "family": family, "C": c} for family in PROCEDURES[3:] for c in CS]


def planned_operations():
    return [f"initial:{target}:{item['name']}" for target in TARGETS for item in candidates()] + [
        f"refit:{target}:{name}" for target in TARGETS for name in PROCEDURES] + [
        f"calibrate:{target}:{name}" for target in TARGETS for name in PROCEDURES]


def _select(records, family):
    expected = [item for item in candidates() if item["family"] == family]
    block = [item for item in records if item["config"]["family"] == family]
    if [item["config"] for item in block] != expected:
        raise ProtocolError("Reduced, reordered or enlarged candidate grid")
    complete = [item for item in block if item["status"] == "fitted"]
    if not complete:
        return {"name": family, "family": "context_table", "fallback_for": family, "comparison_available": False}
    best = min(item["log_loss"] for item in complete)
    selected = min((item for item in complete if item["log_loss"] <= best + 1e-6), key=lambda item: item["config"]["C"])
    return {"name": family, "family": family, "C": selected["config"]["C"], "comparison_available": True}


def _selected(root):
    selected = _read_json(_path(root, "SELECTED.json"))
    if set(selected["designated"]) != set(TARGETS) or set(selected["candidates"]) != set(TARGETS):
        raise PermissionError("Selection must include both targets")
    for target in TARGETS:
        records = selected["candidates"][target]
        if [record["config"] for record in records] != candidates():
            raise PermissionError("Selection did not retain the complete fixed grid")
        for record in records:
            _verified_artifact(root, f"candidates/{target}/{record['config']['name']}.json", record["model_sha256"])
        expected = {name: {"name": name, "family": name} for name in PROCEDURES[:3]}
        expected.update({family: _select(records, family) for family in PROCEDURES[3:]})
        if selected["designated"][target] != expected:
            raise PermissionError("Persisted finalists violate the fixed grid/tie/fallback rule")
    return selected


def _fit_config(root, target, phase, name, config):
    if target not in TARGETS:
        raise PermissionError("Unapproved target")
    if phase == "initial":
        expected = next((item for item in candidates() if item["name"] == name), None)
    elif phase == "refit" and name in PROCEDURES:
        expected = _selected(root)["designated"][target][name]
    else:
        expected = None
    if expected is None or config != expected:
        raise PermissionError("Fit is outside the exact approved grid/finalists")
    return expected


def _reserve(root, phase, target, name, config):
    operation = f"{phase}:{target}:{name}"
    if operation not in planned_operations():
        raise PermissionError("Unplanned operation")
    return gates.record_operation(root, TASK, "development", operation, config, FIT_LIMIT, kind=phase)


def _binary(y, n):
    y = np.asarray(y)
    if y.shape != (n,) or not np.issubdtype(y.dtype, np.integer) or not np.isin(y, (0, 1)).all():
        raise ProtocolError("Binary labels and full eligible denominators are required")
    return y


def _context_keys(values):
    return [f"{row[0]}|{row[1]}" for row in values]


def _table(values, y, family):
    constant = float((int(y.sum()) + 1) / (len(y) + 2))
    state = {"constant": constant}
    if family == "constant":
        return state
    counts = defaultdict(lambda: [0, 0])
    history = defaultdict(lambda: [0, 0])
    for key, row, label in zip(_context_keys(values), values, y):
        counts[key][0] += 1
        counts[key][1] += int(label)
        hkey = f"{key}|{row[9]}"
        history[hkey][0] += 1
        history[hkey][1] += int(label)
    state["contexts"] = {key: (success + 100 * constant) / (n + 100) for key, (n, success) in counts.items()}
    if family == "history_table":
        state["history"] = {key: (success + 100 * state["contexts"][key.rsplit("|", 1)[0]]) / (n + 100)
                            for key, (n, success) in history.items()}
    return state


def _matrix(values, categories):
    width = sum(len(levels) for levels in categories)
    row_indices, col_indices = [], []
    offset = 0
    for column, levels in enumerate(categories):
        lookup = {value: i + offset for i, value in enumerate(levels)}
        matched = [(row, lookup[value]) for row, value in enumerate(values[:, column]) if value in lookup]
        row_indices.extend(row for row, _ in matched)
        col_indices.extend(col for _, col in matched)
        offset += len(levels)
    return csr_matrix((np.ones(len(row_indices), dtype=np.float64), (row_indices, col_indices)), shape=(len(values), width), dtype=np.float64)


def _predict(model, values):
    """Pure local inference; no source access, fitting, eligibility or target use."""
    if model["status"] != "fitted":
        return None
    family = model["config"]["family"]
    state = model["state"]
    if family == "constant":
        result = np.full(len(values), state["constant"], dtype=np.float64)
    elif family in ("context_table", "history_table"):
        result = []
        for key, row in zip(_context_keys(values), values):
            parent = state["contexts"].get(key, state["constant"])
            result.append(state.get("history", {}).get(f"{key}|{row[9]}", parent) if family == "history_table" else parent)
        result = np.asarray(result, dtype=np.float64)
    elif family in PROCEDURES[3:]:
        matrix = _matrix(values, state["categories"])
        result = expit(matrix @ np.asarray(state["coef"], dtype=np.float64) + state["intercept"])
    else:
        raise ProtocolError("Unrecognized persisted model family")
    if not np.isfinite(result).all() or ((result < 0) | (result > 1)).any():
        raise ProtocolError("Invalid probability; do not silently renormalize")
    return result


def _support(values, games):
    cells = defaultdict(lambda: [0, set()])
    for key, game in zip(_context_keys(values), games):
        cells[key][0] += 1
        cells[key][1].add(game)
    return {key: {"opportunities": n, "games": len(gids), "display_allowed": n >= 200 and len(gids) >= 20}
            for key, (n, gids) in cells.items()}


def _unseen(model, values):
    if model["status"] != "fitted" or "categories" not in model["state"]:
        return None
    result = {}
    for index, (name, levels) in enumerate(zip(model["state"]["features"], model["state"]["categories"])):
        allowed = set(levels)
        n = sum(value not in allowed for value in values[:, index])
        result[name] = {"n": len(values), "unseen": int(n), "unseen_rate": float(n / len(values))}
    return result


def _fit(root, cohort, y, phase, name, config):
    permit = _guard(root, "develop")
    _fit_config(root, cohort.target, phase, name, config)
    roles = ("initial",) if phase == "initial" else ("initial", "selection")
    _assert_cohort(root, cohort, cohort.target, roles)
    y = _checked_labels(root, y, cohort, permit)
    _reserve(root, phase, cohort.target, name, {"procedure": config, "logistic": LOGISTIC_CONFIG if "logistic" in config["family"] else None,
                                              "cohort_sha256": _cohort_hash(cohort), "target_sha256": hashlib.sha256(y.tobytes()).hexdigest()})
    result = {"status": "fitted", "target": cohort.target, "phase": phase, "config": config, "n": len(cohort),
              "training_roles": list(roles), "training_cohort_sha256": _cohort_hash(cohort), "notice": parser.NOTICE, "source_hashes": dict(parser.SOURCE_PINS),
              "support": _support(cohort.values, cohort.games)}
    family = config["family"]
    if family in PROCEDURES[:3]:
        result["state"] = _table(cohort.values, y, family)
        return result
    names = CONTEXT if family == "context_logistic" else SEQUENCE
    encoder = OneHotEncoder(handle_unknown="ignore", drop=None, min_frequency=None, sparse_output=True, dtype=np.float64)
    try:
        x = encoder.fit_transform(cohort.values[:, :len(names)])
        estimator = LogisticRegression(C=config["C"], **LOGISTIC_CONFIG)
        with threadpool_limits(limits=2), warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            estimator.fit(x, y)
        if list(estimator.classes_) != [0, 1] or np.any(estimator.n_iter_ >= LOGISTIC_CONFIG["max_iter"]):
            raise ConvergenceWarning("Class contract/iteration cap failed")
        coef = np.asarray(estimator.coef_, dtype=np.float64)
        intercept = np.asarray(estimator.intercept_, dtype=np.float64)
        if coef.shape != (1, x.shape[1]) or intercept.shape != (1,) or not np.isfinite(coef).all() or not np.isfinite(intercept).all():
            raise ProtocolError("Invalid estimator parameters")
        result["state"] = {"features": list(names), "categories": [levels.tolist() for levels in encoder.categories_],
                           "coef": coef[0].tolist(), "intercept": float(intercept[0]), "n_iter": np.asarray(estimator.n_iter_).tolist(),
                           "one_hot": {"handle_unknown": "ignore", "drop": None, "min_frequency": None, "dtype": "float64", "sparse_output": True}}
        native = estimator.predict_proba(x)[:, 1]
        restored = _predict(result, cohort.values)
        if not np.allclose(native, restored, atol=1e-12, rtol=0):
            raise ProtocolError("Saved-parameter inference parity failed")
        result["inference_parity_max_absolute_error"] = float(np.max(np.abs(native - restored)))
    except (ConvergenceWarning, ValueError) as exc:
        if isinstance(exc, ProtocolError):
            raise
        result.update(status="failed", error_type=type(exc).__name__, error=str(exc), state=None)
    return result


def _summary(y, probability, target):
    result = classification_summary(y, probability, epsilon=1e-12, bin_edges=RELIABILITY_EDGES)
    result["accuracy"] = float(np.mean((probability >= .5) == y))
    result["auroc"] = float(roc_auc_score(y, probability)) if len(np.unique(y)) == 2 else None
    result["reliability"] = [row for row in result["reliability"] if row["class"] == 1]
    result.update(target=target, metric_definition=METRIC_DEFINITION,
                  log_loss_units="nats per eligible delivered pitch" if target == "swing" else "nats per eligible swing",
                  denominator="all identical frozen target-specific eligible row IDs")
    return result


@contextmanager
def _phase(root, name):
    directory = _path(root, "")
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "runner.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _guard(root, name)  # every public numerical entry checks full source hashes
        _write_once(directory / f"{name}_started.json", {"phase": name, "started_utc": datetime.now().astimezone().isoformat()})
        try:
            yield
        except Exception as exc:
            _write_once(directory / f"{name}_failed.json", {"phase": name, "error_type": type(exc).__name__,
                "error": str(exc), "retry_allowed": False})
            raise
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


@contextmanager
def _resources(root, phase):
    previous = 0.
    if phase == "calibrate":
        previous = _read_json(_path(root, "resources_develop.json"))["wall_seconds"]
    maximum = 1800. if phase == "evaluate" else 21600. - previous
    if maximum <= 0:
        raise ResourceLimitError("Complete selection/refit/calibration wall-time cap exhausted")
    start, cpu = time.monotonic(), time.process_time()
    old_limit = resource.getrlimit(resource.RLIMIT_AS)
    soft = min(8 * 1024**3, old_limit[0]) if old_limit[0] != resource.RLIM_INFINITY else 8 * 1024**3
    old_handler = signal.getsignal(signal.SIGALRM)
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    def timeout(_signum, _frame):
        raise ResourceLimitError("Frozen wall-clock cap reached; no reduced-data retry")
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, maximum)
    resource.setrlimit(resource.RLIMIT_AS, (soft, old_limit[1]))
    status = "failed"
    try:
        with threadpool_limits(limits=2):
            yield
        status = "complete"
    finally:
        resource.setrlimit(resource.RLIMIT_AS, old_limit)
        signal.setitimer(signal.ITIMER_REAL, *old_timer)
        signal.signal(signal.SIGALRM, old_handler)
        _write_once(_path(root, f"resources_{phase}.json"), {"phase": phase, "status": status,
            "wall_seconds": time.monotonic() - start, "cpu_seconds": time.process_time() - cpu,
            "peak_resident_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "memory_cap_bytes": 8 * 1024**3, "threads": 2, "seed": SEED, "runtime": gates.runtime_fingerprint()})


def develop(root=ROOT):
    root = Path(root).resolve()
    with _phase(root, "develop"), _resources(root, "develop"):
        records, designated = {}, {}
        for target in TARGETS:
            train = _load_cohort(root, ("initial",), target)
            selection = _load_cohort(root, ("selection",), target)
            y = _labels(root, train, "develop")
            selection_y = _labels(root, selection, "develop")
            records[target] = []
            for config in candidates():
                fitted = _fit(root, train, y, "initial", config["name"], config)
                model_sha = _write_once(_path(root, f"candidates/{target}/{config['name']}.json"), fitted)
                record = {"config": config, "status": fitted["status"], "model_sha256": model_sha, "n": len(selection)}
                if fitted["status"] == "fitted":
                    probability = _predict(fitted, selection.values)
                    record.update(log_loss=float(per_case_scores(selection_y.values, probability, epsilon=1e-12)["log_loss"].mean()),
                                  metric_definition=METRIC_DEFINITION,
                                  log_loss_units="nats per eligible delivered pitch" if target == "swing" else "nats per eligible swing",
                                  denominator="all identical frozen selection target-specific row IDs", unseen_categories=_unseen(fitted, selection.values))
                else:
                    record["failure"] = fitted["error"]
                records[target].append(record)
            designated[target] = {name: {"name": name, "family": name} for name in PROCEDURES[:3]}
            designated[target].update({family: _select(records[target], family) for family in PROCEDURES[3:]})
            del train, selection, y, selection_y
        selected = {"task": TASK, "designated": designated, "candidates": records, "selection_attempts": 18,
                    "tie_tolerance_nats": 1e-6, "tie_breaker": "smaller C", "metric_definition": METRIC_DEFINITION,
                    "notice": parser.NOTICE, "source_hashes": dict(parser.SOURCE_PINS), "evaluation_labels_read": False}
        selection_sha = _write_once(_path(root, "SELECTED.json"), selected)
        models = {}
        for target in TARGETS:
            refit = _load_cohort(root, ("initial", "selection"), target)
            y = _labels(root, refit, "develop")
            models[target] = {}
            for name in PROCEDURES:
                fitted = _fit(root, refit, y, "refit", name, designated[target][name])
                models[target][name] = _write_once(_path(root, f"models/{target}/{name}.json"), fitted)
            del refit, y
        result = {"task": TASK, "selection_sha256": selection_sha, "models": models, "selection_attempts": 18,
                  "refit_attempts": 10, "calibration_pending": True, "notice": parser.NOTICE, "source_hashes": dict(parser.SOURCE_PINS)}
        _write_once(_path(root, "DEVELOPMENT.json"), result)
        return result


def _calibration_objective(theta, z, y):
    a, b = theta
    linear = a * z + b
    residual = expit(linear) - y
    objective = np.mean(np.logaddexp(0., linear) - y * linear) + 1e-4 * ((a - 1)**2 + b**2)
    gradient = np.array([np.mean(residual * z) + 2e-4 * (a - 1), np.mean(residual) + 2e-4 * b])
    return float(objective), gradient


def _fit_calibrator(root, cohort, y, name, model):
    permit = _guard(root, "calibrate")
    _assert_cohort(root, cohort, cohort.target, ("calibration",))
    development = _development(root)
    if name not in PROCEDURES or _digest(model) != _digest(_verified_artifact(root, f"models/{cohort.target}/{name}.json", development["models"][cohort.target][name])):
        raise PermissionError("Calibrator does not reference the exact refitted finalist")
    y = _checked_labels(root, y, cohort, permit)
    _reserve(root, "calibrate", cohort.target, name, {"calibrator": CALIBRATION_CONFIG,
               "model_sha256": development["models"][cohort.target][name], "cohort_sha256": _cohort_hash(cohort)})
    result = {"config": CALIBRATION_CONFIG, "target": cohort.target, "procedure": name, "n": len(cohort),
              "training_roles": ["calibration"], "status": "unavailable_raw_model", "available": False,
              "notice": parser.NOTICE, "source_hashes": dict(parser.SOURCE_PINS)}
    raw = _predict(model, cohort.values)
    if raw is None:
        return result
    clipped = np.clip(raw, 1e-6, 1 - 1e-6)
    z = np.log(clipped) - np.log1p(-clipped)
    with threadpool_limits(limits=2):
        fitted = minimize(_calibration_objective, np.array([1., 0.]), args=(z, y), method="L-BFGS-B", jac=True,
                          bounds=((0., 10.), (-10., 10.)), options={"maxiter": 200, "ftol": 1e-12})
    a, b = map(float, fitted.x)
    finite = np.isfinite([a, b, fitted.fun]).all()
    boundary = bool(finite and (min(abs(a), abs(a - 10), abs(b + 10), abs(b - 10)) <= 1e-8))
    available = bool(fitted.success and finite and 0 <= a <= 10 and -10 <= b <= 10 and not boundary)
    result.update(status="fitted" if available else "boundary" if boundary else "failed", available=available,
                  a=a if np.isfinite(a) else None, b=b if np.isfinite(b) else None,
                  converged=bool(fitted.success), boundary=boundary, iterations=int(fitted.nit),
                  objective=float(fitted.fun) if np.isfinite(fitted.fun) else None, message=str(fitted.message))
    return result


def _calibrated(raw, calibrator):
    if raw is None or not calibrator["available"]:
        return None
    p = np.clip(raw, 1e-6, 1 - 1e-6)
    return expit(calibrator["a"] * (np.log(p) - np.log1p(-p)) + calibrator["b"])


def calibrate(root=ROOT):
    root = Path(root).resolve()
    with _phase(root, "calibrate"), _resources(root, "calibrate"):
        development = _development(root)
        calibrators = {}
        for target in TARGETS:
            cohort = _load_cohort(root, ("calibration",), target)
            y = _labels(root, cohort, "calibrate")
            calibrators[target] = {}
            for name in PROCEDURES:
                model = _verified_artifact(root, f"models/{target}/{name}.json", development["models"][target][name])
                fitted = _fit_calibrator(root, cohort, y, name, model)
                calibrators[target][name] = _write_once(_path(root, f"calibration/{target}/{name}.json"), fitted)
            del cohort, y
        result = {"schema_version": 1, "task": TASK, "binding_sha256": gates.verify_binding(root, TASK, include_data=True)["binding_sha256"],
                  "development_sha256": gates.digest_file(_path(root, "DEVELOPMENT.json")), "calibrators": calibrators,
                  "designated_procedures": list(PROCEDURES), "development_attempts": FIT_LIMIT,
                  "primary_comparison": "calibrated sequence minus context logistic swing log loss",
                  "claim_threshold_nats": -.001, "bootstrap_replicates": 2000, "seed": SEED,
                  "notice": parser.NOTICE, "source_hashes": dict(parser.SOURCE_PINS), "evaluation_labels_read": False}
        _write_once(_path(root, "SELECTION_FREEZE.json"), result)
        return result


def _save_npz_once(path, **arrays):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    try:
        with temporary.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return gates.digest_file(path)


def predict(root=ROOT):
    """Seal every designated 2025 procedure before permitting 2025 target access."""
    root = Path(root).resolve()
    with _phase(root, "predict"):
        freeze = _selection_freeze(root)
        development = _development(root)
        output = {"task": TASK, "selection_freeze_sha256": gates.digest_file(_path(root, "SELECTION_FREEZE.json")),
                  "targets": {}, "evaluation_labels_read": False, "notice": parser.NOTICE, "source_hashes": dict(parser.SOURCE_PINS)}
        for target in TARGETS:
            cohort = _load_cohort(root, ("test",), target)
            arrays = {"ids": cohort.ids, "games": cohort.games}
            procedures = {}
            for name in PROCEDURES:
                model = _verified_artifact(root, f"models/{target}/{name}.json", development["models"][target][name])
                calibration = _verified_artifact(root, f"calibration/{target}/{name}.json", freeze["calibrators"][target][name])
                raw = _predict(model, cohort.values)
                calibrated = _calibrated(raw, calibration)
                for kind, values in (("raw", raw), ("calibrated", calibrated)):
                    if values is not None:
                        arrays[f"{name}__{kind}"] = values
                procedures[name] = {"raw_available": raw is not None, "calibrated_available": calibrated is not None,
                                    "model_status": model["status"], "calibration_status": calibration["status"],
                                    "fallback": model["config"].get("fallback_for"), "unseen_categories": _unseen(model, cohort.values)}
            filename = f"predictions/{target}.npz"
            sha = _save_npz_once(_path(root, filename), **arrays)
            output["targets"][target] = {"file": filename, "sha256": sha, "n": len(cohort),
                                         "cohort_sha256": _cohort_hash(cohort), "procedures": procedures}
            del cohort, arrays
        _write_once(_path(root, "PREDICTIONS_SEALED.json"), output)
        return output


def _slices(cohort, y, arrays):
    result = []
    for field in ("count", "hand_pair", "inning_band", "bases", "score_band"):
        column = SEQUENCE.index(field)
        for value in sorted(set(cohort.values[:, column])):
            mask = cohort.values[:, column] == value
            result.append({"field": field, "value": value, "n": int(mask.sum()), "games": len(np.unique(cohort.games[mask])),
                           "exploratory": True, "procedures": {name: _summary(y[mask], probability[mask], cohort.target)
                                                                   for name, probability in arrays.items()}})
    return result


def _paired_comparisons(differences, games):
    """One seeded game-resampling stream per target, shared by all comparisons."""
    if not differences:
        return {}
    ids, inverse = np.unique(np.asarray(games), return_inverse=True)
    if not len(ids):
        raise ProtocolError("No evaluation games for paired uncertainty")
    names = list(differences)
    counts = np.bincount(inverse).astype(np.float64)
    sums = np.column_stack([np.bincount(inverse, weights=differences[name]) for name in names])
    draws = np.empty((2000, len(names)), dtype=np.float64)
    rng = np.random.default_rng(SEED)
    for index in range(2000):
        chosen = rng.integers(0, len(ids), len(ids))
        draws[index] = sums[chosen].sum(axis=0) / counts[chosen].sum()
    intervals = np.quantile(draws, [.025, .975], axis=0, method="linear")
    return {name: {"difference": float(np.mean(differences[name])), "interval": intervals[:, i].tolist(),
                   "groups": len(ids), "cases": len(games), "replicates": 2000, "seed": SEED,
                   "weighting": "pitch-weighted whole-game resampling", "confidence": .95,
                   "interval_method": "paired game percentile; numpy quantile method=linear",
                   "game_order": "lexicographic", "shared_game_draws": True}
            for i, name in enumerate(names)}


def evaluate(root=ROOT):
    root = Path(root).resolve()
    with _phase(root, "evaluate"), _resources(root, "evaluate"):
        _selection_freeze(root)
        sealed = _prediction_evidence(root)
        report = {"task": TASK, "metric_definition": METRIC_DEFINITION, "targets": {}, "notice": parser.NOTICE, "source_hashes": dict(parser.SOURCE_PINS),
                  "limitations": ["Retrospective, conditional current-category cohort; 2025 performance-blind after source QA",
                                  "Association only; no unthrown-pitch strategy, physical mechanics or causal recommendation",
                                  "Bootstrap omits model-selection and data-bias uncertainty; raw rows and weights stay local"]}
        for target in TARGETS:
            cohort = _load_cohort(root, ("test",), target)
            evidence = sealed["targets"][target]
            if evidence["n"] != len(cohort) or evidence["cohort_sha256"] != _cohort_hash(cohort):
                raise ProtocolError("Prediction/target denominator mismatch")
            with np.load(_path(root, evidence["file"]), allow_pickle=False) as saved:
                if not np.array_equal(saved["ids"], cohort.ids) or not np.array_equal(saved["games"], cohort.games):
                    raise ProtocolError("Prediction identities/order differ from frozen target cohort")
                arrays = {key: saved[key] for key in saved.files if key not in ("ids", "games")}
            y = _labels(root, cohort, "evaluate").values
            result = {"n": len(cohort), "games": len(np.unique(cohort.games)), "procedures": {},
                      "eligibility_sha256": evidence["cohort_sha256"], "denominator": "all identical frozen target-specific eligible row IDs"}
            for name in PROCEDURES:
                result["procedures"][name] = {**evidence["procedures"][name],
                    **{kind: _summary(y, arrays[f"{name}__{kind}"], target) if f"{name}__{kind}" in arrays else None for kind in ("raw", "calibrated")}}
            comparison = {"available": False, "useful_improvement_claim": False}
            names = ("sequence_logistic", "context_logistic")
            differences = {}
            if all(f"{name}__calibrated" in arrays and not evidence["procedures"][name]["fallback"] for name in names):
                differences["sequence_minus_context"] = per_case_scores(y, arrays["sequence_logistic__calibrated"], epsilon=1e-12)["log_loss"] - per_case_scores(y, arrays["context_logistic__calibrated"], epsilon=1e-12)["log_loss"]
            for kind in ("raw", "calibrated"):
                if all(f"{name}__{kind}" in arrays for name in ("history_table", "context_table")):
                    differences[f"history_minus_context_{kind}"] = per_case_scores(y, arrays[f"history_table__{kind}"], epsilon=1e-12)["log_loss"] - per_case_scores(y, arrays[f"context_table__{kind}"], epsilon=1e-12)["log_loss"]
            intervals = _paired_comparisons(differences, cohort.games)
            if "sequence_minus_context" in intervals:
                interval = intervals.pop("sequence_minus_context")
                comparison.update(available=True, **interval)
                comparison["useful_improvement_claim"] = bool(target == "swing" and interval["difference"] <= -.001 and interval["interval"][1] < 0)
            comparison["primary"] = target == "swing"
            comparison["direction"] = "calibrated sequence logistic minus calibrated context logistic"
            comparison["units"] = "nats per eligible delivered pitch" if target == "swing" else "nats per eligible swing"
            comparison["denominator"] = "all identical frozen evaluation target-specific row IDs"
            result["comparison"] = comparison
            result["secondary_history_comparisons"] = {name: {**interval, "exploratory": True,
                "useful_improvement_claim": False, "units": comparison["units"], "denominator": comparison["denominator"]}
                for name, interval in intervals.items()}
            result["slices"] = _slices(cohort, y, arrays)
            report["targets"][target] = result
            del cohort, y, arrays
        _write_once(_path(root, "EVALUATION.json"), report)
        return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("phase", choices=("prepare", "develop", "calibrate", "predict", "evaluate"))
    cli.add_argument("--root", type=Path, default=ROOT)
    args = cli.parse_args()
    result = globals()[args.phase](args.root)
    print(json.dumps({"task": TASK, "phase": args.phase, "status": "complete", "binding_sha256": result.get("binding_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
