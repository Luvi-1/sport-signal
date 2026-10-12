"""Reproduce V1 NFL with the licensed, odds-free normalized input snapshot.

This is an explicit frozen-data entrypoint. Refresh mode only exports newly
reviewable provider results into a separate destination; it never overwrites
published inputs, models, reports or snapshot hashes.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments.frozen_nfl import load_snapshot
from sportslab.data import validate_events
from sportslab.evaluate import train_evaluate
from sportslab.adapters import football

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['frozen','refresh'],default='frozen')
    parser.add_argument('--output',type=Path,help='Required fresh review directory for refresh; never used as a benchmark automatically')
    args=parser.parse_args()
    if args.mode=='refresh':
        if args.output is None or args.output.exists():parser.error('Refresh requires --output pointing to a new, nonexistent review directory')
        args.output.mkdir(parents=True)
        football.download(args.output/'raw')
        frame=validate_events(football.load(args.output/'raw'),'football')
        frame.to_csv(args.output/'candidate_processed.csv',index=False)
        print('Candidate refresh exported for schema/hash/source review. No benchmark or published snapshot was replaced.')
        return
    events=load_snapshot(2024)
    destination=ROOT/'data/processed/football.csv';destination.parent.mkdir(parents=True,exist_ok=True)
    events.to_csv(destination,index=False)
    result=train_evaluate(events,'football',ROOT)
    # Keep original provider bytes and normalized representation identities distinct.
    result['frozen_input_snapshot']=events.attrs['snapshot_provenance']
    result['ingestion_entrypoint']='scripts/reproduce_frozen_nfl.py --mode frozen; original V1 estimator/feature code unchanged'
    (ROOT/'reports/football/evaluation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'rows':len(events),'log_loss':result['test']['selected_calibrated']['log_loss'],'source_mode':'licensed normalized frozen snapshot'},indent=2))
if __name__=='__main__':main()
