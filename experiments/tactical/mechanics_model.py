"""Frozen grouped laboratory experiments; import and prepare never parse target CSVs.

Development is grouped training, not a chronological development/test split. It
saves EVERY outer prediction before the separately approved evaluation can score
one. Raw data, group membership, parameters and case predictions remain private.
This operational gate is auditable local process control, not authentication.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
import re
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from . import gates, mechanics as source
from .metrics import paired_cluster_interval, per_case_scores

VERSION = "mechanics-grouped-numerical-v1"
ROOT = Path(__file__).resolve().parents[2]
CONTEXT = tuple(field for field, *_ in source.PITCH)
BODY = tuple(field for field, *_ in source.BODY)
ALPHAS = (0.1, 1.0, 10.0, 100.0)
BASEBALL_MODELS = ("mean", "context", "augmented")
TENNIS_MODELS = ("B0", "B1")
CELLS = tuple((period, region) for period in (1, 2) for region in source.REGIONS)
SEED = 20261011
ELLIPSE_CUTOFF = -2 * math.log(0.1)
SPECS = {
    "baseball_mechanics": {
        "sport": "baseball", "protocol": "BASEBALL_MECHANICS_PROTOCOL_DRAFT.md",
        "rows": 571, "groups": 82, "folds": 5, "operations": 175, "fits": 170,
        "models": BASEBALL_MODELS,
        "counts": {"source_swings": 677, "source_athletes": 98,
                   "under_18_swings_excluded": 34, "under_18_athletes_excluded": 5,
                   "unknown_age_swings_excluded": 0, "adult_swings": 643, "adult_athletes": 93,
                   "adult_recorded_exit_velocity_swings": 638,
                   "adult_recorded_exit_velocity_athletes": 92, "adult_missing_exit_velocity": 5,
                   "adult_observed_exit_without_paired_context": 67,
                   "primary_swings": 571, "primary_athletes": 82},
    },
    "tennis_execution": {
        "sport": "tennis", "protocol": "TENNIS_EXECUTION_PROTOCOL_PUBLIC.md",
        "rows": 548, "groups": 8, "folds": 8, "operations": 16, "fits": 16,
        "models": TENNIS_MODELS,
        "counts": {"source_attempts": 567, "source_players": 8, "source_sessions": 8,
                   "stated_targets": 32, "source_first_period_attempts": 401,
                   "source_second_period_attempts": 166, "lets_excluded": 19,
                   "lets_with_missing_bounce": 5, "source_observed_bounce_pairs": 451,
                   "source_missing_speeds": 23, "nonlet_attempts": 548,
                   "nonlet_observed_bounce_pairs": 437, "nonlet_net_censored": 111,
                   "repeated_short_key_extra_rows_retained": 21,
                   "nonlet_player_session_cells": 14, "nonlet_player_period_region_cells": 64},
    },
}
CODE_PATHS = ("experiments/tactical/mechanics_model.py", "experiments/tactical/mechanics.py",
              "experiments/tactical/gates.py", "experiments/tactical/metrics.py",
              "experiments/tactical/__init__.py", "pyproject.toml")
REVIEW_PATHS = ("docs/tactical/INDEPENDENT_STAGE_ONE_REVIEW.md",
                "docs/tactical/INDEPENDENT_STAGE_ONE_REVIEW_MANIFEST.json",
                "docs/research/INDEPENDENT_METHOD_REVIEW.md",
                "docs/research/TACTICAL_MEASUREMENT_CONTRACT.json")


def _spec(task):
    if task not in SPECS:
        raise ValueError("Unsupported mechanics task")
    return SPECS[task]


def _hash(value):
    return hashlib.sha256(gates.canonical_bytes(value)).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text())


def _write_once(path, value):
    """Never overwrite or retry an existing artifact, including partial failures."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(gates.canonical_bytes(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return gates.digest_file(path)


def _check_counts(counts, task):
    if any(counts.get(key) != value for key, value in _spec(task)["counts"].items()):
        raise ValueError("Reviewed cohort/eligibility/censoring denominator changed")


def prepare(root=ROOT, task="baseball_mechanics"):
    """Hash source bytes; inspect existing aggregate metadata, never parse CSVs.

    This creates no approval. The lead must independently validate this binding
    before granting development. Existing private memberships are never rewritten.
    """
    root = Path(root).resolve()
    spec = _spec(task)
    sport = spec["sport"]
    paths, notice = source.validate_sources(root, sport)
    summary_path = f"reports/tactical/mechanics/{sport}_summary.json"
    plan_path = f"data/tactical/mechanics/{sport}_split_manifest.json"
    summary = _read(root / summary_path)
    plan = _read(root / plan_path)
    _check_counts(summary["population"]["counts"], task)
    protocol = f"docs/tactical/{spec['protocol']}"
    if (summary["protocol"]["sha256"] != gates.digest_file(root / protocol)
            or summary["split_description"]["private_membership_sha256"] != gates.digest_file(root / plan_path)
            or summary["source"]["adapter_sha256"] != gates.digest_file(root / "experiments/tactical/mechanics.py")
            or summary["source"]["manifest_sha256"] != notice["manifest_sha256"]
            or summary["source"]["files"] != notice["files"]):
        raise PermissionError("Descriptive source/protocol/group-plan provenance changed")
    _validate_plan_structure(plan, task)
    data = {gates.relative_path(root, path): source.OBM_HASHES[name] if sport == "baseball" else source.BYU_HASHES[name]
            for name, path in paths.items()}
    manifest = "docs/research/baseball_football/openbiomechanics_manifest.json" if sport == "baseball" else "docs/research/tennis/source_manifest.json"
    for path in (summary_path, plan_path, manifest, *REVIEW_PATHS):
        data[path] = gates.digest_file(root / path)
    return gates.prepare_binding(root, task, protocol, CODE_PATHS, data, metadata={
        "version": VERSION, "design": "fixed grouped outer predictions; separate gated performance inspection",
        "rows": spec["rows"], "groups": spec["groups"], "outer_folds": spec["folds"],
        "fit_limit": spec["fits"], "operation_limit": spec["operations"], "retry_limit": 0,
        "feature_allowlist": {"context": list(CONTEXT), "augmented": list(CONTEXT + BODY)} if sport == "baseball" else ["serve_period", "region", "known_stated_target"],
        "models": list(spec["models"]), "designated_candidate": "augmented" if sport == "baseball" else "B1",
        "split_plan": plan_path, "source_summary": summary_path,
        "group_plan_sha256": gates.digest_file(root / plan_path), "publication": "private_local_only",
    })


