"""Small, explicit command-line interface; no service credentials required."""
from __future__ import annotations
import argparse
import re
import json
from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd
from sportslab.data import SPORTS, prepare, validate_events, sha256
from sportslab.features import FEATURES, build_features
from sportslab.evaluate import train_evaluate, temperature_scale

def verify_lock(root, sport):
    lock = root / "data_manifest.json"
    if not lock.exists():
        return
    for record in json.loads(lock.read_text())["files"]:
        if record["sport"] != sport:
            continue
        path = root/record["path"]
        if not path.exists() or sha256(path)!=record["sha256"]:
            raise ValueError(f"Source snapshot changed: {path}. Review provider revision; do not silently reuse benchmark claims.")

def load_processed(root,sport):
    path = root/"data"/"processed"/f"{sport}.csv"
    # Stable participant IDs must remain strings, including tennis IDs.
    return validate_events(pd.read_csv(path,dtype={"side_a":str,"side_b":str,"season":str,"event_id":str}),sport)

def predict(root,sport,side_a,side_b,date,surface="all",neutral=False,rank_a=None,rank_b=None,allow_cold=False):
    """Only load artifacts produced locally by this project. Pickle is not safe for untrusted files."""
    artifact = joblib.load(root/"artifacts"/sport/"model.joblib")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",str(date)):
        raise ValueError("Forecast date must be YYYY-MM-DD")
    date = pd.Timestamp(date).normalize()
    if pd.isna(date):
        raise ValueError("A valid forecast date is required")
    if any(r is not None and (not np.isfinite(r) or r <= 0) for r in (rank_a,rank_b)):
        raise ValueError("Provided rankings must be positive finite numbers")
    requested_a,requested_b = side_a,side_b
    swapped = sport=="tennis" and side_a > side_b
    if swapped:
        side_a,side_b,rank_a,rank_b = side_b,side_a,rank_b,rank_a
    if date < pd.Timestamp(artifact["calibration_cutoff"]):
        raise ValueError("Forecast date precedes the model's calibration cutoff; that would leak future labels")
    if side_a==side_b:
        raise ValueError("Participants must differ")
    if sport=="tennis" and surface not in {"Hard","Clay","Grass","Carpet"}:
        raise ValueError("Tennis requires --surface Hard, Clay, Grass, or Carpet")
    history = load_processed(root,sport)
    history = history[history.date < date].copy()
    participants = set(history.side_a)|set(history.side_b)
    unknown = [x for x in (side_a,side_b) if x not in participants]
    if unknown and not allow_cold:
        raise ValueError(f"Unknown participant IDs {unknown}; inspect data or explicitly pass --allow-cold-start")
    # The synthetic result exists only to use the same feature path; it is never read into its own features.
    row = {"event_id":"__forecast__","date":date,"available_date":date,"season":str(date.year),
        "side_a":side_a,"side_b":side_b,"score_a":1,"score_b":0,"neutral":neutral or sport=="tennis",
        "surface":surface,"rank_a":rank_a if rank_a is not None else np.nan,"rank_b":rank_b if rank_b is not None else np.nan}
    frame = pd.concat([history,pd.DataFrame([row])],ignore_index=True)
    features = build_features(frame,sport).query("event_id == '__forecast__'")
    p = temperature_scale(artifact["model"].predict_proba(features[FEATURES]),artifact["temperature"])[0]
    if swapped:
        p = p[::-1]
    f = features.iloc[0]
    direction = -1 if swapped else 1
    snapshot = {"prior_elo_a_minus_b":float(direction*f.elo_diff*400),
        "prior_surface_elo_a_minus_b":float(direction*f.surface_elo_diff*400),
        "prior_10game_result_mean_a_minus_b":float(direction*f.form_diff),
        "known_rest_a_minus_b_days":float(direction*f.rest_diff*30),
        "cold_start_a":bool(f.cold_b if swapped else f.cold_a),
        "cold_start_b":bool(f.cold_a if swapped else f.cold_b)}
    warnings = []
    if unknown:
        warnings.append("Cold-start participants: little or no historical evidence")
    if history.empty or (date-history.available_date.max()).days>120:
        warnings.append("Historical snapshot is stale; this is an illustrative forecast, not a current live model")
    if sport=="tennis" and (rank_a is None or rank_b is None):
        warnings.append("Missing pre-tournament ranking input; accuracy may differ from the historical benchmark")
    return {"sport":sport,"side_a":requested_a,"side_b":requested_b,"date":str(date.date()),"artifact_id":artifact["artifact_id"],
        "probabilities":dict(zip(artifact["classes"],map(float,p))),"warnings":warnings,
        "historical_input_snapshot":snapshot,
        "interpretation":"Input differences describe historical evidence; they are not causal explanations or recommendations",
        "feature_source_latest_available_date":str(features.max_source_available_date.iloc[0]),
        "note":"Estimated outcome probabilities, not guaranteed outcomes; research use only"}

def main(argv=None):
    parser = argparse.ArgumentParser(prog="sportslab",description="Reproducible four-sport historical prediction research")
    parser.add_argument("--root",type=Path,default=Path("."),help="Project data/artifact directory")
    commands = parser.add_subparsers(dest="command",required=True)
    for command in ("fetch","train","run","analyze"):
        p=commands.add_parser(command)
        p.add_argument("--sport",choices=(*SPORTS,"all"),required=True)
    p=commands.add_parser("predict")
    p.add_argument("--sport",choices=SPORTS,required=True)
    p.add_argument("--side-a",required=True)
    p.add_argument("--side-b",required=True)
    p.add_argument("--date",required=True)
    p.add_argument("--surface",default="all")
    p.add_argument("--neutral",action="store_true")
    p.add_argument("--rank-a",type=float)
    p.add_argument("--rank-b",type=float)
    p.add_argument("--allow-cold-start",action="store_true")
    args=parser.parse_args(argv)
    try:
        if args.command=="predict":
            result=predict(args.root,args.sport,args.side_a,args.side_b,args.date,args.surface,args.neutral,args.rank_a,args.rank_b,args.allow_cold_start)
            print(json.dumps(result,indent=2,allow_nan=False));return
        for sport in SPORTS if args.sport=="all" else [args.sport]:
            if args.command in ("fetch","run"):
                events=prepare(sport,args.root)
                verify_lock(args.root,sport)
                print(json.dumps({"sport":sport,"downloaded_and_validated_rows":len(events)}),flush=True)
            else:
                events=load_processed(args.root,sport)
                verify_lock(args.root,sport)
            if args.command in ("train","run"):
                report=train_evaluate(events,sport,args.root)
                print(json.dumps({"sport":sport,"model":report["selected_config"],"test":{
                    k:{m:v[m] for m in ("n","accuracy","log_loss","brier","top_label_ece_10_bins")}
                    for k,v in report["test"].items()}},indent=2),flush=True)
            if args.command=="analyze":
                wins=(events.score_a>events.score_b).mean()
                draws=(events.score_a==events.score_b).mean()
                print(json.dumps({"sport":sport,"games":len(events),"start":str(events.date.min().date()),
                    "end":str(events.date.max().date()),"participants":len(set(events.side_a)|set(events.side_b)),
                    "side_a_win_fraction":wins,"draw_fraction":draws,
                    "games_by_season":events.groupby("season").size().to_dict()},indent=2))
    except (ValueError,FileNotFoundError) as exc:
        parser.exit(2,f"Error: {exc}\n")

if __name__=="__main__":
    main()
