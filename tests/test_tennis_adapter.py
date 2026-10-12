"""Synthetic, offline tests. No source tennis results are embedded."""

import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from sportslab.adapters import tennis
from sportslab.data import validate_events


def match(**changes):
    row = dict(tourney_id="2024-TEST", tourney_date="20240401", match_num="1",
               winner_id="20", loser_id="100", score="6-4 6-3", best_of="3",
               surface="Hard", winner_rank="7", loser_rank="50", tourney_name="Synthetic Open")
    row.update(changes)
    return row


class TennisAdapterTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, rows, year=2024):
        path = self.root / f"atp_matches_{year}.csv"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_lexicographic_ids_assign_sides_independently_of_winner(self):
        self.write([match(), match(match_num="2", winner_id="100", loser_id="20",
                                   winner_rank="50", loser_rank="7")])
        frame = validate_events(tennis.load(self.root), "tennis")
        self.assertEqual(frame.side_a.tolist(), ["100", "100"])
        self.assertEqual(frame.side_b.tolist(), ["20", "20"])
        self.assertEqual(frame.score_a.tolist(), [0.0, 1.0])
        self.assertEqual(frame.score_b.tolist(), [1.0, 0.0])
        self.assertEqual(frame.rank_a.tolist(), [50.0, 50.0])
        self.assertEqual(frame.rank_b.tolist(), [7.0, 7.0])
        self.assertEqual(frame.event_id.tolist(), ["atp:2024-TEST:1", "atp:2024-TEST:2"])
        self.assertEqual(frame.surface.tolist(), ["Hard", "Hard"])
        self.assertTrue(frame.neutral.all())
        self.assertEqual(list(frame.columns), tennis.COLUMNS)

    def test_date_proxy_and_conservative_result_availability(self):
        self.write([match(), match(match_num="2")])
        frame = tennis.load(self.root)
        self.assertTrue((frame.date == pd.Timestamp("2024-04-01")).all())
        self.assertTrue((frame.available_date == pd.Timestamp("2024-04-22")).all())
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(frame.date))
        self.assertTrue(pd.api.types.is_bool_dtype(frame.neutral))

    def test_previous_december_is_valid_tournament_start(self):
        self.write([match(tourney_date="20231230")])
        frame = tennis.load(self.root)
        self.assertEqual(frame.season.iloc[0], "2024")
        self.assertEqual(frame.date.iloc[0], pd.Timestamp("2023-12-30"))

    def test_incomplete_retirements_walkovers_and_defaults_excluded(self):
        scores = ["6-4 6-3", "6-4 6-3 RET", "W/O", "Walkover", "6-4 4-4 Def.",
                  "6-4 1-0 Default", "2-1 Played and abandoned", "2-2 ABD", "",
                  "6-4", "6-4 6-6", "6-4 7-4", "4-6 3-6", "6-4 6-3 6-1", "6-4 6-3 unknown"]
        self.write([match(match_num=str(i + 1), score=score) for i, score in enumerate(scores)])
        frame = tennis.load(self.root)
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.attrs["source_rows"], len(scores))
        self.assertEqual(frame.attrs["exclusions"], {
            "retirement_walkover_default_or_abandoned": 7,
            "incomplete_or_inconsistent_score": 7,
        })

    def test_complete_standard_extended_and_match_tiebreaks(self):
        cases = [
            ("7-6(12) 6-7(3) 6-4", "3", "Synthetic Open"),
            ("6-4 4-6 6-4 4-6 18-16", "5", "Synthetic Major"),
            ("6-4 4-6 6-4 4-6 13-12(2)", "5", "Synthetic Major"),
            ("6-4 4-6 [10-8]", "3", "Synthetic Team Cup"),
            ("6-4 4-6 [14-12]", "3", "Synthetic Team Cup"),
            ("4-3(5) 2-4 4-0 4-1", "5", "Next Gen Finals"),
            ("4-3(5) 2-4 4-0 4-1", "5", "NextGen Finals"),
        ]
        for score, best_of, tournament in cases:
            with self.subTest(score=score, tournament=tournament):
                self.assertTrue(tennis._completed_score(score, best_of, tournament))

    def test_ambiguous_or_malformed_scores_not_invented(self):
        cases = ["6-4 4-6 [1-0]", "6-4 4-6 [10-9]", "6-4 4-6 [8-10]",
                 "6-4 4-6 [12-8]", "6-4 [10-5]", "6-4(5) 6-3",
                 "6-4 6-3 1-6", "6-4 4-6 [10-7", "4-1 4-2", "6-4 6-3 0-0"]
        for score in cases:
            with self.subTest(score=score):
                self.assertFalse(tennis._completed_score(score, "3", "Synthetic Open"))
        self.assertFalse(tennis._completed_score("6-4 6-3", "unknown", "Synthetic Open"))

    def test_missing_invalid_rank_and_surface_handled_without_outcome_info(self):
        values = ["", "0", "-1", "nan", "inf", "2.5", "bad"]
        self.write([match(match_num=str(i + 1), winner_rank=value, loser_rank=value,
                          surface="", w_ace="999", l_ace="0", minutes="42")
                    for i, value in enumerate(values)])
        frame = tennis.load(self.root)
        self.assertTrue(frame.rank_a.isna().all())
        self.assertTrue(frame.rank_b.isna().all())
        self.assertTrue(frame.surface.eq("unknown").all())
        self.assertFalse(any(name.startswith(("winner", "loser", "w_", "l_")) for name in frame.columns))
        self.assertNotIn("minutes", frame)

    def test_invalid_ids_dates_and_duplicates_fail_loudly(self):
        changes = [dict(tourney_date="20240230"), dict(tourney_date="2024041"),
                   dict(tourney_date="20220401"), dict(tourney_id="2023-TEST"),
                   dict(match_num=""), dict(winner_id=""), dict(winner_id="100"),
                   dict(winner_id="2.0")]
        for change in changes:
            with self.subTest(change=change):
                self.write([match(**change)])
                with self.assertRaises(ValueError):
                    tennis.load(self.root)
        self.write([match(), match()])
        with self.assertRaisesRegex(ValueError, "Duplicate ATP event_id"):
            tennis.load(self.root)

    def test_missing_columns_rejected(self):
        row = match()
        del row["winner_rank"]
        self.write([row])
        with self.assertRaisesRegex(ValueError, "Missing ATP columns"):
            tennis.load(self.root)

    def test_malformed_csv_row_rejected(self):
        path = self.write([match()])
        with path.open("a") as stream:
            stream.write("2024-TEST,20240401\n")
        with self.assertRaisesRegex(ValueError, "Malformed ATP CSV record"):
            tennis.load(self.root)

    def test_no_supported_files(self):
        self.write([match()], year=2025)
        with self.assertRaises(FileNotFoundError):
            tennis.load(self.root)

    def test_empty_after_filter_preserves_schema_and_types(self):
        self.write([match(score="W/O")])
        frame = tennis.load(self.root)
        self.assertTrue(frame.empty)
        self.assertEqual(list(frame.columns), tennis.COLUMNS)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(frame.available_date))
        self.assertTrue(pd.api.types.is_float_dtype(frame.rank_a))

    def test_download_pins_data_and_documentation_and_records_provenance(self):
        with patch("sportslab.data.fetch", side_effect=lambda url, path: path) as fetch:
            paths = tennis.download(self.root)
        self.assertEqual(len(paths), 15)
        self.assertEqual([path.name for path in paths], [f"atp_matches_{year}.csv" for year in tennis.YEARS])
        self.assertEqual(fetch.call_count, 17)
        for call in fetch.call_args_list:
            url, path = call.args
            self.assertEqual(url, f"{tennis.SOURCE_BASE}/{path.name}")
            self.assertIn(tennis.SOURCE_COMMIT, url)


if __name__ == "__main__":
    unittest.main()