def _validate_plan_structure(plan, task):
    spec = _spec(task)
    if (plan.get("version") != source.VERSION or plan.get("sport") != spec["sport"]
            or plan.get("observations") != spec["rows"] or plan.get("groups") != spec["groups"]
            or plan.get("outcome_independent") is not True or len(plan.get("folds", [])) != spec["folds"]):
        raise ValueError("Frozen grouped plan contract changed")
    tests = []
    universe = None
    for i, fold in enumerate(plan["folds"]):
        training, test = fold["training_groups"], fold["test_groups"]
        if fold["fold"] != i or len(training) != len(set(training)) or len(test) != len(set(test)):
            raise ValueError("Duplicate/invalid frozen fold membership")
        combined = set(training) | set(test)
        if not training or not test or set(training) & set(test) or len(combined) != spec["groups"]:
            raise ValueError("Invalid grouped train/test partition")
        if universe is not None and universe != combined:
            raise ValueError("Outer folds have unequal group universes")
        universe = combined
        tests.extend(test)
        if spec["sport"] == "baseball":
            inner = fold["inner_assignment"]
            if set(inner) != set(training) or set(inner.values()) != set(range(4)):
                raise ValueError("Invalid inner training-only partition")
        elif len(test) != 1:
            raise ValueError("BYU must withhold exactly one complete player")
    if len(tests) != len(set(tests)) or set(tests) != universe:
        raise ValueError("Each group must be held out exactly once")
    if any(not isinstance(group, str) or not re.fullmatch(r"[0-9a-f]{64}", group) for group in universe):
        raise ValueError("Private memberships must use the frozen opaque group digests")
    ordered = sorted(universe)
    for fold in plan["folds"]:
        i = fold["fold"]
        test = ([group for j, group in enumerate(ordered) if j % 5 == i]
                if spec["sport"] == "baseball" else [ordered[i]])
        training = [group for group in ordered if group not in test]
        if fold["test_groups"] != test or fold["training_groups"] != training:
            raise ValueError("Group membership differs from the exact salted-hash order")
        if spec["sport"] == "baseball":
            inner_order = sorted(training, key=lambda group: hashlib.sha256((f"inner-{i}|" + group).encode()).hexdigest())
            if fold["inner_assignment"] != {group: j % 4 for j, group in enumerate(inner_order)}:
                raise ValueError("Inner memberships differ from the exact salted-hash assignment")


class LabelStore:
    """Explicit fold target access; the parser's eligibility QA is retrospective.

    All source labels are parsed only after stage approval. A fit receives labels
    only via its explicit training indices; prediction receives only contexts.
    Outer scoring additionally requires evaluation approval and the full freeze.
    """
    def __init__(self, labels):
        self._labels = tuple(labels)
        self.accesses = []

    def take(self, indices, *, allowed, purpose):
        indices = tuple(int(i) for i in indices)
        if not set(indices) <= set(allowed) or len(indices) != len(set(indices)):
            raise PermissionError("Target read escapes this training/validation fold")
        self.accesses.append({"purpose": purpose, "indices_sha256": _hash(indices), "rows": len(indices)})
        return [self._labels[i] for i in indices]


def _load_cohort(root, task, stage):
    """Stage authorization MUST occur before any real CSV reader is called."""
    gates.require_stage(root, task, stage)
    sport = _spec(task)["sport"]
    paths, _ = source.validate_sources(root, sport)
    if sport == "baseball":
        rows, counts = source.adapt_baseball(
            source.read_csv(paths["baseball_hitting/data/metadata.csv"], source.META_COLUMNS),
            source.read_csv(paths["baseball_hitting/data/poi/poi_metrics.csv"], required=("session_swing", "session", *BODY)),
            source.read_csv(paths["baseball_hitting/data/poi/hittrax.csv"], source.HIT_COLUMNS))
        contexts = [{"row": i, "group": source.opaque_group(sport, row.group),
                     "session": _hash([sport, row.session]),
                     "context": [row.pitch[field] for field in CONTEXT],
                     "augmented": [row.pitch[field] for field in CONTEXT] + [row.body[field] for field in BODY]}
                    for i, row in enumerate(rows)]
        labels = [row.observed["exit_velocity"] for row in rows]
        _finite(labels)
        for context in contexts:
            _finite(context["augmented"])
    else:
        rows, counts = source.adapt_tennis(
            source.read_csv(paths["data/serves.csv"], source.SERVE_COLUMNS),
            source.read_csv(paths["data/targets.csv"], source.TARGET_COLUMNS))
        contexts = [{"row": i, "group": source.opaque_group(sport, row.group),
                     "session": _hash([sport, row.session]), "period": row.period,
                     "region": row.region, "target": [row.target_x, row.target_y]}
                    for i, row in enumerate(rows)]
        labels = [{"net": not row.clear_net,
                   "error": None if not row.clear_net else [row.dx, row.dy]} for row in rows]
        _validate_hurdle_labels(labels)
    _check_counts(counts, task)
    frozen = _read(Path(root) / f"data/tactical/mechanics/{sport}_split_manifest.json")
    _validate_plan_structure(frozen, task)
    if source.split_plan(rows, sport) != frozen:
        raise PermissionError("Exact deterministic source group memberships changed")
    if len(contexts) != _spec(task)["rows"] or len({r["group"] for r in contexts}) != _spec(task)["groups"]:
        raise ValueError("Primary cohort changed")
    return contexts, LabelStore(labels), frozen, counts


