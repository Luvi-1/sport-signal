"""Synthetic, offline regression tests; no Retrosheet source rows are embedded."""

import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd

from sportslab.adapters import baseball


def game(date="20240401", number="0", away="BOS", home="SEA", away_score="2", home_score="4", completion="", forfeit=""):
    row = [""] * 161
    for index, value in {0: date, 1: number, 3: away, 6: home, 9: away_score, 10: home_score, 13: completion, 14: forfeit}.items():
        row[index] = value
    return row


class BaseballAdapterTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, rows, member="GL2024.TXT", extra=None):
        text = io.StringIO(newline="")
        csv.writer(text).writerows(rows)
        path = self.root / "gl2024.zip"
        with ZipFile(path, "w") as archive:
            archive.writestr(member, text.getvalue())
            for name, value in (extra or {}).items():
                archive.writestr(name, value)
        return path

    def test_home_away_and_doubleheaders_are_distinct(self):
        self.write([game(number="2", home_score="1"), game(number="1")])
        frame = baseball.load(self.root)
        self.assertEqual(frame.event_id.tolist(), ["retrosheet:SEA202404011", "retrosheet:SEA202404012"])
        self.assertEqual(frame.side_a.tolist(), ["SEA", "SEA"])
        self.assertEqual(frame.side_b.tolist(), ["BOS", "BOS"])
        self.assertEqual(frame.score_a.tolist(), [4.0, 1.0])
        self.assertEqual(frame.score_b.tolist(), [2.0, 2.0])
        self.assertEqual(frame.season.tolist(), ["2024", "2024"])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(frame.date))
        self.assertTrue(pd.api.types.is_float_dtype(frame.score_a))
        self.assertTrue(pd.api.types.is_bool_dtype(frame.neutral))
        self.assertTrue((frame.available_date == frame.date).all())
        self.assertFalse(frame.neutral.any())

    def test_ties_invalid_scores_and_forfeits_excluded(self):
        self.write([
            game(date="20240401"),
            game(date="20240402", home_score="2"),
            game(date="20240403", home_score=""),
            game(date="20240404", home_score="nan"),
            game(date="20240405", home_score="-1"),
            game(date="20240406", home_score="2.5"),
            game(date="20240407", forfeit="T"),
            game(date="20240408", forfeit="V"),
        ])
        frame = baseball.load(self.root)
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.attrs["source_rows"], 8)
        self.assertEqual(frame.attrs["exclusions"], {"missing_or_invalid_scores": 4, "ties": 1, "forfeits_or_no_decisions": 2})

    def test_suspended_result_available_on_completion_date(self):
        self.write([game(completion="20240415,SEA03,2,1,30")])
        frame = baseball.load(self.root)
        self.assertEqual(frame.date.iloc[0], pd.Timestamp("2024-04-01"))
        self.assertEqual(frame.available_date.iloc[0], pd.Timestamp("2024-04-15"))
        self.assertEqual(frame.attrs["delayed_results"], 1)

    def test_duplicate_event_ids_rejected(self):
        self.write([game(), game()])
        with self.assertRaisesRegex(ValueError, "Duplicate Retrosheet"):
            baseball.load(self.root)

    def test_malformed_record_rejected(self):
        self.write([game()[:11]])
        with self.assertRaisesRegex(ValueError, "161 Retrosheet fields"):
            baseball.load(self.root)

    def test_invalid_or_mismatched_date_rejected(self):
        for date in ["20240230", "2024011", "20230401"]:
            with self.subTest(date=date):
                self.write([game(date=date)])
                with self.assertRaises(ValueError):
                    baseball.load(self.root)

    def test_earlier_completion_rejected(self):
        self.write([game(completion="20240301,SEA03,2,1,30")])
        with self.assertRaisesRegex(ValueError, "Completion date precedes"):
            baseball.load(self.root)

    def test_zip_path_not_extracted(self):
        self.write([game()], extra={"../unexpected.txt": "never extract", "GLWS.TXT": "postseason,ignored"})
        frame = baseball.load(self.root)
        self.assertEqual(len(frame), 1)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["gl2024.zip"])

    def test_wrong_archive_member_rejected(self):
        self.write([game()], member="GLWS.TXT")
        with self.assertRaisesRegex(ValueError, "exactly one gl2024.txt"):
            baseball.load(self.root)

    def test_no_supported_files(self):
        with self.assertRaises(FileNotFoundError):
            baseball.load(self.root)

    def test_download_requests_only_official_annual_archives(self):
        with patch("sportslab.data.fetch", side_effect=lambda url, path: path) as fetch:
            paths = baseball.download(self.root)
        self.assertEqual(len(paths), 10)
        self.assertEqual([path.name for path in paths], [f"gl{year}.zip" for year in range(2015, 2025)])
        self.assertEqual(fetch.call_count, 10)
        for year, call in zip(range(2015, 2025), fetch.call_args_list):
            self.assertEqual(call.args, (f"https://www.retrosheet.org/gamelogs/gl{year}.zip", self.root / f"gl{year}.zip"))

    def test_empty_after_filter_has_required_columns(self):
        self.write([game(home_score="2")])
        frame = baseball.load(self.root)
        self.assertTrue(frame.empty)
        self.assertEqual(list(frame.columns), baseball.COLUMNS)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(frame.available_date))


if __name__ == "__main__":
    unittest.main()
