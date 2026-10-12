import unittest
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
from sportslab.data import validate_events
from sportslab.features import build_features,FEATURES
from sportslab.evaluate import temperature_scale,metrics,fit_temperature,split_frames,bootstrap_loss

def events():
    return validate_events(pd.DataFrame([
        dict(event_id="g1",date="2020-01-01",season="2020",side_a="A",side_b="B",score_a=2,score_b=0),
        dict(event_id="g2",date="2020-01-01",season="2020",side_a="A",side_b="C",score_a=1,score_b=2),
        dict(event_id="g3",date="2020-01-05",season="2020",side_a="A",side_b="B",score_a=0,score_b=0),
        dict(event_id="g4",date="2020-01-10",season="2020",side_a="C",side_b="B",score_a=2,score_b=1),
    ]),"soccer")

class LeakageTests(unittest.TestCase):
    def test_current_and_future_results_do_not_change_past_features(self):
        data=events();before=build_features(data,"soccer")
        data.loc[2:,["score_a","score_b"]]=[99,3]
        after=build_features(data,"soccer")
        np.testing.assert_allclose(before.loc[:2,FEATURES],after.loc[:2,FEATURES])
        self.assertFalse(np.allclose(before.loc[3,FEATURES].astype(float),after.loc[3,FEATURES].astype(float)))
    def test_same_day_outcomes_are_hidden(self):
        data=events();f=build_features(data,"soccer")
        self.assertEqual(f.loc[1,"elo_diff"],0)
        self.assertEqual(f.loc[1,"cold_a"],1)
    def test_delayed_availability_hidden_until_after_completion(self):
        data=events();data.loc[0,"available_date"]=pd.Timestamp("2020-01-05")
        data.loc[1,"available_date"]=pd.Timestamp("2020-01-10")
        f=build_features(data,"soccer")
        self.assertEqual(f.loc[2,"elo_diff"],0)
        self.assertGreater(f.loc[3,"elo_diff"],0)
    def test_append_future_matches_does_not_change_features(self):
        data=events()
        np.testing.assert_allclose(build_features(data.iloc[:3],"soccer")[FEATURES],build_features(data,"soccer").iloc[:3][FEATURES])
    def test_input_order_does_not_change_output(self):
        data=events()
        pd.testing.assert_frame_equal(build_features(data,"soccer"),build_features(data.sample(frac=1,random_state=8),"soccer"))
    def test_current_postevent_extras_are_ignored(self):
        data=events();data["odds"]=999;data["winner"]=data.side_a
        pd.testing.assert_frame_equal(build_features(events(),"soccer"),build_features(data,"soccer"))
    def test_audit_availability_is_strict(self):
        data=events();f=build_features(data,"soccer")
        self.assertTrue((f.max_source_available_date.dropna()<f.loc[f.max_source_available_date.notna(),"date"]).all())
    def test_tennis_orientation_not_always_winner(self):
        data=events().iloc[:2].copy();data["neutral"]=True
        f=build_features(data,"tennis")
        self.assertEqual(f.target.tolist(),[1,0])

class ValidationTests(unittest.TestCase):
    def test_duplicate_ids_rejected(self):
        data=events();data.loc[1,"event_id"]="g1"
        with self.assertRaisesRegex(ValueError,"Duplicate"):validate_events(data,"soccer")
    def test_negative_scores_rejected(self):
        data=events();data.loc[1,"score_a"]=-1
        with self.assertRaises(ValueError):validate_events(data,"soccer")
    def test_early_availability_rejected(self):
        data=events();data.loc[1,"available_date"]=pd.Timestamp("1990-01-01")
        with self.assertRaises(ValueError):validate_events(data,"soccer")
    def test_missing_names_rejected(self):
        data=events();data.loc[1,"side_a"]=None
        with self.assertRaises(ValueError):validate_events(data,"soccer")
    def test_binary_ties_rejected(self):
        with self.assertRaises(ValueError):validate_events(events(),"football")
    def test_missing_date_rejected(self):
        data=events();data.loc[1,"date"]=pd.NaT
        with self.assertRaises(ValueError):validate_events(data,"soccer")

class EvaluationTests(unittest.TestCase):
    def test_temperature_probabilities(self):
        p=np.array([[.1,.9],[.7,.3]])
        np.testing.assert_allclose(temperature_scale(p,1),p)
        np.testing.assert_allclose(temperature_scale(p,3).sum(1),1)
    def test_binary_brier_convention(self):
        m=metrics(np.array([0,1]),np.array([[.8,.2],[.3,.7]]))
        self.assertAlmostEqual(m["brier"],(.2**2+.3**2)/2)
    def test_multiclass_brier_convention(self):
        m=metrics(np.array([1]),np.array([[.2,.5,.3]]))
        self.assertAlmostEqual(m["brier"],.38)
    def test_calibration_fit_bounded(self):
        t=fit_temperature(np.array([[.99,.01],[.99,.01],[.01,.99],[.01,.99]]),[0,1,0,1],[0,1])
        self.assertTrue(.5<=t<=5)
    def test_paired_bootstrap_same_model_zero_difference(self):
        p=np.array([[.8,.2],[.3,.7],[.9,.1]])
        dates=pd.Series(pd.to_datetime(["2020-01-01","2020-02-01","2020-03-01"]))
        m=bootstrap_loss([0,1,0],p,p,dates,reps=20)
        self.assertEqual(m["difference_95pct_interval"],[0,0])
    def test_reliability_counts_cover_data(self):
        m=metrics(np.array([0,1]),np.array([[.8,.2],[.3,.7]]))
        for cls in m["reliability"]:self.assertEqual(sum(b["n"] for b in cls["bins"]),2)

if __name__=="__main__":unittest.main()