def _finite(value):
    a = np.asarray(value, dtype=np.float64)
    if not np.isfinite(a).all():
        raise ValueError("Nonfinite numerical input/output; no imputation or clipping")
    return a


def athlete_weights(groups):
    groups = np.asarray(groups)
    if groups.ndim != 1 or not len(groups) or any(not isinstance(g, str) or not g for g in groups):
        raise ValueError("One nonempty athlete identity per training row is required")
    unique, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
    return len(groups) / (len(unique) * counts[inverse].astype(np.float64))


def weighted_standardizer(x, weights):
    x, weights = _finite(x), _finite(weights)
    if x.ndim != 2 or not len(x) or weights.shape != (len(x),) or (weights <= 0).any():
        raise ValueError("Invalid weighted training matrix")
    # Weighted floating-point reduction can move a repeated decimal value by an
    # ulp, manufacturing a tiny positive variance. Detect literal constants from
    # training observations, not from the rounded weighted reduction.
    constant = np.all(x == x[0], axis=0)
    mean = np.average(x, axis=0, weights=weights)
    mean[constant] = x[0, constant]
    variance = np.average((x - mean) ** 2, axis=0, weights=weights)
    variance[constant] = 0.0
    _finite(mean); _finite(variance)
    active = ~constant & (variance > 0)
    return {"mean": mean.tolist(), "variance": variance.tolist(), "active": active.tolist(),
            "zero_variance_columns": int((~active).sum()), "variance_denominator": "sum_training_weights"}


def transform(x, preprocessing):
    x = _finite(x)
    mean, variance = _finite(preprocessing["mean"]), _finite(preprocessing["variance"])
    active = np.asarray(preprocessing["active"], dtype=bool)
    if (x.ndim != 2 or x.shape[1] != len(mean) or variance.shape != mean.shape
            or active.shape != mean.shape or (variance < 0).any() or not np.array_equal(active, variance > 0)):
        raise ValueError("Invalid saved standardizer")
    # Inactive columns are excluded from the fitted coefficient vector entirely.
    return (x[:, active] - mean[active]) / np.sqrt(variance[active])


def regression_metrics(y, prediction, groups):
    y, prediction = _finite(y), _finite(prediction)
    groups = np.asarray(groups)
    if y.ndim != 1 or not len(y) or prediction.shape != y.shape or groups.shape != y.shape:
        raise ValueError("Regression score dimensions disagree")
    error = y - prediction
    unique = np.unique(groups)
    maes = [float(np.abs(error[groups == group]).mean()) for group in unique]
    rmses = [float(np.sqrt(np.square(error[groups == group]).mean())) for group in unique]
    result = {"macro_MAE": float(np.mean(maes)), "macro_RMSE": float(np.mean(rmses)),
              "row_MAE": float(np.abs(error).mean()), "row_RMSE": float(np.sqrt(np.square(error).mean())),
              "rows": len(y), "groups": len(unique)}
    # A distinct scalar recomputation challenges reduction order/denominators.
    independent = []
    independent_rmse = []
    for group in unique:
        e = [float(a) - float(b) for a, b, g in zip(y, prediction, groups) if g == group]
        independent.append(math.fsum(abs(v) for v in e) / len(e))
        independent_rmse.append(math.sqrt(math.fsum(v * v for v in e) / len(e)))
    if not np.allclose([result["macro_MAE"], result["macro_RMSE"]],
                       [math.fsum(independent) / len(unique), math.fsum(independent_rmse) / len(unique)], rtol=0, atol=1e-10):
        raise ValueError("Independent macro metric recomputation failed")
    return result


def choose_alpha(scores):
    if set(scores) != set(ALPHAS) or not np.isfinite(list(scores.values())).all():
        raise ValueError("The complete fixed alpha grid is required")
    minimum = min(scores.values())
    return max(alpha for alpha in ALPHAS if scores[alpha] <= minimum + 1e-12)


def _ridge_fit(x, y, groups, alpha):
    """Called only after an exact durable budget reservation by Runner."""
    if alpha not in ALPHAS:
        raise ValueError("Unapproved ridge alpha")
    x, y = _finite(x), _finite(y)
    weights = athlete_weights(groups)
    if y.shape != (len(x),):
        raise ValueError("One training target per row is required")
    prep = weighted_standardizer(x, weights)
    design = transform(x, prep)
    if design.shape[1] == 0:
        raise ValueError("All training columns constant; stop for review, no substituted estimator")
    estimator = Ridge(alpha=alpha, fit_intercept=True, solver="svd", copy_X=True)
    estimator.fit(design, y, sample_weight=weights)
    coef, intercept = _finite(estimator.coef_), float(estimator.intercept_)
    if coef.shape != (design.shape[1],) or not math.isfinite(intercept):
        raise ValueError("Malformed fitted ridge parameters")
    model = {"kind": "ridge", "alpha": alpha, "solver": "svd", "dtype": "float64",
             "objective": "sum(weight * residual**2) + alpha * sum(standardized_coef**2)",
             "preprocessing": prep, "coef": coef.tolist(), "intercept": intercept}
    if not np.allclose(predict_regression(model, x), estimator.predict(design), rtol=0, atol=1e-10):
        raise ValueError("Serialized ridge prediction parity failed")
    return model


