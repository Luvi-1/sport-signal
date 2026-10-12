import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('reproduction_check',Path(__file__).resolve().parents[1]/'scripts/check_reproduction.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ReproductionTests(unittest.TestCase):
    def fixtures(self,root):
        a,b=Path(root)/'a',Path(root)/'b'
        for path in (a,b):
            for sport in module.SPORTS:
                for relative in [f'data/processed/{sport}.csv',f'data/v2/processed/{sport}.csv',f'data/v2/pre_holdout_development/{sport}.csv',f'artifacts/{sport}/features.csv',f'artifacts/v2/{sport}/development_features.csv',f'artifacts/v2/{sport}/features.csv']:
                    dest=path/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('test fixture bytes\n')
                for prefix in ('','v2/'):
                    dest=path/f'reports/{prefix}{sport}/evaluation.json';dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_text(json.dumps({('test' if prefix=='' else 'metrics'):{'test_model':dict.fromkeys(module.METRICS,.5)}}))
                    dest=path/f'artifacts/{prefix}{sport}/holdout_predictions.csv'
                    dest.write_text('event_id,date,side_a,side_b,target,p\nfixture,2025-01-01,A,B,1,0.5\n')
        return a,b
    def test_identical_checkouts_pass_and_same_directory_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            a,b=self.fixtures(temp);self.assertEqual(module.check(a,b)['status'],'passed')
            with self.assertRaisesRegex(ValueError,'distinct'):module.check(a,a)
    def test_changed_input_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            a,b=self.fixtures(temp);(b/'data/processed/soccer.csv').write_text('changed')
            with self.assertRaisesRegex(ValueError,'Input/feature'):module.check(a,b)
    def test_nonfinite_prediction_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            a,b=self.fixtures(temp);(b/'artifacts/soccer/holdout_predictions.csv').write_text('event_id,date,side_a,side_b,target,p\nfixture,2025-01-01,A,B,1,NaN\n')
            with self.assertRaisesRegex(ValueError,'Nonfinite'):module.check(a,b)
if __name__=='__main__':unittest.main()
