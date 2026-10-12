"""Two-stage research runner: develop first, explicitly unlock evaluation second."""
from __future__ import annotations
import argparse,hashlib,json,time,platform
import sklearn,scipy
from datetime import datetime,timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import log_loss
from sportslab.data import validate_events,sha256,SPORTS
from sportslab.evaluate import fit_temperature,temperature_scale,elo_probabilities,metrics,bootstrap_loss,SEED
from experiments.v2.features import extended_features,FEATURES
from experiments.v2.models import CONFIGS,make

ROOT=Path(__file__).resolve().parents[2]
SPLITS={'soccer':('2024-07-01','2025-07-01','2026-07-01'),
 'baseball':('2024-01-01','2025-01-01','2026-01-01'),
 'football':('2024-03-01','2025-03-01','2026-03-01'),
 'tennis':('2024-01-01','2025-01-01','2026-01-01')}
ENSEMBLE_FAMILIES=('logistic','boost','random_forest','extra_trees','dixon_coles')

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def code_hash():
    files=sorted(Path(__file__).parent.glob('*.py'))
    files += sorted((ROOT/'sportslab').rglob('*.py'))
    files += [ROOT/'scripts'/'stage_v2_data.py',ROOT/'experiments'/'frozen_nfl.py']
    return hashlib.sha256(b''.join(str(p.relative_to(ROOT)).encode()+p.read_bytes() for p in files)).hexdigest()

def features_for(sport,development_only=False):
    directory='pre_holdout_development' if development_only else 'processed'
    path=ROOT/'data'/'v2'/directory/f'{sport}.csv'
    events=validate_events(pd.read_csv(path,dtype={'event_id':str,'side_a':str,'side_b':str,'season':str}),sport)
    # Development parses only the cutoff-purged historical file. Full sequential
    # test history is constructed only inside explicitly unlocked evaluation.
    print(f'{sport}: building {len(events):,} availability-aware feature rows',flush=True)
    frame=extended_features(events,sport).merge(events[['event_id','score_a','score_b','season']],on='event_id',validate='one_to_one')
    output=ROOT/'artifacts'/'v2'/sport;output.mkdir(parents=True,exist_ok=True)
    frame.to_csv(output/('development_features.csv' if development_only else 'features.csv'),index=False)
    return frame,path

def partition(frame,sport,require_test=True):
    a,b,c=map(pd.Timestamp,SPLITS[sport])
    train=frame[(frame.date<a)&(frame.available_date<a)].copy()
    cal=frame[(frame.date>=a)&(frame.date<b)&(frame.available_date<b)].copy()
    test=frame[(frame.date>=b)&(frame.date<c)].copy()
    if min(len(train),len(cal))<100 or (require_test and len(test)<100):raise ValueError('Insufficient split coverage')
    return train,cal,test

def summary(frame):
    return {'n':len(frame),'first_date':str(frame.date.min().date()),'last_date':str(frame.date.max().date())}

