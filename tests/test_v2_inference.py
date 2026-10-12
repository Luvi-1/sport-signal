import tempfile,json,hashlib
import unittest
from pathlib import Path
from unittest.mock import patch
import joblib
import numpy as np
import pandas as pd
from experiments.v2 import predict as module

class FixedV2TestModel:
    def predict_proba(self,frame):return np.tile([.2,.8],(len(frame),1))

class V2InferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        directory=self.root/'artifacts/v2/tennis';directory.mkdir(parents=True)
        (self.root/'data/v2/processed').mkdir(parents=True)
        joblib.dump({'models':{'fixed':FixedV2TestModel()},'ensemble_names':['fixed'],'ensemble_weights':np.array([1.]),'temperatures':{'fixed':1.,'ensemble':1.}},directory/'models.joblib')
        (directory/'selection.json').write_text(json.dumps({'code_sha256':'test-only','models_sha256':hashlib.sha256((directory/'models.joblib').read_bytes()).hexdigest(),'splits':{'calibration_end':'2025-01-01'}}))
        pd.DataFrame([dict(event_id='synthetic',date='2024-01-01',available_date='2024-01-22',season='2024',side_a='10',side_b='20',score_a=1,score_b=0,neutral=True,surface='Hard',rank_a=10,rank_b=20)]).to_csv(self.root/'data/v2/processed/tennis.csv',index=False)
        self.root_patch=patch.object(module,'ROOT',self.root);self.root_patch.start()
        self.hash_patch=patch.object(module,'code_hash',return_value='test-only');self.hash_patch.start()
    def tearDown(self):self.hash_patch.stop();self.root_patch.stop();self.temp.cleanup()
    def test_reverse_orientation_and_disagreement_label(self):
        a=module.predict('tennis','10','20','2025-03-01','Hard')
        b=module.predict('tennis','20','10','2025-03-01','Hard')
        self.assertAlmostEqual(a['probabilities']['side_a_win'],b['probabilities']['side_b_win'])
        self.assertIn('not a statistical confidence interval',a['range_note'])
        self.assertEqual(b['side_a'],'20')
    def test_invalid_surface_and_calibration_date(self):
        with self.assertRaises(ValueError):module.predict('tennis','10','20','2025-03-01','Hrad')
        with self.assertRaisesRegex(ValueError,'calibration'):module.predict('tennis','10','20','2024-03-01','Hard')
    def test_model_hash_mismatch_rejected_before_load(self):
        path=self.root/'artifacts/v2/tennis/models.joblib';path.write_bytes(path.read_bytes()+b'x')
        with self.assertRaisesRegex(ValueError,'identity differs'):module.predict('tennis','10','20','2025-03-01','Hard')
if __name__=='__main__':unittest.main()
