"""Local, gated MCP direction experiment. No fitting happens on import.

The four cells, grids, 21-day availability rule and attempt ceiling are fixed by
TENNIS_PROTOCOL_DRAFT.md. Raw identities are historical lookup keys, never model
columns. This is retrospective research, not a live-feed/coaching model.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import gzip
from functools import lru_cache
import signal
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import pickle
import platform
import resource
import sqlite3
import sys
import time
import warnings

# Set before numerical-library imports; threadpoolctl additionally caps libraries
# already imported by the calling process. One process, no joblib workers.
THREAD_SETTINGS = {name: "4" for name in (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
for _name, _value in THREAD_SETTINGS.items():
    os.environ[_name] = _value

import numpy as np
from scipy import sparse
from scipy.optimize import minimize_scalar
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from . import tennis
from .metrics import classification_summary, paired_cluster_interval, per_case_scores

SEED = 20261011
CLASSES = ("wide", "body", "T")
CELLS = (("A1", "m"), ("A1", "w"), ("A2", "m"), ("A2", "w"))
B1_GRID = ((365, 50), (365, 200), (None, 50), (None, 200))
L_GRID = (0.1, 1.0, 10.0)
N_GRID = (15, 31)
EPSILON = 1e-12
EMBARGO_DAYS = 21
EVALUATION_AS_OF = "20260122"
PROTOCOL = "docs/tactical/TENNIS_PROTOCOL_DRAFT.md"
STAGES = {
    "train": ("20100101", "20221231", "20230101"),
    "selection": ("20230101", "20231231", "20240101"),
    "calibration": ("20240101", "20241231", "20250101"),
    "evaluation": ("20250101", "20251231", None),
}
CATEGORY_MAP = {
    "surface": ("Hard", "Clay", "Grass"), "serve_side": ("deuce", "ad"),
    "server_hand": ("R", "L", "U"), "returner_hand": ("R", "L", "U"),
    "current_tiebreak": ("0", "1"),
    "server_points": ("0", "15", "30", "40", "AD", "NA"),
    "returner_points": ("0", "15", "30", "40", "AD", "NA"),
}
FAULT_CATEGORY_MAP = {
    "first_fault_direction": ("wide", "body", "T", "unknown"),
    "first_fault_direction_status": ("known", "explicit_unknown", "omitted"),
    "first_fault_type": ("net", "wide", "deep", "wide_and_deep", "foot_fault", "unknown", "shank"),
}
NUMERIC_NAMES = (
    "server_sets", "returner_sets", "server_games", "returner_games", "game_number", "point_ordinal",
    "tiebreak_server_points", "tiebreak_returner_points",
    *("b0_" + c for c in CLASSES), *("server_tendency_" + c for c in CLASSES),
    *("returner_tendency_" + c for c in CLASSES),
    "log_server_effective_count", "log_server_match_count", "log_returner_effective_count", "log_returner_match_count",
)
HISTORY_SETTINGS = {
    "start": "20100101", "availability": "source Date + 21 calendar days strictly before analysis date",
    "availability_is_verified": False, "same_day": "day-start frozen", "within_match_updates": False,
    "b0_pseudocounts": [1, 100, 30], "feature_half_life_days": 730, "feature_alpha": 100,
    "support_definition": "actor-total eligible observations and distinct prior eligible matches, across sides/surfaces",
    "weights_frozen_after": "2010-2022 fit; 2023 selection; no refit", "pre2010_history": False,
}


def zeros3():
    return np.zeros(3, dtype=np.float64)


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


@lru_cache(maxsize=10000)
def ordinal(value):
    return datetime.strptime(value, "%Y%m%d").date().toordinal()


def available_ordinal(source_date):
    return ordinal(source_date) + EMBARGO_DAYS


def stage_eligible(source_date, stage, *, as_of=None):
    start, end, cutoff = STAGES[stage]
    if not start <= source_date <= end:
        return False
    if stage == "evaluation":
        if as_of is None:
            raise ValueError("Evaluation needs an explicit label-availability as_of date")
        cutoff = as_of
    return available_ordinal(source_date) < ordinal(cutoff)


def category_map(task):
    if task not in ("A1", "A2"):
        raise ValueError("Unknown task")
    return dict(CATEGORY_MAP, **(FAULT_CATEGORY_MAP if task == "A2" else {}))


def normalize_probabilities(probabilities):
    p = np.asarray(probabilities, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all() or (p < 0).any():
        raise ValueError("Expected finite nonnegative three-class probabilities")
    if not np.allclose(p.sum(axis=1), 1, rtol=0, atol=1e-10):
        raise ValueError("Unnormalized probability vector")
    q = np.maximum(p, EPSILON)
    return q / q.sum(axis=1, keepdims=True)


@dataclass
class DecayedCounter:
    values: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    at: int | None = None

    def read(self, day, half_life):
        if self.at is not None and day < self.at:
            raise ValueError("History cannot move backwards")
        if self.at is not None and half_life is not None:
            self.values *= 2.0 ** (-(day-self.at)/half_life)
        self.at = day
        return self.values

    def add(self, day, source_day, target, half_life, count=1):
        values = self.read(day, half_life)
        values[target] += count * (1 if half_life is None else 2.0 ** (-(day-source_day)/half_life))


class CellHistory:
    """Only already-available accepted matches enter this object.

    snapshots do not accept current target, suffix, winner or QA result. History
    ingestion is distinct, rejects overlap, and verifies both temporal bounds.
    """
    def __init__(self):
        self.global_counts = np.zeros(3, dtype=np.float64)
        self.surface = defaultdict(zeros3)
        self.context = defaultdict(zeros3)
        self.actor = {h: {} for h in (None, 365, 730)}
        self.match_counts = defaultdict(int)
        self.raw_counts = Counter()
        self.ingested_matches = set()
        self.last_analysis_day = None
        self.last_snapshot_day = None

    def ingest(self, match_id, source_date, observations, analysis_date, *, accepted=True):
        source_day, day = ordinal(source_date), ordinal(analysis_date)
        if not accepted:
            return
        if source_date < "20100101" or source_day + EMBARGO_DAYS >= day:
            raise ValueError("History label is not available strictly before analysis date")
        if self.last_analysis_day is not None and day < self.last_analysis_day:
            raise ValueError("History cannot move backwards")
        if self.last_snapshot_day is not None and day <= self.last_snapshot_day:
            raise ValueError("Day-start history is already frozen for this analysis date")
        if match_id in self.ingested_matches:
            raise ValueError("Whole match already ingested")
        self.last_analysis_day = day
        self.ingested_matches.add(match_id)
        actors = set()
        # A whole match is submitted atomically; aggregate before updating.
        aggregates = Counter((r["surface"], r["serve_side"], r["server"], r["returner"], int(y)) for r,y in observations)
        for (surface, side, server, returner, target), n in aggregates.items():
            if target not in (0,1,2):
                raise ValueError("Unknown target direction")
            self.global_counts[target] += n
            self.surface[surface][target] += n
            self.context[(surface, side)][target] += n
            for role, actor in (("server", server), ("returner", returner)):
                actors.add((role, actor)); self.raw_counts[(role, actor)] += n
                for h, groups in self.actor.items():
                    for key in ((role,actor), (role,actor,side), (role,actor,surface,side)):
                        groups.setdefault(key, DecayedCounter()).add(day, source_day, target, h, n)
        for key in actors:
            self.match_counts[key] += 1

    def b0(self, surface, side):
        global_p = (self.global_counts+1)/(self.global_counts.sum()+3)
        sc = self.surface.get(surface, np.zeros(3))
        sp = (sc+100*global_p)/(sc.sum()+100)
        cc = self.context.get((surface,side), np.zeros(3))
        return (cc+30*sp)/(cc.sum()+30)

    def tendency(self, actor, role, surface, side, source_date, half_life, alpha):
        day = ordinal(source_date)
        if self.last_analysis_day is not None and day < self.last_analysis_day:
            raise ValueError("Analysis precedes admitted history")
        base = self.b0(surface, side)
        groups = self.actor[half_life]
        def counts(key):
            entry = groups.get(key)
            return entry.read(day, half_life) if entry else np.zeros(3, dtype=np.float64)
        ss = counts((role,actor,side))
        pside = base.copy() if ss.sum()==0 else (ss+alpha*base)/(ss.sum()+alpha)
        ctx = counts((role,actor,surface,side))
        p = pside.copy() if ctx.sum()==0 else (ctx+alpha*pside)/(ctx.sum()+alpha)
        return p, float(counts((role,actor)).sum()), self.match_counts.get((role,actor),0)

    def features(self, raw, task):
        """Consume only the parser's explicit pre-point feature mapping."""
        source_date = raw["match_date"]
        day = ordinal(source_date)
        if self.last_analysis_day is not None and day < self.last_analysis_day:
            raise ValueError("Analysis cannot move backwards")
        self.last_analysis_day = day
        self.last_snapshot_day = day
        surface, side = raw["surface"], raw["serve_side"]
        tb = bool(raw["current_tiebreak"])
        cats = {"surface":surface, "serve_side":side,
                "server_hand":raw["server_hand"] or "U", "returner_hand":raw["returner_hand"] or "U",
                "current_tiebreak":str(int(tb)),
                "server_points":"NA" if tb else str(raw["server_points"]),
                "returner_points":"NA" if tb else str(raw["returner_points"])}
        if task == "A2":
            cats.update(first_fault_direction=raw["first_fault_direction"] or "unknown",
                        first_fault_direction_status=raw["first_fault_direction_status"], first_fault_type=raw["first_fault_type"])
        cmap = category_map(task)
        for name, choices in cmap.items():
            if cats[name] not in choices:
                raise ValueError(f"Unexpected categorical value for {name}: {cats[name]!r}")
        nums = [float(raw[name]) for name in NUMERIC_NAMES[:6]]
        nums += [float(raw["server_points"]) if tb else 0., float(raw["returner_points"]) if tb else 0.]
        nums += self.b0(surface,side).tolist()
        support = []
        for role in ("server", "returner"):
            p, count, matches = self.tendency(raw[role],role,surface,side,source_date,730,100)
            nums += p.tolist(); support += [math.log1p(count),math.log1p(matches)]
        nums += support
        values = np.asarray(nums,dtype=np.float64)
        if not np.isfinite(values).all():
            raise ValueError("Unexpected missing/nonfinite numerical feature")
        baselines = [self.b0(surface,side)]
        for h,alpha in B1_GRID:
            baselines.append(self.tendency(raw["server"],"server",surface,side,source_date,h,alpha)[0])
        audit = {role+"_prior_points":self.raw_counts.get((role,raw[role]),0) for role in ("server","returner")}
        audit["server_side_prior_points"]=int(self.actor[None].get(("server",raw["server"],side),DecayedCounter()).values.sum())
        audit.update(server_prior_matches=self.match_counts.get(("server",raw["server"]),0),
                     returner_prior_matches=self.match_counts.get(("returner",raw["returner"]),0))
        return values, np.asarray([cmap[k].index(cats[k]) for k in cmap],dtype=np.int32), np.asarray(baselines,dtype=np.float64), audit


