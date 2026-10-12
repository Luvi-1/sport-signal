"""Additional strictly pre-event features; state changes only on observed results."""
from collections import defaultdict
import math
import numpy as np
import pandas as pd
from sportslab.features import build_features, FEATURES as V1_FEATURES

EXTRA = ["fast_elo_diff","slow_elo_diff","batch_surface_elo_diff","rank_inverse_diff","rank_best_log","rank_worst_log",
         "season_form_diff","season_games_diff","role_form_diff","opponent_strength_diff","surface_form_diff","surface_games_diff"]
for half in (30,90,365):
    EXTRA += [f"result_{half}d_diff",f"margin_{half}d_diff",f"scored_{half}d_a",f"scored_{half}d_b",f"conceded_{half}d_a",f"conceded_{half}d_b"]
EXTRA += ["surface_hard","surface_clay","surface_grass","surface_carpet","absence_log_a","absence_log_b"]
FEATURES = list(V1_FEATURES)+EXTRA
RATING_FEATURES=["fast_elo_diff","slow_elo_diff","batch_surface_elo_diff","log_rank_diff","rank_missing_a","rank_missing_b","neutral"]

class State:
    def __init__(self,sport):
        self.sport=sport
        self.ratings={k:defaultdict(lambda:1500.) for k in (10,40)}
        self.surface=defaultdict(lambda:1500.)
        self.history=defaultdict(list)
    def batch(self,rows):
        changes={k:defaultdict(float) for k in self.ratings}
        surface_changes=defaultdict(float)
        for r in rows:
            win=float(r.score_a>r.score_b)+.5*float(r.score_a==r.score_b)
            home=0 if r.neutral or self.sport=='tennis' else 55
            for k,ratings in self.ratings.items():
                expected=1/(1+10**((ratings[r.side_b]-ratings[r.side_a]-home)/400))
                delta=k*(win-expected)
                changes[k][r.side_a]+=delta;changes[k][r.side_b]-=delta
            ka,kb=(r.side_a,r.surface),(r.side_b,r.surface)
            expected=1/(1+10**((self.surface[kb]-self.surface[ka]-home)/400))
            surface_changes[ka]+=20*(win-expected);surface_changes[kb]-=20*(win-expected)
            # Each tuple is available only after its recorded completion date;
            # calendar weighting does not assume an order among equal-date matches.
            for player,opponent,value,score,against,role in ((r.side_a,r.side_b,win,r.score_a,r.score_b,1),(r.side_b,r.side_a,1-win,r.score_b,r.score_a,0)):
                self.history[player].append((r.date,value,float(score),float(against),str(r.season),r.surface,role,self.ratings[10][opponent]))
        for k,deltas in changes.items():
            for player,delta in deltas.items():self.ratings[k][player]+=delta
        for key,delta in surface_changes.items():self.surface[key]+=delta
    def summarize(self,player,date,season,surface,role):
        hist=self.history[player]
        output={}
        if not hist:
            score_prior={'soccer':1.35,'baseball':4.4,'football':22.,'tennis':.5}[self.sport]
            for half in (30,90,365):
                output[f'result{half}']=.5;output[f'margin{half}']=0;output[f'scored{half}']=score_prior;output[f'conceded{half}']=score_prior
            output.update(season_form=.5,season_games=0,role_form=.5,opponent=1500,surface_form=.5,surface_games=0)
            return output
        days=np.array([(date-r[0]).days for r in hist],float)
        numeric=np.array([[r[1],r[2]-r[3],r[2],r[3]] for r in hist],float)
        for half in (30,90,365):
            w=np.exp2(-np.maximum(days,0)/half)
            # Avoid zero denominators after a very long absence.
            if w.sum()<1e-12:w=np.ones(len(w))
            means=np.average(numeric,axis=0,weights=w)
            for key,value in zip(('result','margin','scored','conceded'),means):output[f'{key}{half}']=float(value)
        season_values=[r[1] for r in hist if r[4]==str(season)]
        role_values=[r[1] for r in hist if (r[6]==role or self.sport=='tennis') and (date-r[0]).days<=365]
        surf_values=[r[1] for r in hist if r[5]==surface and (date-r[0]).days<=730]
        shrink=lambda values:(sum(values)+2.5)/(len(values)+5)
        output.update(season_form=shrink(season_values),season_games=len(season_values),role_form=shrink(role_values),
            opponent=float(np.average([r[7] for r in hist],weights=np.exp2(-np.maximum(days,0)/365))),
            surface_form=shrink(surf_values),surface_games=len(surf_values))
        return output
    def features(self,r):
        a=self.summarize(r.side_a,r.date,r.season,r.surface,1)
        b=self.summarize(r.side_b,r.date,r.season,r.surface,0)
        ra,rb=getattr(r,'rank_a',np.nan),getattr(r,'rank_b',np.nan)
        ra=ra if np.isfinite(ra) and ra>0 else 1000
        rb=rb if np.isfinite(rb) and rb>0 else 1000
        out={"event_id":r.event_id,"fast_elo_diff":(self.ratings[40][r.side_a]-self.ratings[40][r.side_b])/400,
             "slow_elo_diff":(self.ratings[10][r.side_a]-self.ratings[10][r.side_b])/400,
             "batch_surface_elo_diff":(self.surface[(r.side_a,r.surface)]-self.surface[(r.side_b,r.surface)])/400,
             "rank_inverse_diff":1/ra-1/rb,"rank_best_log":math.log(min(ra,rb)),"rank_worst_log":math.log(max(ra,rb)),
             "season_form_diff":a['season_form']-b['season_form'],"season_games_diff":math.log1p(a['season_games'])-math.log1p(b['season_games']),
             "role_form_diff":a['role_form']-b['role_form'],"opponent_strength_diff":(a['opponent']-b['opponent'])/400,
             "surface_form_diff":a['surface_form']-b['surface_form'],"surface_games_diff":math.log1p(a['surface_games'])-math.log1p(b['surface_games'])}
        for half in (30,90,365):
            out[f'result_{half}d_diff']=a[f'result{half}']-b[f'result{half}']
            out[f'margin_{half}d_diff']=a[f'margin{half}']-b[f'margin{half}']
            for stat in ('scored','conceded'):
                out[f'{stat}_{half}d_a']=a[f'{stat}{half}'];out[f'{stat}_{half}d_b']=b[f'{stat}{half}']
        for surface in ('hard','clay','grass','carpet'):out[f'surface_{surface}']=float(r.surface.lower()==surface)
        for side,player in (('a',r.side_a),('b',r.side_b)):
            hist=self.history[player]
            days=(r.date-max(x[0] for x in hist)).days if hist else 1095
            out[f'absence_log_{side}']=math.log1p(min(max(days,0),1095))
        return out

def extended_features(events,sport):
    """Append extensions to frozen V1 feature definitions without changing V1."""
    base=build_features(events,sport)
    state=State(sport)
    complete=events.sort_values(['available_date','date','event_id'],kind='stable')
    groups=list(complete.groupby('available_date',sort=True))
    group_index=0;records=[]
    for date,current in events.sort_values(['date','event_id'],kind='stable').groupby('date',sort=True):
        while group_index<len(groups) and groups[group_index][0]<date:
            state.batch(list(groups[group_index][1].itertuples(index=False)))
            group_index+=1
        records.extend(state.features(row) for row in current.itertuples(index=False))
    result=base.merge(pd.DataFrame(records),on='event_id',validate='one_to_one')
    if not np.isfinite(result[FEATURES].values).all():raise ValueError('Nonfinite extended feature')
    return result
