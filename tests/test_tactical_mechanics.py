"""Synthetic measurement/parser/privacy tests; no source trial rows embedded."""
import ast
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.tactical import mechanics as m


def baseball_rows(count=6):
    metadata, poi, hittrax = [], [], []
    for i in range(count):
        meta = {field: "0" for field in m.META_COLUMNS}
        meta.update(session_swing=f"PRIVATE_TRIAL_{i}", user=f"PRIVATE_ATHLETE_{i}",
                    session=f"{i+1:03d}", athlete_age="22", exit_velo_mph_x="90",
                    blast_bat_speed_mph_x="72", bat_speed_mph_max_x="75")
        p = {field: "1" for pair in m.ALIASES for field in pair}
        p.update({field: "40" for field, *_ in m.BODY})
        p["x_factor_fp_z"] = p["torso_pelvis_launchpos_x"]
        p.update(session_swing=meta["session_swing"], session=str(i+1),
                 exit_velo_mph_x="90", blast_bat_speed_mph_x="72", bat_speed_mph_max_x="75",
                 bat_speed_mph_contact_x="70", attack_angle_contact_x="10")
        h = {field: "1" for field in m.HIT_COLUMNS}
        h.update(session_swing=meta["session_swing"], pitch="65", pitch_angle="-4",
                 horizontal_distance="-2", vertical_distance="3", la="20")
        metadata.append(meta)
        poi.append(p)
        hittrax.append(h)
    return metadata, poi, hittrax


def tennis_rows():
    serves, targets = [], []
    for player in range(1, 9):
        for region in m.REGIONS:
            targets.append(dict(player_id=str(player), dominant_hand="R", region=region,
                                target_x="5", target_y="2" if region.startswith("deuce") else "-2"))
        for period in (1, 2):
            for index, region in enumerate(m.REGIONS, 1):
                serves.append(dict(session_id="1", player_id=str(player), serve_period=str(period),
                                   region=region, index=str(index), speed_mph="100", clear_net="1", let="0",
                                   shot_x="5.3", shot_y="2.4" if region.startswith("deuce") else "-1.6"))
    return serves, targets


