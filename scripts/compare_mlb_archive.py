"""Diagnostic only: preserved FiveThirtyEight archive, not authenticated as-issued forecasts.
Reproduce locally. The optional --download flag fetches only the pinned public archive.
"""
import csv, json, hashlib
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'artifacts'/'external'
OUT.mkdir(parents=True,exist_ok=True)
import argparse,urllib.request
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--download',action='store_true')
args=parser.parse_args()
assert hashlib.sha256((ROOT/'artifacts/baseball/holdout_predictions.csv').read_bytes()).hexdigest() == '18f6432e2c51fe91b89b8b1225168282f3a9fda7344333704356e85ebe349df7', 'V1 predictions changed; do not silently update benchmark'
assert hashlib.sha256((ROOT/'data/processed/baseball.csv').read_bytes()).hexdigest() == '8d351a9ddc2402e89d7ee60006bd72fa5138ebb2d61f3bcaa71c4013aa3430a6', 'V1 source results changed; do not silently update benchmark'
ALIASES = {'CHC':'CHN','CHW':'CHA','KCR':'KCA','LAD':'LAN','NYM':'NYN','NYY':'NYA','SDP':'SDN','SFG':'SFN','STL':'SLN','TBD':'TBA','FLA':'MIA','WSN':'WAS'}
archive = OUT/'mlb_elo_latest_mirror.csv'
if not archive.exists():
 if not args.download:raise SystemExit('Missing preserved archive. Run with --download to fetch the pinned public source.')
 url='https://raw.githubusercontent.com/Angelogallardo05/Assignment01/04b528e1d5327aeb112672e39a6eb3a75a3bd4a5/mlb_elo_latest.csv'
 with urllib.request.urlopen(url,timeout=60) as response:archive.write_bytes(response.read())
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '12491eafd6e1ef2e97066b6517096381577e79f1db82b5e8cc141afbd6bfbc52', 'Unreviewed archive bytes'
source = list(csv.DictReader(archive.open()))
# Freeze cutoff from the publisher's discontinuation notice, before scoring.
# Exclude all dates >= 2023-06-13 regardless of later filled scores in this mirror.
eligible = [r for r in source if '2023-03-30' <= r['date'] < '2023-06-13' and r['score1'] and r['score2'] and not r['playoff']]
def sk(r): return (r['date'], ALIASES.get(r['team1'],r['team1']), ALIASES.get(r['team2'],r['team2']))
def lk(r): return (r['date'],r['side_a'],r['side_b'])
sidx = defaultdict(list)
for r in eligible: sidx[sk(r)].append(r)
local = list(csv.DictReader((ROOT/'artifacts/baseball/holdout_predictions.csv').open()))
lidx = defaultdict(list)
for r in local: lidx[lk(r)].append(r)
results = {r['event_id']:r for r in csv.DictReader((ROOT/'data/processed/baseball.csv').open())}
matched, exclusions = [],Counter()
for key, rows in sidx.items():
 if len(rows)!=1:
  exclusions['ambiguous_source_matchup_rows'] += len(rows); continue
 if len(lidx.get(key,[]))!=1:
  exclusions['ambiguous_or_missing_local_matchup_rows'] += len(rows); continue
 r, v = rows[0], lidx[key][0]
 truth=results[v['event_id']]
 if float(r['score1'])!=float(truth['score_a']) or float(r['score2'])!=float(truth['score_b']):
  exclusions['score_mismatch']+=1;continue
 if float(r['score1'])==float(r['score2']):
  exclusions['tie']+=1;continue
 y=int(v['target']); assert y==int(float(r['score1'])>float(r['score2']))
 assert abs(float(r['elo_prob1'])+float(r['elo_prob2'])-1)<1e-12
 assert abs(float(r['rating_prob1'])+float(r['rating_prob2'])-1)<1e-12
 ps={name:float(r[col]) for name,col in [('538_pitcher_ratings','rating_prob1'),('538_simple_elo','elo_prob1')]}
 ps.update({'sportslab_v1_selected':float(v['selected_calibrated__side_a_win']), 'sportslab_v1_calibrated_elo':float(v['elo_calibrated__side_a_win'])})
 if not all(0<p<1 for p in ps.values()): raise ValueError('Invalid probability')
 matched.append(dict(event_id=v['event_id'],date=v['date'],target=y,**ps))