def predict_regression(model, x):
    x = _finite(x)
    if x.ndim != 2:
        raise ValueError("Predictors must be a numeric matrix")
    if model["kind"] == "mean":
        result = np.full(len(x), model["value"], dtype=np.float64)
    elif model["kind"] == "ridge":
        design = transform(x, model["preprocessing"])
        coef = _finite(model["coef"])
        if coef.shape != (design.shape[1],):
            raise ValueError("Serialized coefficient dimension mismatch")
        result = design @ coef + float(model["intercept"])
    else:
        raise ValueError("Unknown regression model")
    return _finite(result)


def _validate_hurdle_labels(labels):
    if not labels:
        raise ValueError("Empty hurdle training/scoring sample")
    for label in labels:
        if type(label.get("net")) is not bool:
            raise ValueError("Net outcome must be boolean")
        if label["net"]:
            if label.get("error") is not None:
                raise ValueError("Net-censored attempt cannot have bounce coordinates")
        elif label.get("error") is None or _finite(label["error"]).shape != (2,):
            raise ValueError("Observed bounce requires exactly two finite error coordinates")


def _branch(p_net, mu, q):
    mu, q = _finite(mu), _finite(q)
    if not 0 < p_net < 1 or mu.shape != (2,) or q.shape != (2, 2):
        raise ValueError("Invalid hurdle parameters")
    covariance = q - np.outer(mu, mu) + 0.0025 * np.eye(2, dtype=np.float64)
    _validate_gaussian(mu, covariance)
    return {"p_net": float(p_net), "mu": mu.tolist(), "Q": q.tolist(), "covariance": covariance.tolist()}


def _validate_gaussian(mu, covariance):
    mu, covariance = _finite(mu), _finite(covariance)
    if mu.shape != (2,) or covariance.shape != (2, 2) or not np.allclose(covariance, covariance.T, rtol=0, atol=1e-12):
        raise ValueError("Malformed Gaussian mean/covariance")
    try:
        chol = np.linalg.cholesky(covariance)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Covariance is not positive definite; stop without clipping") from exc
    return mu, covariance, chol


def hurdle_parameters(contexts, labels, form):
    """Pure fixed raw-moment formula; no learned hyperparameters or speed input."""
    _validate_hurdle_labels(labels)
    if form not in TENNIS_MODELS or len(contexts) != len(labels):
        raise ValueError("Invalid fixed hurdle form or row count")
    if any((r["period"], r["region"]) not in CELLS for r in contexts):
        raise ValueError("Unknown supplied period/region")
    errors = _finite([label["error"] for label in labels if not label["net"]])
    if not len(errors):
        raise ValueError("No observed training bounces")
    mu = errors.mean(axis=0)
    q = np.einsum("ni,nj->ij", errors, errors) / len(errors)
    p_net = (sum(label["net"] for label in labels) + 1) / (len(labels) + 2)
    pooled = _branch(p_net, mu, q)
    cells = []
    if form == "B1":
        for period, region in CELLS:
            selected = [label for row, label in zip(contexts, labels) if (row["period"], row["region"]) == (period, region)]
            observed = _finite([label["error"] for label in selected if not label["net"]]).reshape(-1, 2)
            n, n_bounce = len(selected), len(observed)
            total = observed.sum(axis=0)
            moment = observed.T @ observed
            branch = _branch((sum(label["net"] for label in selected) + 20 * p_net) / (n + 20),
                             (total + 20 * mu) / (n_bounce + 20),
                             (moment + 20 * q) / (n_bounce + 20))
            cells.append({"period": period, "region": region, "attempts": n, "bounces": n_bounce,
                          "empty_attempt_cell": n == 0, "empty_bounce_cell": n_bounce == 0, **branch})
    return {"kind": "observed_data_hurdle", "form": form, "pooled": pooled, "cells": cells,
            "smoothing": 1, "shrinkage": 20, "diagonal_addition_m2": 0.0025,
            "training_weighting": "equal attempts", "raw_moment_denominator": "observed training bounce count"}


def predict_hurdle(model, contexts):
    if (model.get("form") not in TENNIS_MODELS or model.get("smoothing") != 1
            or model.get("shrinkage") != 20 or model.get("diagonal_addition_m2") != 0.0025):
        raise ValueError("Unapproved hurdle model")
    indexed = {(r["period"], r["region"]): r for r in model["cells"]}
    if model["form"] == "B1" and (set(indexed) != set(CELLS) or len(model["cells"]) != 8):
        raise ValueError("Missing/duplicate fixed hurdle cell")
    result = []
    for row in contexts:
        if (row["period"], row["region"]) not in CELLS:
            raise ValueError("Unknown period/region at prediction")
        branch = model["pooled"] if model["form"] == "B0" else indexed[row["period"], row["region"]]
        mu, covariance, _ = _validate_gaussian(branch["mu"], branch["covariance"])
        if not 0 < branch["p_net"] < 1:
            raise ValueError("Invalid saved net probability")
        target = _finite(row["target"])
        if target.shape != (2,):
            raise ValueError("Exact stated target is required")
        result.append({"p_net": branch["p_net"], "mu": mu.tolist(), "covariance": covariance.tolist(),
                       "mean_bounce": (target + mu).tolist()})
    return result


