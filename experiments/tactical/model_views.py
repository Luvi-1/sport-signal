"""Strict aggregate-only presentation contract; no numerical execution or approval.

This module reads only an independently installed review, bound run metadata and
completed aggregate reports. It never imports runners, opens target caches,
loads models, changes a gate, or writes a report. See MODEL_VIEWS.md.
"""
from __future__ import annotations

import hashlib
import json
import math
import errno
import os
from pathlib import Path
import re
import stat

SCHEMA_VERSION = 1
MAX_BYTES = 2_000_000
FINAL_REPORT_MAX_BYTES = 8 * 1024 * 1024
REVIEW = "docs/tactical/INDEPENDENT_FINAL_MODEL_VIEW_REVIEW.json"
SNAPSHOT_REVIEW = "docs/tactical/INDEPENDENT_AGGREGATE_SNAPSHOT_REVIEW.json"
NUMERICAL_REVIEW = "docs/tactical/INDEPENDENT_FINAL_NUMERICAL_REVIEW.json"
GLOBAL_FREEZE = "artifacts/tactical/EVALUATION_FREEZE.json"
VIEW_DIRECTORY = "reports/tactical/model_views"
IMPLEMENTATION = ("experiments/tactical/model_views.py", "experiments/tactical/workbench.py",
                  "experiments/tactical/web/app.js", "experiments/tactical/web/index.html",
                  "experiments/tactical/web/style.css")
# Final display review binds the code actually imported by this process, as well
# as its on-disk copy. Restart after source edits; a reviewed alternate --root
# cannot substitute different copied implementation bytes for the live server.
LIVE_ROOT = Path(__file__).resolve().parents[2]
RUNNING_CODE_SHA256 = {path: hashlib.sha256((LIVE_ROOT / path).read_bytes()).hexdigest()
                       for path in IMPLEMENTATION if path.endswith(".py")}
TASKS = ("soccer", "basketball", "baseball", "football", "tennis",
         "baseball_mechanics", "tennis_execution")
SOURCE_QA = ("Performance-blind after source QA. Some later-period annotations or "
             "marginal outcomes were already inspected; not prospective or fully human-blind evidence.")
NO_CAUSAL = "Predictive association only; no causal coaching, medical, readiness or individual-ranking claim."


def _variants(names, kinds=("raw", "calibrated")):
    return [f"{name}_{kind}" for name in names for kind in kinds]


