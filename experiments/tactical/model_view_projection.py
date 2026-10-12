"""Deterministic, aggregate-only presentation projection. Never a numerical runner.

No source targets, row-level predictions, models or private group plans are read.
Pure projection consumes already reported aggregate values plus independently
verified case-set support. The optional file driver requires a complete seven-
study final numerical audit before reading any final aggregate report, and writes
only candidate projections. It never creates/replaces approval or review files.
"""
from __future__ import annotations

import argparse
import errno
import copy
import json
import os
import stat
from pathlib import Path

from . import model_views as v

CANDIDATE_DIRECTORY = "artifacts/tactical/model_view_candidates"
SUPPORT_FIELDS = ("id", "cohort", "cases", "clusters", "case_set_sha256")


def _read(root, relative):
    """Read a fixed regular file without following any in-root path alias."""
    path = Path(relative)
    if not isinstance(relative, str) or path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Invalid projection evidence path")
    limit = v._evidence_limit(relative)
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
                raise ValueError("Projection evidence must be a bounded regular file")
            raw = stream.read(limit + 1)
            if len(raw) > limit: raise ValueError("Projection evidence exceeds its size limit")
            return raw
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ValueError("Projection evidence paths cannot contain symlink aliases") from error
        raise
    finally:
        os.close(directory_fd)


def _verify_selection_evidence(root, audit):
    # Same audit metadata contract as the view reader, using this driver's
    # stronger no-alias reader rather than following any in-root links.
    raw = _read(root, v.GLOBAL_FREEZE)
    if v._digest(raw) != audit["evaluation_freeze_sha256"]:
        raise ValueError("Audited global evaluation freeze changed")
    freeze = v._json(raw)
    if not isinstance(freeze, dict) or type(freeze.get("schema_version")) is not int or freeze.get("schema_version") != 1:
        raise ValueError("Invalid global evaluation freeze")
    v._exact(freeze.get("tasks"), v.TASKS)
    for task, item in freeze["tasks"].items():
        path = f"artifacts/tactical/{task}/SELECTION_FREEZE.json"
        record = audit["tasks"][task]
        if (not isinstance(item, dict) or item.get("binding_sha256") != record["binding_sha256"]
                or item.get("selection_path") != path or item.get("selection_sha256") != record["selection_sha256"]):
            raise ValueError("Global freeze and numerical audit disagree")
        if v._digest(_read(root, path)) != record["selection_sha256"]:
            raise ValueError("Audited selection commitment changed")


def _object(value):
    if not isinstance(value, dict):
        raise ValueError("Expected an aggregate report object")
    return value


def _check_counts(source, target):
    """Compare declared aggregates only; never count records or derive support."""
    for key in ("n", "rows"):
        if key in source:
            v._integer(source[key])
            if source[key] != target["cases"]:
                raise ValueError("Reported case count differs from independently audited support")
    for key in ("games", "groups", "athletes", "players"):
        if key in source:
            v._integer(source[key])
            if source[key] != target["clusters"]:
                raise ValueError("Reported cluster count differs from independently audited support")


def _support(task, records):
    v._list(records, len(v.CONTRACTS[task]["targets"]) * len(v.CONTRACTS[task]["cohorts"]))
    result = {}
    for record in records:
        v._exact(record, SUPPORT_FIELDS)
        key = (record["id"], record["cohort"])
        if key in result or key[0] not in v.CONTRACTS[task]["targets"] or key[1] not in v.CONTRACTS[task]["cohorts"]:
            raise ValueError("Unexpected independently audited support cell")
        v._integer(record["cases"], 1); v._integer(record["clusters"], 1); v._hash(record["case_set_sha256"])
        if record["clusters"] > record["cases"]:
            raise ValueError("Invalid independently audited support")
        result[key] = record
    return result


