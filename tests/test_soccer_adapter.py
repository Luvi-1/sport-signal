"""Offline synthetic contract and data-quality tests for the soccer adapter."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from sportslab.adapters import soccer


class SoccerAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raw = Path(self.temp.name)

    def write(self, matches, season="2024-25"):
        (self.raw / f"en.1-{season}.json").write_text(
            json.dumps({"name": "Synthetic fixtures only", "matches": matches}), encoding="utf-8"
        )

    @staticmethod
    def match(**updates):
        match = {
            "date": "2024-08-16", "round": "Matchday 1", "team1": "Example United FC",
            "team2": "Example City FC", "score": {"ht": [0, 0], "ft": [2, 1]},
        }
        match.update(updates)
        return match

    def test_contract_and_home_away_order(self):
        self.write([self.match()])
        frame = soccer.load(self.raw)
        self.assertEqual(list(frame), soccer.COLUMNS)
        row = frame.iloc[0]
        self.assertEqual((row.side_a, row.side_b), ("Example United", "Example City"))
        self.assertEqual((row.score_a, row.score_b), (2.0, 1.0))
        self.assertEqual(str(frame.score_a.dtype), "float64")
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(frame.date))
        self.assertEqual(row.date, pd.Timestamp("2024-08-16"))
        self.assertEqual(row.available_date, row.date)
        self.assertFalse(row.neutral)
        self.assertEqual(frame.attrs["license"], "CC0-1.0")

    def test_skips_unplayed_partial_and_halftime_only(self):
        self.write([
            self.match(), self.match(score=None), self.match(score={"ht": [1, 0]}),
            self.match(score={"ft": [None, 1]}), self.match(score={"ft": None}),
        ])
        frame = soccer.load(self.raw)
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.attrs["skipped_incomplete_matches"], 4)

    def test_invalid_scores_fail_without_imputation(self):
        for score in ([True, 1], [-1, 1], [1.5, 0], ["2", 1], [1], [float("nan"), 1]):
            with self.subTest(score=score):
                self.write([self.match(score={"ft": score})])
                with self.assertRaisesRegex(ValueError, "score"):
                    soccer.load(self.raw)

    def test_july_2020_correction_is_narrow_and_auditable(self):
        self.write([self.match(date="2019-07-26", round="Matchday 38")], "2019-20")
        frame = soccer.load(self.raw)
        self.assertEqual(frame.iloc[0].date, pd.Timestamp("2020-07-26"))
        self.assertEqual(frame.attrs["corrected_july_2020_dates"], 1)
        # Raw data is retained verbatim; only the normalized output is corrected.
        self.assertIn("2019-07-26", (self.raw / "en.1-2019-20.json").read_text())
        self.write([self.match(date="2019-07-26", round="Matchday 1")], "2019-20")
        with self.assertRaisesRegex(ValueError, "outside"):
            soccer.load(self.raw)

    def test_other_seasons_are_not_year_shifted(self):
        self.write([self.match(date="2024-07-26", round="Matchday 38")])
        with self.assertRaisesRegex(ValueError, "outside"):
            soccer.load(self.raw)

    def test_ids_ignore_result_date_and_fc_suffix_changes(self):
        self.write([self.match()])
        first_id = soccer.load(self.raw).iloc[0].event_id
        self.write([self.match(
            date="2024-08-17", team1="Example United", team2="Example City", score={"ft": [0, 0]}
        )])
        self.assertEqual(first_id, soccer.load(self.raw).iloc[0].event_id)

    def test_reversed_home_away_fixture_has_distinct_id_and_date_sort(self):
        self.write([
            self.match(date="2025-02-01", team1="Example City FC", team2="Example United FC"),
            self.match(),
        ])
        frame = soccer.load(self.raw)
        self.assertEqual(frame.event_id.nunique(), 2)
        self.assertTrue(frame.date.is_monotonic_increasing)
        self.assertEqual(frame.iloc[0].side_a, "Example United")

    def test_duplicates_raise_even_with_score_or_date_change(self):
        self.write([self.match(), self.match(date="2024-08-17")])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            soccer.load(self.raw)

    def test_afc_name_preserved(self):
        self.write([self.match(team1="AFC Example", team2="Another Club AFC")])
        row = soccer.load(self.raw).iloc[0]
        self.assertEqual((row.side_a, row.side_b), ("AFC Example", "Another Club AFC"))

    def test_missing_files_fail_clearly(self):
        with self.assertRaises(FileNotFoundError):
            soccer.load(self.raw)

    def test_malformed_schema_names_dates_and_self_match_fail(self):
        for update in ({"team1": ""}, {"date": "not-a-date"}, {"team2": "Example United"}):
            with self.subTest(update=update):
                self.write([self.match(**update)])
                with self.assertRaises(ValueError):
                    soccer.load(self.raw)
        (self.raw / "en.1-2024-25.json").write_text('{"rounds": []}')
        with self.assertRaisesRegex(ValueError, "matches list"):
            soccer.load(self.raw)

    def test_no_complete_results_fails_clearly(self):
        self.write([self.match(score=None)])
        with self.assertRaisesRegex(ValueError, "No completed"):
            soccer.load(self.raw)

    def test_download_uses_immutable_urls_and_shared_provenance_fetcher(self):
        with patch("sportslab.data.fetch", side_effect=lambda url, path: path) as fetch:
            paths = soccer.download(self.raw)
        self.assertEqual(len(paths), 13)
        self.assertEqual(len([path for path in paths if path.suffix == ".json"]), 10)
        self.assertEqual(fetch.call_count, 13)
        for call in fetch.call_args_list:
            url, path = call.args
            self.assertIn("https://raw.githubusercontent.com/openfootball/", url)
            self.assertTrue(soccer.SOURCE_COMMIT in url or soccer.TEXT_SOURCE_COMMIT in url)
            self.assertEqual(path.parent, self.raw)

    def test_valid_2019_season_dates_remain_unchanged(self):
        self.write([
            self.match(date="2019-08-09"),
            self.match(date="2020-07-26", round="Matchday 38", team1="Third Example FC"),
        ], "2019-20")
        frame = soccer.load(self.raw)
        self.assertEqual(frame.attrs["corrected_july_2020_dates"], 0)
        self.assertEqual(frame.date.tolist(), [pd.Timestamp("2019-08-09"), pd.Timestamp("2020-07-26")])


if __name__ == "__main__":
    unittest.main()
