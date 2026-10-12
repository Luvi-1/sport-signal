"""Time-aware model selection, calibration, and one frozen holdout evaluation."""
from __future__ import annotations
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import scipy
from scipy.optimize import minimize_scalar
from scipy.special import softmax
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sportslab.features import FEATURES, build_features
from sportslab.data import sha256

SEED = 20261011
SPLITS = {
    "soccer": ("2022-07-01", "2023-07-01", "2025-07-01"),
    "baseball": ("2022-01-01", "2023-01-01", "2025-01-01"),
    "football": ("2022-03-01", "2023-03-01", "2025-03-01"),
    "tennis": ("2022-01-01", "2023-01-01", "2025-01-01"),
}
CANDIDATES = [
    {"family":"logistic", "C":.1}, {"family":"logistic", "C":1.0},
    {"family":"logistic", "C":10.0},
    {"family":"hist_gradient_boosting", "leaves":7, "l2":5.0},
    {"family":"hist_gradient_boosting", "leaves":15, "l2":10.0},
]

def make_model(config):
    if config["family"] == "logistic":
        return make_pipeline(StandardScaler(), LogisticRegression(C=config["C"], max_iter=1500, random_state=SEED))
    # No random early-stopping split: all selection is chronological externally.
    return HistGradientBoostingClassifier(max_iter=120, learning_rate=.06,
        max_leaf_nodes=config["leaves"], l2_regularization=config["l2"],
        min_samples_leaf=40, early_stopping=False, random_state=SEED)

def temperature_scale(p, temperature):
    return softmax(np.log(np.clip(p,1e-12,1))/temperature, axis=1)

def fit_temperature(p, y, classes):
    result = minimize_scalar(lambda t: log_loss(y, temperature_scale(p,t), labels=classes),
                             method="bounded", bounds=(.5,5.0))
    if not result.success:
        raise RuntimeError("Calibration optimizer failed")
    return float(result.x)

def elo_probabilities(frame, sport, prior):
    advantage = np.where(frame.neutral.to_numpy()==1, 0,55)/400 if sport != "tennis" else 0
    win = 1/(1+10**(-frame.elo_diff.to_numpy()-advantage))
    if sport=="soccer":
        draw = float(prior[1])
        return np.column_stack([(1-win)*(1-draw), np.full(len(win),draw), win*(1-draw)])
    return np.column_stack([1-win,win])

def reliability(p, y, bins=10):
    output = []
    for label in range(p.shape[1]):
        b = np.minimum((p[:,label]*bins).astype(int),bins-1)
        points = []
        for i in range(bins):
            mask = b==i
            if mask.any():
                points.append({"lower":i/bins,"upper":(i+1)/bins,"n":int(mask.sum()),
                    "mean_probability":float(p[mask,label].mean()), "observed_frequency":float((y[mask]==label).mean())})
        output.append({"class":label,"bins":points})
    return output

def metrics(y, p):
    y = np.asarray(y,dtype=int)
    predicted, confidence = p.argmax(1),p.max(1)
    ids = np.minimum((confidence*10).astype(int),9)
    ece = sum(float((ids==i).mean()) * abs(float((predicted[ids==i]==y[ids==i]).mean()) - float(confidence[ids==i].mean()))
              for i in range(10) if (ids==i).any())
    # Binary convention is positive-class squared error; multiclass is sum over classes.
    brier = np.mean((p[:,1]-y)**2) if p.shape[1]==2 else np.mean(np.sum((p-np.eye(p.shape[1])[y])**2,axis=1))
    return {"n":len(y),"accuracy":float(accuracy_score(y,predicted)),
        "log_loss":float(log_loss(y,p,labels=np.arange(p.shape[1]))),
        "brier":float(brier),"top_label_ece_10_bins":float(ece),
        "reliability":reliability(p,y)}

