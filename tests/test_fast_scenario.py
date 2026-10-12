import unittest
import numpy as np
import pandas as pd
from sportslab.data import validate_events
from experiments.v2.features import extended_features,FEATURES
from experiments.scenario import latest_features

class FastScenarioTests(unittest.TestCase):
    def test_matches_full_builder_with_delayed_and_same_day_results(self):
        for sport in ('soccer','baseball','football','tennis'):
            records=[]
            for i in range(35):
                date=pd.Timestamp('2020-01-01')+pd.Timedelta(days=i//2)
                records.append(dict(event_id=f'g{i:03d}',date=date,available_date=date+pd.Timedelta(days=21 if sport=='tennis' else i%3),
                    season='2020',side_a=f'T{i%5}',side_b=f'T{(i+1)%5}',score_a=float(i%2),score_b=float(1-i%2),neutral=sport=='tennis',surface='Hard' if sport=='tennis' else 'all',rank_a=i+1,rank_b=i+5))
            history=validate_events(pd.DataFrame(records),sport)
            scenario={**records[0],'event_id':'__v2_scenario__','date':pd.Timestamp('2020-02-15'),'available_date':pd.Timestamp('2020-02-15')}
            events=pd.concat([history,pd.DataFrame([scenario])],ignore_index=True)
            full=extended_features(events,sport).query("event_id=='__v2_scenario__'")
            fast=latest_features(events,sport)
            np.testing.assert_allclose(full[FEATURES].to_numpy(),fast[FEATURES].to_numpy(),rtol=0,atol=1e-12)
    def test_current_day_and_future_results_are_not_consumed(self):
        date=pd.Timestamp('2020-01-01')
        rows=[dict(event_id='future',date=date,available_date=date,season='2020',side_a='A',side_b='B',score_a=10,score_b=0,neutral=False,surface='all'),dict(event_id='__v2_scenario__',date=date,available_date=date,season='2020',side_a='A',side_b='B',score_a=1,score_b=0,neutral=False,surface='all')]
        f=latest_features(pd.DataFrame(rows),'baseball')
        self.assertEqual(f.elo_diff.iloc[0],0);self.assertEqual(f.fast_elo_diff.iloc[0],0)
if __name__=='__main__':unittest.main()