class NumericTests(unittest.TestCase):
    def test_missing_sentinels_and_finite_only(self):
        for value in ("", "NA", " NaN ", None, "null"):
            self.assertIsNone(m.number(value))
        for value in ("inf", "-inf", "invalid"):
            with self.assertRaises(ValueError):
                m.number(value)
        self.assertEqual(m.number(" 2.5 "), 2.5)

    def test_integer_flags_are_not_silently_rounded(self):
        for value in ("1.5", "", "3"):
            with self.assertRaises(ValueError):
                m.integer(value, "flag", {0, 1})
        self.assertEqual(m.integer("01", "session"), 1)

    def test_quantiles_missing_denominator_and_small_sample_suppression(self):
        stats = m.distribution([None] + list(range(10)))
        self.assertEqual((stats["denominator"], stats["observed"], stats["missing"]), (11, 10, 1))
        self.assertEqual((stats["q10"], stats["median"], stats["q90"]), (.9, 4.5, 8.1))
        self.assertTrue(m.distribution([1, 2])["values_suppressed"])
        self.assertNotIn("mean", m.distribution([]))

    def test_csv_schema_and_row_width(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.csv"
            for contents in ("a,a\n1,2\n", "a,b\n1\n", "a,b\n1,2,3\n"):
                path.write_text(contents)
                with self.assertRaises(ValueError):
                    m.read_csv(path, ("a", "b"))
            path.write_text("a,b\n1,2\n")
            self.assertEqual(m.read_csv(path, ("a", "b")), [{"a": "1", "b": "2"}])


class BaseballTests(unittest.TestCase):
    def test_semantic_allowlist_and_zero_padded_session_join(self):
        rows, counts = m.adapt_baseball(*baseball_rows())
        self.assertEqual(len(rows), 6)
        self.assertEqual(set(rows[0].body), {f for f, *_ in m.BODY})
        self.assertEqual(set(rows[0].pitch), {f for f, *_ in m.PITCH})
        self.assertEqual(counts["primary_athletes"], 6)
        self.assertEqual(rows[0].observed["marker_contact_speed"], 70)
        self.assertEqual(rows[0].observed["blast_contact_speed"], 72)

    def test_adult_outcome_context_flow_is_distinct(self):
        metadata, poi, hit = baseball_rows()
        metadata[0]["athlete_age"] = "17"
        metadata[1]["athlete_age"] = ""
        metadata[2]["exit_velo_mph_x"] = poi[2]["exit_velo_mph_x"] = "NA"
        hit = [row for row in hit if row["session_swing"] != metadata[3]["session_swing"]]
        rows, c = m.adapt_baseball(metadata, poi, hit)
        self.assertEqual((c["under_18_swings_excluded"], c["unknown_age_swings_excluded"]), (1, 1))
        self.assertEqual((c["adult_swings"], c["adult_recorded_exit_velocity_swings"], c["primary_swings"]), (4, 3, 2))
        self.assertEqual(c["adult_observed_exit_without_paired_context"], 1)
        self.assertEqual(len(rows), 2)

    def test_duplicate_and_orphaned_joins_fail(self):
        for index in range(3):
            parts = baseball_rows()
            parts[index].append(deepcopy(parts[index][0]))
            with self.assertRaises(ValueError):
                m.adapt_baseball(*parts)
        parts = baseball_rows()
        parts[1].pop()
        with self.assertRaises(ValueError):
            m.adapt_baseball(*parts)
        parts = baseball_rows()
        parts[2][0]["session_swing"] = "unknown"
        with self.assertRaises(ValueError):
            m.adapt_baseball(*parts)

    def test_duplicate_measurement_disagreement_fails(self):
        parts = baseball_rows()
        parts[1][0]["exit_velo_mph_x"] = "91"
        with self.assertRaises(ValueError):
            m.adapt_baseball(*parts)
        parts = baseball_rows()
        parts[1][0]["x_factor_fp_z"] = "99"
        with self.assertRaises(ValueError):
            m.adapt_baseball(*parts)

    def test_no_future_session_claim_when_contract_changes(self):
        parts = baseball_rows()
        parts[0][1]["user"] = parts[0][0]["user"]
        with self.assertRaises(ValueError):
            m.adapt_baseball(*parts)

    def test_outcome_and_unsafe_metadata_mutation_never_changes_features_or_splits(self):
        original = baseball_rows()
        rows, _ = m.adapt_baseball(*original)
        changed = deepcopy(original)
        for meta, poi, hit in zip(*changed):
            meta["exit_velo_mph_x"] = poi["exit_velo_mph_x"] = "130"
            meta["filename"] = "PRIVATE_BODY_OUTCOME_130.c3d"
            poi["sweet_spot_velo_mph_contact_x"] = "1000000"
            poi["bat_speed_mph_contact_x"] = "120"
            hit["res"], hit["dist"], hit["la"] = "synthetic winner", "500", "45"
        other, _ = m.adapt_baseball(*changed)
        self.assertEqual([r.body for r in rows], [r.body for r in other])
        self.assertEqual([r.pitch for r in rows], [r.pitch for r in other])
        self.assertEqual(m.split_plan(rows, "baseball"), m.split_plan(other, "baseball"))
        self.assertNotEqual(rows[0].observed, other[0].observed)

    def test_primary_display_has_no_identifiers_or_unsafe_candidates(self):
        rows, counts = m.adapt_baseball(*baseball_rows(15))
        summary = m.baseball_summary(rows, counts, {}, m.split_plan(rows, "baseball"))
        text = json.dumps(summary)
        self.assertNotIn("PRIVATE_", text)
        self.assertNotIn("sweet_spot_velo", text)
        self.assertNotIn("x_factor_fp_z", text)
        self.assertNotIn("bat_speed_mph_max_x", text)
        self.assertEqual(summary["predictive_gate"], {"status": "closed", "fitting_allowed": False})
        self.assertTrue(all(x["future_predictor"] is False for x in summary["observed_outcomes"]))


class TennisTests(unittest.TestCase):
    def test_exact_target_join_units_error_and_repeated_short_keys(self):
        serves, targets = tennis_rows()
        rows, c = m.adapt_tennis(serves, targets)
        self.assertEqual(c["repeated_short_key_extra_rows_retained"], 32)
        self.assertEqual(len(rows), 64)
        self.assertAlmostEqual(rows[0].dx, .3)
        self.assertAlmostEqual(rows[0].dy, .4)
        self.assertAlmostEqual(rows[0].radial_error, .5)
        self.assertAlmostEqual(rows[2].dy, .4)  # no automatic ad-side reflection
        targets[0]["target_x"] = "4"
        other, _ = m.adapt_tennis(serves, targets)
        self.assertAlmostEqual(other[0].dx, 1.3)
        self.assertEqual(other[4].target_x, 4)  # exact same target across periods
        self.assertEqual(other[1].target_x, 5)  # do not replace a whole region with a center

    def test_all_lets_excluded_but_net_missingness_retained(self):
        serves, targets = tennis_rows()
        serves[0].update(let="1", shot_x="NA", shot_y="NA")
        serves[1]["let"] = "1"
        serves[2].update(clear_net="0", shot_x="NA", shot_y="NA", speed_mph="NA")
        rows, c = m.adapt_tennis(serves, targets)
        self.assertEqual((c["lets_excluded"], c["lets_with_missing_bounce"]), (2, 1))
        self.assertEqual((c["nonlet_attempts"], c["nonlet_observed_bounce_pairs"], c["nonlet_net_censored"]), (62, 61, 1))
        net = rows[0]
        self.assertFalse(net.clear_net)
        self.assertIsNone(net.x)
        self.assertIsNone(net.dx)
        self.assertIsNone(net.radial_error)
        self.assertIsNone(net.speed)

    def test_partial_bounces_and_inconsistent_censoring_fail(self):
        for changes in (dict(shot_x="NA"), dict(shot_x="NA", shot_y="NA"), dict(clear_net="0"), dict(let="1", clear_net="0", shot_x="NA", shot_y="NA")):
            serves, targets = tennis_rows()
            serves[0].update(changes)
            with self.assertRaises(ValueError):
                m.adapt_tennis(serves, targets)

    def test_invalid_flag_unmatched_target_and_exact_duplicate_fail(self):
        serves, targets = tennis_rows()
        serves[0]["let"] = "2"
        with self.assertRaises(ValueError):
            m.adapt_tennis(serves, targets)
        serves, targets = tennis_rows()
        targets.pop(0)
        with self.assertRaises(ValueError):
            m.adapt_tennis(serves, targets)
        serves, targets = tennis_rows()
        serves.append(deepcopy(serves[0]))
        with self.assertRaises(ValueError):
            m.adapt_tennis(serves, targets)

    def test_target_duplicate_or_missing_coordinates_fail(self):
        for variant in ("duplicate", "missing"):
            serves, targets = tennis_rows()
            if variant == "duplicate":
                targets.append(deepcopy(targets[0]))
            else:
                targets[0]["target_y"] = "NA"
            with self.assertRaises(ValueError):
                m.adapt_tennis(serves, targets)

    def test_no_speed_clipping_or_simulated_label_import(self):
        serves, targets = tennis_rows()
        # Deliberately fabricated, nonphysical speed fixture; never a source observation.
        serves[0].update(speed_mph="1000.25", simulated_win_probability="0.999")
        rows, _ = m.adapt_tennis(serves, targets)
        self.assertEqual(rows[0].speed, 1000.25)
        self.assertFalse(hasattr(rows[0], "simulated_win_probability"))
        serves[0]["speed_mph"] = "0"
        with self.assertRaises(ValueError):
            m.adapt_tennis(serves, targets)

    def test_summary_has_no_raw_participant_or_attempt_keys(self):
        serves, targets = tennis_rows()
        rows, counts = m.adapt_tennis(serves, targets)
        summary = m.tennis_summary(rows, targets, counts, {}, m.split_plan(rows, "tennis"))
        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(v) for v in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(v) for v in value))
            return set()
        self.assertFalse(keys(summary) & {"player_id", "session_id", "group", "index", "dominant_hand", "shot_x", "shot_y"})
        self.assertFalse(summary["validation"]["borrowed_simulated_win_labels"])
        self.assertFalse(summary["validation"]["age_and_individual_consent_details_independently_verified"])