def bootstrap_loss(y, model_p, baseline_p, dates, reps=400):
    """Paired calendar-week cluster bootstrap; captures some local dependence.

    Approximate sampling intervals, not a guarantee or per-match uncertainty.
    Does not account for dataset revisions, tuning, or all long-range dependence.
    """
    y = np.asarray(y,dtype=int)
    loss = -np.log(np.clip(model_p[np.arange(len(y)),y],1e-12,1))
    reference = -np.log(np.clip(baseline_p[np.arange(len(y)),y],1e-12,1))
    frame = pd.DataFrame({"week":pd.to_datetime(dates).dt.to_period("W").astype(str).to_numpy(),
                          "loss":loss,"difference":loss-reference,"n":1})
    group = frame.groupby("week").sum(numeric_only=True)
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0,len(group),size=(reps,len(group)))
    totals = group.to_numpy()[draws].sum(axis=1)
    l, d, n = totals[:,0],totals[:,1],totals[:,2]
    return {"method":"paired calendar-week cluster bootstrap", "replicates":reps,"blocks":len(group),
        "log_loss_95pct_interval":np.quantile(l/n,[.025,.975]).tolist(),
        "model_minus_baseline_log_loss":float(np.mean(loss-reference)),
        "difference_95pct_interval":np.quantile(d/n,[.025,.975]).tolist()}

def split_frames(features, sport):
    train_end,val_end,test_end = map(pd.Timestamp,SPLITS[sport])
    # Availability-based label embargo stops a late-completing training event crossing the boundary.
    train = features[(features.date < train_end)&(features.available_date < train_end)].copy()
    val = features[(features.date >= train_end)&(features.date < val_end)&(features.available_date < val_end)].copy()
    test = features[(features.date >= val_end)&(features.date < test_end)].copy()
    if min(map(len,(train,val,test))) < 100:
        raise ValueError("At least 100 observations required in each partition")
    return train,val,test

def _range(frame):
    return {"n":len(frame),"first_date":str(frame.date.min().date()),"last_date":str(frame.date.max().date()),
            "class_counts":{str(k):int(v) for k,v in frame.target.value_counts().sort_index().items()}}