def _conventions(task, source, target_id=None):
    """Reject contrary declared conventions; never relabel unlike metric values."""
    contract = v.CONTRACTS[task]
    if task in ("baseball_mechanics", "tennis_execution"):
        expected_unit = "mph" if task == "baseball_mechanics" else "nats per recorded non-let attempt; density per square meter"
        if "unit" in source and source["unit"] != expected_unit:
            raise ValueError("Reported mechanics units differ from the fixed measurement contract")
        fixed = ({"macro_RMSE_definition": "mean of within-athlete square-root MSEs", "practical_threshold_mph": .5}
                 if task == "baseball_mechanics" else {"practical_threshold_nats": .02, "ellipse90_mahalanobis_squared_cutoff": 4.605170185988091})
        if any(key in source and source[key] != value for key, value in fixed.items()):
            raise ValueError("Reported mechanics metric definition changed")
    expected_class_order = ["wide", "body", "T"] if task == "tennis" else [0, 1]
    if "class_order" in source and list(source["class_order"]) != expected_class_order:
        raise ValueError("Reported class order differs from the task contract")
    if contract["epsilon"] is not None:
        if "log_clip_epsilon" in source and source["log_clip_epsilon"] != contract["epsilon"]:
            raise ValueError("Reported metric clipping differs from the task contract")
        expected_brier = "mean sum of squared class errors" if task == "tennis" else "mean positive-class squared error"
        if "brier_definition" in source and source["brier_definition"] != expected_brier:
            raise ValueError("Reported Brier convention differs from the task contract")
        allowed_units = {"natural-log units per case"}
        if task == "baseball":
            allowed_units.add("nats per eligible delivered pitch" if target_id == "swing" else "nats per eligible swing")
        if "log_loss_units" in source and source["log_loss_units"] not in allowed_units:
            raise ValueError("Reported log-loss unit differs from the target contract")
    if "accuracy_tie_rule" in source:
        expected = ("argmax; ties choose the first class in [wide, body, T]" if task == "tennis"
                    else "argmax with class order [0,1]; exact p=0.5 ties choose class 0" if task == "basketball"
                    else "class 1 when p >= 0.5, including exact ties")
        if source["accuracy_tie_rule"] != expected:
            raise ValueError("Reported accuracy tie rule differs from the task contract")
    if task == "baseball" and "metric_definition" in source:
        definition = _object(source["metric_definition"])
        for key, expected in (("log_loss_clip_epsilon", 1e-12), ("brier", "mean((original_probability-y)^2)"),
                              ("accuracy", "predict 1 when p >= 0.5")):
            if key in definition and definition[key] != expected:
                raise ValueError("Reported baseball metric convention changed")


def _model(task, name, source, target, unavailable="not_reported"):
    source = {} if source is None else _object(source)
    _check_counts(source, target)
    _conventions(task, source, target["id"])
    metrics = {}
    for metric in sorted(v._metric_ids(task)):
        cases, clusters, value = target["cases"], target["clusters"], None
        status = unavailable
        if task == "tennis_execution":
            suffix = "attempt_weighted" if metric.endswith("_attempt_weighted") else "equal_player"
            key = metric[:-(len(suffix) + 1)]
            record = source.get(key)
            cases, clusters = 0, 0  # Missing metric support must not become non-let support.
            if record is not None:
                record = _object(record)
                expected = 437 if key in ("location_NLL", "euclidean_error", "ellipse90_covered") else target["cases"]
                # Both denominator fields must actually be reported for this subtarget.
                if "attempts" in record and "players" in record:
                    cases, clusters = record["attempts"], record["players"]
                    if (cases != expected or clusters > target["clusters"]
                            or (key in ("joint_NLL", "net_Brier") and clusters != target["clusters"])):
                        raise ValueError("BYU net/bounce metric denominator changed")
                    value = record.get(suffix)
        else:
            value = source.get(metric)
        if value is not None:
            v._finite(value); status = "reported"
        elif metric == "auroc" and source.get("auroc_status") == "undefined_single_label_class":
            status = "undefined_single_class"
        metrics[metric] = dict(value=value, cases=cases, clusters=clusters, status=status)
    return dict(id=name, case_set_sha256=target["case_set_sha256"], metrics=metrics)