class PrivacyAndSplitTests(unittest.TestCase):
    def test_bins_use_fixed_boundaries_and_explicit_missingness(self):
        h = m.histogram([(x, str(i % 4)) for i, x in enumerate([0] * 12 + [1] * 12 + [None])], (0, 1, 2), "x", "m", "test")
        self.assertEqual([b["count"] for b in h["bins"]], [0, 12, 12, 0])
        self.assertEqual((h["denominator"], h["observed"], h["missing"]), (25, 24, 1))
        self.assertIsNone(h["bins"][0]["lower"])
        self.assertIsNone(h["bins"][-1]["upper"])

    def test_sparse_bin_and_complementary_count_are_suppressed(self):
        h = m.histogram([(0, "a")] + [(1, str(i % 4)) for i in range(20)], (1,), "x", "m", "test")
        self.assertTrue(all(b["suppressed"] for b in h["bins"]))
        self.assertTrue(all(b["count"] is None for b in h["bins"]))

    def test_single_participant_bin_not_disclosed_despite_many_rows(self):
        h = m.histogram([(0, "one_person")] * 100, (), "x", "m", "test")
        self.assertIsNone(h["bins"][0]["count"])

    def test_nested_plan_no_group_overlap_and_order_independent(self):
        rows, _ = m.adapt_baseball(*baseball_rows(15))
        plan = m.split_plan(rows, "baseball")
        self.assertEqual(plan, m.split_plan(list(reversed(rows)), "baseball"))
        all_test = []
        for fold in plan["folds"]:
            test, train = set(fold["test_groups"]), set(fold["training_groups"])
            self.assertFalse(test & train)
            self.assertEqual(set(fold["inner_assignment"]), train)
            self.assertEqual(set(fold["inner_assignment"].values()), {0, 1, 2, 3})
            all_test.extend(test)
        self.assertEqual(len(all_test), len(set(all_test)))
        self.assertEqual(len(all_test), 15)
        self.assertNotIn("PRIVATE_", json.dumps(plan))

    def test_leave_player_out_excludes_all_sessions_and_conditions(self):
        serves, targets = tennis_rows()
        serves[0]["session_id"] = "2"
        rows, _ = m.adapt_tennis(serves, targets)
        plan = m.split_plan(rows, "tennis")
        self.assertEqual(len(plan["folds"]), 8)
        for fold in plan["folds"]:
            self.assertEqual(len(fold["test_groups"]), 1)
            self.assertEqual(len(fold["training_groups"]), 7)
            self.assertFalse(set(fold["test_groups"]) & set(fold["training_groups"]))
        changed = deepcopy(serves)
        for row in changed:
            row.update(shot_x="8", shot_y="4", speed_mph="120")
        other, _ = m.adapt_tennis(changed, targets)
        self.assertEqual(plan, m.split_plan(other, "tennis"))

    def test_unknown_fit_option_rejected_before_source_access(self):
        proc = subprocess.run([sys.executable, "-m", "experiments.tactical.mechanics", "--fit"], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unrecognized arguments", proc.stderr)

    def test_no_model_library_or_fitting_scoring_calls(self):
        tree = ast.parse(Path(m.__file__).read_text())
        forbidden = {"fit", "fit_transform", "predict", "predict_proba", "score", "corr", "corrcoef", "polyfit"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(not alias.name.startswith(("sklearn", "scipy", "numpy", "pandas", "torch")) for alias in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertFalse((node.module or "").startswith(("sklearn", "scipy", "numpy", "pandas", "torch")))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, forbidden)


class SourceIntegrityTests(unittest.TestCase):
    def test_hash_pin_url_and_bytes_must_all_match(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            (cache / "sample.csv").write_text("a,b\n1,2\n")
            sha = m.digest(cache / "sample.csv")
            expected = {"sample.csv": sha}
            entry = {"path": "sample.csv", "sha256": sha, "bytes": 8,
                     "url": "https://raw.githubusercontent.com/org/repo/pin/sample.csv"}
            m.verify_files(cache, [entry], expected, "https://github.com/org/repo", "pin", "path")
            for patch in (dict(url=entry["url"].replace("/pin/", "/main/")), dict(sha256="0" * 64), dict(bytes=9)):
                with self.assertRaises(ValueError):
                    m.verify_files(cache, [{**entry, **patch}], expected, "https://github.com/org/repo", "pin", "path")
            (cache / "sample.csv").write_text("a,b\n2,1\n")
            with self.assertRaises(ValueError):
                m.verify_files(cache, [entry], expected, "https://github.com/org/repo", "pin", "path")

    def test_duplicate_manifest_entry_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                m.verify_files(Path(temp), [{"path": "sample"}, {"path": "sample"}], {"sample": "x"}, "repo", "pin", "path")


if __name__ == "__main__":
    unittest.main()