def hurdle_losses(labels, predictions):
    _validate_hurdle_labels(labels)
    if len(labels) != len(predictions):
        raise ValueError("Hurdle score dimensions disagree")
    result = {name: [] for name in ("joint_NLL", "net_Brier", "location_NLL", "euclidean_error", "ellipse90_covered")}
    for label, prediction in zip(labels, predictions):
        p = float(prediction["p_net"])
        if not 0 < p < 1:
            raise ValueError("Invalid branch probability; no loss clipping")
        result["net_Brier"].append((p - int(label["net"])) ** 2)
        if label["net"]:
            result["joint_NLL"].append(-math.log(p))
            for name in ("location_NLL", "euclidean_error", "ellipse90_covered"):
                result[name].append(None)
            continue  # No Gaussian call, bounce read, or invented coordinate for a net.
        mu, covariance, chol = _validate_gaussian(prediction["mu"], prediction["covariance"])
        difference = _finite(label["error"]) - mu
        z = np.linalg.solve(chol, difference)
        mahalanobis = float(z @ z)
        location = math.log(2 * math.pi) + float(np.log(np.diag(chol)).sum()) + 0.5 * mahalanobis
        sign, logdet = np.linalg.slogdet(covariance)
        independent = math.log(2 * math.pi) + .5 * (float(logdet) + float(difference @ np.linalg.solve(covariance, difference)))
        if sign <= 0 or not math.isclose(location, independent, rel_tol=0, abs_tol=1e-9):
            raise ValueError("Independent Gaussian density recomputation failed")
        result["joint_NLL"].append(-math.log1p(-p) + location)
        result["location_NLL"].append(location)
        result["euclidean_error"].append(float(np.linalg.norm(difference)))
        result["ellipse90_covered"].append(float(mahalanobis <= ELLIPSE_CUTOFF))
    for values in result.values():
        _finite([v for v in values if v is not None])
    shared_brier = per_case_scores(np.array([int(x["net"]) for x in labels]),
                                  [p["p_net"] for p in predictions])["brier"]
    if not np.allclose(shared_brier, result["net_Brier"], rtol=0, atol=1e-14):
        raise ValueError("Independent Brier recomputation failed")
    return result


def _equal_group_mean(values, groups):
    values, groups = _finite(values), np.asarray(groups)
    if values.ndim != 1 or not len(values) or groups.shape != values.shape:
        raise ValueError("Invalid equal-group aggregation")
    return float(np.mean([values[groups == g].mean() for g in np.unique(groups)]))


def cluster_bootstrap(difference, groups, expected_groups):
    difference, groups = _finite(difference), np.asarray(groups)
    unique = np.unique(groups)
    if difference.ndim != 1 or groups.shape != difference.shape or len(unique) != expected_groups:
        raise ValueError("Bootstrap denominator/group universe changed")
    means = np.array([difference[groups == g].mean() for g in unique])
    indices = np.random.Generator(np.random.PCG64(SEED)).integers(0, len(unique), size=(2000, len(unique)))
    boot = means[indices].mean(axis=1)
    interval = np.quantile(boot, [.025, .975], method="linear")
    independent = paired_cluster_interval(difference, groups, replicates=2000, confidence=.95,
                                          seed=SEED, minimum_groups=1, weighting="group")
    if not np.allclose(interval, independent["interval"], rtol=0, atol=1e-12):
        raise ValueError("Independent saved-loss cluster bootstrap differs")
    return {"difference": float(means.mean()), "interval95": interval.tolist(), "groups": len(unique),
            "replicates": 2000, "seed": SEED, "generator": "PCG64", "draw_shape": [2000, len(unique)],
            "percentile_method": "linear", "unit": "whole held-out participant",
            "limitation": "Conditional on saved grouped predictions; overlapping training sets and selection/sensor/population biases not captured"}


def operation_schedule(task):
    """Exact named slots; unused slots cannot become alternate candidates/retries."""
    spec = _spec(task)
    schedule = {}
    for outer in range(spec["folds"]):
        if spec["sport"] == "baseball":
            schedule[f"outer{outer}/mean"] = {"outer": outer, "model": "mean", "kind": "analytic_mean"}
            for block in ("context", "augmented"):
                for alpha in ALPHAS:
                    for inner in range(4):
                        schedule[f"outer{outer}/{block}/alpha{alpha:g}/inner{inner}"] = {
                            "outer": outer, "model": block, "alpha": alpha, "inner": inner, "kind": "ridge_fit"}
                schedule[f"outer{outer}/{block}/refit"] = {"outer": outer, "model": block, "kind": "ridge_refit"}
        else:
            for form in TENNIS_MODELS:
                schedule[f"outer{outer}/{form}"] = {"outer": outer, "model": form, "kind": "hurdle_fit"}
    assert len(schedule) == spec["operations"]
    return schedule


