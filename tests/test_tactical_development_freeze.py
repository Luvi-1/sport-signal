"""Invented operation files only; no source reads or estimator fitting."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.tactical import _soccer_football_common as common
from experiments.tactical import football_model, soccer_model

class DevelopmentFreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.out=Path(self.tmp.name)
        (self.out/'operations').mkdir()
        self.plan=['candidate','refit','calibrate_model'];attempts=[]
        for name in self.plan[:2]:
            path=self.out/'operations'/f'{name}.joblib';path.write_bytes(b'invented non-pickle artifact')
            attempts.append({'id':name,'status':'complete','artifact':path.name,'sha256':common.sha256_file(path)})
        common.write_json(self.out/'operations/operations.json',{'planned_ids':self.plan,'attempts':attempts})
        common.write_json(self.out/'selection.json',{'chosen':'fixed'})
        common.write_json(self.out/'development_candidates.json',[{'candidate':'fixed'}])
        (self.out/'developed.joblib').write_bytes(b'invented model bytes')
        common.write_json(self.out/'development_manifest.json',{'artifact':'developed.joblib',
            'sha256':common.sha256_file(self.out/'developed.joblib'),'prepared_sha256':'prepared',
            'selection_sha256':common.sha256_file(self.out/'selection.json')})
    def tearDown(self):self.tmp.cleanup()
    def test_complete_freeze_is_repeatable_and_verifies_exact_links(self):
        a=common.freeze_development(self.out,'prepared',self.plan)
        self.assertEqual(a,common.freeze_development(self.out,'prepared',self.plan))
        self.assertEqual(common.verify_development(self.out,'prepared',self.plan)['prepared_sha256'],'prepared')
        with self.assertRaises(PermissionError):common.verify_development(self.out,'wrong',self.plan)
    def test_changed_selection_candidate_or_operation_is_rejected(self):
        common.freeze_development(self.out,'prepared',self.plan)
        for relative in ('selection.json','development_candidates.json','operations/candidate.joblib'):
            path=self.out/relative;original=path.read_bytes();path.write_bytes(b'changed')
            with self.assertRaises(PermissionError):common.verify_development(self.out,'prepared',self.plan)
            path.write_bytes(original)
    def test_incomplete_grid_cannot_freeze(self):
        path=self.out/'operations/operations.json';ops=json.loads(path.read_text());ops['attempts'].pop()
        common.write_json(path,ops)
        with self.assertRaises(ValueError):common.freeze_development(self.out,'prepared',self.plan)
    def test_calibration_checks_freeze_before_any_label_read(self):
        for model,prepared in ((football_model,(self.out,{},{})),(soccer_model,(self.out,{},[]))):
            with patch.object(model,'_guard'),patch.object(model,'_prepared',return_value=prepared), \
                 patch.object(common,'verify_development',side_effect=PermissionError('unreviewed mixed artifacts')), \
                 patch.object(model,'_labels') as labels:
                with self.assertRaises(PermissionError):model.calibrate(self.out)
                labels.assert_not_called()
    def test_existing_commitment_cannot_be_overwritten(self):
        path=self.out/'commitment.json';common.write_once_json(path,{'selected':1})
        with self.assertRaises(PermissionError):common.write_once_json(path,{'selected':2})
        self.assertEqual(json.loads(path.read_text()),{'selected':1})

if __name__=='__main__':unittest.main()