# All display text is code-controlled. Reports cannot supply IDs, prose, paths,
# feature weights, free-form records, individual labels or executable artifacts.
CONTRACTS = {
    "soccer": dict(name="Soccer", unit="recorded non-penalty shot", population="FA Women's Super League",
        targets={"goal": "Goal conditional on a recorded valid non-penalty shot"},
        cohorts={"full": "All eligible recorded shots", "matched": "Identical shots with the required recorded defensive geometry"},
        models=["full_A_raw", "full_B_raw", "matched_A_raw", "matched_B_raw", *_variants(["full_G", "matched_G", "matched_R"])],
        factors=["G: distance, goal opening, lateral geometry, broad body part and restart context", "R: G plus recorded goalkeeper/opponent geometry on matched cases", "A/B: constant and geometry-cell references"],
        unavailable=["Unseen defenders and complete defensive positions", "Intended target and unchosen actions", "Joint mechanics and verified readiness"],
        design="Fixed season-based development and calibration; later-season evaluation. Full and matched denominators remain separate.",
        caveats=["Source coordinates are a standardized 120 × 80 grid, not metres", "Selective freeze-frame geometry does not measure all defenders"],
        bins=[0, .05, .1, .2, .4, .6, 1], sparse=50, classes=["goal"], epsilon=1e-6),
    "basketball": dict(name="Basketball", unit="recorded field-goal release", population="Ten sampled Liga ACB games",
        targets={"make": "Made field goal conditional on a recorded release, including fouled misses"},
        cohorts={"event_geometry": "Eligible event-geometry releases", "all_releases_with_A_fallback": "All recorded releases with prespecified A fallback",
                 "raw_consistent_0p1ft": "Representation agreement within 0.1 ft", "raw_consistent_1ft": "Representation agreement within 1 ft",
                 "raw_consistent_and_directly_detected_0p1ft": "Directly detected and representation agreement within 0.1 ft"},
        models=["A", "B", "C", "D"],
        factors=["A/B: constant and distance/three-point cell references", "C: distance, bearing, three-point flag and shot clock", "D: C plus nearest-defender distance and limited interaction"],
        unavailable=["Unchosen possession options", "Independent physical tracking accuracy", "Joint mechanics and general NBA transfer"],
        design="Five-game prequential evaluation: each next game's predictions saved before its labels update later training. No new selection or recalibrator.",
        caveats=["Only five sampled evaluation games; exploratory evidence", "No headline confidence interval or p-value; aggregate leave-one-game-out sensitivity only", "Coordinates and defender distance are feet; representation consistency is not physical accuracy"],
        bins=[0, .2, .4, .6, .8, 1], sparse=30, classes=["make"], epsilon=1e-6),
    "baseball": dict(name="Baseball", unit="eligible delivered pitch or eligible swing", population="MLB regular-season Retrosheet records",
        targets={"swing": "Swing conditional on an eligible delivered pitch", "contact_given_swing": "Contact conditional on an eligible swing"},
        cohorts={"eligible": "Identical frozen target-specific eligible cases"},
        models=_variants(["constant", "context_table", "history_table", "context_logistic", "sequence_logistic"]),
        factors=["Context: count, hands, outs, bases, batting side, inning and score", "Sequence: context plus delivery band and three previous observed pitch-outcome codes", "Constant/context/history-table references"],
        unavailable=["Pitch type, trajectory and unthrown alternatives", "Batting stance and joint mechanics in Retrosheet", "Pitch intention"],
        design="2023 fitting, first-half-2024 selection, second-half-2024 calibration, frozen 2025 evaluation. Swing and contact denominators differ.",
        caveats=["Pitch-outcome sequence is not pitch-type sequence", "Contact evidence is conditional on a swing; no strategy or causal interpretation"],
        bins=[i / 10 for i in range(11)], sparse=30, classes=["positive"], epsilon=1e-12),
    "football": dict(name="American football", unit="eligible competitive run/pass play", population="NFL regular-season competitive plays with a validated charting join",
        targets={"dropback": "Realized dropback, including sacks and scrambles"}, cohorts={"eligible": "Identical eligible charting-joined plays"},
        models=["constant_raw", *_variants(["context", "logistic_A", "logistic_B", "logistic_C", "tree_A", "tree_B", "tree_C"])],
        factors=["A: down, distance, field position, clocks, score and timeouts", "B: A plus formation and offensive/defensive personnel", "C: B plus motion, box count, backfield and starting hash"],
        unavailable=["Original play call and blocking assignments", "Verified live charting latency", "Joint angles and leverage"],
        design="Retrospective at-snap physical setup; 2023 fit, split-2024 selection/calibration and frozen 2025 evaluation.",
        caveats=["Realized dropback is not original play-call intent", "Game-cluster uncertainty omits repeated-team dependence; week sensitivity has few clusters"],
        bins=[i * .1 for i in range(11)], sparse=30, classes=["dropback"], epsilon=1e-6),
    "tennis": dict(name="Tennis", unit="eligible charted first or second serve", population="Volunteer-charted professional singles matches",
        targets={"A1_m": "First-serve direction · men's corpus", "A1_w": "First-serve direction · women's corpus",
                 "A2_m": "Second-serve direction · men's corpus", "A2_w": "Second-serve direction · women's corpus"},
        cohorts={"eligible": "Identical eligible cases within this serve/corpus cell"},
        models=_variants(["B0", "B1", "L", "N"], ("uncalibrated", "calibrated")),
        factors=["B0: global, surface and serve-side reference", "B1: past server directional history with fixed shrinkage", "L/N: score/context plus past server/returner histories and support"],
        unavailable=["Verified historical ingestion/publication time", "Professional intended aim, spin and continuous positions", "Joint mechanics and readiness"],
        design="Four separate serve/corpus cells; assumed source date + 21 days strictly before use. Full-2025 cutoff: 22 January 2026.",
        caveats=["21-day availability is an assumption, not verified live availability", "No current rally suffix or current outcome input", "Class order wide, body, T; four primary comparisons use 98.75% intervals"],
        bins=[i * .1 for i in range(11)], sparse=20, classes=["wide", "body", "T"], epsilon=1e-12),
    "baseball_mechanics": dict(name="Baseball laboratory companion", unit="adult paired-context machine-hitting swing", population="82 adults; 571 paired-context swings",
        targets={"exit_velocity": "Recorded ball exit velocity"}, cohorts={"adult_paired": "Fixed adult-only paired cohort; 571 swings from 82 athletes"},
        models=["mean", "context", "augmented"],
        factors=["Context: pitch speed (mph), descent angle (degrees), zone offsets (inches)", "Augmented: context plus four source-defined foot-plant body angles (degrees)", "Foot plant is the 100% bodyweight lead-force threshold"],
        unavailable=["Verified elapsed event timing and pre-pitch stance", "Future-session or professional transfer", "Causal technique, injury, health and readiness effects"],
        design="Five-outer/four-inner athlete-grouped procedure. Unseen-athlete estimate, not an untouched chronological lockbox.",
        caveats=["Adult-only fixed cohort; one session per athlete", "Macro RMSE is the mean of within-athlete RMSEs", "Source-processed angles retain anatomical/sign definitions; marker and Blast bat speed are distinct measurements"],
        bins=[], sparse=10, classes=[], epsilon=None),
    "tennis_execution": dict(name="Tennis laboratory companion", unit="recorded non-let practice attempt", population="Eight collegiate players; ages and individual consent unverified",
        targets={"joint_execution": "Joint observed-data net/bounce outcome conditional on a recorded non-let"},
        cohorts={"nonlet": "548 non-lets = 437 observed bounces + 111 net-censored attempts; 19 lets excluded"},
        models=["B0", "B1"], factors=["B0: pooled net/bounce distribution around stated target", "B1: fixed serve-period/region cells with pooled shrinkage", "Stated target and tape-derived bounce coordinates are meters; radar speed is mph but is not this model's input"],
        unavailable=["Unobserved bounce positions for net attempts", "Body/joint mechanics", "All-attempt pre-serve forecast and verified adult status"],
        design="Eight leave-player-out comparisons with fixed hurdle models. Conditional non-let denominator; nets remain censored, never coordinate-imputed.",
        caveats=["All eight individual and pseudonymous player/fold records are suppressed", "Eight players, shared sessions and overlapping training sets limit inference", "Ellipse coverage is a diagnostic, not established calibration", "Location density uses square meters; its NLL is not classification log loss"],
        bins=[], sparse=10, classes=[], epsilon=None),
}