def _reliability(task, name, source, target, warnings):
    if not v.CONTRACTS[task]["classes"] or not source or "reliability" not in source:
        return []
    buckets = source["reliability"]
    if not isinstance(buckets, list):
        raise ValueError("Malformed aggregate reliability")
    result = []; contract = v.CONTRACTS[task]
    for index, label in enumerate(contract["classes"]):
        source_class = index if task == "tennis" else 1
        own = [bucket for bucket in buckets if isinstance(bucket, dict) and bucket.get("class") == source_class]
        if len(own) != len(contract["bins"]) - 1:
            warnings.append(f"reliability_unavailable:{target['id']}:{target['cohort']}:{name}:{label}")
            continue
        projected = []
        for number, bucket in enumerate(own):
            if bucket.get("lower") != contract["bins"][number] or bucket.get("upper") != contract["bins"][number + 1]:
                raise ValueError("Source reliability edges differ from frozen task convention")
            if not {"n", "mean_probability", "observed_fraction"} <= set(bucket):
                raise ValueError("Reliability aggregate support is missing")
            projected.append({"n": bucket["n"], "clusters": bucket.get("games"),
                              "mean_probability": bucket["mean_probability"], "observed_fraction": bucket["observed_fraction"]})
        result.append(dict(model=name, **{"class": label}, bins=projected))
    return result


def _contrast_support(task, target, metric, source, uncertainty):
    """Validate already reported uncertainty support under its actual estimand."""
    cases, groups = target["cases"], target["clusters"]
    if task == "baseball": expected_weighting = "pitch-weighted whole-game resampling"
    elif task == "tennis" and metric == "match_macro_log_loss":
        expected_weighting = "match_macro_with_event_clusters" if uncertainty == "tournament_year_bootstrap" else "group"
    elif task in ("baseball_mechanics", "tennis_execution") and uncertainty in ("paired_athlete_bootstrap", "paired_player_bootstrap"):
        expected_weighting = "group"
    else: expected_weighting = "case"
    if "weighting" in source and source["weighting"] != expected_weighting:
        raise ValueError("Reported contrast weighting differs from its normalized estimand")
    if task in ("baseball_mechanics", "tennis_execution") and "unit" in source and source["unit"] != "whole held-out participant":
        raise ValueError("Reported mechanics resampling unit changed")
    expected_cases = groups if uncertainty == "tournament_year_bootstrap" and metric == "match_macro_log_loss" else cases
    if "cases" in source:
        v._integer(source["cases"], 1)
        if source["cases"] != expected_cases:
            raise ValueError("Contrast case support differs from its declared estimand")
    if "groups" in source:
        v._integer(source["groups"], 1)
        exact = uncertainty in {"paired_match_bootstrap", "paired_game_bootstrap", "paired_athlete_bootstrap", "paired_player_bootstrap"}
        upper = groups if uncertainty == "tournament_year_bootstrap" else cases
        if (exact and source["groups"] != groups) or (not exact and source["groups"] > upper):
            raise ValueError("Contrast cluster support differs from its declared method")
    if uncertainty == "four_week_block_bootstrap":
        fixed = {"calendar_bins": 53, "weeks_per_block": 4, "candidate_contiguous_blocks": 50}
        for key, value in fixed.items():
            if key in source and source[key] != value:
                raise ValueError("Tennis temporal-block convention changed")
        for key, maximum in (("populated_weeks", 53), ("populated_blocks", 50)):
            if key in source:
                v._integer(source[key])
                if source[key] > maximum: raise ValueError("Invalid temporal support")
        return all(source.get(key) == value for key, value in fixed.items()) and source.get("populated_weeks", 0) >= 4
    if uncertainty == "tournament_year_bootstrap" and metric == "match_macro_log_loss":
        for key, expected in (("original_points", cases), ("matches", groups)):
            if key in source and source[key] != expected:
                raise ValueError("Tennis event-cluster match-macro support changed")
        return all(key in source for key in ("cases", "groups", "original_points", "matches"))
    if uncertainty in {"paired_athlete_bootstrap", "paired_player_bootstrap"}:
        return "groups" in source
    return all(key in source for key in ("cases", "groups")) if uncertainty != "not_available" else True