matched.sort(key=lambda x:x['event_id']); y=np.array([r['target'] for r in matched]); ps={n:np.array([r[n] for r in matched]) for n in matched[0] if n not in ['event_id','date','target']}
def metrics(p):
 ll=-(y*np.log(p)+(1-y)*np.log(1-p)); conf=np.maximum(p,1-p); hit=(p>=.5)==y
 bins=np.minimum((conf*10).astype(int),9); ece=sum(np.mean(bins==b)*abs(hit[bins==b].mean()-conf[bins==b].mean()) for b in np.unique(bins))
 return {'n':len(y),'accuracy':float(hit.mean()),'log_loss':float(ll.mean()),'binary_brier':float(np.mean((p-y)**2)),'top_label_ece_10_bins':float(ece)},ll
stats, losses={},{}
for n,p in ps.items():stats[n],losses[n]=metrics(p)
# Monday-start calendar-week clusters; paired differences, all forecasters same rows.
from datetime import date,timedelta
weeks=[str(date.fromisoformat(r['date'])-timedelta(days=date.fromisoformat(r['date']).weekday())) for r in matched]
indices=[np.flatnonzero(np.array(weeks)==w) for w in sorted(set(weeks))]
rng=np.random.default_rng(20261011); cis={}
for name in ['538_pitcher_ratings','538_simple_elo']:
 delta=losses['sportslab_v1_selected']-losses[name]; draws=[]
 for _ in range(2000):
  ix=np.concatenate([indices[i] for i in rng.integers(0,len(indices),len(indices))]);draws.append(delta[ix].mean())
 cis[name]={'sportslab_minus_comparator_log_loss':float(delta.mean()),'paired_week_bootstrap_95pct':np.quantile(draws,[.025,.975]).tolist(),'clusters':len(indices),'replicates':2000}
report={
 'status':'DIAGNOSTIC_ONLY_PRESERVED_MIRROR_NOT_AUTHENTICATED_AS_ISSUED',
 'source_url':'https://raw.githubusercontent.com/Angelogallardo05/Assignment01/04b528e1d5327aeb112672e39a6eb3a75a3bd4a5/mlb_elo_latest.csv',
 'source_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
 'mirror_commit_time':'2024-02-04T03:59:36Z',
 'mirror_commit_url':'https://github.com/Angelogallardo05/Assignment01/commit/04b528e1d5327aeb112672e39a6eb3a75a3bd4a5',
 'source_data_attribution':'FiveThirtyEight, CC BY 4.0; preserved by Angelogallardo05/Assignment01; alias normalization, date filtering and matched scoring performed locally.',
 'local_prediction_sha256':hashlib.sha256((ROOT/'artifacts/baseball/holdout_predictions.csv').read_bytes()).hexdigest(),
 'local_processed_sha256':hashlib.sha256((ROOT/'data/processed/baseball.csv').read_bytes()).hexdigest(),
 'local_v1_artifact_id':json.loads((ROOT/'reports/baseball/evaluation.json').read_text())['artifact_id'],
 'publisher_schema':'https://github.com/fivethirtyeight/data/blob/master/mlb-elo/README.md',
 'publisher_license':'https://github.com/fivethirtyeight/data/blob/master/LICENSE',
 'publisher_discontinuation':'https://github.com/fivethirtyeight/data',
 'source_total_rows':len(source),'source_completed_rows':sum(bool(r['score1'] and r['score2']) for r in source),
 'source_completed_last_date':max(r['date'] for r in source if r['score1'] and r['score2']),
 'source_eligible_rows_before_june13':len(eligible),'matched_rows':len(matched),
 'period':[min(r['date'] for r in matched),max(r['date'] for r in matched)],'exclusions':dict(exclusions),
 'local_full_holdout_rows':len(local),'full_holdout_coverage_fraction':len(matched)/len(local),
 'metrics':stats,'uncertainty':cis,
 'limitations':['Third-party preservation; no publisher hash or per-game issuance timestamps, and mirror includes completed records after official discontinuation date.','Primary download endpoint redirected to unrelated ABC News HTML when checked 2026-10-11.','Only pre-2023-06-13 completed unique date/home/away matchups retained; all ambiguous doubleheaders dropped without using outcome to disambiguate.','As-issued information parity is unverified; pitcher-adjusted comparator contains richer inputs than outcome-only SportsLab.','This is neither the full final holdout nor proof of commercial superiority. Bootstrap covers sampling variation, not archival provenance, model selection, or time-of-publication uncertainty.']}
(ROOT/'reports'/'external').mkdir(parents=True,exist_ok=True)
(ROOT/'reports'/'external'/'mlb_archive_diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
with (OUT/'mlb_archive_matched_predictions.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=matched[0]);w.writeheader();w.writerows(matched)
print(json.dumps(report,indent=2))