class Runner:
    def __init__(self, root, task):
        self.root, self.task = Path(root).resolve(), task
        self.spec = _spec(task)
        self.directory = gates.task_dir(self.root, task)
        self.schedule = operation_schedule(task)
        self.used = set()

    @contextmanager
    def _stage(self, stage):
        authorization = gates.require_stage(self.root, self.task, stage)
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / ".run.lock").open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                # A failed or interrupted stage leaves this permanent reservation.
                _write_once(self.directory / f"{stage}_started.json", {
                    "stage": stage, "binding_sha256": authorization["binding_sha256"],
                    "verified_at_utc": authorization["verified_at_utc"], "retry_allowed": False})
                yield authorization
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _reserve(self, slot, extra=None):
        if slot not in self.schedule or slot in self.used:
            raise PermissionError("Unknown or repeated fixed operation slot")
        permitted = {"selected_alpha"} if self.schedule[slot]["kind"] == "ridge_refit" else set()
        if set(extra or {}) != permitted or (permitted and extra["selected_alpha"] not in ALPHAS):
            raise PermissionError("Only the fixed refit may supply its selected approved alpha")
        config = {**self.schedule[slot], **(extra or {})}
        if any(config[k] != v for k, v in self.schedule[slot].items()):
            raise PermissionError("Reserved candidate configuration changed")
        gates.record_operation(self.root, self.task, "development", slot, config,
                               self.spec["operations"], kind=self.schedule[slot]["kind"])
        self.used.add(slot)

    def _artifact(self, relative, value):
        path = self.directory / relative
        digest = _write_once(path, value)
        return {"path": gates.relative_path(self.root, path), "sha256": digest}

    def _train_baseball_fold(self, contexts, labels, fold):
        outer = fold["fold"]
        training = [r["row"] for r in contexts if r["group"] in fold["training_groups"]]
        held_out = [r for r in contexts if r["group"] in fold["test_groups"]]
        by_id = {r["row"]: r for r in contexts}
        train_y = _finite(labels.take(training, allowed=training, purpose=f"outer{outer}/training"))
        groups = [by_id[i]["group"] for i in training]
        self._reserve(f"outer{outer}/mean")
        models = {"mean": {"kind": "mean", "value": float(np.average(train_y, weights=athlete_weights(groups)))}}
        selections = {}
        for block in ("context", "augmented"):
            scores = {}
            inner_artifacts = []
            for alpha in ALPHAS:
                ys, ps, gs = [], [], []
                for inner in range(4):
                    train = [i for i in training if fold["inner_assignment"][by_id[i]["group"]] != inner]
                    valid = [i for i in training if fold["inner_assignment"][by_id[i]["group"]] == inner]
                    if not train or not valid:
                        raise ValueError("Empty inner fold")
                    y = _finite(labels.take(train, allowed=train, purpose=f"outer{outer}/{block}/inner{inner}/train"))
                    self._reserve(f"outer{outer}/{block}/alpha{alpha:g}/inner{inner}")
                    model = _ridge_fit([by_id[i][block] for i in train], y, [by_id[i]["group"] for i in train], alpha)
                    pred = predict_regression(model, [by_id[i][block] for i in valid])
                    inner_artifacts.append({"alpha": alpha, "inner_fold": inner,
                                            "training_rows_sha256": _hash(train), "validation_row_ids": valid,
                                            "model": model, "predictions": pred.tolist()})
                    val_y = labels.take(valid, allowed=valid, purpose=f"outer{outer}/{block}/inner{inner}/selection")
                    ys.extend(val_y); ps.extend(pred.tolist()); gs.extend(by_id[i]["group"] for i in valid)
                if len(ys) != len(training):
                    raise ValueError("Incomplete inner out-of-fold predictions")
                scores[alpha] = regression_metrics(ys, ps, gs)["macro_MAE"]
            alpha = choose_alpha(scores)
            self._reserve(f"outer{outer}/{block}/refit", {"selected_alpha": alpha})
            models[block] = _ridge_fit([by_id[i][block] for i in training], train_y, groups, alpha)
            selections[block] = {"alpha": alpha, "inner_macro_MAE": {str(k): v for k, v in scores.items()},
                                 "saved_inner_models_and_predictions": inner_artifacts}
        prediction = {name: predict_regression(model, [r["context" if name == "mean" else name] for r in held_out]).tolist()
                      for name, model in models.items()}
        return models, {"fold": outer, "row_ids": [r["row"] for r in held_out], "predictions": prediction}, selections

    def _train_tennis_fold(self, contexts, labels, fold):
        outer = fold["fold"]
        training = [r for r in contexts if r["group"] in fold["training_groups"]]
        held_out = [r for r in contexts if r["group"] in fold["test_groups"]]
        indices = [r["row"] for r in training]
        train_y = labels.take(indices, allowed=indices, purpose=f"outer{outer}/training")
        bounces = [row for row, label in zip(training, train_y) if not label["net"]]
        if len(training) < 100 or len(bounces) < 50 or len({r["group"] for r in bounces}) < 3:
            raise ValueError("Prespecified BYU training support gate failed")
        models = {}
        for form in TENNIS_MODELS:
            self._reserve(f"outer{outer}/{form}")
            models[form] = hurdle_parameters(training, train_y, form)
        prediction = {name: predict_hurdle(model, held_out) for name, model in models.items()}
        support = {"training_attempts": len(training), "training_bounces": len(bounces),
                   "training_players_with_bounces": len({r["group"] for r in bounces}),
                   "shared_sessions": len({r["session"] for r in training} & {r["session"] for r in held_out}),
                   "empty_attempt_cells": sum(c["empty_attempt_cell"] for c in models["B1"]["cells"]),
                   "empty_bounce_cells": sum(c["empty_bounce_cell"] for c in models["B1"]["cells"])}
        return models, {"fold": outer, "row_ids": [r["row"] for r in held_out], "predictions": prediction}, support

    def develop(self):
        with self._stage("development") as authorization:
            contexts, labels, plan, counts = _load_cohort(self.root, self.task, "development")
            artifacts = []
            metadata = []
            for fold in plan["folds"]:
                train = self._train_baseball_fold if self.spec["sport"] == "baseball" else self._train_tennis_fold
                models, prediction, details = train(contexts, labels, fold)
                saved_model = self._artifact(f"models/outer{fold['fold']}.json", models)
                saved_prediction = self._artifact(f"predictions/outer{fold['fold']}.json", prediction)
                artifacts.append({"fold": fold["fold"], "model": saved_model, "prediction": saved_prediction})
                metadata.append({"fold": fold["fold"], "details": details})
            if self.used != set(self.schedule):
                raise ValueError("Fixed operation schedule incomplete")
            details_artifact = self._artifact("development_details.json", {
                "fold_details": metadata, "target_access_audit": labels.accesses,
                "outer_performance_inspected": False, "counts": counts})
            ledger = self.directory / "development_operations.jsonl"
            freeze = {"schema_version": 1, "task": self.task, "binding_sha256": authorization["binding_sha256"],
                      "status": "all_grouped_outer_predictions_saved_without_outer_scores", "version": VERSION,
                      "models": list(self.spec["models"]), "designated_candidate": "augmented" if self.spec["sport"] == "baseball" else "B1",
                      "outer_folds": artifacts, "details": details_artifact,
                      "operation_ledger": {"path": gates.relative_path(self.root, ledger), "sha256": gates.digest_file(ledger)},
                      "context_sha256": _hash(contexts), "rows": len(contexts),
                      "operation_count": len(self.used), "fit_count": self.spec["fits"],
                      "outer_scores": "not computed; requires separate global evaluation approval",
                      "publication": "private_local_only; separate rights/privacy review required"}
            digest = _write_once(self.directory / "SELECTION_FREEZE.json", freeze)
            return {"task": self.task, "status": freeze["status"], "selection_sha256": digest,
                    "fit_count": self.spec["fits"], "operation_count": len(self.used), "outer_scores_computed": False}

    def _verified_freeze(self, binding):
        freeze = _read(self.directory / "SELECTION_FREEZE.json")
        if (freeze.get("binding_sha256") != binding["binding_sha256"] or freeze.get("task") != self.task
                or freeze.get("version") != VERSION or freeze.get("rows") != self.spec["rows"]
                or freeze.get("models") != list(self.spec["models"])
                or freeze.get("operation_count") != self.spec["operations"]
                or freeze.get("fit_count") != self.spec["fits"]
                or [f["fold"] for f in freeze["outer_folds"]] != list(range(self.spec["folds"]))):
            raise PermissionError("Incomplete or incompatible selection freeze")
        entries = [freeze["details"], freeze["operation_ledger"]]
        entries += [f[k] for f in freeze["outer_folds"] for k in ("model", "prediction")]
        for entry in entries:
            path = gates.resolve(self.root, entry["path"])
            if not path.is_relative_to(self.directory) or gates.digest_file(path) != entry["sha256"]:
                raise PermissionError("Frozen model/prediction/selection artifact changed")
        journal = [json.loads(line) for line in gates.resolve(self.root, freeze["operation_ledger"]["path"]).read_text().splitlines()]
        if len(journal) != self.spec["operations"] or {r["operation_id"] for r in journal} != set(self.schedule):
            raise PermissionError("Incomplete fixed fit-operation journal")
        previous = None
        for attempt, row in enumerate(journal, start=1):
            body = {k: v for k, v in row.items() if k != "record_sha256"}
            if row["previous_record_sha256"] != previous or _hash(body) != row["record_sha256"]:
                raise PermissionError("Fit journal hash chain changed")
            if (row.get("binding_sha256") != binding["binding_sha256"] or row.get("task") != self.task
                    or row.get("stage") != "development" or row.get("attempt") != attempt
                    or row.get("limit") != self.spec["operations"]
                    or row.get("kind") != self.schedule[row["operation_id"]]["kind"]):
                raise PermissionError("Fit journal binding/stage/budget identity changed")
            if any(row["config"].get(k) != v for k, v in self.schedule[row["operation_id"]].items()):
                raise PermissionError("Fit operation deviates from fixed candidate grid")
            previous = row["record_sha256"]
        return freeze

    def evaluate(self):
        with self._stage("evaluation") as authorization:
            freeze = self._verified_freeze(authorization["binding"])
            # Every saved model/prediction is checked before this label-bearing load.
            contexts, labels, plan, _ = _load_cohort(self.root, self.task, "evaluation")
            if _hash(contexts) != freeze["context_sha256"]:
                raise PermissionError("Feature contexts changed since saved predictions")
            predictions = {model: [None] * len(contexts) for model in self.spec["models"]}
            fold_ids = [None] * len(contexts)
            by_id = {row["row"]: row for row in contexts}
            for record, fold in zip(freeze["outer_folds"], plan["folds"]):
                models = _read(gates.resolve(self.root, record["model"]["path"]))
                saved = _read(gates.resolve(self.root, record["prediction"]["path"]))
                expected = [r["row"] for r in contexts if r["group"] in fold["test_groups"]]
                if saved["row_ids"] != expected or saved["fold"] != fold["fold"] or set(saved["predictions"]) != set(self.spec["models"]):
                    raise ValueError("Saved outer row membership or model pairing changed")
                held_out = [by_id[i] for i in expected]
                for model in self.spec["models"]:
                    old = saved["predictions"][model]
                    new = (predict_hurdle(models[model], held_out) if self.spec["sport"] == "tennis"
                           else predict_regression(models[model], [r["context" if model == "mean" else model] for r in held_out]).tolist())
                    if gates.canonical_bytes(old) != gates.canonical_bytes(new):
                        raise ValueError("Saved prediction/model serialization parity failed")
                    if len(old) != len(expected):
                        raise ValueError("Saved prediction denominator mismatch")
                    for i, prediction in zip(expected, old):
                        if predictions[model][i] is not None:
                            raise ValueError("Duplicate outer prediction")
                        predictions[model][i] = prediction
                for i in expected:
                    fold_ids[i] = fold["fold"]
            if any(v is None for a in predictions.values() for v in a) or any(f is None for f in fold_ids):
                raise ValueError("Not all paired outer predictions are saved")
            gates.record_operation(self.root, self.task, "evaluation", "score_all_saved_outer_predictions",
                                   {"selection_sha256": gates.digest_file(self.directory / "SELECTION_FREEZE.json")}, 1, kind="score")
            y = labels.take(range(len(contexts)), allowed=range(len(contexts)), purpose="all_saved_outer_predictions/evaluation")
            report, private = (score_baseball(y, predictions, contexts, fold_ids) if self.spec["sport"] == "baseball"
                               else score_tennis(y, predictions, contexts, fold_ids))
            report.update(task=self.task, status="evaluation_complete", binding_sha256=authorization["binding_sha256"],
                          selection_sha256=gates.digest_file(self.directory / "SELECTION_FREEZE.json"),
                          new_model_selection=False, recalibrator_fits=0, independent_recomputation=True,
                          publication="Local aggregate only; no public release authorized")
            self._artifact("private_evaluation_details.json", private)
            artifact = self._artifact("evaluation_report.json", report)
            # No participant/fold outputs enter reports or the workbench automatically.
            return {"task": self.task, "status": report["status"], "report": artifact, "summary": report}


