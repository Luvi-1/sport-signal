"""Compare an independently rerun checkout with a preserved benchmark checkout."""
from pathlib import Path
import argparse
from datetime import datetime,timezone
import hashlib
import json
import numpy as np
import pandas as pd

SPORTS=('soccer','baseball','football','tennis')
METRICS=('accuracy','log_loss','brier','top_label_ece_10_bins')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def check(reference,reproduced,tolerance=1e-6):
    reference,reproduced=Path(reference),Path(reproduced)
    if reference.resolve()==reproduced.resolve():raise ValueError('Use two distinct checkout directories')
    result={'status':'passed','checked_at_utc':datetime.now(timezone.utc).isoformat(),
      'scope':'Comparison of supplied checkouts: normalized inputs, feature bytes, per-event predictions and aggregate metrics',
      'original_raw_nfl_absent_from_reproduction':not (reproduced/'data/raw/football/games.csv').exists(),
      'tolerance':tolerance,'sports':{}}
    for sport in SPORTS:
        record={'identical_data_and_feature_files':[],'experiments':{}}
        for relative in [f'data/processed/{sport}.csv',f'data/v2/processed/{sport}.csv',
          f'data/v2/pre_holdout_development/{sport}.csv',f'artifacts/{sport}/features.csv',
          f'artifacts/v2/{sport}/development_features.csv',f'artifacts/v2/{sport}/features.csv']:
            a,b=reference/relative,reproduced/relative
            if digest(a)!=digest(b):raise ValueError(f'Input/feature bytes differ: {relative}')
            record['identical_data_and_feature_files'].append({'path':relative,'sha256':digest(a)})
        for version in ('v1','v2'):
            prefix='' if version=='v1' else 'v2/'
            a=json.loads((reference/f'reports/{prefix}{sport}/evaluation.json').read_text())
            b=json.loads((reproduced/f'reports/{prefix}{sport}/evaluation.json').read_text())
            metric_key='test' if version=='v1' else 'metrics'
            if set(a[metric_key])!=set(b[metric_key]):raise ValueError('Reported model set differs')
            diffs=[abs(a[metric_key][m][k]-b[metric_key][m][k]) for m in a[metric_key] for k in METRICS]
            if not np.isfinite(diffs).all():raise ValueError('Nonfinite report metric')
            if max(diffs)>tolerance:raise ValueError(f'{version}/{sport}: metric tolerance exceeded')
            relative=f'artifacts/{prefix}{sport}/holdout_predictions.csv'
            x=pd.read_csv(reference/relative,dtype={'event_id':str,'side_a':str,'side_b':str},float_precision='round_trip')
            y=pd.read_csv(reproduced/relative,dtype={'event_id':str,'side_a':str,'side_b':str},float_precision='round_trip')
            if list(x.columns)!=list(y.columns) or x.shape!=y.shape:raise ValueError('Prediction schema differs')
            delta=0.
            for key in x:
                if pd.api.types.is_numeric_dtype(x[key]):
                    values_x,values_y=x[key].to_numpy(),y[key].to_numpy()
                    if not np.isfinite(values_x).all() or not np.isfinite(values_y).all():raise ValueError('Nonfinite prediction values')
                    delta=max(delta,float(np.max(np.abs(values_x-values_y))))
                elif not x[key].equals(y[key]):raise ValueError(f'Prediction identity mismatch: {key}')
            if delta>tolerance:raise ValueError(f'{version}/{sport}: predictions exceed tolerance')
            record['experiments'][version]={'events':len(x),'model_variants':len(a[metric_key]),
              'maximum_metric_difference':max(diffs),'maximum_prediction_difference':delta}
        result['sports'][sport]=record
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference',type=Path);p.add_argument('reproduced',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args();result=check(a.reference,a.reproduced)
    text=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    print(text,end='')
if __name__=='__main__':main()
