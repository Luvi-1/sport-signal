import unittest
import numpy as np
import pandas as pd
from sportslab.data import validate_events
from experiments.v2.features import extended_features,EXTRA,FEATURES
from experiments.v2.models import DixonColes

def sample():
    return validate_events(pd.DataFrame([
        dict(event_id='x1',date='2020-01-01',available_date='2020-01-22',season='2020',side_a='A',side_b='B',score_a=1,score_b=0,neutral=True,surface='Hard',rank_a=1,rank_b=2),
        dict(event_id='x2',date='2020-01-01',available_date='2020-01-22',season='2020',side_a='A',side_b='C',score_a=0,score_b=1,neutral=True,surface='Hard',rank_a=1,rank_b=3),
        dict(event_id='x3',date='2020-02-01',available_date='2020-02-22',season='2020',side_a='A',side_b='B',score_a=1,score_b=0,neutral=True,surface='Clay',rank_a=1,rank_b=2),
    ]),'tennis')

class V2FeatureTests(unittest.TestCase):
    def test_same_bucket_history_hidden(self):
        f=extended_features(sample(),'tennis')
        self.assertEqual(f.iloc[1].fast_elo_diff,0)
        self.assertEqual(f.iloc[1].result_30d_diff,0)
    def test_current_outcome_cannot_change_features(self):
        data=sample();before=extended_features(data,'tennis')
        data.loc[2,['score_a','score_b']]=[0,1]
        after=extended_features(data,'tennis')
        np.testing.assert_allclose(before[FEATURES],after[FEATURES])
    def test_future_append_does_not_change_features(self):
        np.testing.assert_allclose(extended_features(sample().iloc[:2],'tennis')[FEATURES],extended_features(sample(),'tennis').iloc[:2][FEATURES])
    def test_batch_rating_and_time_features_invariant_to_event_id_order(self):
        data=sample();before=extended_features(data,'tennis').iloc[-1]
        data.loc[:1,'event_id']=['z2','z1']
        after=extended_features(data,'tennis').iloc[-1]
        np.testing.assert_allclose(before[EXTRA].astype(float),after[EXTRA].astype(float))
    def test_poisson_probabilities_valid_on_new_team(self):
        data=sample();data['date']=pd.to_datetime(data.date);data['target']=[2,0,2]
        model=DixonColes().fit(data)
        future=data.iloc[:1].copy();future['side_a']='NEW'
        p=model.predict_proba(future)
        self.assertEqual(p.shape,(1,3));self.assertTrue((p>0).all());self.assertAlmostEqual(p.sum(),1)

if __name__=='__main__':unittest.main()