METRICS = {
    "log_loss": ("Log loss", "nats per eligible case", "lower"),
    "brier": ("Brier", "dimensionless", "lower"),
    "accuracy": ("Accuracy", "fraction of eligible cases", "higher"),
    "auroc": ("AUROC", "dimensionless", "higher"),
    "match_macro_log_loss": ("Match-macro log loss", "nats; equal match weight", "lower"),
    "server_macro_log_loss": ("Server-macro log loss", "nats; equal server weight", "lower"),
    "macro_MAE": ("Equal-athlete MAE", "mph", "lower"),
    "macro_RMSE": ("Mean within-athlete RMSE", "mph", "lower"),
    "row_MAE": ("Swing-weighted MAE", "mph", "lower"),
    "row_RMSE": ("Swing-weighted RMSE", "mph", "lower"),
}
for _metric, _unit in (("joint_NLL", "nats per non-let; bounce density per m²"),
                      ("net_Brier", "dimensionless; all non-lets"),
                      ("location_NLL", "nats; observed-bounce density per m²"),
                      ("euclidean_error", "meters; observed bounces only"),
                      ("ellipse90_covered", "fraction of observed bounces")):
    for _weight in ("attempt_weighted", "equal_player"):
        METRICS[f"{_metric}_{_weight}"] = (f"{_metric.replace('_', ' ')} · {_weight.replace('_', ' ')}", _unit,
                                          "diagnostic" if _metric == "ellipse90_covered" else "lower")

METRIC_STATUS = {"reported", "not_reported", "insufficient_support", "undefined_single_class", "procedure_unavailable"}
UNCERTAINTY = {
    "soccer": {"paired_match_bootstrap"}, "basketball": {"five_game_leave_one_out"},
    "baseball": {"paired_game_bootstrap"}, "football": {"paired_game_bootstrap", "paired_week_bootstrap"},
    "tennis": {"paired_match_bootstrap", "tournament_year_bootstrap", "four_week_block_bootstrap"},
    "baseball_mechanics": {"paired_athlete_bootstrap"}, "tennis_execution": {"paired_player_bootstrap"},
}
CLUSTER_UNITS = {"soccer": "matches", "basketball": "games", "baseball": "games", "football": "games",
                 "tennis": "matches", "baseball_mechanics": "athletes", "tennis_execution": "players"}
CRITERIA = {
    "soccer": "Practical yardstick: calibrated matched R minus G log loss ≤ −0.005 nats/shot and no Brier worsening; not a statistical superiority claim.",
    "basketball": "Exploratory practical yardstick: D minus C log loss ≤ −0.005 nats/release, no Brier worsening and favorable loss in at least four of five games; no population effect established.",
    "baseball": "Primary swing criterion: calibrated sequence minus context log loss ≤ −0.001 nats/pitch and paired 95% interval wholly below zero. Contact and history comparisons remain secondary.",
    "football": "Primary criterion: calibrated logistic C minus A log loss ≤ −0.005 nats/play, both game and week interval upper bounds below zero, and Brier worsening ≤ 0.001.",
    "tennis": "Each cell's designated main versus B1 criterion: log loss ≤ −0.005 nats/serve and a 98.75% match-cluster interval wholly below zero; B1 itself cannot establish improvement over B1.",
    "baseball_mechanics": "Primary criterion: augmented minus context equal-athlete MAE ≤ −0.5 mph and paired athlete 95% interval wholly below zero.",
    "tennis_execution": "Practical yardstick: B1 minus B0 equal-player joint NLL ≤ −0.02 nats/non-let; this threshold alone is not a statistical superiority claim.",
}
NUMERICAL_CHECKS = {"saved_prediction_metrics_recomputed", "frozen_selection_verified", "same_case_comparisons_verified",
                    "uncertainty_method_verified", "no_test_reselection", "runtime_attempts_disclosed"}