def train_evaluate(events, sport, root=Path(".")):
    root = Path(root)
    features = build_features(events,sport)
    train,val,test = split_frames(features,sport)
    classes = np.arange(3 if sport=="soccer" else 2)
    if any(set(f.target)!=set(classes) for f in (train,val,test)):
        raise ValueError("Each evaluation partition must contain every outcome class")
    train_end = pd.Timestamp(SPLITS[sport][0])
    folds = []
    # Two full-year validation windows contained entirely within the training era.
    for offset in (2,1):
        cutoff = train_end-pd.DateOffset(years=offset)
        end = cutoff+pd.DateOffset(years=1)
        fit = train[(train.date<cutoff)&(train.available_date<cutoff)]
        check = train[(train.date>=cutoff)&(train.date<end)&(train.available_date<end)]
        if len(fit)<100 or len(check)<100 or set(fit.target)!=set(classes):
            raise ValueError("Not enough data for chronological backtest folds")
        folds.append((fit,check))
    comparisons = []
    for config in CANDIDATES:
        rows = []
        for fit,check in folds:
            model = make_model(config).fit(fit[FEATURES],fit.target)
            p = model.predict_proba(check[FEATURES])
            rows.append({"fit":_range(fit),"validation":_range(check),"log_loss":float(log_loss(check.target,p,labels=classes))})
        comparisons.append({"config":config,"mean_fold_log_loss":float(np.mean([r["log_loss"] for r in rows])),"folds":rows})
    chosen = min(comparisons,key=lambda x:x["mean_fold_log_loss"])["config"]
    model = make_model(chosen).fit(train[FEATURES],train.target)
    val_raw = model.predict_proba(val[FEATURES])
    temperature = fit_temperature(val_raw,val.target,classes)
    raw = model.predict_proba(test[FEATURES])
    calibrated = temperature_scale(raw,temperature)
    prior = (np.bincount(train.target,minlength=len(classes))+1)/(len(train)+len(classes))
    prior_p = np.tile(prior,(len(test),1))
    elo = elo_probabilities(test,sport,prior)
    elo_temperature = fit_temperature(elo_probabilities(val,sport,prior),val.target,classes)
    elo_calibrated = temperature_scale(elo,elo_temperature)
    predictions = {"training_prior":prior_p,"elo":elo,"elo_calibrated":elo_calibrated,
                   "selected_uncalibrated":raw,"selected_calibrated":calibrated}
    labels = ["side_b_win","draw","side_a_win"] if sport=="soccer" else ["side_b_win","side_a_win"]
    report = {
        "sport":sport,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"seed":SEED,
        "protocol":"rolling pre-event history; frozen model parameters; calibration on validation only",
        "classes":labels,"features":FEATURES,"selected_config":chosen,"temperature":temperature,
        "elo_temperature":elo_temperature,"splits":{"train":_range(train),"calibration":_range(val),"test":_range(test)},
        "cutoffs":{"train_end_exclusive":SPLITS[sport][0],"validation_end_exclusive":SPLITS[sport][1],"test_end_exclusive":SPLITS[sport][2]},
        "backtests":comparisons,"validation":{"uncalibrated":metrics(val.target.to_numpy(),val_raw),
               "calibrated_in_sample":metrics(val.target.to_numpy(),temperature_scale(val_raw,temperature))},
        "test":{name:metrics(test.target.to_numpy(),p) for name,p in predictions.items()},
        "uncertainty_vs_prior":bootstrap_loss(test.target,calibrated,prior_p,test.date),
        "uncertainty_vs_calibrated_elo":bootstrap_loss(test.target,calibrated,elo_calibrated,test.date),
        "per_test_year":{str(year):metrics(test.target[mask].to_numpy(),calibrated[mask])
                         for year in sorted(test.date.dt.year.unique()) for mask in [(test.date.dt.year.to_numpy()==year)]},
        "runtime":{"python":platform.python_version(),"pandas":pd.__version__,"numpy":np.__version__,"scikit_learn":sklearn.__version__,"scipy":scipy.__version__},
        "raw_provenance":[]}
    for p in sorted((root/"data"/"raw"/sport).glob("*.source.json")):
        record = json.loads(p.read_text())
        record["local_file"] = str(p.relative_to(root)).removesuffix(".source.json")
        report["raw_provenance"].append(record)
    processed = root/"data"/"processed"/f"{sport}.csv"
    report["processed_sha256"] = sha256(processed)
    report["dataset_rows"] = len(events)
    code_files = sorted((Path(__file__).parent).rglob("*.py"))
    report["code_sha256"] = hashlib.sha256(b"".join(p.relative_to(Path(__file__).parent).as_posix().encode()+p.read_bytes() for p in code_files)).hexdigest()
    artifact_id = hashlib.sha256(json.dumps({"data":report["processed_sha256"],"code":report["code_sha256"],"config":chosen,
                           "splits":SPLITS[sport],"features":FEATURES,"seed":SEED},sort_keys=True).encode()).hexdigest()[:16]
    report["artifact_id"] = artifact_id
    out = root/"reports"/sport
    out.mkdir(parents=True,exist_ok=True)
    (out/"evaluation.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    pred = test[["event_id","date","side_a","side_b","target"]].copy()
    for model_name,p in predictions.items():
        for i,label in enumerate(labels):
            pred[f"{model_name}__{label}"] = p[:,i]
    private = root/"artifacts"/sport
    private.mkdir(parents=True,exist_ok=True)
    pred.to_csv(private/"holdout_predictions.csv",index=False)
    features.to_csv(private/"features.csv",index=False)
    joblib.dump({"model":model,"temperature":temperature,"features":FEATURES,"sport":sport,
                 "classes":labels,"artifact_id":artifact_id,"training_cutoff":SPLITS[sport][0],
                 "calibration_cutoff":SPLITS[sport][1],"training_prior":prior,
                 "created_at_utc":report["generated_at_utc"]},private/"model.joblib")
    report["model_sha256"] = sha256(private/"model.joblib")
    (out/"evaluation.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    reliability_plot(report,out/"reliability.svg")
    return report

def reliability_plot(report,path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes = plt.subplots(1,len(report["classes"]),figsize=(5*len(report["classes"]),4.4),squeeze=False)
    for i,label in enumerate(report["classes"]):
        ax = axes[0,i]
        ax.plot([0,1],[0,1],"--",color="#aaa",label="Perfect calibration")
        for name,color in (("selected_uncalibrated","#df8f44"),("selected_calibrated","#255fbd"),("elo_calibrated","#25806d")):
            bins = report["test"][name]["reliability"][i]["bins"]
            ax.plot([b["mean_probability"] for b in bins],[b["observed_frequency"] for b in bins],"o-",label=name.replace("_"," "),color=color)
        ax.set(xlim=(0,1),ylim=(0,1),title=label.replace("_"," "),xlabel="Mean predicted probability",ylabel="Observed fraction")
        ax.grid(alpha=.15)
    axes[0,0].legend(fontsize=7)
    fig.suptitle(f"{report['sport'].title()} holdout reliability (10 fixed-width bins)")
    fig.tight_layout()
    fig.savefig(path,format="svg",metadata={"Date":None})
    plt.close(fig)
