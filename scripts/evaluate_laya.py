#!/usr/bin/env python3
"""Frozen, identity-blinded comparison of pretrained Laya with sports baselines.

No tuning or calibration is performed on the holdout. Requires optional laya==0.4.2.
Run with the isolated CPU environment described in docs/laya_experiment.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sportslab.features import FEATURES
from sportslab.evaluate import metrics

PACKAGE_VERSION = "0.4.2"
MODEL_ID = "convaiinnovations/laya"
REVISION = "7b928d828b7b0e022f929d9bd2e44165aa270148"
SPORTS = ("soccer", "baseball", "football", "tennis")
INSTRUCTIONS = "Predict the match outcome from the supplied pre-event statistics."
DEFINITIONS = (
    "A is the home team unless "
    "neutral=1; tennis A/B are arbitrary. Each diff is A minus B. "
    "elo_diff and surface_elo_diff are rating differences divided by 400. "
    "form_diff is recent win-fraction difference. margin_diff, scoring_diff and "
    "conceding_diff compare recent scoring margins, scores and scores conceded. "
    "experience_diff is log historical game-count difference. rest_diff is rest-day "
    "difference divided by 30. cold_a/cold_b indicate no history. log_rank_diff is "
    "log(rank_B/rank_A), positive favors A. rank_missing_a/b mark missing rankings."
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def labels_for(sport):
    return ["side_b_win", "draw", "side_a_win"] if sport == "soccer" else ["side_b_win", "side_a_win"]


def question(sport, reverse=False):
    definitions = {"side_b_win": "B wins", "draw": "The match is drawn", "side_a_win": "A wins"}
    labels = labels_for(sport)
    if reverse:
        labels = labels[::-1]
    return {"outcome": {"type": "choice", "instructions": INSTRUCTIONS,
                        "criteria": {label: definitions[label] for label in labels}}}


def state_for(row, sport):
    # Explicit whitelist: outcome, IDs, dates, names and source metadata never enter the model.
    values = {name: round(float(row[name]), 5) for name in FEATURES}
    if not np.isfinite(list(values.values())).all():
        raise ValueError("Non-finite pregame feature")
    return DEFINITIONS + "\n" + json.dumps({"sport": sport, "features": values}, separators=(",", ":"))


def freeze(root, sports, n):
    """Selection depends only on date/ID ordering, never labels or model results."""
    output = root / "reports" / "laya"
    records, frames = {}, {}
    for sport in sports:
        folder = root / "artifacts" / sport
        fp, pp = folder / "features.csv", folder / "holdout_predictions.csv"
        features = pd.read_csv(fp, dtype={"event_id": str})
        predictions = pd.read_csv(pp, dtype={"event_id": str})
        if features.event_id.duplicated().any() or predictions.event_id.duplicated().any():
            raise ValueError(f"Duplicate event IDs for {sport}")
        ordered = predictions.sort_values(["date", "event_id"], kind="stable")
        if len(ordered) < n:
            raise ValueError(f"{sport} has {len(ordered)} holdout rows, fewer than requested {n}")
        positions = np.linspace(0, len(ordered) - 1, n, dtype=int)
        selected = ordered.iloc[positions].copy()
        selected = selected.merge(features[["event_id", "target"] + list(FEATURES)],
                                  on="event_id", suffixes=("", "_feature"), validate="one_to_one")
        if not (selected.target == selected.target_feature).all():
            raise ValueError(f"Target mismatch for {sport}")
        records[sport] = {"n": len(selected), "holdout_n": len(ordered),
                          "first_date": str(selected.date.min()), "last_date": str(selected.date.max()),
                          "features_sha256": sha(fp), "predictions_sha256": sha(pp),
                          "selected_event_ids": selected.event_id.tolist(),
                          "states_sha256": hashlib.sha256("\n".join(state_for(r, sport) for _, r in selected.iterrows()).encode()).hexdigest()}
        frames[sport] = selected
    spec = {"package": f"laya=={PACKAGE_VERSION}", "model": MODEL_ID, "revision": REVISION,
            "selection": "200 evenly spaced rows in date/event_id sorted holdout; n configurable",
            "n_per_sport": n, "features": list(FEATURES), "feature_definitions": DEFINITIONS,
            "questions": {s: question(s) for s in sports},
            "sports": records}
    manifest = output / "frozen_manifest.json"
    if manifest.exists():
        existing = json.loads(manifest.read_text())
        if existing["spec"] != spec:
            raise ValueError("Frozen manifest differs. Use a new output/root for a genuinely new experiment; do not silently reselect")
    else:
        dump(manifest, {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "spec": spec})
    return frames, spec


def probabilities(result, labels):
    answer = result["answers"]["outcome"]
    distribution = answer["probabilities"]
    if set(distribution) != set(labels):
        raise ValueError(f"Unexpected labels: {distribution}")
    p = np.array([distribution[label] for label in labels], dtype=float)
    # Laya rounds each returned probability to four decimals (Agent._format_answers).
    # Permit only the analytically bounded sum error from that serialization.
    rounding_bound = len(labels) * 0.00005 + 1e-9
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any() or abs(p.sum() - 1) > rounding_bound:
        raise ValueError("Invalid probability distribution")
    return p / p.sum()


def validate_cached(record, labels, expected_id, expected_target, manifest_hash):
    """Reject corrupted, swapped or foreign cached records before resuming."""
    if record.get("manifest_sha256") != manifest_hash:
        raise ValueError("Cached predictions belong to a different manifest")
    if record.get("event_id") != expected_id or record.get("target") != int(expected_target):
        raise ValueError("Cached event or target differs from the frozen row")
    if record.get("labels") != labels:
        raise ValueError("Cached label order differs from the expected mapping")
    values = record.get("probabilities")
    if not isinstance(values, list) or len(values) != len(labels):
        raise ValueError("Cached probability vector has the wrong shape")
    elapsed = record.get("seconds")
    if not isinstance(elapsed, (float, int)) or not np.isfinite(elapsed) or elapsed < 0:
        raise ValueError("Cached inference duration is invalid")
    return probabilities({"answers": {"outcome": {"probabilities": dict(zip(labels, values))}}}, labels)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--sports", nargs="+", choices=SPORTS, default=list(SPORTS))
    parser.add_argument("--n-per-sport", type=int, default=200)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)
    if args.n_per_sport < 10 or args.threads < 1:
        parser.error("At least 10 rows/sport and one thread are required")
    root = args.root.resolve()
    output = root / "reports" / "laya"
    frames, spec = freeze(root, args.sports, args.n_per_sport)
    print(f"Frozen {sum(len(f) for f in frames.values())} rows before inference", flush=True)
    if args.prepare_only:
        return 0
    os.environ.setdefault("HF_HOME", str(root / ".cache-laya"))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
    os.environ.pop("HF_TOKEN", None)  # Public checkpoint: never attach an ambient credential.
    os.environ.setdefault("USE_TF", "0")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import torch
    import laya
    if importlib.metadata.version("laya") != PACKAGE_VERSION:
        raise RuntimeError(f"Expected laya=={PACKAGE_VERSION}")
    torch.set_num_threads(args.threads)
    torch.manual_seed(20261011)
    start = time.monotonic()
    agent = laya.load(MODEL_ID, device="cpu", backend="eager", revision=REVISION)
    load_seconds = time.monotonic() - start
    token = getattr(agent, "tok", None) or getattr(agent, "tokenizer", None)
    if token is None:
        raise RuntimeError("Cannot verify token budget: tokenizer unavailable")
    from laya.common import build_sequence
    from laya.train import to_internal
    # Validate actual encoded input with the same pinned formatter used by inference.
    max_budget = 0
    for sport, frame in frames.items():
        internal = to_internal("outcome", question(sport)["outcome"])
        for _, row in frame.iterrows():
            ids, markers, stats, truncation = build_sequence(token, state_for(row, sport), internal,
                max_len=512, head_max_len=192, return_stats=True, return_truncation_stats=True)
            budget = len(ids)
            max_budget = max(max_budget, budget)
            if truncation["truncated"] or stats["options_distinct"] != len(labels_for(sport)):
                raise ValueError(f"Input truncates or loses labels: {truncation}, {stats}")
    runtime = {"python": sys.version.split()[0], "laya": PACKAGE_VERSION, "torch": torch.__version__,
               "transformers": importlib.metadata.version("transformers"), "device": "cpu",
               "threads": args.threads, "model_load_seconds": load_seconds,
               "max_verified_input_tokens": max_budget,
               "probability_normalization": "Renormalize only within k*0.00005 sum tolerance for SDK four-decimal output"}
    report = {"status": "running", "experiment": "identity-blinded pretrained Laya zero-shot",
              "fine_tuned_on_sports": False, "calibrated_on_sports": False,
              "manifest_sha256": sha(output / "frozen_manifest.json"), "runtime": runtime, "sports": {}}
    dump(output / "evaluation.json", report)
    smoke_times = []
    for sport, frame in frames.items():
        labels = labels_for(sport)
        result_file = root / "artifacts" / sport / "laya_predictions.jsonl"
        completed = {}
        if result_file.exists():
            for line in result_file.read_text().splitlines():
                record = json.loads(line)
                if record["event_id"] in completed:
                    raise ValueError("Duplicate cached event ID")
                completed[record["event_id"]] = record
        if set(completed) - set(frame.event_id):
            raise ValueError("Cached predictions include events outside the frozen selection")
        times, probs = [], []
        with result_file.open("a") as stream:
            for number, (_, row) in enumerate(frame.iterrows(), 1):
                if row.event_id in completed:
                    record = completed[row.event_id]
                    p = validate_cached(record, labels, row.event_id, row.target, report["manifest_sha256"])
                else:
                    t0 = time.monotonic()
                    answer = agent.predict(state_for(row, sport), question(sport), max_len=512)
                    p = probabilities(answer, labels)
                    elapsed = time.monotonic() - t0
                    record = {"event_id": row.event_id, "target": int(row.target), "labels": labels,
                              "probabilities": p.tolist(), "seconds": elapsed,
                              "manifest_sha256": report["manifest_sha256"]}
                    stream.write(json.dumps(record, allow_nan=False) + "\n")
                    stream.flush()
                times.append(record["seconds"])
                probs.append(p)
                if len(smoke_times) < 10:
                    smoke_times.append(record["seconds"])
                    if len(smoke_times) == 10:
                        runtime["smoke_10_rows_seconds"] = sum(smoke_times)
                        runtime["smoke_peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
                        dump(output / "evaluation.json", report)
                        print(f"Real-row CPU smoke: 10 passed, {sum(smoke_times):.2f}s, peak RSS {runtime['smoke_peak_rss_mib']:.0f} MiB", flush=True)
                if number % 25 == 0:
                    print(f"{sport}: {number}/{len(frame)}", flush=True)
        matrix = np.asarray(probs)
        y = frame.target.to_numpy(dtype=int)
        comparison = {"laya_pretrained_zero_shot": metrics(y, matrix)}
        methods = sorted({col.split("__")[0] for col in frame.columns if "__" in col})
        for method in methods:
            columns = [f"{method}__{label}" for label in labels]
            if all(c in frame for c in columns):
                comparison[method] = metrics(y, frame[columns].to_numpy(float))
        # Diagnostic only: no prompt selection, refitting or favorable-row exclusion follows it.
        order_deltas = []
        for i, (_, row) in enumerate(frame.iloc[:10].iterrows()):
            reverse = probabilities(agent.predict(state_for(row, sport), question(sport, reverse=True), max_len=512), labels)
            order_deltas.append(float(np.max(np.abs(reverse - matrix[i]))))
        report["sports"][sport] = {"n": len(frame), "first_date": str(frame.date.min()),
                                   "last_date": str(frame.date.max()), "metrics": comparison,
                                   "median_inference_seconds": float(np.median(times)),
                                   "total_inference_seconds": float(sum(times)),
                                   "option_order_diagnostic_first_10_max_probability_change": max(order_deltas),
                                   "option_order_diagnostic_first_10_mean_probability_change": float(np.mean(order_deltas))}
        dump(output / "evaluation.json", report)
        print(f"{sport} completed: Laya log loss {comparison['laya_pretrained_zero_shot']['log_loss']:.4f}; selected calibrated {comparison['selected_calibrated']['log_loss']:.4f}", flush=True)
    runtime["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    report["status"] = "completed"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    dump(output / "evaluation.json", report)
    print(f"Completed; {output / 'evaluation.json'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Laya experiment blocked: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
