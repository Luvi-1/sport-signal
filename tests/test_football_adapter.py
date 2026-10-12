"""Offline adapter tests use invented games, never redistributed source rows."""

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from sportslab.adapters import football


class FootballAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raw_dir = Path(self.tmp.name)

    @staticmethod
    def row(**changes):
        row = {
            "game_id": "synthetic_home_win", "season": 2024,
            "game_type": "REG", "gameday": "2024-09-08", "home_team": "AAA",
            "away_team": "BBB", "home_score": 24, "away_score": 17,
            "location": "Home", "spread_line": 99, "home_moneyline": -999,
            "away_qb_name": "Excluded fictional player", "total_line": 100,
        }
        row.update(changes)
        return row

    def write(self, *rows):
        pd.DataFrame(rows).to_csv(self.raw_dir / football.RAW_FILENAME, index=False)

    def test_filters_season_type_ties_and_unfinished(self):
        self.write(
            self.row(),
            self.row(game_id="tie", home_score=17),
            self.row(game_id="unplayed", home_score=None, away_score=None),
            self.row(game_id="partial", home_score=None),
            self.row(game_id="playoff", game_type="WC"),
            self.row(game_id="old", season=2009),
            self.row(game_id="future", season=2025),
        )
        result = football.load(self.raw_dir)
        self.assertEqual(result.event_id.tolist(), ["synthetic_home_win"])
        self.assertEqual(tuple(result.columns), football.OUTPUT_COLUMNS)
        self.assertEqual(result.side_a.iloc[0], "AAA")
        self.assertEqual(result.side_b.iloc[0], "BBB")
        self.assertEqual(result.score_a.iloc[0], 24.0)
        self.assertEqual(result.score_b.iloc[0], 17.0)
        self.assertEqual(result.season.iloc[0], "2024")
        self.assertEqual(result.score_a.dtype, "float64")
        self.assertEqual(result.neutral.dtype, "bool")
        self.assertFalse(result.neutral.iloc[0])
        pd.testing.assert_series_equal(result.date, result.available_date, check_names=False)

    def test_neutral_designation_and_franchise_continuity(self):
        self.write(
            self.row(game_id="second", home_team="STL", away_team="SD", location="Neutral"),
            self.row(game_id="first", gameday="2024-09-01", home_team="LA", away_team="OAK"),
        )
        result = football.load(self.raw_dir)
        self.assertEqual(result.event_id.tolist(), ["first", "second"])
        self.assertEqual(result.side_a.tolist(), ["LAR", "LAR"])
        self.assertEqual(result.side_b.tolist(), ["LV", "LAC"])
        self.assertEqual(result.neutral.tolist(), [False, True])

    def test_january_belongs_to_previous_season(self):
        self.write(self.row(gameday="2025-01-05", season=2024))
        result = football.load(self.raw_dir)
        self.assertEqual(result.date.iloc[0], pd.Timestamp("2025-01-05"))
        self.assertEqual(result.season.iloc[0], "2024")

    def test_duplicate_ids_raise(self):
        self.write(self.row(), self.row())
        with self.assertRaisesRegex(ValueError, "unique"):
            football.load(self.raw_dir)

    def test_unknown_location_raises(self):
        self.write(self.row(location="Unknown"))
        with self.assertRaisesRegex(ValueError, "Home or Neutral"):
            football.load(self.raw_dir)

    def test_missing_identity_raises(self):
        self.write(self.row(home_team=None))
        with self.assertRaisesRegex(ValueError, "home_team is missing"):
            football.load(self.raw_dir)

    def test_invalid_scores_raise(self):
        for score in (-1, 17.5, float("inf"), "not a score"):
            with self.subTest(score=score):
                self.write(self.row(home_score=score))
                with self.assertRaises(ValueError):
                    football.load(self.raw_dir)

    def test_invalid_date_raises(self):
        self.write(self.row(gameday="2024-99-99"))
        with self.assertRaises(ValueError):
            football.load(self.raw_dir)

    def test_missing_required_column_raises(self):
        row = self.row()
        del row["location"]
        self.write(row)
        with self.assertRaises(ValueError):
            football.load(self.raw_dir)

    def test_no_in_scope_games_returns_typed_empty_table(self):
        self.write(self.row(season=2009))
        result = football.load(self.raw_dir)
        self.assertTrue(result.empty)
        self.assertEqual(tuple(result.columns), football.OUTPUT_COLUMNS)
        self.assertEqual(result.score_a.dtype, "float64")
        self.assertEqual(result.neutral.dtype, "bool")
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result.date))


if __name__ == "__main__":
    unittest.main()