class Preprocessor:
    def __init__(self, task):
        self.task=task; self.vocabulary=category_map(task); self.fitted=False

    def fit(self, numeric, categorical, *, stage):
        if stage != "train" or self.fitted:
            raise ValueError("Preprocessing is fitted exactly once on training only")
        self._validate(numeric,categorical)
        self.scaler=StandardScaler(with_mean=False).fit(numeric)
        self.encoder=OneHotEncoder(categories=[np.arange(len(v),dtype=np.int32) for v in self.vocabulary.values()],
                                   handle_unknown="ignore",sparse_output=True,dtype=np.float64).fit(categorical)
        self.fitted=True
        return self

    def _validate(self, numeric, categorical):
        if numeric.dtype != np.float64 or categorical.dtype != np.int32:
            raise ValueError("Feature dtypes must be float64 / int32")
        if numeric.ndim!=2 or numeric.shape[1]!=len(NUMERIC_NAMES) or categorical.shape!=(len(numeric),len(self.vocabulary)):
            raise ValueError("Feature shape disagreement")
        if not np.isfinite(numeric).all():
            raise ValueError("Unexpected missing/nonfinite numerical feature")
        for col, choices in enumerate(self.vocabulary.values()):
            if ((categorical[:,col]<0)|(categorical[:,col]>=len(choices))).any():
                raise ValueError("Unknown category code; explicit U/unknown is required")

    def transform(self, numeric, categorical, *, family):
        if not self.fitted:
            raise ValueError("Unfitted preprocessing")
        self._validate(numeric,categorical)
        if family=="L":
            return sparse.hstack([sparse.csr_matrix(self.scaler.transform(numeric)),self.encoder.transform(categorical)],format="csr",dtype=np.float64)
        if family=="N":
            return np.hstack([numeric,categorical.astype(np.float64)])
        raise ValueError("Unknown model family")

    def manifest(self):
        return {"numeric_names":list(NUMERIC_NAMES),"categories":self.vocabulary,"numeric_dtype":"float64","categorical_dtype":"int32",
                "numeric_mean":self.scaler.mean_.tolist(),"numeric_scale":self.scaler.scale_.tolist(),"with_mean":False,"fit_stage":"train"}


def runtime_manifest():
    import scipy, sklearn, pandas
    return {"python":sys.version,"platform":platform.platform(),"numpy":np.__version__,"pandas":pandas.__version__,
            "scipy":scipy.__version__,"scikit_learn":sklearn.__version__,"threads":THREAD_SETTINGS,"seed":SEED,"processes":1}


def verify_runtime():
    found=runtime_manifest()
    if sys.version_info[:2]!=(3,12) or any(found[k]!=v for k,v in {"numpy":"2.3.5","pandas":"2.2.3","scipy":"1.17.0","scikit_learn":"1.8.0"}.items()):
        raise RuntimeError("Runtime differs from reviewed Python/dependency pins")
    return found


def rss_bytes():
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform=="darwin" else peak*1024)


class BudgetExceeded(RuntimeError):
    pass


@contextmanager
def optimizer_resource_limits(remaining_cpu):
    """OS address-space and CPU guards, in addition to peak-RSS reporting.

    The 4 GiB virtual-address cap is stricter than the resident-memory cap and
    can fail conservatively. SIGXCPU raises at the next interpreter boundary;
    the CPU soft limit is rounded up by less than one second.
    """
    old_as=resource.getrlimit(resource.RLIMIT_AS)
    old_cpu=resource.getrlimit(resource.RLIMIT_CPU)
    old_signal=signal.getsignal(signal.SIGXCPU)
    def exhausted(signum,frame):
        raise BudgetExceeded("90 CPU-minute stage budget exhausted")
    cap=4*1024**3
    if old_as[0]!=resource.RLIM_INFINITY:cap=min(cap,old_as[0])
    cpu=max(1,math.ceil(time.process_time()+max(0,remaining_cpu)))
    if old_cpu[1]!=resource.RLIM_INFINITY:cpu=min(cpu,old_cpu[1])
    try:
        signal.signal(signal.SIGXCPU,exhausted)
        resource.setrlimit(resource.RLIMIT_AS,(cap,old_as[1]))
        resource.setrlimit(resource.RLIMIT_CPU,(cpu,old_cpu[1]))
        yield
    finally:
        resource.setrlimit(resource.RLIMIT_AS,old_as)
        resource.setrlimit(resource.RLIMIT_CPU,old_cpu)
        signal.signal(signal.SIGXCPU,old_signal)


