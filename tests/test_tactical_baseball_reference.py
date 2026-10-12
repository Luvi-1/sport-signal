"""Offline tests for deterministic selection and frozen-membership protection."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from experiments.tactical import baseball_reference_sample as ref
from experiments.tactical.baseball import RawRecord


class BaseballReferenceSampleTest(unittest.TestCase):
    def test_hash_key_is_exact_and_zero_delivery_is_distinct(self):
        expected = hashlib.sha256(b"20261011|SYN202304010|9|3").hexdigest()
        self.assertEqual(ref.delivery_hash("SYN202304010", 9, 3), expected)
        self.assertNotEqual(ref.delivery_hash("SYN202304010", 9, 0), expected)

    def test_independent_prefix_replay_preserves_count_and_admin_rules(self):
        self.assertEqual(ref.independent_prefix_count("VACCFFX", 6), (1, 3, list("CCFF")))
        self.assertEqual(ref.independent_prefix_count("CCFFX", 4), (0, 2, list("CCFF")))
        self.assertEqual(ref.independent_prefix_count("CCLX", 3), (0, 3, list("CCL")))
        self.assertEqual(ref.independent_prefix_count("BUX", 2), (None, None, list("BU")))

    def test_membership_is_deterministic_and_cannot_be_reselected(self):
        gid = "SYN202304010"
        fake = {
            "pitches": [{"lineage": {"gid": gid, "pa": 1},
                "features": {"pa_delivered_pitch_index": 1, "pitcher": "p", "strikes": 2,
                             "balls": 0, "batter_hand": "L", "pitcher_hand": "R"},
                "target": {"symbol": "F"}, "eligibility": {"swing": True}}],
            "events": [
                {"gid": gid, "pa": 1, "raw_row": 2, "raw_sequence": "F", "parsed_pn": None},
                {"gid": gid, "pa": 2, "raw_row": 3, "raw_sequence": "VVVV", "parsed_pn": None,
                 "omitted_np": True}],
            "issues": [{"gid": gid, "pa": 1, "reason": "terminal_walk_before_ball_four"}],
        }
        source_rows = [RawRecord("SYN.EVN", 1, ("id", gid)),
            RawRecord("SYN.EVN", 2, ("play", "1", "0", "b", "02", "F", "NP")),
            RawRecord("SYN.EVN", 3, ("play", "1", "0", "b", "30", "VVVV", "IW"))]
        season = {"local_derivatives": {k: {"path": k} for k in fake}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(ref, "context", return_value=(season, {"test": "fixed"})), \
                    patch.object(ref.bb, "load_parsed", return_value=({}, {})), \
                    patch.object(ref.bb, "source_path", return_value=Path("synthetic.zip")), \
                    patch.object(ref.zipfile, "ZipFile", return_value=MagicMock()), \
                    patch.object(ref.bb, "raw_games", side_effect=lambda _: iter([(gid, source_rows)])), \
                    patch.object(ref, "rows", side_effect=lambda p: iter(deepcopy(fake[p.name]))):
                first = ref.select(root)
                second = ref.select(root)
                self.assertEqual(first, second)
                membership = json.loads((root / "data/tactical/baseball/reference_sample/membership.json").read_text())
                self.assertEqual(len(membership["entries"]), 2)
                self.assertEqual(membership["entries"][1]["pa_anchor_delivery_index"], 0)
                self.assertEqual(membership["adjudication_status"], "not_performed")
                self.assertEqual(first["mandatory_exclusion_pas"], 1)
                fake["pitches"][0]["features"]["balls"] = 1
                with self.assertRaisesRegex(ValueError, "Frozen membership differs"):
                    ref.select(root)


if __name__ == "__main__":
    unittest.main()
