import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('fast_entrypoint',Path(__file__).resolve().parents[1]/'scripts/analyze_matchup.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class FastEntrypointGateTests(unittest.TestCase):
    def test_cannot_parse_future_history_before_global_freeze(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(module,'ROOT',Path(temp)),patch.object(module.pd,'read_csv') as reader:
            with self.assertRaisesRegex(ValueError,'locked'):
                module.predict('football','KC','BUF','2026-02-01')
            reader.assert_not_called()
    def test_incomplete_or_mismatched_report_cannot_unlock(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(module,'ROOT',Path(temp)),patch.object(module.pd,'read_csv') as reader:
            root=Path(temp);directory=root/'artifacts/v2';directory.mkdir(parents=True)
            selection=directory/'soccer/selection.json';selection.parent.mkdir();selection.write_text('{}')
            freeze={'selection_hashes':{'soccer':module.sha256(selection)}}
            (directory/'SELECTION_FREEZE.json').write_text(json.dumps(freeze))
            with self.assertRaisesRegex(ValueError,'locked'):
                module.predict('football','KC','BUF','2026-02-01')
            report=root/'reports/v2/soccer/evaluation.json';report.parent.mkdir(parents=True)
            report.write_text(json.dumps({'status':'completed_single_new_holdout_evaluation','selection_manifest_sha256':'wrong'}))
            with self.assertRaisesRegex(ValueError,'does not match'):
                module.predict('football','KC','BUF','2026-02-01')
            reader.assert_not_called()
if __name__=='__main__':unittest.main()
