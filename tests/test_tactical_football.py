"""Invented fixtures exercise the descriptive NFL contract; no real rows are distributed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from experiments.tactical import football as f


def fixtures(season=2023, n=4):
    pbp, part, ftn = [], [], []
    for i in range(n):
        game = f"{season}_01_AAA_BBB"
        pbp.append(dict(game_id=game, play_id=i + 1, season=season, season_type="REG", week=1,
                        posteam="AAA", defteam="BBB", game_date=f"{season}-09-10", down=1 + i % 4,
                        ydstogo=10, yardline_100=65, qtr=1, quarter_seconds_remaining=800,
                        half_seconds_remaining=1700, game_seconds_remaining=3500, score_differential=0,
                        posteam_timeouts_remaining=3, defteam_timeouts_remaining=3, no_huddle=0,
                        posteam_type="away", play_type="run" if i in [0, 3] else "pass", qb_kneel=0,
                        qb_spike=0, play_deleted=0, qb_dropback=0 if i in [0, 3] else 1,
                        sack=int(i == 2), qb_scramble=int(i == 3),
                        epa=90, passer_player_id="future", receiver_player_id="future", yards_gained=40))
        part.append(dict(nflverse_game_id=game, play_id=i + 1, offense_formation="SHOTGUN",
                         offense_personnel="1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR",
                         defense_personnel="3 CB, 2 DE, 2 DT, 1 FS, 1 MLB, 1 OLB, 1 SS",
                         defenders_in_box=6, was_pressure=bool(i), number_of_pass_rushers=i,
                         defense_man_zone_type="leaking", defense_coverage_type="later", time_to_throw=i))
        ftn.append(dict(nflverse_game_id=game, nflverse_play_id=i + 1, qb_location="S", starting_hash="L",
                        n_offense_backfield=1, n_defense_box=6, is_motion=bool(i % 2),
                        n_pass_rushers=i, n_blitzers=i, is_rpo=True, read_thrown=i))
    return pd.DataFrame(pbp), pd.DataFrame(part), pd.DataFrame(ftn)


class FootballContractTests(unittest.TestCase):
    def test_cohort_and_realized_dropbacks_include_scrambles_and_sacks(self):
        p, part, chart = fixtures()
        panel = f.build_panel(p, part, chart, 2023)
        self.assertEqual(panel.target.tolist(), [0, 1, 1, 1])
        self.assertEqual(panel.qa["development_target_definition_checks"]["qb_dropback_flag_disagreements_with_union"], 1)
        self.assertEqual(panel.qa["joins"]["ftn"]["matched"], 4)
        self.assertEqual(tuple(panel.features.columns), f.FEATURE_COLUMNS)
        self.assertTrue(set(f.FORBIDDEN_EXAMPLES).isdisjoint(panel.features))
        self.assertTrue(set(f.PBP_TARGETS).isdisjoint(panel.features))

    def test_all_exclusions_partition_rows_and_missing_flags_fail_closed(self):
        p, part, chart = fixtures(n=10)
        p.loc[0, "season_type"] = "POST"
        p.loc[1, "play_deleted"] = 1
        p.loc[2, "play_type"] = "no_play"
        p.loc[3, "down"] = 5
        p.loc[4, "qb_kneel"] = 1
        p.loc[5, "qb_spike"] = 1
        p.loc[6, "qb_kneel"] = None
        p.loc[7, "play_deleted"] = None
        panel = f.build_panel(p, part, chart, 2023)
        self.assertEqual(panel.metadata.play_id.tolist(), [9, 10])
        self.assertTrue(panel.qa["cohort"]["exclusions_partition_input"])
        self.assertEqual(sum(panel.qa["cohort"]["sequential_exclusions"].values()), 8)

    def test_duplicate_keys_rejected_even_outside_eligible_population(self):
        for which in range(3):
            data = list(fixtures())
            data[which] = pd.concat([data[which], data[which].iloc[:1]], ignore_index=True)
            with self.subTest(source=which), self.assertRaisesRegex(ValueError, "duplicate"):
                f.build_panel(*data, 2023)

    def test_null_fractional_and_cross_season_keys_rejected(self):
        for value in [None, 1.5, -1]:
            p, part, chart = fixtures()
            chart["nflverse_play_id"] = chart.nflverse_play_id.astype(object)
            chart.loc[0, "nflverse_play_id"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "join keys"):
                f.build_panel(p, part, chart, 2023)
        p, part, chart = fixtures()
        part.loc[0, "nflverse_game_id"] = "2025_01_AAA_BBB"
        with self.assertRaisesRegex(ValueError, "season"):
            f.build_panel(p, part, chart, 2023)

    def test_unmatched_rows_retained_with_null_features_and_support_audit(self):
        p, part, chart = fixtures()
        panel = f.build_panel(p, part.iloc[1:], chart.iloc[2:], 2023)
        self.assertEqual(len(panel.features), 4)
        self.assertTrue(pd.isna(panel.features.loc[0, "offense_rb"]))
        self.assertTrue(pd.isna(panel.features.loc[0, "formation"]))
        self.assertEqual(panel.qa["joins"]["participation"]["unmatched"], 1)
        self.assertEqual(panel.qa["joins"]["ftn"]["unmatched"], 2)
        self.assertTrue(panel.qa["joins"]["ftn"]["unmatched_by_team_and_play_category"])

    def test_sentinels_whitespace_ranges_and_source_choice(self):
        p, part, chart = fixtures()
        chart = chart.astype({"is_motion": object, "n_defense_box": float, "n_offense_backfield": float})
        chart.loc[0, ["qb_location", "starting_hash", "n_defense_box", "n_offense_backfield"]] = ["0", "0", 0, 0]
        chart.loc[1, ["qb_location", "starting_hash", "is_motion"]] = [" S ", " r ", "false"]
        chart.loc[2, ["n_defense_box", "n_offense_backfield"]] = [12, -1]
        chart.loc[3, ["n_defense_box", "n_offense_backfield"]] = [6.5, 1.5]
        part["offense_formation"] = "UNDER CENTER"
        p.loc[0, "score_differential"] = 900
        panel = f.build_panel(p, part, chart, 2023)
        self.assertTrue(pd.isna(panel.features.loc[0, "formation"]))
        self.assertTrue(pd.isna(panel.features.loc[0, "starting_hash"]))
        self.assertTrue(pd.isna(panel.features.loc[0, "defenders_in_box"]))
        self.assertEqual(panel.features.loc[0, "offense_backfield"], 0)
        self.assertEqual(panel.features.loc[1, "formation"], "SHOTGUN")
        self.assertEqual(panel.features.loc[1, "starting_hash"], "right")
        self.assertEqual(panel.features.loc[1, "motion"], 0)
        self.assertTrue(panel.features.loc[[2, 3], ["defenders_in_box", "offense_backfield"]].isna().all().all())
        self.assertTrue(pd.isna(panel.features.loc[0, "score_differential"]))

    def test_legacy_formation_categories_are_not_fabricated_alignments(self):
        self.assertEqual(f.normalize_formation(" I_FORM ", 2022), "I_FORM")
        self.assertEqual(f.normalize_formation("EMPTY", 2022), "EMPTY")
        self.assertIsNone(f.normalize_formation("EMPTY", 2023))
        self.assertEqual(f.normalize_formation("under center", 2023), "UNDER_CENTER")
        self.assertIsNone(f.normalize_formation("0", 2023))

    def test_personnel_normalization_preserves_era_limits_and_fullback(self):
        legacy = f.normalize_personnel("1 RB, 1 TE, 3 WR", "offense", 2022)
        self.assertTrue(legacy["valid"])
        self.assertEqual([legacy[c] for c in ["offense_rb", "offense_te", "offense_wr"]], [1, 1, 3])
        self.assertIsNone(legacy["offense_ol"])
        self.assertIsNone(legacy["offense_qb"])
        modern = f.normalize_personnel("1 C, 1 FB, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 2 WR", "offense", 2023)
        self.assertEqual(modern["offense_rb"], 2)
        self.assertEqual(modern["offense_ol"], 5)
        defense = f.normalize_personnel("3 CB, 2 DE, 2 DT, 1 FS, 1 MLB, 1 OLB, 1 SS", "defense", 2023)
        self.assertEqual([defense[c] for c in ["defense_dl", "defense_lb", "defense_db"]], [4, 2, 5])

    def test_unknown_malformed_and_non11_personnel_quarantined(self):
        for raw in ["1 GARBAGE", "1 RB, 1 RB", "1 RB junk", "99 WR", "0", None, "1 RB, 1 TE, 3 WR"]:
            with self.subTest(raw=raw):
                result = f.normalize_personnel(raw, "offense", 2023)
                self.assertFalse(result["valid"])
                self.assertIsNone(result["offense_rb"])
        self.assertFalse(f.normalize_personnel("1 QB, 5 OL, 1 RB, 2 TE, 3 WR", "offense", 2023)["valid"])

    def test_current_outcomes_and_missingness_cannot_change_features(self):
        p, part, chart = fixtures()
        before = f.build_panel(p, part, chart, 2023)
        p["epa"] = -1000
        p["receiver_player_id"] = None
        p["passer_player_id"] = None
        p["yards_gained"] = -99
        p["score_differential_post"] = 999
        p["qb_dropback"] = 1 - p.qb_dropback
        p["sack"] = 1 - p.sack
        p["qb_scramble"] = 1 - p.qb_scramble
        for col in ["was_pressure", "number_of_pass_rushers", "defense_man_zone_type", "defense_coverage_type", "time_to_throw"]:
            part[col] = None
        for col in ["n_pass_rushers", "n_blitzers", "is_rpo", "read_thrown"]:
            chart[col] = None
        after = f.build_panel(p, part, chart, 2023)
        pd.testing.assert_frame_equal(before.features, after.features)
        pd.testing.assert_frame_equal(before.raw_presnap, after.raw_presnap)
        self.assertFalse(before.target.equals(after.target))

    def test_future_appending_and_permuting_supplemental_rows_do_not_change_earlier_features(self):
        p, part, chart = fixtures(n=8)
        before = f.build_panel(p.iloc[:4], part.iloc[:4], chart.iloc[:4], 2023)
        after = f.build_panel(p, part.sample(frac=1, random_state=1), chart.sample(frac=1, random_state=2), 2023)
        pd.testing.assert_frame_equal(before.features, after.features.iloc[:4])
        pd.testing.assert_series_equal(before.target, after.target.iloc[:4])
        altered = p.copy()
        altered.loc[4:, ["qb_dropback", "sack", "qb_scramble"]] = 1
        future = f.build_panel(altered, part, chart, 2023)
        pd.testing.assert_frame_equal(before.features, future.features.iloc[:4])

    def test_holdout_and_selection_targets_are_not_accessed(self):
        for season in [2024, 2025]:
            p, part, chart = fixtures(season)
            p = p.drop(columns=list(f.PBP_TARGETS))
            panel = f.build_panel(p, part, chart, season)
            self.assertIsNone(panel.target)
            self.assertNotIn("development_target_definition_checks", panel.qa)
            with self.assertRaisesRegex(ValueError, "2023"):
                f.development_distributions(panel)
            with self.assertRaisesRegex(ValueError, "2023"):
                f.build_panel(p, part, chart, season, include_targets=True)

    def test_wrong_role_unpinned_and_unverified_source_read_nothing(self):
        with patch.object(f.pd, "read_csv") as read:
            with self.assertRaisesRegex(ValueError, "season"):
                f._read_source(Path("play_by_play_2025.csv.gz"), 2023)
            with self.assertRaisesRegex(ValueError, "Unpinned"):
                f._read_source(Path("play_by_play_2021.csv.gz"), 2023)
            with patch.object(f, "verify_source", side_effect=ValueError("hash mismatch")):
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    f._read_source(Path("play_by_play_2023.csv.gz"), 2023)
            read.assert_not_called()

    def test_future_join_qa_never_groups_by_play_category(self):
        for season in [2024, 2025]:
            p, part, chart = fixtures(season)
            report = f.build_panel(p, part.iloc[1:], chart.iloc[2:], season).qa
            for join in report["joins"].values():
                self.assertIn("unmatched_by_team", join)
                self.assertNotIn("unmatched_by_team_and_play_category", join)
                self.assertNotIn("play_type", json.dumps(join))

    def test_descriptive_denominators_sum_without_prediction_fields(self):
        report = f.development_distributions(f.build_panel(*fixtures(), 2023))
        self.assertEqual(report["phase"], "descriptive")
        for table in report["tables"]:
            self.assertEqual(sum(c["n"] for c in table["cells"]), 4)
            self.assertEqual(sum(c["dropbacks"] for c in table["cells"]), 3)
            for c in table["cells"]:
                self.assertAlmostEqual(c["observed_dropback_fraction"], c["dropbacks"] / c["n"])
                self.assertEqual(c["n"], c["dropbacks"] + c["rushes_without_dropback"])
        with self.assertRaises(PermissionError):
            f.predict({})

    def test_empty_cohort_and_no_targets_have_well_formed_summary(self):
        p, part, chart = fixtures()
        p["season_type"] = "POST"
        panel = f.build_panel(p, part, chart, 2023)
        self.assertEqual(len(panel.features), 0)
        self.assertEqual(f.development_distributions(panel)["denominator"], 0)
        self.assertTrue(all(t["cells"] == [] for t in f.development_distributions(panel)["tables"]))

    def test_source_hash_and_sidecar_are_both_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.csv"
            path.write_text("value\n1\n")
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            sidecar = Path(str(path) + ".source.json")
            record = dict(url="https://official.example/source", retrieved_utc="2026-10-11T09:00:00+00:00", bytes=path.stat().st_size, sha256=sha)
            sidecar.write_text(json.dumps(record))
            self.assertEqual(f.verify_source(path, sha, record["url"])["sha256"], sha)
            with self.assertRaisesRegex(ValueError, "source/time"):
                f.verify_source(path, sha, "https://other.example/source")
            record["retrieved_utc"] = "invalid"
            sidecar.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "time"):
                f.verify_source(path, sha)
            path.write_text("value\n2\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                f.verify_source(path, sha)

    def test_unpinned_names_and_missing_files_do_not_trigger_network(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(f, "urlopen") as network:
            with self.assertRaises(ValueError):
                f.acquire_source("play_by_play_2024.csv.gz", Path(tmp), Path(tmp))
            with self.assertRaises(FileNotFoundError):
                f.acquire_source("play_by_play_2023.csv.gz", Path(tmp), Path(tmp))
            network.assert_not_called()

    def test_changed_download_is_rejected_before_cache_write(self):
        from io import BytesIO
        with tempfile.TemporaryDirectory() as tmp, patch.object(f, "urlopen", return_value=BytesIO(b"changed data")):
            with self.assertRaisesRegex(ValueError, "changed"):
                f.acquire_source("play_by_play_2023.csv.gz", Path(tmp), Path(tmp), download_missing=True)
            self.assertEqual(list(Path(tmp).iterdir()), [])


class FootballCachedSourceTests(unittest.TestCase):
    @unittest.skipUnless((f.ROOT / "data/tactical/football/play_by_play_2024.csv.gz").is_file(), "protocol QA cache unavailable")
    def test_actual_2024_protocol_support_without_targets(self):
        path = f.ROOT / "data/tactical/football/play_by_play_2024.csv.gz"
        expected = "23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06"
        f.verify_source(path, expected, "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2024.csv.gz")
        pbp, schema = f._read_source(path, 2024)
        self.assertTrue(set(f.PBP_TARGETS).isdisjoint(pbp))
        self.assertFalse(schema["target_columns_loaded"])
        frames = []
        for filename in ["pbp_participation_2024.csv", "ftn_charting_2024.csv"]:
            source, _ = f.acquire_source(filename, f.ROOT / "data/raw/tactical_research", f.ROOT / "data/tactical/football")
            frame, _ = f._read_source(source, 2024)
            frames.append(frame)
        panel = f.build_panel(pbp, *frames, 2024)
        self.assertIsNone(panel.target)
        for low, high, rows, games in [(1, 9, 16824, 138), (10, 18, 16511, 134)]:
            mask = panel.metadata.week.between(low, high)
            self.assertEqual(int(mask.sum()), rows)
            self.assertEqual(panel.metadata.loc[mask, "game_id"].nunique(), games)
        self.assertEqual(panel.qa["joins"]["ftn"]["matched"], 33335)

    @unittest.skipUnless((f.ROOT / "data/tactical/football/play_by_play_2023.csv.gz").is_file(), "official local cache unavailable")
    def test_actual_pinned_sources_and_holdout_firewall(self):
        summary = f.build_summary()
        self.assertEqual(summary["phase"], "descriptive")
        self.assertFalse(summary["predictive_gate"]["fitting_allowed"])
        self.assertEqual(summary["denominators"], [dict(season=2023, eligible_plays=33836, games=272), dict(season=2025, eligible_plays=32813, games=272)])
        self.assertEqual(len(summary["sources"]), 10)
        holdout = next(s for s in summary["source_schema_qa"] if s["filename"] == "play_by_play_2025.csv.gz")
        self.assertFalse(holdout["target_columns_loaded"])
        self.assertTrue(set(f.PBP_TARGETS).isdisjoint(holdout["loaded_columns"]))
        qa = next(q for q in summary["cohort_quality"] if q["season"] == 2025)
        self.assertNotIn("development_target_definition_checks", qa)
        self.assertEqual(qa["joins"]["ftn"]["matched"], 32813)
        self.assertEqual(summary["development_distributions"]["season"], 2023)
        json.dumps(summary, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