def score_baseball(y, predictions, contexts, folds):
    y = _finite(y)
    groups = np.asarray([r["group"] for r in contexts])
    folds = np.asarray(folds)
    if len(y) != 571 or len(np.unique(groups)) != 82 or set(folds) != set(range(5)):
        raise ValueError("Baseball score denominator changed")
    summaries = {model: regression_metrics(y, predictions[model], groups) for model in BASEBALL_MODELS}
    difference = np.abs(y - _finite(predictions["augmented"])) - np.abs(y - _finite(predictions["context"]))
    interval = cluster_bootstrap(difference, groups, 82)
    by_fold = [{"fold": int(fold), "rows": int((folds == fold).sum()),
                "groups": len(np.unique(groups[folds == fold])),
                "augmented_minus_context_macro_MAE": _equal_group_mean(difference[folds == fold], groups[folds == fold])}
               for fold in range(5)]
    report = {"rows": 571, "athletes": 82, "unit": "mph", "models": summaries,
              "primary_comparison": "augmented minus context macro-athlete MAE", "primary": interval,
              "outer_folds": by_fold, "practical_threshold_mph": .5,
              "practical_threshold_met": interval["difference"] <= -.5 and interval["interval95"][1] < 0,
              "macro_RMSE_definition": "mean of within-athlete square-root MSEs",
              "claims": ["Retrospective foot-plant association in adult paired machine-hitting records",
                         "Nested unseen-athlete procedure; no untouched final lockbox or future-session test",
                         "No causal technique, calibrated interval, professional transfer or individual ranking claim"]}
    return report, {"participant_results_exported": False}


