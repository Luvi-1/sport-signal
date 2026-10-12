"""Efficient single-scenario features, equivalent to the full historical builder.

Updates rating/history state once, then computes just the requested row; it never
builds tens of thousands of unused historical feature rows at inference time.
"""
import pandas as pd
from sportslab.features import FeatureState
from experiments.v2.features import State

def latest_features(events,sport):
    scenario=events.loc[events.event_id.eq('__v2_scenario__')]
    if len(scenario)!=1:raise ValueError('Exactly one scenario row required')
    row=next(scenario.itertuples(index=False))
    prior=events.loc[events.event_id.ne('__v2_scenario__') & (events.available_date<row.date)]
    prior=prior.sort_values(['available_date','date','event_id'],kind='stable')
    base,extended=FeatureState(sport),State(sport)
    for _,group in prior.groupby('available_date',sort=True):
        rows=list(group.itertuples(index=False))
        for old in rows:base.update(old)
        extended.batch(rows)
    values=base.features(row)
    values.update(extended.features(row))
    values.update(date=row.date,available_date=row.available_date,side_a=row.side_a,side_b=row.side_b,
                  max_source_available_date=base.last_available)
    return pd.DataFrame([values])