def _contrast(task, target, model, reference, metric, source, uncertainty, criterion=None, interval_key="interval"):
    """Copy a precomputed contrast, never manufacture one from marginal scores."""
    if not isinstance(source, dict) or source.get("difference") is None:
        return None
    models = {item["id"]: item for item in target["models"]}
    if model not in models or reference not in models:
        return None
    if any(models[name]["metrics"][metric]["status"] != "reported" for name in (model, reference)):
        return None
    complete_support = _contrast_support(task, target, metric, source, uncertainty)
    interval = source.get(interval_key) if complete_support else None
    # Keep the declared method identity when support is incomplete. Collapsing
    # game/week or match/event methods into one name would create duplicate
    # contrasts; a named method with a null interval makes no precision claim.
    confidence = (.95 if interval_key == "interval95" else source.get("confidence")) if interval is not None else None
    return dict(model=model, reference=reference, metric=metric, delta=source["difference"], interval=interval,
                confidence=confidence, uncertainty=uncertainty, sensitivity_range=None,
                criterion_met=False if criterion is False else None)


def _comparisons(task, report, section, target):
    results = []
    def append(model, reference, metric, source, uncertainty, criterion=None, interval_key="interval"):
        value = _contrast(task, target, model, reference, metric, source, uncertainty, criterion, interval_key)
        if value is not None: results.append(value)
    if task == "soccer" and target["cohort"] == "matched":
        for metric in ("log_loss", "brier"):
            append("matched_R_calibrated", "matched_G_calibrated", metric, report.get("primary", {}).get(metric),
                   "paired_match_bootstrap", report.get("usefulness_yardstick_met") if metric == "log_loss" else None)
        # Equal-game sensitivity is a different estimand; do not relabel it as the
        # available shot-weighted metric or invent new equal-game marginal scores.
    elif task == "football":
        for key, method in (("primary_game_bootstrap", "paired_game_bootstrap"), ("week_dependence_sensitivity", "paired_week_bootstrap")):
            for metric in ("log_loss", "brier"):
                append("logistic_C_calibrated", "logistic_A_calibrated", metric, report.get(key, {}).get(metric), method,
                       report.get("usefulness_yardstick_met") if metric == "log_loss" else None)
    elif task == "basketball":
        for metric, delta in section.get("D_minus_C_shot_weighted", {}).items():
            if metric in ("log_loss", "brier"):
                criterion = report.get("diagnostics", {}).get("exploratory_practical_yardstick", {}).get("met") if target["cohort"] == "event_geometry" and metric == "log_loss" else None
                append("D", "C", metric, {"difference": delta}, "not_available", criterion)
        # The runner's individual omission records are intentionally not traversed.
        # No aggregate range is reported; none is inferred or recalculated here.
    elif task == "baseball":
        comparison = section.get("comparison", {})
        if comparison.get("available") is True:
            append("sequence_logistic_calibrated", "context_logistic_calibrated", "log_loss", comparison,
                   "paired_game_bootstrap", comparison.get("useful_improvement_claim"))
        for kind in ("raw", "calibrated"):
            append(f"history_table_{kind}", f"context_table_{kind}", "log_loss",
                   section.get("secondary_history_comparisons", {}).get(f"history_minus_context_{kind}"), "paired_game_bootstrap")
    elif task == "tennis":
        methods = {"match": "paired_match_bootstrap", "tournament_year": "tournament_year_bootstrap", "four_week": "four_week_block_bootstrap"}
        for kind in ("uncalibrated", "calibrated"):
            comparison = section.get("contrasts", {}).get(kind)
            if not isinstance(comparison, dict): continue
            for prefix, method in methods.items():
                for weight, metric in (("case", "log_loss"), ("group", "match_macro_log_loss")):
                    append(comparison.get("main"), comparison.get("reference"), metric,
                           comparison.get("intervals", {}).get(f"{prefix}_{weight}"), method,
                           comparison.get("demonstrated_improvement") if prefix == "match" and weight == "case" else None)
    elif task == "baseball_mechanics":
        append("augmented", "context", "macro_MAE", report.get("primary"), "paired_athlete_bootstrap", report.get("practical_threshold_met"), "interval95")
    elif task == "tennis_execution":
        append("B1", "B0", "joint_NLL_equal_player", report.get("primary"), "paired_player_bootstrap", report.get("practical_threshold_met"), "interval95")
        if report.get("attempt_weighted_contrast") is not None:
            append("B1", "B0", "joint_NLL_attempt_weighted", {"difference": report["attempt_weighted_contrast"]}, "not_available")
    return results