def develop(sport):
    started=time.monotonic()
    output=ROOT/'artifacts'/'v2'/sport
    manifest_path=output/'selection.json'
    if manifest_path.exists():raise ValueError(f'{sport}: selection already frozen; do not overwrite')
    frame,path=features_for(sport,development_only=True)
    train,cal,_=partition(frame,sport,require_test=False)
    classes=np.arange(3 if sport=='soccer' else 2)
    cutoff=pd.Timestamp(SPLITS[sport][0])
    folds=[]
    for offset in (3,2,1):
        start=cutoff-pd.DateOffset(years=offset);end=start+pd.DateOffset(years=1)
        fit=train[(train.date<start)&(train.available_date<start)]
        valid=train[(train.date>=start)&(train.date<end)&(train.available_date<end)]
        if min(len(fit),len(valid))<100 or set(fit.target)!=set(classes):raise ValueError('Insufficient fold')
        folds.append((fit,valid))
    v1=json.loads((ROOT/'reports'/sport/'evaluation.json').read_text())['selected_config']
    configs=[{'name':'v1_recipe_refit','family':'v1_recipe','v1_config':v1}]+list(CONFIGS)
    if sport=='soccer':configs += [{'name':'dixon_coles','family':'dixon_coles'}]
    oof_y=np.concatenate([v.target.to_numpy() for _,v in folds])
    results=[];oof={}
    for config in configs:
        before=time.monotonic();predictions=[];scores=[]
        for fit,valid in folds:
            model=make(config).fit(fit)
            p=model.predict_proba(valid)
            if p.shape!=(len(valid),len(classes)) or not np.isfinite(p).all():raise ValueError('Invalid candidate probabilities')
            predictions.append(p);scores.append(float(log_loss(valid.target,p,labels=classes)))
        oof[config['name']]=np.concatenate(predictions)
        results.append({'config':config,'fold_log_losses':scores,'mean_fold_log_loss':float(np.mean(scores)),'fit_seconds':time.monotonic()-before})
        print(f"{sport}: {config['name']} development log loss {np.mean(scores):.5f}",flush=True)
    selected={}
    for row in results:
        family=row['config']['family']
        if family not in selected or row['mean_fold_log_loss']<selected[family]['mean_fold_log_loss']:selected[family]=row
    ensemble_names=[selected[f]['config']['name'] for f in ENSEMBLE_FAMILIES if f in selected]
    stack=np.stack([oof[name] for name in ensemble_names])
    size=len(ensemble_names);uniform=np.ones(size)/size
    def objective(weights):
        p=np.tensordot(weights,stack,axes=(0,0))
        return log_loss(oof_y,p,labels=classes)+.02*np.sum((weights-uniform)**2)
    optimized=minimize(objective,uniform,method='SLSQP',bounds=[(0,1)]*size,constraints={'type':'eq','fun':lambda w:w.sum()-1},options={'maxiter':500,'ftol':1e-10})
    if not optimized.success:raise ValueError(f'Ensemble fitting failed: {optimized.message}')
    weights=np.clip(optimized.x,0,1);weights/=weights.sum()
    final_models={};temperatures={};calibration={};cal_preds={}
    for family,row in selected.items():
        name=row['config']['name'];model=make(row['config']).fit(train);p=model.predict_proba(cal)
        final_models[name]=model;cal_preds[name]=p
        temperatures[name]=fit_temperature(p,cal.target,classes)
        calibration[name]={'uncalibrated_log_loss':float(log_loss(cal.target,p,labels=classes)),
            'temperature_fit_log_loss':float(log_loss(cal.target,temperature_scale(p,temperatures[name]),labels=classes))}
    ensemble_cal=np.tensordot(weights,np.stack([cal_preds[n] for n in ensemble_names]),axes=(0,0))
    temperatures['ensemble']=fit_temperature(ensemble_cal,cal.target,classes)
    prior=(np.bincount(train.target,minlength=len(classes))+1)/(len(train)+len(classes))
    temperatures['elo']=fit_temperature(elo_probabilities(cal,sport,prior),cal.target,classes)
    artifact={'models':final_models,'temperatures':temperatures,'ensemble_names':ensemble_names,
              'ensemble_weights':weights,'prior':prior,'classes':classes,'sport':sport}
    joblib.dump(artifact,output/'models.joblib')
    manifest={'status':'development_frozen_test_not_scored','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'sport':sport,'seed':SEED,'protocol_sha256':sha256(ROOT/'docs'/'v2'/'PROTOCOL.md'),
        'code_sha256':code_hash(),'data_sha256':sha256(ROOT/'data'/'v2'/'processed'/f'{sport}.csv'),
        'development_data_sha256':sha256(path),'development_features_sha256':sha256(output/'development_features.csv'),
        'source_manifest_sha256':sha256(ROOT/'data'/'v2'/'manifest.json'),
        'models_sha256':sha256(output/'models.joblib'),'splits':dict(zip(('train_end','calibration_end','test_end'),SPLITS[sport])),
        'training':summary(train),'calibration':summary(cal),'folds':[{'fit':summary(t),'validation':summary(v)} for t,v in folds],
        'candidates':results,'selected_by_family':{f:r['config'] for f,r in selected.items()},
        'ensemble_names':ensemble_names,'ensemble_weights':weights.tolist(),
        'ensemble_fitted_oof_loss_not_unbiased':float(log_loss(oof_y,np.tensordot(weights,stack,axes=(0,0)),labels=classes)),
        'temperatures':temperatures,'calibration_fit_metrics':calibration,
        'elapsed_seconds':time.monotonic()-started,'features':FEATURES,
        'runtime':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scikit_learn':sklearn.__version__,'scipy':scipy.__version__,'joblib':joblib.__version__}}
    dump(manifest_path,manifest)
    dump(ROOT/'reports'/'v2'/sport/'development.json',manifest)
    print(f'{sport}: selection frozen; new holdout not scored',flush=True)

def freeze_all():
    directory=ROOT/'artifacts'/'v2'
    paths={s:directory/s/'selection.json' for s in SPORTS}
    if not all(p.exists() for p in paths.values()):return
    for p in paths.values():
        manifest=json.loads(p.read_text())
        if manifest['code_sha256']!=code_hash() or manifest['protocol_sha256']!=sha256(ROOT/'docs'/'v2'/'PROTOCOL.md'):
            raise ValueError('Cannot globally freeze mismatched development versions')
    target=directory/'SELECTION_FREEZE.json'
    record={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'code_sha256':code_hash(),
        'protocol_sha256':sha256(ROOT/'docs'/'v2'/'PROTOCOL.md'),'selection_hashes':{s:sha256(p) for s,p in paths.items()}}
    if target.exists():
        if json.loads(target.read_text())['selection_hashes']!=record['selection_hashes']:raise ValueError('Global freeze changed')
    else:dump(target,record)
    print('All four sports globally frozen; no new-holdout score has been used',flush=True)

def evaluate(sport):
    global_freeze=ROOT/'artifacts'/'v2'/'SELECTION_FREEZE.json'
    if not global_freeze.exists():raise ValueError('All four sports must finish development and freeze before scoring any new holdout')
    frozen=json.loads(global_freeze.read_text())
    for name in SPORTS:
        p=ROOT/'artifacts'/'v2'/name/'selection.json'
        if not p.exists() or sha256(p)!=frozen['selection_hashes'][name]:raise ValueError('Global selection freeze mismatch')
    directory=ROOT/'artifacts'/'v2'/sport
    output=ROOT/'reports'/'v2'/sport/'evaluation.json'
    if output.exists():raise ValueError(f'{sport}: test was already scored; do not silently rerun')
    selection=json.loads((directory/'selection.json').read_text())
    checks={'code_sha256':code_hash(),'protocol_sha256':sha256(ROOT/'docs'/'v2'/'PROTOCOL.md'),
      'data_sha256':sha256(ROOT/'data'/'v2'/'processed'/f'{sport}.csv'),
      'development_data_sha256':sha256(ROOT/'data'/'v2'/'pre_holdout_development'/f'{sport}.csv'),
      'development_features_sha256':sha256(directory/'development_features.csv'),
      'source_manifest_sha256':sha256(ROOT/'data'/'v2'/'manifest.json'),'models_sha256':sha256(directory/'models.joblib')}
    for key,value in checks.items():
        if selection[key]!=value:raise ValueError(f'{sport}: frozen {key} changed before evaluation')
    frame,_=features_for(sport,development_only=False)
    _,_,test=partition(frame,sport)
    artifact=joblib.load(directory/'models.joblib')
    raw={name:model.predict_proba(test) for name,model in artifact['models'].items()}
    raw['ensemble']=np.tensordot(artifact['ensemble_weights'],np.stack([raw[n] for n in artifact['ensemble_names']]),axes=(0,0))
    raw['elo']=elo_probabilities(test,sport,artifact['prior'])
    predictions={'training_prior':np.tile(artifact['prior'],(len(test),1))}
    for name,p in raw.items():
        predictions[name+'_raw']=p
        predictions[name+'_calibrated']=temperature_scale(p,artifact['temperatures'][name])
    y=test.target.to_numpy(dtype=int)
    report={'sport':sport,'status':'completed_single_new_holdout_evaluation','evaluated_at_utc':datetime.now(timezone.utc).isoformat(),
       'selection_manifest_sha256':sha256(directory/'selection.json'),'global_selection_freeze_sha256':sha256(global_freeze),'protocol_sha256':checks['protocol_sha256'],
       'selection_frozen_at_utc':selection['frozen_at_utc'],'test':summary(test),'classes':['side_b_win','draw','side_a_win'] if sport=='soccer' else ['side_b_win','side_a_win'],
       'prespecified_main_model':'ensemble_calibrated','metrics':{name:metrics(y,p) for name,p in predictions.items()},
       'uncertainty_vs_v1_recipe_refit':bootstrap_loss(y,predictions['ensemble_calibrated'],predictions['v1_recipe_refit_calibrated'],test.date),
       'uncertainty_vs_calibrated_elo':bootstrap_loss(y,predictions['ensemble_calibrated'],predictions['elo_calibrated'],test.date)}
    pred=test[['event_id','date','side_a','side_b','target']].copy()
    for name,p in predictions.items():
        for i,label in enumerate(report['classes']):pred[name+'__'+label]=p[:,i]
    pred.to_csv(directory/'holdout_predictions.csv',index=False)
    dump(output,report)
    print(json.dumps({'sport':sport,'new_holdout_n':len(test),'main':{k:report['metrics']['ensemble_calibrated'][k] for k in ('accuracy','log_loss','brier')},
        'v1_refit_log_loss':report['metrics']['v1_recipe_refit_calibrated']['log_loss'],
        'paired_difference_interval':report['uncertainty_vs_v1_recipe_refit']['difference_95pct_interval']},indent=2),flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['develop','evaluate'])
    parser.add_argument('--sport',choices=[*SPORTS,'all'],required=True)
    parser.add_argument('--unlock-new-holdout',action='store_true')
    args=parser.parse_args()
    if args.stage=='evaluate' and not args.unlock_new_holdout:parser.error('Evaluation requires --unlock-new-holdout after frozen selection review')
    for sport in SPORTS if args.sport=='all' else [args.sport]:
        (develop if args.stage=='develop' else evaluate)(sport)
    if args.stage=='develop':freeze_all()
if __name__=='__main__':main()