def score_tennis(y, predictions, contexts, folds):
    groups = np.asarray([r["group"] for r in contexts])
    sessions = np.asarray([r["session"] for r in contexts])
    folds = np.asarray(folds)
    if (len(y) != 548 or len(np.unique(groups)) != 8 or sum(v["net"] for v in y) != 111
            or set(folds) != set(range(8)) or len(np.unique(sessions)) != 8):
        raise ValueError("BYU score denominator/censoring changed")
    losses = {model: hurdle_losses(y, predictions[model]) for model in TENNIS_MODELS}
    summaries = {}
    for model, values in losses.items():
        summaries[model] = {}
        for metric, raw in values.items():
            keep = np.asarray([v is not None for v in raw])
            values_kept = _finite([v for v in raw if v is not None])
            summaries[model][metric] = {"attempt_weighted": float(values_kept.mean()),
                                       "equal_player": _equal_group_mean(values_kept, groups[keep]),
                                       "attempts": int(keep.sum()), "players": len(np.unique(groups[keep]))}
    difference = _finite(losses["B1"]["joint_NLL"]) - _finite(losses["B0"]["joint_NLL"])
    interval = cluster_bootstrap(difference, groups, 8)
    session_exclusion = []
    for index, session in enumerate(np.unique(sessions)):
        keep = sessions != session
        session_exclusion.append({"private_session_label": f"S{index + 1}", "remaining_players": len(np.unique(groups[keep])),
                                  "remaining_attempts": int(keep.sum()), "contrast": _equal_group_mean(difference[keep], groups[keep])})
    player_details = [{"private_player_label": f"P{fold + 1}", "attempts": int((folds == fold).sum()),
                       "B1_minus_B0_joint_NLL": float(difference[folds == fold].mean())} for fold in range(8)]
    report = {"rows": 548, "players": 8, "observed_bounces": 437, "net_censored": 111,
              "lets_excluded": 19, "models": summaries, "unit": "nats per recorded non-let attempt; density per square meter",
              "primary_comparison": "B1 minus B0 equal-player joint observed-data NLL", "primary": interval,
              "attempt_weighted_contrast": float(difference.mean()), "practical_threshold_nats": .02,
              "practical_threshold_met": interval["difference"] <= -.02,
              "ellipse90_mahalanobis_squared_cutoff": ELLIPSE_CUTOFF,
              "session_exclusion": {"contrast_range": [min(x["contrast"] for x in session_exclusion), max(x["contrast"] for x in session_exclusion)],
                                    "remaining_player_counts": [x["remaining_players"] for x in session_exclusion],
                                    "predictions_unchanged": True},
              "participant_level_results": "Private; separate privacy approval required even for pseudonymous fold aggregates",
              "claims": ["Conditional on recorded non-let practice attempts; not an all-attempt pre-serve forecast",
                         "Eight held-out players with shared sessions and overlapping training sets limit inference",
                         "Coverage is a diagnostic, not established calibration; no causal or professional transfer claim"]}
    return report, {"players_in_fixed_fold_order_not_ranked": player_details, "session_exclusion": session_exclusion}


def develop(root=ROOT, task="baseball_mechanics"):
    return Runner(root, task).develop()


def evaluate(root=ROOT, task="baseball_mechanics"):
    return Runner(root, task).evaluate()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "develop", "evaluate"))
    parser.add_argument("--task", choices=tuple(SPECS), required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    result = {"prepare": prepare, "develop": develop, "evaluate": evaluate}[args.phase](args.root, args.task)
    # CLI prints status/hashes only; private file paths and aggregate scores stay local.
    print(json.dumps({k: v for k, v in result.items() if k not in {"summary", "report", "code", "data", "metadata"}}, indent=2))


if __name__ == "__main__":
    main()