def _section(task, report, target_id, cohort):
    """Read declared report-construction keys only; no raw/group-output traversal."""
    if task == "soccer": return report, report.get("streams", {})
    if task == "football": return report, report.get("procedures", {})
    if task == "basketball":
        section = report.get("diagnostics", {}).get("cohorts", {}).get(cohort)
        return (section, section.get("candidates", {})) if isinstance(section, dict) and section.get("status") == "scored" else (None, {})
    if task == "baseball":
        section = report.get("targets", {}).get(target_id)
        if not isinstance(section, dict): return None, {}
        methods = {}
        for name, procedure in section.get("procedures", {}).items():
            if name not in ("constant", "context_table", "history_table", "context_logistic", "sequence_logistic"): continue
            _object(procedure)
            for kind in ("raw", "calibrated"):
                # A prespecified logistic fallback is not a fitted logistic result.
                methods[f"{name}_{kind}"] = None if procedure.get("fallback") else procedure.get(kind)
        return section, methods
    if task == "tennis":
        section = report.get("cells", {}).get(target_id)
        return (section, section.get("methods", {})) if isinstance(section, dict) and section.get("status") == "evaluated" else (None, {})
    return report, report.get("models", {})


def project_report(task, report, aggregate_view_support):
    """Pure aggregate projection. Caller must supply independently audited support.

    For tests only, invented inputs exercise this function directly. Real source
    reports may be used only after independently cleared seven-study evaluation.
    """
    if task not in v.TASKS: raise ValueError("Unknown study")
    v._completed(task, report)
    _conventions(task, report)
    if task == "tennis_execution" and any(report.get(key) != value for key, value in
            (("observed_bounces", 437), ("net_censored", 111), ("lets_excluded", 19))):
        raise ValueError("Reported BYU non-let/censoring population changed")
    support = _support(task, aggregate_view_support)
    targets, warnings = [], []
    contract = v.CONTRACTS[task]
    for target_id in contract["targets"]:
        for cohort in contract["cohorts"]:
            key = (target_id, cohort)
            if key not in support:
                warnings.append(f"audited_support_unavailable:{target_id}:{cohort}"); continue
            section, sources = _section(task, report, target_id, cohort)
            if section is None:
                warnings.append(f"reported_aggregate_unavailable:{target_id}:{cohort}"); continue
            _object(sources)
            target = {**copy.deepcopy(support[key]), "models": [], "comparisons": [], "reliability": []}
            if task not in ("soccer", "football"):
                _check_counts(section, target)
            if task == "tennis": _check_counts(section.get("common_data", {}), target)
            for name in contract["models"]:
                if task == "soccer" and not name.startswith(cohort + "_"): continue
                source = sources.get(name)
                unavailable = "procedure_unavailable" if name in sources and source is None else "not_reported"
                target["models"].append(_model(task, name, source, target, unavailable))
                target["reliability"].extend(_reliability(task, name, source, target, warnings))
            target["comparisons"] = _comparisons(task, report, section, target)
            if task == "basketball": warnings.append(f"omission_range_not_reported_as_aggregate:{target_id}:{cohort}")
            if not any(score["status"] == "reported" for model in target["models"] for score in model["metrics"].values()):
                warnings.append(f"all_metrics_unavailable:{target_id}:{cohort}")
            targets.append(target)
    if not targets:
        return dict(task=task, status="aggregate_projection_unavailable", view=None, unavailable=warnings)
    view = dict(schema_version=1, task=task, phase="independently_verified_final_aggregate", targets=targets)
    v.validate_view(task, view)
    return dict(task=task, status="candidate_aggregate_projection", view=view, unavailable=warnings)