CHECKS = {"final_evaluation_complete", "independent_metric_recomputation", "same_case_comparisons_verified",
          "normalized_projection_verified", "aggregate_only_privacy_review", "source_terms_checked"}


def _exact(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError("Unexpected or missing aggregate schema fields")


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("Invalid aggregate count")


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("A finite aggregate number is required")


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        raise ValueError("An exact SHA-256 binding is required")


def _list(value, maximum, minimum=0):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError("Aggregate list size is invalid")


def _metric_ids(task):
    if task == "baseball_mechanics":
        return {"macro_MAE", "macro_RMSE", "row_MAE", "row_RMSE"}
    if task == "tennis_execution":
        return {k for k in METRICS if k.endswith(("_attempt_weighted", "_equal_player"))}
    return {"log_loss", "brier", "accuracy", "auroc"} | ({"match_macro_log_loss", "server_macro_log_loss"} if task == "tennis" else set())


def _metric(metric, value, target, task):
    _exact(value, ("value", "cases", "clusters", "status"))
    _integer(value["cases"]); _integer(value["clusters"])
    if value["cases"] > target["cases"] or value["clusters"] > min(value["cases"], target["clusters"]):
        raise ValueError("Metric denominator exceeds its cohort")
    if value["status"] not in METRIC_STATUS:
        raise ValueError("Unknown metric availability")
    if value["status"] != "reported":
        if value["value"] is not None:
            raise ValueError("Unavailable metrics must not contain a result")
        return
    _finite(value["value"])
    if not value["cases"] or not value["clusters"]:
        raise ValueError("A result needs case and cluster support")
    ceiling = 2 if task == "tennis" and metric == "brier" else 1
    if metric in {"brier", "accuracy", "auroc"} or metric.startswith(("net_Brier", "ellipse90_covered")):
        if not 0 <= value["value"] <= ceiling:
            raise ValueError("Fraction/Brier outside its defined range")
    elif "NLL" not in metric and value["value"] < 0:
        raise ValueError("Negative nonnegative loss")
    expected = 437 if task == "tennis_execution" and metric.startswith(("location_NLL", "euclidean_error", "ellipse90_covered")) else target["cases"]
    if value["cases"] != expected:
        raise ValueError("Metric changed the fixed eligible denominator")


def validate_view(task: str, view: dict) -> dict:
    """Validate only aggregates. Reject extra fields rather than silently redact."""
    if task not in CONTRACTS:
        raise ValueError("Unknown numerical task")
    contract = CONTRACTS[task]
    _exact(view, ("schema_version", "task", "phase", "targets"))
    if (type(view["schema_version"]) is not int or view["schema_version"] != 1 or view["task"] != task
            or view["phase"] != "independently_verified_final_aggregate"):
        raise ValueError("Only completed independently verified final aggregates are displayable")
    _list(view["targets"], len(contract["targets"]) * len(contract["cohorts"]), 1)
    seen = set()
    for target in view["targets"]:
        _exact(target, ("id", "cohort", "cases", "clusters", "case_set_sha256", "models", "comparisons", "reliability"))
        pair = (target["id"], target["cohort"])
        if pair in seen or pair[0] not in contract["targets"] or pair[1] not in contract["cohorts"]:
            raise ValueError("Unknown or duplicated target/cohort")
        seen.add(pair); _integer(target["cases"], 1); _integer(target["clusters"], 1); _hash(target["case_set_sha256"])
        if target["clusters"] > target["cases"]:
            raise ValueError("Cluster count exceeds cases")
        if task in ("baseball_mechanics", "tennis_execution"):
            if (target["cases"], target["clusters"]) != ((571, 82) if task == "baseball_mechanics" else (548, 8)):
                raise ValueError("Fixed mechanics population changed")
        _list(target["models"], len(contract["models"]), 1)
        models = {}
        for model in target["models"]:
            _exact(model, ("id", "case_set_sha256", "metrics"))
            name = model["id"]
            if name not in contract["models"] or name in models or model["case_set_sha256"] != target["case_set_sha256"]:
                raise ValueError("Model or same-case identity changed")
            if task == "soccer" and not name.startswith(target["cohort"] + "_"):
                raise ValueError("Full and matched soccer cases cannot be mixed")
            if not isinstance(model["metrics"], dict) or not model["metrics"] or set(model["metrics"]) - _metric_ids(task):
                raise ValueError("Unknown metrics for this target")
            for key, value in model["metrics"].items():
                _metric(key, value, target, task)
            models[name] = model
        _list(target["comparisons"], 100)
        comparisons = set()
        for comparison in target["comparisons"]:
            _exact(comparison, ("model", "reference", "metric", "delta", "interval", "confidence", "uncertainty", "sensitivity_range", "criterion_met"))
            key = (comparison["model"], comparison["reference"], comparison["metric"], comparison["uncertainty"])
            if key in comparisons or key[0] not in models or key[1] not in models or key[2] not in _metric_ids(task):
                raise ValueError("Comparison has missing models or duplicate identity")
            comparisons.add(key)
            if METRICS[key[2]][2] != "lower":
                raise ValueError("Only prespecified lower-is-better loss gaps are supported")
            left = models[key[0]]["metrics"].get(key[2]); right = models[key[1]]["metrics"].get(key[2])
            if not left or not right or (left["cases"], left["clusters"]) != (right["cases"], right["clusters"]):
                raise ValueError("Comparison denominators differ")
            if comparison["uncertainty"] not in UNCERTAINTY[task] | {"not_available"} or type(comparison["criterion_met"]) not in (bool, type(None)):
                raise ValueError("Unknown comparison interpretation")
            # The small normalized schema does not carry every cross-metric,
            # per-game or dependence condition needed to verify a success claim.
            # A favorable source-report criterion must project as null, not true.
            if comparison["criterion_met"] is True:
                raise ValueError("Success-criterion claims require supporting evidence absent from this schema")
            if comparison["delta"] is None:
                if left["status"] == right["status"] == "reported" or any(comparison[k] is not None for k in ("interval", "confidence", "sensitivity_range", "criterion_met")) or comparison["uncertainty"] != "not_available":
                    raise ValueError("Invalid unavailable comparison")
                continue
            _finite(comparison["delta"])
            if left["status"] != "reported" or right["status"] != "reported" or not math.isclose(comparison["delta"], left["value"] - right["value"], rel_tol=1e-9, abs_tol=1e-10):
                raise ValueError("Gap does not equal the same-case model-minus-reference loss")
            if comparison["interval"] is None:
                if comparison["confidence"] is not None:
                    raise ValueError("No confidence level without an interval")
            else:
                _list(comparison["interval"], 2, 2)
                for bound in comparison["interval"]:
                    _finite(bound)
                if comparison["interval"][0] > comparison["interval"][1]:
                    raise ValueError("Reversed interval")
                if comparison["uncertainty"] in ("not_available", "five_game_leave_one_out"):
                    raise ValueError("Sensitivity range must not masquerade as confidence interval")
                if comparison["confidence"] != (.9875 if task == "tennis" else .95):
                    raise ValueError("Confidence level differs from the task contract")
            if task == "basketball" and (comparison["interval"] is not None or comparison["uncertainty"] not in ("not_available", "five_game_leave_one_out")):
                raise ValueError("Five-game basketball has no headline confidence interval")
            if comparison["sensitivity_range"] is not None:
                if task != "basketball" or comparison["uncertainty"] != "five_game_leave_one_out":
                    raise ValueError("Only aggregate five-game omission ranges are supported")
                _list(comparison["sensitivity_range"], 2, 2)
                for value in comparison["sensitivity_range"]:
                    _finite(value)
                if comparison["sensitivity_range"][0] > comparison["sensitivity_range"][1]:
                    raise ValueError("Reversed sensitivity range")
        _list(target["reliability"], len(models) * len(contract["classes"]))
        seen_reliability = set()
        for series in target["reliability"]:
            _exact(series, ("model", "class", "bins"))
            key = (series["model"], series["class"])
            if key in seen_reliability or key[0] not in models or key[1] not in contract["classes"]:
                raise ValueError("Unknown or repeated reliability series")
            seen_reliability.add(key)
            _list(series["bins"], len(contract["bins"]) - 1, len(contract["bins"]) - 1)
            for index, bucket in enumerate(series["bins"]):
                _exact(bucket, ("n", "clusters", "mean_probability", "observed_fraction"))
                _integer(bucket["n"])
                if bucket["clusters"] is not None:
                    _integer(bucket["clusters"])
                    if bucket["clusters"] > min(bucket["n"], target["clusters"]) or (bucket["n"] > 0 and bucket["clusters"] == 0):
                        raise ValueError("Invalid bin cluster support")
                for field in ("mean_probability", "observed_fraction"):
                    if bucket["n"] == 0:
                        if bucket[field] is not None:
                            raise ValueError("Empty bins cannot have rates")
                    else:
                        _finite(bucket[field])
                        if not 0 <= bucket[field] <= 1:
                            raise ValueError("Invalid reliability rate")
                if bucket["n"] and not contract["bins"][index] <= bucket["mean_probability"] <= contract["bins"][index + 1]:
                    raise ValueError("Mean probability lies outside its fixed bin")
            if sum(bucket["n"] for bucket in series["bins"]) != target["cases"]:
                raise ValueError("Reliability bins do not cover the same eligible cases")
    return view


def _path(root, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Invalid local evidence path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Evidence path escapes the project")
    return path


def _evidence_limit(relative):
    """Larger cap only for exact original-report names produced by _final_path.

    This is a size policy, not authority to read: callers still verify the
    independent audit, fixed task binding, completion marker and exact hashes.
    No normalized views, reviews, metadata or arbitrary report paths qualify.
    """
    originals = ("reports/tactical/soccer/model/evaluation.json",
                 "reports/tactical/football/model/evaluation.json",
                 "reports/tactical/tennis/model/evaluation.json",
                 "artifacts/tactical/baseball/EVALUATION.json",
                 "artifacts/tactical/baseball_mechanics/evaluation_report.json",
                 "artifacts/tactical/tennis_execution/evaluation_report.json")
    if isinstance(relative, str) and (relative in originals or re.fullmatch(
            r"reports/tactical/basketball/model/[0-9a-f]{64}/evaluation_report\.json", relative)):
        return FINAL_REPORT_MAX_BYTES
    return MAX_BYTES


def _bytes(root, relative):
    # No-follow component opens prevent a fixed original-report filename from
    # lending its larger cap to an unrelated in-root file through an alias.
    if not isinstance(relative, str):
        raise ValueError("Invalid local evidence path")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Invalid local evidence path")
    limit = _evidence_limit(relative)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory_fd = os.open(root, flags)
    try:
        for component in path.parts[:-1]:
            child_fd = os.open(component, flags, dir_fd=directory_fd)
            os.close(directory_fd); directory_fd = child_fd
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise ValueError("Aggregate evidence must be a bounded regular file")
            raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise ValueError("Aggregate evidence exceeds size limit")
            return raw
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ValueError("Aggregate evidence paths cannot contain symlink aliases") from error
        raise
    finally:
        os.close(directory_fd)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON keys")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def _final_path(task, binding):
    if task == "basketball":
        artifact = binding["metadata"]["artifact_id"]; _hash(artifact)
        return f"reports/tactical/basketball/model/{artifact}/evaluation_report.json"
    if task == "baseball":
        return "artifacts/tactical/baseball/EVALUATION.json"
    if task in ("baseball_mechanics", "tennis_execution"):
        return f"artifacts/tactical/{task}/evaluation_report.json"
    return f"reports/tactical/{task}/model/evaluation.json"


def _completed(task, report):
    if not isinstance(report, dict):
        raise ValueError("Final report must be an object")
    if task in ("soccer", "football"):
        complete = report.get("phase") == "frozen_evaluation"
    elif task == "basketball":
        complete = report.get("phase") == "evaluation_complete" and report.get("new_model_selection") is False
    elif task == "tennis":
        complete = report.get("stage") == "locked_2025_evaluation" and report.get("as_of") == "20260122"
    elif task == "baseball":
        complete = report.get("task") == task and set(report.get("targets", {})) == {"swing", "contact_given_swing"}
    else:
        complete = report.get("task") == task and report.get("status") == "evaluation_complete" and report.get("new_model_selection") is False
    if not complete:
        raise ValueError("Source report is not a completed final evaluation")


def metric_definitions(task):
    result = {key: dict(label=METRICS[key][0], unit=METRICS[key][1], direction=METRICS[key][2]) for key in sorted(_metric_ids(task))}
    if task in ("baseball_mechanics", "tennis_execution"):
        definitions = ["Classification accuracy and reliability bins are not reported for this mechanics target.",
                       "Uncertainty describes conditional sampling only, not measurement, model-selection or transport uncertainty."]
    else:
        tie = ("argmax; ties choose the first class in [wide, body, T]" if task == "tennis" else
               "argmax [0, 1]; exact p = 0.5 chooses class 0" if task == "basketball" else "predict class 1 for p ≥ 0.5, including exact ties")
        clipping = ("floor each class at epsilon then renormalize" if task == "tennis" else "clip positive-class p to [epsilon, 1 − epsilon]")
        brier = "mean sum of squared class errors; no division by three" if task == "tennis" else "mean positive-class squared error using original unclipped probabilities"
        definitions = [f"Accuracy: {tie}.", f"Log loss: natural logarithms; epsilon {CONTRACTS[task]['epsilon']:g}; {clipping}.",
                       f"Brier: {brier}.", "Reliability: fixed left-closed/right-open bins; final bin includes 1. Empty and low-support bins remain visible.",
                       "Loss differences are model minus reference on identical cases; negative is favorable. No pooled cross-target accuracy."]
    if task in ("football", "tennis"):
        definitions.append("Reliability uses the frozen serialized floating-point linspace edges. Labels are rounded; nominal decimal boundary values can land in the preceding bin. Binning does not change any score.")
    definitions.append(CRITERIA[task])
    return result, definitions


def _display(task, view, mode):
    metrics, definitions = metric_definitions(task)
    return {**view, "delivery_mode": mode,
            "contract": {**CONTRACTS[task], "cluster_unit": CLUSTER_UNITS[task]},
            "metrics": metrics, "definitions": definitions, "notices": [SOURCE_QA, NO_CAUSAL]}


def _verify_implementation(root, hashes):
    _exact(hashes, IMPLEMENTATION)
    for path, expected in hashes.items():
        _hash(expected)
        if (_digest(_bytes(root, path)) != expected or _digest(_bytes(LIVE_ROOT, path)) != expected
                or (path in RUNNING_CODE_SHA256 and RUNNING_CODE_SHA256[path] != expected)):
            raise ValueError("Reviewed presentation implementation differs from the live server")


def _verify_completion(records):
    _exact(records, TASKS)
    for record in records.values():
        _exact(record, ("status", "binding_sha256", "final_report_sha256", "independent_result_review_sha256"))
        if record["status"] != "verified_final":
            raise ValueError("All seven study completions must be independently attested")
        for field in ("binding_sha256", "final_report_sha256", "independent_result_review_sha256"):
            _hash(record[field])
    if len({record["independent_result_review_sha256"] for record in records.values()}) != 1:
        raise ValueError("The exact seven-study independent numerical audit must be shared")


def validate_numerical_review(review, completion):
    """Require audit semantics, not just hash-shaped provenance; ignore narrative."""
    required = {"schema_version", "review_type", "status", "independent", "reviewer", "evaluation_freeze_sha256", "tasks"}
    if not isinstance(review, dict) or not required <= set(review):
        raise ValueError("Completed numerical audit fields are missing")
    if (type(review["schema_version"]) is not int or review["schema_version"] != 1
            or review["review_type"] != "tactical_final_numerical_review" or review["status"] != "verified_final"
            or review["independent"] is not True or not isinstance(review["reviewer"], str)
            or not review["reviewer"].strip()):
        raise ValueError("Independent final numerical audit is incomplete")
    _hash(review["evaluation_freeze_sha256"])
    _exact(review["tasks"], TASKS)
    for task, record in review["tasks"].items():
        required = {"status", "binding_sha256", "selection_sha256", "final_report_sha256", "checks"}
        if not isinstance(record, dict) or not required <= set(record) or record["status"] != "verified_final":
            raise ValueError("Every numerical study must have a completed audit")
        for field in ("binding_sha256", "selection_sha256", "final_report_sha256"):
            _hash(record[field])
        if any(record[field] != completion[task][field] for field in ("binding_sha256", "final_report_sha256")):
            raise ValueError("Numerical audit and final-view completion identities differ")
        _exact(record["checks"], NUMERICAL_CHECKS)
        if any(value is not True for value in record["checks"].values()):
            raise ValueError("Numerical audit checks are incomplete")
    return review


def verify_selection_evidence(root, audit):
    """Hash-only verification of frozen commitments; never load models/targets."""
    raw = _bytes(root, GLOBAL_FREEZE)
    if _digest(raw) != audit["evaluation_freeze_sha256"]:
        raise ValueError("Independently audited global evaluation freeze changed")
    freeze = _json(raw)
    if not isinstance(freeze, dict) or type(freeze.get("schema_version")) is not int or freeze.get("schema_version") != 1:
        raise ValueError("Invalid global evaluation freeze")
    _exact(freeze.get("tasks"), TASKS)
    for task, item in freeze["tasks"].items():
        path = f"artifacts/tactical/{task}/SELECTION_FREEZE.json"
        reviewed = audit["tasks"][task]
        if (not isinstance(item, dict) or item.get("binding_sha256") != reviewed["binding_sha256"]
                or item.get("selection_path") != path or item.get("selection_sha256") != reviewed["selection_sha256"]):
            raise ValueError("Global freeze differs from independently audited selection identities")
        if _digest(_bytes(root, path)) != reviewed["selection_sha256"]:
            raise ValueError("A completed study's selection commitment changed")


def _load_audited_snapshot(root, task):
    """Verify a separately approved aggregate distribution, without private files.

    Provenance hashes are independent-review attestations in this detached mode;
    they do not claim source/model reproduction from the sanitized distribution.
    This reader never creates, signs, repairs or replaces any review document.
    """
    if not _path(root, SNAPSHOT_REVIEW).exists():
        return "awaiting_independent_final_review", None
    review = _json(_bytes(root, SNAPSHOT_REVIEW))
    _exact(review, ("schema_version", "review_type", "status", "reviewer", "independent",
                    "distribution_scope", "local_final_review_sha256", "implementation_sha256",
                    "seven_task_completion", "tasks"))
    if (type(review["schema_version"]) is not int or review["schema_version"] != 1
            or review["review_type"] != "independent_aggregate_snapshot_review" or review["status"] != "cleared"
            or review["independent"] is not True or not isinstance(review["reviewer"], str)
            or not 1 <= len(review["reviewer"]) <= 200 or not review["reviewer"].strip()
            or review["distribution_scope"] != "local_noncommercial_aggregate_snapshot"):
        raise ValueError("Independent aggregate publication review is missing")
    _hash(review["local_final_review_sha256"])
    _verify_implementation(root, review["implementation_sha256"])
    _verify_completion(review["seven_task_completion"])
    if not isinstance(review["tasks"], dict) or not review["tasks"] or set(review["tasks"]) - set(TASKS):
        raise ValueError("Unexpected snapshot task")
    if task not in review["tasks"]:
        return "awaiting_independent_final_review", None
    entry = review["tasks"][task]
    _exact(entry, ("status", "view_sha256", "checks"))
    _exact(entry["checks"], CHECKS | {"sanitized_snapshot_verified", "aggregate_distribution_authorized"})
    if entry["status"] != "verified_final" or any(value is not True for value in entry["checks"].values()):
        raise ValueError("Aggregate-only distribution has not cleared all reviews")
    _hash(entry["view_sha256"])
    raw = _bytes(root, f"{VIEW_DIRECTORY}/{task}.json")
    if _digest(raw) != entry["view_sha256"]:
        raise ValueError("Reviewed snapshot bytes changed")
    view = validate_view(task, _json(raw))
    return "verified_final_available", _display(task, view, "audited_aggregate_snapshot")


def load_verified_view(root: Path, task: str) -> tuple[str, dict | None]:
    """Fail closed without externally supplied final verification; never create it."""
    if task not in CONTRACTS:
        raise KeyError(task)
    root = Path(root).resolve()
    try:
        review_path = _path(root, REVIEW)
        if not review_path.exists():
            return _load_audited_snapshot(root, task)
        review = _json(_bytes(root, REVIEW))
        _exact(review, ("schema_version", "review_type", "status", "reviewer", "independent", "implementation_sha256", "seven_task_completion", "tasks"))
        if (type(review["schema_version"]) is not int or review["schema_version"] != 1 or review["review_type"] != "independent_final_model_view_review" or review["status"] != "cleared"
                or review["independent"] is not True or not isinstance(review["reviewer"], str) or not 1 <= len(review["reviewer"]) <= 200 or not review["reviewer"].strip()):
            raise ValueError("Independent final review is missing")
        _verify_implementation(root, review["implementation_sha256"])
        _verify_completion(review["seven_task_completion"])
        audit_raw = _bytes(root, NUMERICAL_REVIEW)
        audit_hash = _digest(audit_raw)
        if any(record["independent_result_review_sha256"] != audit_hash for record in review["seven_task_completion"].values()):
            raise ValueError("The completed seven-study independent numerical audit changed")
        audit = validate_numerical_review(_json(audit_raw), review["seven_task_completion"])
        verify_selection_evidence(root, audit)
        if not isinstance(review["tasks"], dict) or set(review["tasks"]) - set(TASKS):
            raise ValueError("Unexpected reviewed task")
        if task not in review["tasks"]:
            return "awaiting_independent_final_review", None
        entry = review["tasks"][task]
        _exact(entry, ("status", "binding_sha256", "binding_file_sha256", "final_report_sha256", "view_sha256", "checks"))
        _exact(entry["checks"], CHECKS)
        if entry["status"] != "verified_final" or any(value is not True for value in entry["checks"].values()):
            raise ValueError("Final metrics or privacy checks are incomplete")
        for field in ("binding_sha256", "binding_file_sha256", "final_report_sha256", "view_sha256"):
            _hash(entry[field])
        completion = review["seven_task_completion"][task]
        if any(entry[field] != completion[field] for field in ("binding_sha256", "final_report_sha256")):
            raise ValueError("Task review differs from the seven-study completion attestation")
        raw_binding = _bytes(root, f"artifacts/tactical/{task}/run_binding.json")
        if _digest(raw_binding) != entry["binding_file_sha256"]:
            raise ValueError("Reviewed binding bytes changed")
        binding = _json(raw_binding)
        if not isinstance(binding, dict):
            raise ValueError("Run binding must be an object")
        body = {key: value for key, value in binding.items() if key != "binding_sha256"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if (binding.get("task") != task or binding.get("binding_sha256") != entry["binding_sha256"]
                or _digest(canonical) != entry["binding_sha256"] or sorted(binding.get("evaluation_cohort", [])) != sorted(TASKS)):
            raise ValueError("Reviewed run identity or seven-task cohort changed")
        # No raw data, private memberships, runtime changes or numerical gates are read here.
        # The independent final review attests their source-to-report verification.
        report_raw = _bytes(root, _final_path(task, binding))
        if _digest(report_raw) != entry["final_report_sha256"]:
            raise ValueError("Reviewed final report changed")
        _completed(task, _json(report_raw))
        view_raw = _bytes(root, f"{VIEW_DIRECTORY}/{task}.json")
        if _digest(view_raw) != entry["view_sha256"]:
            raise ValueError("Reviewed normalized view changed")
        view = validate_view(task, _json(view_raw))
        # Neither evidence paths, binding contents nor the source report are served.
        return "verified_final_available", _display(task, view, "verified_local_final")
    except (OSError, ValueError, KeyError, TypeError, RecursionError, OverflowError):
        return "invalid_final_artifact", None


def response(root, task):
    status, view = load_verified_view(root, task)
    return {"status": status, "view": view}