class AttemptLedger:
    """Write-ahead accounting. An interrupted attempt is never silently retried."""
    def __init__(self,path):
        self.path=Path(path)
        self.records=json.loads(self.path.read_text()) if self.path.exists() else []
        self.cpu_started=time.process_time()
        self.prior_stage_cpu=max((r.get("stage_cpu_seconds",0) for r in self.records),default=0)
        for filename in ("candidate_resource_totals.json","resource_totals.json"):
            saved=self.path.parent/filename
            if saved.exists():self.prior_stage_cpu=max(self.prior_stage_cpu,json.loads(saved.read_text())["cpu_seconds"])
        if not self.path.exists():write_json(self.path,self.records)

    def used_cpu(self):
        return self.prior_stage_cpu+time.process_time()-self.cpu_started

    def check_budget(self):
        totals={"cpu_seconds":self.used_cpu(),"peak_rss_bytes":rss_bytes(),"optimizer_attempts":len(self.records),"cpu_limit_seconds":5400,"rss_limit_bytes":4*1024**3}
        if totals["cpu_seconds"]>5400 or totals["peak_rss_bytes"]>4*1024**3:
            raise BudgetExceeded("Complete candidate stage exceeds CPU/RSS budget")
        return totals

    def _check(self, cell, family, parameter, retry):
        if family not in ("L","N","probe","temperature") or cell not in [cell_name(c) for c in CELLS]:
            raise ValueError("Undeclared optimizer attempt")
        if len(self.records)>=49:
            raise RuntimeError("49-attempt ceiling exhausted")
        if self.used_cpu()>=90*60 or rss_bytes()>4*1024**3:
            raise RuntimeError("CPU/RSS budget exhausted")
        same=[r for r in self.records if (r["cell"],r["family"],r["parameter"])==(cell,family,parameter)]
        if family=="probe":
            if cell!="A1_m" or parameter!=15 or retry or any(r["family"]=="probe" for r in self.records):
                raise RuntimeError("Only the single fixed A1-men probe is permitted")
        elif family=="L":
            if parameter not in L_GRID or (not retry and same) or (retry and (len(same)!=1 or same[0]["status"]!="convergence_warning")):
                raise RuntimeError("Only the declared C and one convergence retry are permitted")
        elif family=="N":
            if parameter not in N_GRID or same or retry:
                raise RuntimeError("Undeclared nonlinear attempt")
        elif family=="temperature":
            if parameter not in ("B0","B1","L","N") or same or retry:
                raise RuntimeError("One scalar calibration per frozen family")

    @contextmanager
    def attempt(self,cell,family,parameter,*,retry=False):
        self._check(cell,family,parameter,retry)
        record={"number":len(self.records)+1,"cell":cell,"family":family,"parameter":parameter,"retry":retry,
                "status":"started","seed":SEED,"thread_settings":THREAD_SETTINGS,"started_utc":datetime.now().isoformat()}
        self.records.append(record);write_json(self.path,self.records)
        cpu,wall=time.process_time(),time.monotonic()
        try:
            with threadpool_limits(limits=4),optimizer_resource_limits(90*60-self.used_cpu()):
                yield record
            if record["status"]=="started":record["status"]="succeeded"
        except BaseException as exc:
            record.update(status="failed",error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            record.update(cpu_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-wall,peak_rss_bytes=rss_bytes(),stage_cpu_seconds=self.used_cpu())
            write_json(self.path,self.records)
        if self.used_cpu()>90*60 or rss_bytes()>4*1024**3:
            raise RuntimeError("Candidate fit CPU/RSS cap exceeded; stop the stage")


def cell_name(cell):
    return "_".join(cell)


def make_estimator(family,parameter,*,retry=False,probe=False):
    if family=="L":
        if parameter not in L_GRID or probe:raise ValueError("Undeclared L setting")
        return LogisticRegression(C=parameter,solver="saga",penalty="l2",fit_intercept=True,class_weight=None,
                                  tol=1e-5,max_iter=1000 if retry else 300,random_state=SEED,n_jobs=None)
    if family=="N":
        if parameter not in N_GRID or retry:raise ValueError("Undeclared N setting")
        return HistGradientBoostingClassifier(learning_rate=.05,max_iter=20 if probe else 120,min_samples_leaf=200,
                l2_regularization=10,max_bins=63,early_stopping=False,random_state=SEED,max_leaf_nodes=parameter,
                categorical_features=[False]*len(NUMERIC_NAMES)+[True]*len(category_map("A1")))
    raise ValueError("Unknown family")


def choose_candidate(losses,family):
    """Tie band is relative to the actual minimum, never chained pairwise."""
    valid={k:v for k,v in losses.items() if np.isfinite(v)}
    if not valid: return None
    eligible=[k for k,v in valid.items() if v<=min(valid.values())+.002]
    if family=="B1":
        return min(eligible,key=lambda key:(0 if B1_GRID[key][1]==200 else 1,0 if B1_GRID[key][0] is None else 1))
    return min(eligible)


def designate(family_losses):
    valid={k:v for k,v in family_losses.items() if np.isfinite(v)}
    if not valid:raise ValueError("No valid family")
    return next(f for f in ("B0","B1","L","N") if f in valid and valid[f]<=min(valid.values())+.002)


def temperature_probabilities(probabilities,temperature):
    if not np.isfinite(temperature) or temperature<=0:raise ValueError("Invalid temperature")
    z=np.log(normalize_probabilities(probabilities))/temperature
    z-=z.max(axis=1,keepdims=True); q=np.exp(z)
    return q/q.sum(axis=1,keepdims=True)


def support(labels,matches,stage):
    counts=np.bincount(np.asarray(labels,dtype=int),minlength=3)
    nmatches=len(set(matches))
    enough=(counts>=1000).all() if stage=="train" else ((counts>=200).all() and nmatches>=50)
    if stage=="calibration":enough=bool(enough and len(labels)>=3000)
    return {"n":len(labels),"matches":nmatches,"class_counts":counts.tolist(),"sufficient":bool(enough)}


@dataclass(frozen=True)
class ReadPermit:
    phase: str
    as_of: str | None = None

    def __post_init__(self):
        if self.phase=="evaluation" and self.as_of!=EVALUATION_AS_OF:
            raise PermissionError("Evaluation cutoff is frozen at 20260122; partial cohorts are forbidden")

    def check(self, source_date, purpose, analysis_date=None):
        allowed={"development":("train","selection"),"calibration":("calibration",),"evaluation":("evaluation",)}
        if self.phase not in allowed:raise PermissionError("Unknown label-access phase")
        if source_date < "20100101" or source_date > "20251231":
            raise PermissionError("Outside approved source-date range")
        if purpose=="parameter":
            if not any(stage_eligible(source_date,s,as_of=self.as_of) for s in allowed[self.phase]):
                raise PermissionError("Parameter label is outside the authorized availability-adjusted partition")
        elif purpose=="history":
            maximum={"development":"20231231","calibration":"20241231","evaluation":"20251231"}[self.phase]
            if analysis_date is None or analysis_date>maximum or available_ordinal(source_date)>=ordinal(analysis_date):
                raise PermissionError("History label is not available for this authorized analysis date")
        else:
            raise PermissionError("Unknown label-read purpose")


class SourceReader:
    """No whole-period target frame. Read and replay one authorized match at a time."""
    def __init__(self,root,permit):
        self.root=Path(root); self.permit=permit
        from .gates import require_stage
        require_stage(self.root,"tennis","evaluation" if permit.phase=="evaluation" else "development")
        if permit.phase=="calibration":verify_selection_freeze(self.root,calibrated=False)
        if permit.phase=="evaluation":verify_selection_freeze(self.root,calibrated=True)
        self.matches,invalid,_=tennis.load_metadata(self.root/"data/research/tennis/source-samples")
        quality={}
        with (self.root/"data/tactical/tennis/match_quality.jsonl").open() as stream:
            for line in stream:
                q=json.loads(line);quality[(q["corpus"],q["match_id"])]=q
        self.keys=[]
        for key,meta in self.matches.items():
            q=quality.get(key)
            if q and not q["quarantined"] and not invalid.get(key) and "20100101"<=meta["Date"]<="20251231":
                if tennis.metadata_errors(meta):raise ValueError("Accepted cache conflicts with current date/metadata QA")
                self.keys.append(key)
        self.keys.sort(key=lambda key:(self.matches[key]["Date"],key[1],key[0]))
        self.quality=quality
        self.db=sqlite3.connect(f"file:{self.root/'data/tactical/tennis/source_index.sqlite3'}?mode=ro",uri=True)
        self.db.execute("PRAGMA cache_size=-32768")
        self.read_log=Counter()

    def read_match(self,key,*,purpose,analysis_date=None):
        meta=self.matches[key]
        self.permit.check(meta["Date"],purpose,analysis_date)
        # Guard must precede SELECT payload, not just downstream model fitting.
        rows=[dict(zip(tennis.POINT_COLUMNS,json.loads(r[0]))) for r in self.db.execute(
            "SELECT payload FROM points WHERE corpus=? AND match_id=? ORDER BY pt",key)]
        if len(rows)!=self.quality[key]["point_count"] or [int(r["Pt"]) for r in rows]!=list(range(1,len(rows)+1)):
            raise ValueError("Source cache changed or has incomplete match")
        states,reasons,_,_=tennis.audit_match(meta,rows)
        if reasons:raise ValueError("Accepted match fails frozen parser replay")
        self.read_log[purpose]+=1
        out={"A1":[],"A2":[]}
        for row,state in zip(rows,states):
            parsed=(tennis.parse_serve(row["1st"]),tennis.parse_serve(row["2nd"]))
            for task in out:
                record=tennis.target_record(meta,row,state,key[0],task,parsed_attempts=parsed,include_quality=False)
                if record["eligible"]:
                    out[task].append((record["features"],CLASSES.index(record["target"]),bool(row["Notes"].strip())))
        return out

    def close(self):self.db.close()


class DatasetWriter:
    def __init__(self,path,task,*,stage=None,label_cutoff=None):
        self.stage=stage;self.label_cutoff=label_cutoff
        self.path=Path(path)
        if self.path.exists():raise FileExistsError("Refusing to replace prepared rows")
        self.path.mkdir(parents=True)
        self.task=task;self.n=0
        self.streams={k:(self.path/(k+".dat")).open("wb") for k in ("numeric","categorical","baselines","labels")}
        self.meta_raw=(self.path/"metadata.jsonl.gz").open("wb")
        self.meta=gzip.GzipFile(filename="",mode="wb",fileobj=self.meta_raw,mtime=0)
        self.row_hash=hashlib.sha256();self.feature_hash=hashlib.sha256();self.label_hash=hashlib.sha256()

    def append(self,numeric,categorical,baselines,label,metadata):
        arrays={"numeric":np.asarray(numeric,dtype=np.float64),"categorical":np.asarray(categorical,dtype=np.int32),
                "baselines":np.asarray(baselines,dtype=np.float64),"labels":np.asarray([label],dtype=np.int8)}
        for key,array in arrays.items():self.streams[key].write(array.tobytes())
        rowid=json.dumps(metadata["row_id"],separators=(",",":")).encode()+b"\n"
        self.row_hash.update(rowid);self.label_hash.update(rowid+arrays["labels"].tobytes())
        self.feature_hash.update(rowid+arrays["numeric"].tobytes()+arrays["categorical"].tobytes()+arrays["baselines"].tobytes())
        self.meta.write((json.dumps(metadata,sort_keys=True,separators=(",",":"))+"\n").encode());self.n+=1

    def close(self):
        for stream in self.streams.values():stream.close()
        self.meta.close();self.meta_raw.close()
        manifest={"task":self.task,"stage":self.stage,"label_cutoff":self.label_cutoff,"n":self.n,"numeric_columns":len(NUMERIC_NAMES),"categorical_columns":len(category_map(self.task)),
                  "row_sha256":self.row_hash.hexdigest(),"feature_sha256":self.feature_hash.hexdigest(),"label_sha256":self.label_hash.hexdigest()}
        manifest["files"]={p.name:tennis.digest(p) for p in self.path.iterdir() if p.is_file()}
        write_json(self.path/"manifest.json",manifest)
        return manifest


class Dataset:
    def __init__(self,path,*,root,stage,verify=True):
        self.path=Path(path)
        if stage not in STAGES:raise PermissionError("Unknown cached-label stage")
        expected=artifact_dir(root)/"rows"/stage
        if self.path.resolve().parent!=expected.resolve():raise PermissionError("Cached labels are in a different stage")
        from .gates import require_stage
        require_stage(root,"tennis","evaluation" if stage=="evaluation" else "development")
        if stage=="calibration":verify_selection_freeze(root,calibrated=False)
        if stage=="evaluation":verify_selection_freeze(root,calibrated=True)
        self.manifest=json.loads((self.path/"manifest.json").read_text())
        cutoff=EVALUATION_AS_OF if stage=="evaluation" else STAGES[stage][2]
        if self.manifest.get("stage")!=stage or self.manifest.get("label_cutoff")!=cutoff:
            raise PermissionError("Cached labels use a different stage or frozen availability cutoff")
        phase={"train":"development","selection":"development","calibration":"calibration","evaluation":"evaluation"}[stage]
        parent_path=artifact_dir(root)/(phase+"_rows.json")
        if not parent_path.exists():raise PermissionError("Cached labels lack their complete stage manifest")
        parent=json.loads(parent_path.read_text())
        if parent.get("datasets",{}).get(stage,{}).get(self.path.name)!=self.manifest:
            raise PermissionError("Cached-label manifest differs from its stage parent")
        if stage in ("train","selection") and (artifact_dir(root)/"CANDIDATE_FREEZE.json").exists():
            verify_selection_freeze(root,calibrated=False)
        if verify:
            for name,digest in self.manifest["files"].items():
                if tennis.digest(self.path/name)!=digest:raise ValueError("Prepared dataset digest changed")
        n=self.manifest["n"]
        def mmap(name,dtype,shape):
            return np.memmap(self.path/(name+".dat"),mode="r",dtype=dtype,shape=shape) if n else np.empty(shape,dtype=dtype)
        self.numeric=mmap("numeric",np.float64,(n,len(NUMERIC_NAMES)))
        self.categorical=mmap("categorical",np.int32,(n,self.manifest["categorical_columns"]))
        self.baselines=mmap("baselines",np.float64,(n,5,3))
        self.labels=mmap("labels",np.int8,(n,))
        self.n=n

    def metadata(self):
        with gzip.open(self.path/"metadata.jsonl.gz","rt") as stream:
            for line in stream:yield json.loads(line)

    def supports(self,stage):
        return support(self.labels,(r["match_id"] for r in self.metadata()),stage)


def artifact_dir(root):return Path(root)/"artifacts/tactical/tennis"


def code_paths():
    return ["experiments/tactical/tennis_model.py","experiments/tactical/tennis.py",
            "experiments/tactical/metrics.py","experiments/tactical/gates.py"]


def verify_source_cache_lineage(root,provenance):
    """An independently recorded derivative anchor is mandatory, never self-created."""
    root=Path(root)
    summary_path="reports/tactical/tennis/summary.json"
    summary=json.loads((root/summary_path).read_text())
    prior=summary["provenance"]
    for key in ("manifest_sha256","parser_code_sha256","commit","files"):
        if prior.get(key)!=provenance.get(key):
            raise PermissionError("Source summary/parser lineage is stale: "+key)
    review_path="docs/tactical/INDEPENDENT_STAGE_ONE_REVIEW_MANIFEST.json"
    review=json.loads((root/review_path).read_text())
    for path in (summary_path,"experiments/tactical/tennis.py","docs/research/tennis/source_manifest.json"):
        if review["files_sha256"].get(path)!=tennis.digest(root/path):
            raise PermissionError("Parser/source summary differs from independent stage-one review")
    anchor_path="artifacts/tactical/tennis/SOURCE_CACHE_REVIEW.json"
    if not (root/anchor_path).exists():
        raise PermissionError("Missing independent source-cache lineage/hash review")
    anchor=json.loads((root/anchor_path).read_text())
    expected={"schema_version":1,"status":"independently_verified",
              "source_manifest_sha256":provenance["manifest_sha256"],"parser_code_sha256":provenance["parser_code_sha256"],
              "raw_files_sha256":{f["file"]:f["sha256"] for f in provenance["files"]},
              "independent_review_manifest_sha256":tennis.digest(root/review_path)}
    if any(anchor.get(key)!=value for key,value in expected.items()) or not anchor.get("reviewed_utc") or not anchor.get("lineage_verification"):
        raise PermissionError("Independent source-cache anchor does not match reviewed inputs")
    required={"data/tactical/tennis/source_index.sqlite3","data/tactical/tennis/match_quality.jsonl",summary_path}
    if set(anchor.get("files_sha256",{}))!=required:
        raise PermissionError("Incomplete source-cache derivative anchor")
    for path,digest in anchor["files_sha256"].items():
        if tennis.digest(root/path)!=digest:raise PermissionError("Reviewed source-cache bytes changed: "+path)
    return {**anchor["files_sha256"],anchor_path:tennis.digest(root/anchor_path),review_path:tennis.digest(root/review_path)}


def prepare(root):
    """Prepare a byte binding only. Never read target payloads or fit estimators."""
    from .gates import prepare_binding
    root=Path(root)
    provenance=tennis.validate_sources(root)
    files={"docs/research/tennis/source_manifest.json":provenance["manifest_sha256"]}
    for entry in provenance["files"]:files["data/research/tennis/source-samples/"+entry["file"]]=entry["sha256"]
    files.update(verify_source_cache_lineage(root,provenance))
    return prepare_binding(root,"tennis",PROTOCOL,code_paths(),files,
                           metadata={"history":HISTORY_SETTINGS,"cells":[cell_name(c) for c in CELLS],"runtime":verify_runtime(),
                                     "prior_2025_exposure":"Source/score/eligibility QA occurred; performance-blind afterward, not untouched"})


def verify_selection_freeze(root,*,calibrated):
    from .gates import verify_binding
    binding=verify_binding(root,"tennis")
    path=artifact_dir(root)/("SELECTION_FREEZE.json" if calibrated else "CANDIDATE_FREEZE.json")
    if not path.exists():raise PermissionError("All four cells must be frozen before later-period label reads")
    freeze=json.loads(path.read_text())
    if set(freeze["cells"])!={cell_name(c) for c in CELLS}:raise PermissionError("Incomplete four-cell freeze")
    for relative,digest in freeze["files"].items():
        if tennis.digest(artifact_dir(root)/relative)!=digest:raise PermissionError("Frozen pipeline changed")
    if freeze["binding_sha256"]!=binding["binding_sha256"]:
        raise PermissionError("Selection was frozen against a different binding")
    return freeze


def _save_pickle(path,obj):
    path=Path(path);tmp=path.with_suffix(path.suffix+".partial")
    with tmp.open("wb") as stream:pickle.dump(obj,stream,protocol=5)
    tmp.replace(path)


def _load_local_pickle(path):
    # Only locally created files pinned by a reviewed binding/freeze, never uploads.
    with Path(path).open("rb") as stream:return pickle.load(stream)


def build_rows(root,phase,*,as_of=None):
    """Shared four-cell chronological pass; parameter/history reads have separate guards."""
    root=Path(root);dest=artifact_dir(root);permit=ReadPermit(phase,as_of)
    source=SourceReader(root,permit)
    phases={"development":("train","selection"),"calibration":("calibration",),"evaluation":("evaluation",)}[phase]
    previous={"calibration":"development","evaluation":"calibration"}.get(phase)
    checkpoint=dest/(previous+"_history.pkl") if previous else None
    if checkpoint:
        prior=json.loads((dest/(previous+"_rows.json")).read_text())
        if tennis.digest(checkpoint)!=prior["history_checkpoint_sha256"]:raise ValueError("History checkpoint changed")
        histories,cursor=_load_local_pickle(checkpoint)
    else:
        histories={cell:CellHistory() for cell in CELLS};cursor=0
    writers={(stage,cell):DatasetWriter(dest/"rows"/stage/cell_name(cell),cell[0],stage=stage,label_cutoff=EVALUATION_AS_OF if stage=="evaluation" else STAGES[stage][2]) for stage in phases for cell in CELLS}
    excluded=Counter();training_actors={cell:{"server":set(),"returner":set()} for cell in CELLS}
    actors_path=dest/"training_actors.pkl"
    if previous:training_actors=_load_local_pickle(actors_path)
    try:
        for key in source.keys:
            meta=source.matches[key];source_date=meta["Date"]
            stage=next((s for s in phases if STAGES[s][0]<=source_date<=STAGES[s][1]),None)
            if stage is None:continue
            if not stage_eligible(source_date,stage,as_of=as_of):
                # Do not parse these unavailable targets even to count directions.
                excluded[stage+"_late_or_unavailable_matches"]+=1
                excluded[stage+"_late_or_unavailable_candidate_points"]+=source.quality[key]["point_count"]
                continue
            while cursor<len(source.keys):
                prior_key=source.keys[cursor];prior_meta=source.matches[prior_key]
                if available_ordinal(prior_meta["Date"])>=ordinal(source_date):break
                admitted=source.read_match(prior_key,purpose="history",analysis_date=source_date)
                for task,obs in admitted.items():
                    histories[(task,prior_key[0])].ingest(prior_key[1],prior_meta["Date"],[(f,y) for f,y,_ in obs],source_date)
                cursor+=1
            match=source.read_match(key,purpose="parameter")
            for task,obs in match.items():
                cell=(task,key[0]);history=histories[cell]
                for raw,target,note in obs:
                    nums,cats,baselines,audit=history.features(raw,task)
                    metadata={"row_id":[key[0],key[1],int(raw["point_ordinal"]),task],"match_id":key[1],
                        "date":source_date,"tournament":meta["Tournament"],"server":raw["server"],"returner":raw["returner"],
                        "surface":raw["surface"],"side":raw["serve_side"],"hand_pair":raw["server_hand"]+raw["returner_hand"],
                        "notes_present":note,**audit}
                    for role in ("server","returner"):
                        metadata[role+"_cold"]=raw[role] not in training_actors[cell][role]
                        if stage=="train":training_actors[cell][role].add(raw[role])
                    writers[(stage,cell)].append(nums,cats,baselines,target,metadata)
        manifests={stage:{cell_name(cell):writers[(stage,cell)].close() for cell in CELLS} for stage in phases}
    finally:
        source.close()
    output_checkpoint=dest/(phase+"_history.pkl")
    _save_pickle(output_checkpoint,(histories,cursor))
    if not previous:_save_pickle(actors_path,training_actors)
    report={"phase":phase,"evaluation_as_of":as_of if phase=="evaluation" else None,"datasets":manifests,"unavailable_parameter_rows":dict(excluded),
            "read_counts":dict(source.read_log),"history_checkpoint_sha256":tennis.digest(output_checkpoint),
            "history_settings":HISTORY_SETTINGS}
    write_json(dest/(phase+"_rows.json"),report)
    return report


def matrix_estimate(dataset):
    # Conservative explicit full-cell envelope: raw/mapped arrays, both transforms,
    # coefficient/gradient copies, histogram workspaces, and 512 MiB fixed headroom.
    dense=dataset.n*(len(NUMERIC_NAMES)+dataset.manifest["categorical_columns"])*8
    sparse_bytes=dataset.n*(len(NUMERIC_NAMES)+dataset.manifest["categorical_columns"])*12+(dataset.n+1)*4
    return int(4*dense+2*sparse_bytes+dataset.n*3*8*8+512*1024**2)


def fit_candidate(root,ledger,cell,family,parameter,X,y,*,retry=False,probe=False):
    from .gates import record_operation
    name=cell_name(cell);kind="probe" if probe else family
    if family=="N" and not probe:
        admission=artifact_dir(root)/"resource_probe.json"
        if not admission.exists() or not json.loads(admission.read_text()).get("admitted"):
            raise PermissionError("N requires the approved fixed resource probe admission")
    model=make_estimator(family,parameter,retry=retry,probe=probe)
    if family=="N":
        model.set_params(categorical_features=[False]*len(NUMERIC_NAMES)+[True]*len(category_map(cell[0])))
    ledger._check(name,kind,parameter,retry)
    config={"family":family,"parameter":parameter,"retry":retry,"probe":probe,"estimator":model.get_params(),
            "seed":SEED,"numeric_dtype":"float64","rows":len(y)}
    record_operation(root,"tennis","development",f"{name}:{kind}:{parameter}:{'retry' if retry else 'initial'}",config,49)
    with ledger.attempt(name,kind,parameter,retry=retry) as record:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always",ConvergenceWarning)
            model.fit(X,y)
        record["warnings"]=[str(w.message) for w in caught]
        if any(issubclass(w.category,ConvergenceWarning) for w in caught):
            record["status"]="convergence_warning"
            return None,"convergence_warning"
        if not np.array_equal(model.classes_,np.arange(3)):
            raise ValueError("Fitted classes do not match permanently ordered directions")
    return model,"succeeded"


def resource_probe(root,datasets,preprocessors,ledger,training_counts):
    dest=artifact_dir(root);path=dest/"resource_probe.json"
    if path.exists():return json.loads(path.read_text())
    cell=("A1","m");data=datasets.get(cell)
    if data is None:
        result={"status":"not_run","admitted":False,"reason":"A1-men training support failed"}
    else:
        n=min(100000,data.n)
        X=preprocessors[cell].transform(data.numeric[:n],data.categorical[:n],family="N")
        try:
            model,status=fit_candidate(root,ledger,cell,"N",15,X,data.labels[:n],probe=True)
            del model
            rec=ledger.records[-1]
            estimate=2*(120/20)*(2*sum(training_counts.values())/n)*rec["cpu_seconds"]
            full_memory=max(matrix_estimate(d) for d in datasets.values())
            admitted=status=="succeeded" and estimate<=1800 and rec["peak_rss_bytes"]<=2*1024**3 and full_memory<=3*1024**3
            result={"status":status,"admitted":bool(admitted),"probe_rows":n,"cpu_seconds":rec["cpu_seconds"],
                    "wall_seconds":rec["wall_seconds"],"peak_rss_bytes":rec["peak_rss_bytes"],"estimated_full_n_cpu_seconds":estimate,
                    "full_cell_matrix_estimator_memory_estimate_bytes":full_memory,
                    "formula":"2 * (120/20) * (2 * sum(four cell training counts) / probe rows) * probe CPU seconds",
                    "outcome_scores_used":False,"probe_model_discarded":True}
        except (ValueError,MemoryError,RuntimeError,FloatingPointError) as exc:
            result={"status":"failed","admitted":False,"reason":str(exc),"outcome_scores_used":False}
        del X
    write_json(path,result)
    return result


def _family_probabilities(bundle,data,family):
    if data.n==0:return np.empty((0,3),dtype=np.float64)
    if family=="B0":return np.asarray(data.baselines[:,0,:])
    if family=="B1":return np.asarray(data.baselines[:,bundle["selected"]["B1"]+1,:])
    X=bundle["preprocessor"].transform(data.numeric,data.categorical,family=family)
    result=bundle["models"][family].predict_proba(X)
    del X
    normalize_probabilities(result)  # validate without changing saved raw probabilities
    return result


def _freeze(root,filename,cells,files,**extra):
    dest=artifact_dir(root)
    value={"schema_version":1,"cells":cells,"files":{str(p.relative_to(dest)):tennis.digest(p) for p in files},
           "binding_sha256":json.loads((dest/"run_binding.json").read_text())["binding_sha256"],"history_settings":HISTORY_SETTINGS,
           "class_order":CLASSES,"protocol_sha256":tennis.digest(Path(root)/PROTOCOL),"runtime":verify_runtime(),**extra}
    path=dest/filename
    if path.exists():raise FileExistsError("Refusing to overwrite a frozen stage")
    write_json(path,value)
    return value


def develop(root,*,run_probe=True):
    """Fit/choose on 2010–2023, freeze all four cells, then calibrate on 2024.

    Explicit approval + independent implementation review must already be bound.
    This API never opens or scores a 2025 target row.
    """
    from .gates import require_stage
    root=Path(root);require_stage(root,"tennis","development");verify_runtime()
    dest=artifact_dir(root);dest.mkdir(parents=True,exist_ok=True)
    if (dest/"SELECTION_FREEZE.json").exists():return verify_selection_freeze(root,calibrated=True)
    if not (dest/"development_rows.json").exists():build_rows(root,"development")
    ledger=AttemptLedger(dest/"fit_attempts.json")
    candidate_path=dest/"CANDIDATE_FREEZE.json"
    if not candidate_path.exists():
        training={};selection={};preprocessors={};cell_reports={};training_counts={}
        for cell in CELLS:
            name=cell_name(cell)
            train=Dataset(dest/"rows/train"/name,root=root,stage="train");select=Dataset(dest/"rows/selection"/name,root=root,stage="selection")
            st,ss=train.supports("train"),select.supports("selection");training_counts[name]=train.n
            cell_reports[name]={"training_support":st,"selection_support":ss}
            if not st["sufficient"] or not ss["sufficient"]:
                cell_reports[name].update(status="descriptive_only",reason="prespecified class/match support failed")
                continue
            if matrix_estimate(train)>3*1024**3:
                raise RuntimeError("Full-cell feature memory estimate exceeds declared envelope")
            training[cell]=train;selection[cell]=select
            preprocessors[cell]=Preprocessor(cell[0]).fit(train.numeric,train.categorical,stage="train")
        probe=resource_probe(root,training,preprocessors,ledger,training_counts) if run_probe else {"status":"not_run","admitted":False,"reason":"Optional N probe not requested"}
        files=[dest/"development_rows.json",dest/"development_history.pkl",dest/"training_actors.pkl"]
        for cell in CELLS:
            name=cell_name(cell);report=cell_reports[name]
            if cell not in training:
                write_json(dest/(name+"_selection.json"),report);files.append(dest/(name+"_selection.json"));continue
            train,select=training[cell],selection[cell];prep=preprocessors[cell]
            scores={"B0":{0:float(per_case_scores(select.labels,select.baselines[:,0,:],epsilon=EPSILON)["log_loss"].mean())},
                    "B1":{i:float(per_case_scores(select.labels,select.baselines[:,i+1,:],epsilon=EPSILON)["log_loss"].mean()) for i in range(4)}}
            selected={"B0":0,"B1":choose_candidate(scores["B1"],"B1")};models={};failures=[]
            for family,grid in (("L",L_GRID),("N",N_GRID)):
                scores[family]={}
                if family=="N" and not probe["admitted"]:
                    failures.extend({"family":family,"parameter":p,"status":"not_run_budget_gate"} for p in grid);continue
                X=prep.transform(train.numeric,train.categorical,family=family)
                Xs=prep.transform(select.numeric,select.categorical,family=family)
                fitted={}
                for parameter in grid:
                    try:
                        model,status=fit_candidate(root,ledger,cell,family,parameter,X,train.labels)
                        if family=="L" and status=="convergence_warning":
                            model,status=fit_candidate(root,ledger,cell,family,parameter,X,train.labels,retry=True)
                        if model is None:
                            failures.append({"family":family,"parameter":parameter,"status":status});continue
                        predictions=model.predict_proba(Xs)
                        scores[family][parameter]=float(per_case_scores(select.labels,predictions,epsilon=EPSILON)["log_loss"].mean())
                        fitted[parameter]=model
                    except (ValueError,MemoryError,FloatingPointError,RuntimeError) as exc:
                        failures.append({"family":family,"parameter":parameter,"status":"failed","reason":str(exc)})
                chosen=choose_candidate(scores[family],family)
                if chosen is not None:selected[family]=chosen;models[family]=fitted[chosen]
                del X,Xs,fitted
            family_losses={family:scores[family][chosen] for family,chosen in selected.items()}
            main=designate(family_losses)
            bundle={"cell":cell,"selected":selected,"models":models,"preprocessor":prep,"main":main}
            _save_pickle(dest/(name+"_selected.pkl"),bundle)
            probabilities={family:_family_probabilities(bundle,select,family) for family in selected}
            np.savez_compressed(dest/(name+"_selection_predictions.npz"),**probabilities)
            report.update(status="selected",all_candidate_selection_losses=scores,selected_parameters=selected,
                          family_selection_losses=family_losses,designated_main=main,failures=failures,
                          preprocessing=prep.manifest(),train_data=train.manifest,selection_data=select.manifest,
                          nonlinear_probe=probe,common_selection_rows=select.manifest["row_sha256"])
            write_json(dest/(name+"_selection.json"),report)
            files.extend(dest/(name+suffix) for suffix in ("_selected.pkl","_selection_predictions.npz","_selection.json"))
        totals=ledger.check_budget();write_json(dest/"candidate_resource_totals.json",totals);files.append(dest/"candidate_resource_totals.json")
        candidate=_freeze(root,"CANDIDATE_FREEZE.json",cell_reports,files,stage="selection_frozen_before_calibration",resource_totals=totals)
    else:candidate=verify_selection_freeze(root,calibrated=False)
    return calibrate(root,ledger=ledger)


def calibrate(root,*,ledger=None):
    from .gates import require_stage,record_operation
    root=Path(root);require_stage(root,"tennis","development")
    candidate=verify_selection_freeze(root,calibrated=False)
    dest=artifact_dir(root)
    if (dest/"SELECTION_FREEZE.json").exists():return verify_selection_freeze(root,calibrated=True)
    if not (dest/"calibration_rows.json").exists():build_rows(root,"calibration")
    ledger=ledger or AttemptLedger(dest/"fit_attempts.json")
    reports={};files=[dest/"CANDIDATE_FREEZE.json",dest/"calibration_rows.json",dest/"calibration_history.pkl"]
    files.extend(dest/name for name in candidate["files"])
    for cell in CELLS:
        name=cell_name(cell);selection=candidate["cells"][name]
        if selection["status"]!="selected":reports[name]=selection;continue
        bundle=_load_local_pickle(dest/(name+"_selected.pkl"))
        data=Dataset(dest/"rows/calibration"/name,root=root,stage="calibration")
        check=data.supports("calibration");temperatures={};statuses={};predictions={}
        for family in bundle["selected"]:
            p=_family_probabilities(bundle,data,family);predictions[family]=p
            if not check["sufficient"]:
                temperatures[family]=1.;statuses[family]="identity_insufficient_calibration_support";continue
            ledger._check(name,"temperature",family,False)
            record_operation(root,"tennis","development",f"{name}:temperature:{family}",
                             {"bounds":[-3,3],"xatol":1e-5,"maxiter":100,"family":family,"rows":data.n},49,kind="calibration")
            try:
                with ledger.attempt(name,"temperature",family) as record:
                    result=minimize_scalar(lambda logt:float(per_case_scores(data.labels,temperature_probabilities(p,math.exp(logt)),epsilon=EPSILON)["log_loss"].mean()),
                                           method="bounded",bounds=(-3,3),options={"xatol":1e-5,"maxiter":100})
                    success=bool(result.success and np.isfinite(result.x) and np.isfinite(result.fun))
                    record.update(status="succeeded" if success else "calibration_failed_identity",iterations=int(result.nfev))
                temperatures[family]=math.exp(float(result.x)) if success else 1.
                statuses[family]="fitted" if success else "identity_optimizer_failed"
            except (ValueError,FloatingPointError,RuntimeError,MemoryError) as exc:
                temperatures[family]=1.;statuses[family]="identity_optimizer_failed: "+str(exc)
        np.savez_compressed(dest/(name+"_calibration_predictions.npz"),**predictions)
        report={"status":"frozen","designated_main":bundle["main"],"selected_parameters":bundle["selected"],
                "temperatures":temperatures,"calibration_status":statuses,"calibration_support":check,"calibration_data":data.manifest,
                "calibration_loss_is_performance_estimate":False,"model_reselection":False}
        write_json(dest/(name+"_calibration.json"),report);reports[name]=report
        files.extend([dest/(name+"_calibration.json"),dest/(name+"_calibration_predictions.npz")])
    files.append(dest/"fit_attempts.json")
    totals=ledger.check_budget();write_json(dest/"resource_totals.json",totals);files.append(dest/"resource_totals.json")
    return _freeze(root,"SELECTION_FREEZE.json",reports,files,stage="all_four_cells_selected_and_calibrated_2025_locked",
                   attempt_summary=dict(Counter(r["status"] for r in ledger.records)),optimizer_attempts=len(ledger.records),resource_totals=totals)


def moving_block_interval(difference,dates,matches,*,weighting="case"):
    """Four-week non-circular moving blocks on all 53 calendar bins of 2025.

    January 1 anchors seven-day bins, with the last bin shortened. Empty bins are
    retained. Whole matches are assigned by source date; a sampled terminal
    block is trimmed by complete calendar bins, never by points within matches.
    """
    values=np.asarray(difference,dtype=np.float64)
    weeks=np.asarray([(ordinal(d)-ordinal("20250101"))//7 for d in dates],dtype=int)
    if len(weeks)!=len(values) or (weeks<0).any() or (weeks>52).any():raise ValueError("Expected whole-match 2025 source dates")
    ids,inverse=np.unique(matches,return_inverse=True)
    match_n=np.bincount(inverse);match_sum=np.bincount(inverse,weights=values)
    match_week=np.empty(len(ids),dtype=int)
    for i in range(len(ids)):
        assigned=np.unique(weeks[inverse==i])
        if len(assigned)!=1:raise ValueError("Match crosses calendar bins")
        match_week[i]=assigned[0]
    if weighting=="case":
        sums=np.bincount(weeks,weights=values,minlength=53);counts=np.bincount(weeks,minlength=53)
    elif weighting=="group":
        sums=np.bincount(match_week,weights=match_sum/match_n,minlength=53);counts=np.bincount(match_week,minlength=53)
    else:raise ValueError("Unknown weighting")
    populated=sum(counts[i:i+4].sum()>0 for i in range(50))
    result={"difference":float(sums.sum()/counts.sum()),"confidence":.9875,"replicates":2000,"seed":SEED,
            "interval":None,"calendar_bins":53,"weeks_per_block":4,"candidate_contiguous_blocks":50,
            "populated_blocks":int(populated),"populated_weeks":int((counts>0).sum()),"weighting":weighting,
            "limitation":"Few independent temporal blocks; overlapping windows are not independent samples"}
    if (counts>0).sum()<4:
        result["status"]="insufficient_populated_weeks";return result
    rng=np.random.default_rng(SEED);draws=[]
    for _ in range(2000):
        selected=(rng.integers(0,50,size=14)[:,None]+np.arange(4)).ravel()[:53]
        denominator=counts[selected].sum()
        if denominator:draws.append(sums[selected].sum()/denominator)
    if len(draws)!=2000:
        result["status"]="empty_resampled_support";return result
    result.update(status="computed",interval=np.quantile(draws,[.00625,.99375],method="linear").tolist())
    return result


def event_match_macro_interval(difference,matches,event_groups):
    """Resample event clusters while the estimand remains equal-weighted matches."""
    values=np.asarray(difference,dtype=np.float64)
    events=np.asarray(event_groups)
    ids,first,inverse=np.unique(matches,return_index=True,return_inverse=True)
    match_events=events[first]
    if not np.array_equal(events,match_events[inverse]):
        raise ValueError("A match spans more than one tournament/year group")
    means=np.bincount(inverse,weights=values)/np.bincount(inverse)
    result=paired_cluster_interval(means,match_events,replicates=2000,confidence=.9875,seed=SEED,weighting="case")
    result.update(weighting="match_macro_with_event_clusters",original_points=len(values),matches=len(ids))
    return result


def _group_mean(values,groups):
    _,inverse=np.unique(groups,return_inverse=True)
    return float((np.bincount(inverse,weights=values)/np.bincount(inverse)).mean())


def performance_summary(labels,probabilities,metadata):
    report=classification_summary(labels,probabilities,epsilon=EPSILON,bin_edges=np.linspace(0,1,11))
    pred=np.argmax(probabilities,axis=1)
    recall=[float((pred[labels==k]==k).mean()) if (labels==k).any() else None for k in range(3)]
    loss=per_case_scores(labels,probabilities,epsilon=EPSILON)["log_loss"]
    report.update(per_class_recall=dict(zip(CLASSES,recall)),macro_recall=float(np.mean([v for v in recall if v is not None])),
                  match_macro_log_loss=_group_mean(loss,[r["match_id"] for r in metadata]),
                  server_macro_log_loss=_group_mean(loss,[r["server"] for r in metadata]),
                  unseen_history_server_fraction=float(np.mean([r["server_prior_points"]==0 for r in metadata])),
                  unseen_history_returner_fraction=float(np.mean([r["returner_prior_points"]==0 for r in metadata])),
                  b0_fallback_fraction=float(np.mean([r["server_side_prior_points"]==0 for r in metadata])))
    for bucket in report["reliability"]:bucket["sparse"]=bucket["n"]<20
    return report


def support_slices(labels,predictions,metadata):
    groups=defaultdict(list)
    for i,row in enumerate(metadata):
        count=row["server_prior_points"]
        tier="0" if count==0 else "1-49" if count<50 else "50-199" if count<200 else "200+"
        items={key:row[key] for key in ("surface","side","hand_pair","notes_present")}
        items.update(prior_server_support=tier,server_history_seen=count>0,returner_history_seen=row["returner_prior_points"]>0,
                     server_training_cold=row["server_cold"],returner_training_cold=row["returner_cold"],
                     both_training_cold=row["server_cold"] and row["returner_cold"])
        for key,value in items.items():groups[(key,str(value))].append(i)
    out=[]
    for (field,value),indices in sorted(groups.items()):
        indices=np.asarray(indices,dtype=int);matches=len({metadata[i]["match_id"] for i in indices})
        row={"field":field,"value":value,"n":len(indices),"matches":matches,"suppressed":len(indices)<200 or matches<20}
        if not row["suppressed"]:
            row["class_counts"]=np.bincount(labels[indices],minlength=3).tolist()
            row["methods"]={family:{key:float(score.mean()) for key,score in per_case_scores(labels[indices],p[indices],epsilon=EPSILON).items()} for family,p in predictions.items()}
        out.append(row)
    return out


def evaluate(root,*,as_of=EVALUATION_AS_OF):
    """A separate global freeze + evaluation approval is mandatory before labels."""
    from .gates import require_stage
    if as_of!=EVALUATION_AS_OF:raise PermissionError("Evaluation requires the frozen full-year 20260122 cutoff")
    root=Path(root);require_stage(root,"tennis","evaluation");verify_runtime()
    freeze=verify_selection_freeze(root,calibrated=True);dest=artifact_dir(root)
    report_dir=root/"reports/tactical/tennis/model";report_dir.mkdir(parents=True,exist_ok=True)
    if (report_dir/"evaluation.json").exists():raise FileExistsError("Evaluation already reported; no silent replacement")
    if not (dest/"evaluation_rows.json").exists():build_rows(root,"evaluation",as_of=as_of)
    if json.loads((dest/"evaluation_rows.json").read_text()).get("evaluation_as_of")!=EVALUATION_AS_OF:
        raise PermissionError("Cached evaluation uses a different availability cutoff")
    output={"stage":"locked_2025_evaluation","as_of":as_of,"class_order":CLASSES,"cells":{},
            "prior_2025_exposure":"Source/score/eligibility QA, then performance-blind until global freeze and separate unlock",
            "history_settings":HISTORY_SETTINGS,"family_confidence":.9875,"bootstrap_replicates":2000,
            "interpretation":"Retrospective annotated-direction prediction; no live-feed, intent, biomechanical or causal coaching claim"}
    for cell in CELLS:
        name=cell_name(cell);frozen=freeze["cells"][name]
        if frozen["status"]!="frozen":output["cells"][name]=frozen;continue
        data=Dataset(dest/"rows/evaluation"/name,root=root,stage="evaluation")
        if not data.n:
            output["cells"][name]={"status":"no_available_evaluation_rows"};continue
        bundle=_load_local_pickle(dest/(name+"_selected.pkl"));predictions={}
        for family in bundle["selected"]:
            raw=_family_probabilities(bundle,data,family)
            predictions[family+"_uncalibrated"]=raw
            predictions[family+"_calibrated"]=temperature_probabilities(raw,frozen["temperatures"][family])
        prediction_path=dest/(name+"_evaluation_predictions.npz")
        np.savez_compressed(prediction_path,**predictions)
        # Predictions and their hashes are persisted before outcome scoring.
        write_json(dest/(name+"_evaluation_prediction_manifest.json"),
                   {"prediction_sha256":tennis.digest(prediction_path),"rows_sha256":data.manifest["row_sha256"],
                    "selection_freeze_sha256":tennis.digest(dest/"SELECTION_FREEZE.json"),"families":list(predictions)})
        metadata=list(data.metadata());labels=np.asarray(data.labels)
        matches=np.asarray([r["match_id"] for r in metadata]);dates=[r["date"] for r in metadata]
        tournaments=np.asarray([" ".join("".join(ch if ch.isalnum() else " " for ch in r["tournament"].casefold()).split())+"|"+r["date"][:4] for r in metadata])
        result={"status":"evaluated","common_data":data.manifest,"designated_main":bundle["main"],
                "methods":{f:performance_summary(labels,p,metadata) for f,p in predictions.items()},"contrasts":{},
                "support_slices":support_slices(labels,predictions,metadata)}
        for kind in ("calibrated","uncalibrated"):
            main=bundle["main"]+"_"+kind;reference="B1_"+kind
            difference=per_case_scores(labels,predictions[main],epsilon=EPSILON)["log_loss"]-per_case_scores(labels,predictions[reference],epsilon=EPSILON)["log_loss"]
            intervals={}
            for weighting in ("case","group"):
                intervals["match_"+weighting]=paired_cluster_interval(difference,matches,replicates=2000,confidence=.9875,seed=SEED,weighting=weighting)
                intervals["tournament_year_"+weighting]=(paired_cluster_interval(difference,tournaments,replicates=2000,confidence=.9875,seed=SEED,weighting="case")
                    if weighting=="case" else event_match_macro_interval(difference,matches,tournaments))
                intervals["four_week_"+weighting]=moving_block_interval(difference,dates,matches,weighting=weighting)
            primary=intervals["match_case"];interval=primary["interval"]
            improvement=bundle["main"]!="B1" and primary["difference"]<=-.005 and interval is not None and interval[1]<0
            result["contrasts"][kind]={"main":main,"reference":reference,"intervals":intervals,"demonstrated_improvement":bool(improvement),
                                       "claim":"demonstrated prespecified improvement" if improvement else "no demonstrated improvement",
                                       "tournament_grouping":"Normalized reused event names can conservatively combine stages"}
        output["cells"][name]=result
    write_json(report_dir/"evaluation.json",output)
    return output


def predict(root,cell,prepoint_features,history):
    """Local research probabilities from explicit pre-point inputs and past history.

    Caller supplies no target row. No player-specific trained coefficients exist.
    This does not make a causal direction/technique recommendation.
    """
    if tuple(cell) not in CELLS:raise ValueError("Unknown fixed task/corpus cell")
    freeze=verify_selection_freeze(root,calibrated=True);name=cell_name(cell)
    if freeze["cells"][name]["status"]!="frozen":raise PermissionError("Cell remains descriptive")
    bundle=_load_local_pickle(artifact_dir(root)/(name+"_selected.pkl"))
    nums,cats,baselines,audit=history.features(prepoint_features,cell[0])
    family=bundle["main"]
    if family=="B0":p=baselines[0][None,:]
    elif family=="B1":p=baselines[bundle["selected"]["B1"]+1][None,:]
    else:p=bundle["models"][family].predict_proba(bundle["preprocessor"].transform(nums[None,:],cats[None,:],family=family))
    p=temperature_probabilities(p,freeze["cells"][name]["temperatures"][family])[0]
    return {"class_order":CLASSES,"probabilities":p.tolist(),"family":family,"history_support":audit,
            "scope":"Local retrospective annotated-direction research; not causal coaching"}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("prepare","develop","evaluate"))
    parser.add_argument("--root",type=Path,default=Path("."))
    parser.add_argument("--no-probe",action="store_true")
    parser.add_argument("--as-of",default=EVALUATION_AS_OF,help="Frozen evaluation cutoff: only 20260122 is permitted")
    args=parser.parse_args(argv)
    if args.command=="prepare":result=prepare(args.root)
    elif args.command=="develop":result=develop(args.root,run_probe=not args.no_probe)
    else:
        result=evaluate(args.root,as_of=args.as_of)
    print(json.dumps({"stage":result.get("stage",args.command),"cells":list(result.get("cells",{}))},sort_keys=True))


if __name__=="__main__":main()