def prepare_candidates(root):
    """Read only after independent all-seven final clearance. No writes or approval."""
    root = Path(root).resolve()
    audit_raw = _read(root, v.NUMERICAL_REVIEW)
    audit = v._json(audit_raw)
    _object(audit)
    records = audit.get("tasks")
    v._exact(records, v.TASKS)
    completion = {task: {"status": record.get("status"), "binding_sha256": record.get("binding_sha256"),
                        "final_report_sha256": record.get("final_report_sha256"), "independent_result_review_sha256": v._digest(audit_raw)}
                  for task, record in records.items() if isinstance(record, dict)}
    v._verify_completion(completion)
    v.validate_numerical_review(audit, completion)
    _verify_selection_evidence(root, audit)
    bindings = {}
    # Reconcile every binding before any final report is opened.
    for task in v.TASKS:
        binding = _object(v._json(_read(root, f"artifacts/tactical/{task}/run_binding.json")))
        body = {key: value for key, value in binding.items() if key != "binding_sha256"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if (binding.get("task") != task or binding.get("binding_sha256") != records[task]["binding_sha256"]
                or v._digest(canonical) != records[task]["binding_sha256"]
                or sorted(binding.get("evaluation_cohort", [])) != sorted(v.TASKS)):
            raise ValueError("Audited study binding is missing or changed")
        bindings[task] = binding
    reports = {}
    for task in v.TASKS:
        raw = _read(root, v._final_path(task, bindings[task]))
        if v._digest(raw) != records[task]["final_report_sha256"]:
            raise ValueError("Independently audited final report changed")
        reports[task] = v._json(raw)
        v._completed(task, reports[task])
    return {task: project_report(task, reports[task], records[task].get("aggregate_view_support", [])) for task in v.TASKS}


def write_candidates(root, candidates):
    """Persist candidates only; not installed display reports or review records."""
    root = Path(root).resolve()
    # Revalidate the current audit/input identity at write time. A caller cannot
    # supply arbitrary candidate numbers to the persistence helper.
    if candidates != prepare_candidates(root):
        raise ValueError("Candidate contents differ from the current independently cleared aggregate projection")
    directory = root
    for component in Path(CANDIDATE_DIRECTORY).parts:
        directory = directory / component
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError("Candidate output directory cannot contain symlink aliases")
    paths = {task: directory / f"{task}.json" for task in v.TASKS if candidates[task]["view"] is not None}
    payloads = {}
    for task, path in paths.items():
        v.validate_view(task, candidates[task]["view"])
        if path.is_symlink(): raise ValueError("Candidate output cannot be a symlink alias")
        if path.exists(): raise FileExistsError("Candidate projections already exist; no silent overwrite")
        payloads[task] = json.dumps(candidates[task]["view"], sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    if paths:
        # Directory-relative, no-follow opens also close the check/write symlink
        # race. Only fixed component names and fixed task basenames are used.
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory_fd = os.open(root, flags)
        try:
            for component in Path(CANDIDATE_DIRECTORY).parts:
                try: os.mkdir(component, mode=0o700, dir_fd=directory_fd)
                except FileExistsError: pass
                child_fd = os.open(component, flags, dir_fd=directory_fd)
                os.close(directory_fd); directory_fd = child_fd
            for task in paths:
                fd = os.open(f"{task}.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
                with os.fdopen(fd, "wb") as stream: stream.write(payloads[task])
        finally:
            os.close(directory_fd)
    return {task: str(path.relative_to(root)) for task, path in paths.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write-candidates", action="store_true", help="Write ignored candidate projections after all verification; never approve display")
    args = parser.parse_args()
    candidates = prepare_candidates(args.root)
    paths = write_candidates(args.root, candidates) if args.write_candidates else {}
    print(json.dumps({task: {"status": result["status"], "target_cohorts": len(result["view"]["targets"]) if result["view"] else 0,
                           "unavailable": result["unavailable"], "candidate_path": paths.get(task)} for task, result in candidates.items()}, sort_keys=True))


if __name__ == "__main__": main()
