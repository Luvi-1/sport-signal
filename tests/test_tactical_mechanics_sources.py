"""Optional local-cache integration QA; skips when licensed source bytes are absent."""
from pathlib import Path
import unittest
from experiments.tactical import mechanics as m

ROOT = Path(__file__).resolve().parents[1]


class LocalMeasurementCacheTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / "data/raw/tactical_research/openbiomechanics/baseball_hitting/data/metadata.csv").exists(), "Local OpenBiomechanics cache unavailable")
    def test_reviewed_baseball_population_and_complete_primary_measurements(self):
        paths, notice = m.validate_sources(ROOT, "baseball")
        rows, c = m.adapt_baseball(
            m.read_csv(paths["baseball_hitting/data/metadata.csv"], m.META_COLUMNS),
            m.read_csv(paths["baseball_hitting/data/poi/poi_metrics.csv"]),
            m.read_csv(paths["baseball_hitting/data/poi/hittrax.csv"], m.HIT_COLUMNS))
        self.assertEqual((c["source_swings"], c["source_athletes"]), (677, 98))
        self.assertEqual((c["adult_recorded_exit_velocity_swings"], c["adult_recorded_exit_velocity_athletes"]), (638, 92))
        self.assertEqual((len(rows), c["primary_athletes"]), (571, 82))
        self.assertEqual(c["primary_strike_zone_category_missing_not_used"], 46)
        self.assertTrue(all(v is not None for r in rows for v in (*r.body.values(), *r.pitch.values())))
        self.assertEqual(notice["commit"], m.OBM_COMMIT)
        self.assertEqual(len(notice["files"]), 7)

    @unittest.skipUnless((ROOT / "data/research/tennis/byu-inspection/serves.csv").exists(), "Local BYU cache unavailable")
    def test_reviewed_tennis_censoring_and_source_counts(self):
        paths, notice = m.validate_sources(ROOT, "tennis")
        rows, c = m.adapt_tennis(m.read_csv(paths["data/serves.csv"], m.SERVE_COLUMNS),
                                m.read_csv(paths["data/targets.csv"], m.TARGET_COLUMNS))
        self.assertEqual((c["source_attempts"], c["source_players"], c["source_sessions"]), (567, 8, 8))
        self.assertEqual((len(rows), c["nonlet_observed_bounce_pairs"], c["nonlet_net_censored"]), (548, 437, 111))
        self.assertEqual((c["lets_excluded"], c["lets_with_missing_bounce"]), (19, 5))
        self.assertEqual(c["repeated_short_key_extra_rows_retained"], 21)
        self.assertEqual(c["source_missing_speeds"], 23)
        self.assertEqual(c["nonlet_player_period_region_cells"], 64)
        self.assertEqual(notice["commit"], m.BYU_COMMIT)
        self.assertEqual(len(notice["files"]), 5)
        self.assertTrue(all(r.radial_error is None for r in rows if not r.clear_net))


if __name__ == "__main__":
    unittest.main()
