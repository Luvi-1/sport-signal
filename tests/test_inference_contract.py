"""Inference API validation with a clearly artificial fixed classifier."""
import tempfile
import unittest
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sportslab.cli import predict
from sportslab.features import FEATURES

class FixedTestModel:
    def predict_proba(self,frame):
        return np.tile([.25,.75],(len(frame),1))

class InferenceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/"artifacts"/"tennis").mkdir(parents=True)
        (self.root/"data"/"processed").mkdir(parents=True)
        joblib.dump({"model":FixedTestModel(),"temperature":1,"sport":"tennis","features":FEATURES,
            "classes":["side_b_win","side_a_win"],"calibration_cutoff":"2023-01-01","artifact_id":"synthetic-test-only"},
            self.root/"artifacts"/"tennis"/"model.joblib")
        pd.DataFrame([dict(event_id="synthetic_1",date="2023-01-01",available_date="2023-01-22",season="2023",
            side_a="10",side_b="20",score_a=1,score_b=0,neutral=True,surface="Hard",rank_a=10,rank_b=20)]).to_csv(
            self.root/"data"/"processed"/"tennis.csv",index=False)
    def tearDown(self):self.temp.cleanup()
    def test_typo_surface_rejected(self):
        with self.assertRaisesRegex(ValueError,"surface"):
            predict(self.root,"tennis","10","20","2023-03-01",surface="Hrad")
    def test_canonical_player_order_maps_probabilities_back(self):
        a=predict(self.root,"tennis","10","20","2023-03-01","Hard",rank_a=10,rank_b=20)
        b=predict(self.root,"tennis","20","10","2023-03-01","Hard",rank_a=20,rank_b=10)
        self.assertEqual(a["probabilities"]["side_a_win"],b["probabilities"]["side_b_win"])
        self.assertEqual(b["side_a"],"20")
        self.assertEqual(a["historical_input_snapshot"]["prior_elo_a_minus_b"],-b["historical_input_snapshot"]["prior_elo_a_minus_b"])
    def test_invalid_rank_rejected(self):
        for rank in (0,-1,float("inf")):
            with self.assertRaisesRegex(ValueError,"rankings"):
                predict(self.root,"tennis","10","20","2023-03-01","Hard",rank_a=rank)
    def test_non_iso_and_timezone_dates_rejected(self):
        for date in ("03/01/2023","2023-03-01T00:00:00Z"):
            with self.assertRaisesRegex(ValueError,"YYYY-MM-DD"):
                predict(self.root,"tennis","10","20",date,"Hard")
    def test_stale_snapshot_warning(self):
        p=predict(self.root,"tennis","10","20","2025-03-01","Hard")
        self.assertTrue(any("stale" in w for w in p["warnings"]))
    def test_unknown_ids_require_opt_in(self):
        with self.assertRaisesRegex(ValueError,"Unknown participant"):
            predict(self.root,"tennis","99","20","2023-03-01","Hard")
        p=predict(self.root,"tennis","99","20","2023-03-01","Hard",allow_cold=True)
        self.assertTrue(any("Cold-start" in w for w in p["warnings"]))
    def test_missing_rank_warning(self):
        p=predict(self.root,"tennis","10","20","2023-03-01","Hard")
        self.assertTrue(any("ranking" in w for w in p["warnings"]))

if __name__=="__main__":unittest.main()
