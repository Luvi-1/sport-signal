import unittest
from pathlib import Path
import tempfile,shutil,json,hashlib
from experiments.frozen_nfl import load_snapshot,ROOT

class FrozenNFLTests(unittest.TestCase):
    def test_normalized_snapshot_reproduces_both_published_inputs(self):
        meta=json.loads((ROOT/'snapshots/nfl_regular_2010_2025.json').read_text())
        for year,n in ((2024,3891),(2025,4162)):
            data=load_snapshot(year)
            self.assertEqual(len(data),n)
            self.assertEqual(hashlib.sha256(data.to_csv(index=False).encode()).hexdigest(),meta['processed_sha256_by_end_season'][str(year)])
            self.assertFalse(any('odds' in x or 'spread' in x or 'line' in x for x in data.columns))
    def test_fresh_root_needs_no_original_raw_download(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);shutil.copytree(ROOT/'snapshots',root/'snapshots')
            self.assertEqual(len(load_snapshot(2024,root)),3891)
            self.assertFalse((root/'data').exists())
    def test_corrupted_compressed_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);shutil.copytree(ROOT/'snapshots',root/'snapshots')
            path=root/'snapshots/nfl_regular_2010_2025.csv.gz';path.write_bytes(path.read_bytes()+b'x')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):load_snapshot(2024,root)
    def test_unsupported_future_scope_rejected(self):
        with self.assertRaises(ValueError):load_snapshot(2026)
if __name__=='__main__':unittest.main()
