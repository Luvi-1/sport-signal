"""Reporting preserves completed-model identity; synthetic fixtures are tests only."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from sportslab.evaluate import metrics

spec=importlib.util.spec_from_file_location('v2_report',Path(__file__).resolve().parents[1]/'scripts/summarize_v2.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ReportTests(unittest.TestCase):
    def test_refuses_incomplete_benchmark(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(module,'ROOT',Path(temp)):
            with self.assertRaisesRegex(SystemExit,'pending'):
                module.main()

    def test_complete_binary_and_multiclass_reports_render(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(module,'ROOT',Path(temp)):
            root=Path(temp)
            (root/'data/v2').mkdir(parents=True)
            (root/'data/v2/manifest.json').write_text('{}')
            (root/'artifacts/v2').mkdir(parents=True)
            (root/'artifacts/v2/SELECTION_FREEZE.json').write_text('{}')
            for sport in module.SPORTS:
                classes=3 if sport=='soccer' else 2
                y=np.tile(np.arange(classes),4);p=np.ones((len(y),classes))/classes
                m=metrics(y,p)
                selection={'features':['test_only'], 'ensemble_names':['test_model'],'ensemble_weights':[1.0],
                  'temperatures':{'ensemble':1.0},'training':{'n':len(y),'first_date':'2020-01-01','last_date':'2020-12-31'},
                  'calibration':{'n':len(y),'first_date':'2021-01-01','last_date':'2021-12-31'}}
                r={'sport':sport,'status':'completed_single_new_holdout_evaluation',
                  'test':{'n':len(y),'first_date':'2022-01-01','last_date':'2022-12-31'},
                  'classes':[str(i) for i in range(classes)],'selection_manifest_sha256':'test-only',
                  'metrics':{k:m for k in ['ensemble_calibrated','ensemble_raw','v1_recipe_refit_calibrated','elo_calibrated','training_prior']},
                  'uncertainty_vs_v1_recipe_refit':{'difference_95pct_interval':[-.01,.01],'model_minus_baseline_log_loss':0.0}}
                out=root/'reports/v2'/sport;out.mkdir(parents=True)
                (out/'evaluation.json').write_text(json.dumps(r))
                out=root/'artifacts/v2'/sport;out.mkdir(parents=True)
                (out/'selection.json').write_text(json.dumps(selection))
            module.main()
            text=(root/'reports/v2/RESULTS.md').read_text()
            self.assertIn('Prespecified ensemble',text)
            self.assertIn('remains uncertain',text)
            self.assertIn('not post-test model selection',text)
            for sport in module.SPORTS:
                self.assertIn('<svg',(root/'reports/v2'/sport/'reliability.svg').read_text())
                self.assertIn('test-only',(root/'docs/v2/model_cards'/f'{sport}.md').read_text())
if __name__=='__main__':unittest.main()
