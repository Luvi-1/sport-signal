"""Synthetic baseball grammar/state/leakage tests; no downloaded rows embedded."""
from copy import deepcopy
import unittest

from experiments.tactical.baseball import (
    AlignmentError, FEATURE_FIELDS, RawRecord, advance_count, classify_target,
    parse_game, pitch_letters,
)


GID = "SYN202304010"
ROSTER = {"b": ("R", "R"), "p": ("R", "R"), "q": ("L", "L"),
          "r": ("L", "R"), "s": ("B", "R"), "h": ("L", "R")}


class Fixture:
    def __init__(self):
        self.raw = []
        self.parsed = []
        self.outs = 0
        self.bases = ["", "", ""]
        self.scores = [0, 0]
        self.add("id", GID)
        self.add("info", "date", "2023/04/01")
        self.add("start", "b", "Batter", "0", "1", "7")
        self.add("start", "p", "Pitcher", "1", "0", "1")
        self.add("start", "q", "Other pitcher", "0", "0", "1")

    def add(self, *fields):
        self.raw.append(RawRecord("synthetic.EVN", len(self.raw) + 1, fields))

    def play(self, sequence, count, event, *, pa=1, batter="b", pitcher="p", inning=1,
             side=0, outs=None, bases=None, runs=0, parsed=True, **extra):
        self.add("play", str(inning), str(side), batter, count, sequence, event)
        if not parsed:
            return
        row = {"gid": GID, "pn": str(len(self.parsed) + 1), "event": event,
            "batter": batter, "pitcher": pitcher, "bathand": ROSTER[batter][0],
            "pithand": ROSTER[pitcher][1], "inning": str(inning), "vis_home": str(side),
            "top_bot": str(side), "pitches": sequence, "count": count,
            "balls": count[0] if count not in {"??", ""} else "0",
            "strikes": count[1] if count not in {"??", ""} else "0",
            "pa": str(pa), "outs_pre": str(self.outs), "outs_post": str(self.outs if outs is None else outs),
            "score_v": str(self.scores[0]), "score_h": str(self.scores[1]), "runs": str(runs),
            "date": "20230401", "bunt": "0", "bip": str(int("X" in sequence or "Y" in sequence)),
            "k": str(int(event.startswith("K"))), "walk": str(int(event.startswith(("W", "IW")))),
            "hbp": str(int(event == "HP")), "source_file": "synthetic.csv",
            "source_row": len(self.parsed) + 2}
        row.update({f"br{i + 1}_pre": runner for i, runner in enumerate(self.bases)})
        row.update({f"br{i + 1}_post": runner for i, runner in enumerate(self.bases if bases is None else bases)})
        row.update({k: str(v) for k, v in extra.items()})
        self.parsed.append(row)
        self.outs = int(row["outs_post"])
        self.bases = [row[f"br{i}_post"] for i in range(1, 4)]
        self.scores[side] += runs

    def parse(self):
        return parse_game(GID, self.raw, self.parsed, ROSTER)


class BaseballGrammarTest(unittest.TestCase):
    def test_pickoffs_modifiers_and_no_pitch_are_not_deliveries(self):
        self.assertEqual(pitch_letters("+1.>B*F2N"), [(4, "B"), (6, "F"), (8, "N")])
        f = Fixture()
        f.play("+1.>B*F2NX", "11", "63", outs=1)
        result = f.parse()
        self.assertEqual([r["target"]["symbol"] for r in result.pitches], list("BFX"))
        self.assertEqual(result.stats["administrative_N"], 1)

    def test_unknown_grammar_fails_closed(self):
        for sequence in ("BCZ", "bcx", "BC?", "B0C"):
            with self.subTest(sequence=sequence), self.assertRaises(AlignmentError):
                pitch_letters(sequence)

    def test_two_strike_fouls_do_not_add_strike(self):
        f = Fixture()
        f.play("BCFFBS", "22", "K", outs=1)
        result = f.parse()
        self.assertEqual([(p["features"]["balls"], p["features"]["strikes"]) for p in result.pitches],
                         [(0, 0), (1, 0), (1, 1), (1, 2), (1, 2), (2, 2)])
        self.assertTrue(all(p["eligibility"]["swing"] for p in result.pitches))

    def test_automatic_counts_update_without_delivery(self):
        f = Fixture()
        f.play("VAFX", "12", "63", outs=1)
        result = f.parse()
        self.assertEqual(len(result.pitches), 2)
        self.assertEqual((result.pitches[0]["features"]["balls"], result.pitches[0]["features"]["strikes"]), (1, 1))
        self.assertEqual(result.pitches[1]["features"]["pa_delivered_pitch_index"], 2)
        self.assertEqual(result.stats["administrative_A"], 1)
        self.assertEqual(result.stats["administrative_V"], 1)

    def test_pitchouts_target_exclusions_and_count(self):
        f = Fixture()
        f.play("PQRY", "12", "63", outs=1)
        result = f.parse()
        self.assertTrue(all(p["target"]["taxonomy_exclusion"] == "pitchout_delivery" for p in result.pitches))
        self.assertEqual(result.pitches[-1]["features"]["strikes"], 2)

    def test_foul_bunt_strike_three_and_missed_tip_bunts(self):
        f = Fixture()
        f.play("CLL", "02", "K", outs=1, bunt=1)
        result = f.parse()
        self.assertTrue(result.pitches[0]["eligibility"]["swing"])
        self.assertFalse(result.pitches[1]["eligibility"]["swing"])
        self.assertEqual(result.events[-1]["terminal_target_check"], "consistent")
        for code in "LMO":
            self.assertEqual(advance_count(0, 2, code), (0, 3))
            self.assertEqual(classify_target(code)["taxonomy_exclusion"], "bunt_delivery")

    def test_inplay_bunt_excludes_only_current_pitch(self):
        f = Fixture()
        f.play("BCX", "11", "13/SH", outs=1, bunt=1)
        result = f.parse()
        self.assertEqual([p["eligibility"]["swing"] for p in result.pitches], [True, True, False])

    def test_unknown_strike_vs_unknown_count(self):
        f = Fixture()
        f.play("KCX", "02", "63", outs=1)
        result = f.parse()
        self.assertEqual([p["eligibility"]["swing"] for p in result.pitches], [False, True, True])
        f = Fixture()
        f.play("BUX", "??", "63", outs=1)
        result = f.parse()
        self.assertTrue(result.pitches[0]["eligibility"]["swing"])
        self.assertFalse(result.pitches[-1]["eligibility"]["swing"])
        self.assertIn("count_unknown_after_U", result.pitches[-1]["qa_exclusions"])

    def test_hit_batter_and_intentional_walk(self):
        f = Fixture()
        f.play("H", "00", "HP", bases=["b", "", ""])
        f.play("", "00", "IW", batter="r", bases=["r", "b", ""])
        result = f.parse()
        self.assertEqual(len(result.pitches), 1)
        self.assertEqual(result.pitches[0]["target"]["taxonomy_exclusion"], "hit_by_pitch")
        self.assertEqual(result.stats["empty_pitch_string_parsed_rows"], 1)
        self.assertEqual(classify_target("I")["taxonomy_exclusion"], "intentional_delivered_ball")

    def test_administrative_walk_appeal_has_no_delivered_target(self):
        f = Fixture()
        f.play("VVVV", "30", "2", outs=1)
        result = f.parse()
        self.assertFalse(result.pitches)
        self.assertEqual(result.stats["administrative_no_delivery_nonwalk_outcomes"], 1)
        self.assertFalse(result.issues)

    def test_interference_excludes_only_current_pitch(self):
        f = Fixture()
        f.play("BCX", "11", "C/E2", xi=1, bip=0, bases=["b", "", ""])
        result = f.parse()
        self.assertEqual([p["eligibility"]["swing"] for p in result.pitches], [True, True, False])
        self.assertEqual(result.pitches[-1]["target"]["taxonomy_exclusion"], "interference_delivery")
        self.assertFalse(result.issues)

    def test_home_run_is_contact_even_when_bip_flag_excludes_homers(self):
        f = Fixture()
        f.play("X", "00", "HR", hr=1, bip=0, runs=1)
        result = f.parse()
        self.assertEqual(result.pitches[0]["target"]["contact_given_swing"], 1)
        self.assertFalse(result.issues)

    def test_batter_interference_is_current_pitch_exclusion(self):
        f = Fixture()
        f.play("BCS", "11", "2/BINT", bip=1, outs=1)
        result = f.parse()
        self.assertEqual([p["eligibility"]["swing"] for p in result.pitches], [True, True, False])
        self.assertFalse(result.issues)

    def test_three_ball_walk_has_explicit_conservative_exclusion(self):
        f = Fixture()
        f.play("CBBB", "21", "W", bases=["b", "", ""])
        result = f.parse()
        self.assertTrue(all(not p["eligibility"]["swing"] for p in result.pitches))
        self.assertEqual(result.stats["terminal_walk_before_ball_four"], 1)

    def test_foul_tip_is_contact_and_swinging_strike_is_not(self):
        self.assertEqual(classify_target("T")["contact_given_swing"], 1)
        self.assertEqual(classify_target("S")["contact_given_swing"], 0)
        self.assertIsNone(classify_target("C")["contact_given_swing"])


class BaseballStateTest(unittest.TestCase):
    def test_omitted_np_still_emits_prefix_before_pitcher_change(self):
        f = Fixture()
        f.play("BC", "11", "NP", pa=0, parsed=False)
        f.add("sub", "q", "Reliever", "1", "0", "1")
        f.play("BC.X", "11", "63", pitcher="q", outs=1)
        result = f.parse()
        self.assertEqual([p["features"]["pitcher"] for p in result.pitches], ["p", "p", "q"])
        self.assertEqual(result.stats["omitted_np_rows"], 1)
        self.assertEqual(result.stats["duplicate_prefix_symbols_removed"], 2)
        self.assertEqual(result.stats["pitches_after_midpa_pitcher_change"], 1)

    def test_retained_np_and_repeated_empty_delta(self):
        f = Fixture()
        f.play("BC", "11", "NP", pa=0)
        f.play("BC.", "11", "NP", pa=0, parsed=False)
        f.play("BC..X", "11", "63", outs=1)
        result = f.parse()
        self.assertEqual(len(result.pitches), 3)
        self.assertEqual(result.stats["retained_np_rows"], 1)
        self.assertEqual(result.stats["omitted_np_rows"], 1)

    def test_midpa_pinch_hitter_and_responsibility_attribution(self):
        f = Fixture()
        f.play("CC", "02", "NP", parsed=False, pa=0)
        f.add("sub", "h", "Pinch hitter", "0", "1", "11")
        f.play("CC.S", "02", "K", batter="h", outs=1)
        f.parsed[-1].update(batter="b", bathand="R", pitches="CC")
        result = f.parse()
        self.assertEqual([p["features"]["batter"] for p in result.pitches], ["b", "b", "h"])
        self.assertEqual(result.stats["parsed_strikeout_attribution_retains_replaced_batter"], 1)
        self.assertEqual(result.pitches[-1]["features"]["strikes"], 2)

    def test_generated_attribution_np_requires_exact_no_state_change(self):
        f = Fixture()
        f.play("CC", "02", "NP", parsed=False, pa=0)
        f.add("sub", "h", "Pinch hitter", "0", "1", "11")
        f.play("CC.S", "02", "K", batter="h", outs=1)
        actual = deepcopy(f.parsed[-1])
        f.parsed[-1].update(batter="b", bathand="R", pitches="CC")
        actual.update(pn="2", event="NP", pa="0", k="0", outs_pre="1")
        f.parsed.append(actual)
        result = f.parse()
        self.assertEqual(len(result.pitches), 3)
        self.assertEqual(result.stats["aligned_parsed_rows"], 2)
        self.assertEqual(result.stats["generated_attribution_np_rows"], 1)
        f.parsed[-1]["score_v"] = "1"
        with self.assertRaises(AlignmentError):
            f.parse()

    def test_replaced_pitcher_walk_attribution_uses_actual_active_pitcher(self):
        f = Fixture()
        f.play("BBB", "30", "NP", parsed=False, pa=0)
        f.add("sub", "q", "Reliever", "1", "0", "1")
        f.play("BBB.B", "30", "W", pitcher="q", bases=["b", "", ""])
        f.parsed[-1].update(pitcher="p", pithand="R", pitches="BBB")
        result = f.parse()
        self.assertEqual(result.pitches[-1]["features"]["pitcher"], "q")
        self.assertEqual(result.pitches[-1]["features"]["pitcher_hand"], "L")
        self.assertEqual(result.stats["parsed_walk_attribution_retains_replaced_pitcher_prefix"], 1)

    def test_no_pitch_annotation_can_disappear_without_repeating_deliveries(self):
        f = Fixture()
        f.play("BN", "10", "NP", pa=0, parsed=False)
        f.play("B.1X", "10", "63", outs=1)
        result = f.parse()
        self.assertEqual([p["target"]["symbol"] for p in result.pitches], ["B", "X"])
        self.assertEqual(result.stats["no_pitch_prefix_normalizations"], 1)
        self.assertEqual(result.stats["administrative_N"], 1)

    def test_unproved_batter_attribution_mismatch_fails(self):
        f = Fixture()
        f.play("CCS", "02", "K", outs=1)
        f.parsed[-1]["batter"] = "h"
        with self.assertRaises(AlignmentError):
            f.parse()

    def test_unproved_pitcher_attribution_mismatch_fails(self):
        f = Fixture()
        f.play("BCX", "11", "63", outs=1)
        f.parsed[0].update(pitcher="q", pithand="L")
        with self.assertRaisesRegex(AlignmentError, "Unproved parsed pitcher attribution"):
            f.parse()

    def test_raw_adjustments_and_switch_side_inference(self):
        f = Fixture()
        f.add("padj", "p", "L")
        f.add("badj", "s", "L")
        f.play("X", "00", "63", batter="s", pithand="L", bathand="L", outs=1)
        f.play("X", "00", "63", batter="s", outs=2)
        result = f.parse()
        first, second = [p["features"] for p in result.pitches]
        self.assertEqual((first["batter_hand"], first["pitcher_hand"]), ("L", "L"))
        self.assertEqual(first["batter_hand_method"], "raw_adjustment")
        self.assertEqual(second["pitcher_hand"], "R")
        self.assertEqual(second["batter_hand"], "L")
        self.assertIn("inference", second["batter_hand_method"])

    def test_runner_interruption_updates_bases_without_repeating_pitch(self):
        f = Fixture()
        f.play("", "00", "IW", batter="r", bases=["r", "", ""])
        f.play(">B", "00", "SB2", pa=0, bases=["", "r", ""])
        f.play(">B.X", "10", "63", outs=1)
        result = f.parse()
        first, second = [p["features"] for p in result.pitches]
        self.assertTrue(first["on_first"])
        self.assertFalse(first["on_second"])
        self.assertFalse(second["on_first"])
        self.assertTrue(second["on_second"])
        self.assertEqual(second["balls"], 1)

    def test_score_changes_only_after_completed_event(self):
        f = Fixture()
        f.play("BX", "10", "HR", runs=1)
        f.play("X", "00", "63", outs=1)
        result = f.parse()
        self.assertEqual([p["features"]["visitor_score"] for p in result.pitches], [0, 0, 1])

    def test_pinch_runner_and_extra_inning_runner_adjustments(self):
        f = Fixture()
        f.play("", "00", "IW", bases=["b", "", ""])
        f.add("sub", "r", "Pinch runner", "0", "1", "12")
        f.bases = ["r", "", ""]
        f.play("X", "00", "63", batter="h", outs=1)
        self.assertTrue(f.parse().pitches[-1]["features"]["on_first"])
        f = Fixture()
        f.add("radj", "r", "2")
        f.bases = ["", "r", ""]
        f.play("X", "00", "63", inning=10, outs=1)
        self.assertTrue(f.parse().pitches[-1]["features"]["on_second"])

    def test_inning_end_on_runner_event_resets_count(self):
        f = Fixture()
        f.play("X", "00", "63", outs=1)
        f.play("X", "00", "63", outs=2)
        f.play("", "00", "IW", batter="r", bases=["r", "", ""])
        f.play("C.1", "01", "CS2(26)", pa=0, outs=3, bases=["", "", ""])
        f.outs = 0
        f.play("X", "00", "63", side=1, pitcher="q", outs=1)
        result = f.parse()
        self.assertEqual(result.pitches[-1]["features"]["strikes"], 0)
        self.assertEqual(result.pitches[-1]["features"]["outs"], 0)
        self.assertEqual(result.pitches[-1]["features"]["pa_delivered_pitch_index"], 1)

    def test_suspended_date_from_raw_boundary_not_gid(self):
        f = Fixture()
        f.play("B", "10", "NP", pa=0, parsed=False)
        f.add("com", "suspended,20230403,SYN01,rain")
        f.play("BX", "10", "63", date="20230403", outs=1)
        result = f.parse()
        self.assertEqual([p["lineage"]["event_date"] for p in result.pitches], ["20230401", None])
        self.assertTrue(result.pitches[0]["eligibility"]["swing"])
        self.assertFalse(result.pitches[1]["eligibility"]["swing"])
        self.assertEqual(result.pitches[1]["lineage"]["source_record_date"], "20230403")

    def test_unseen_prefix_after_suspension_has_no_invented_exact_date(self):
        f = Fixture()
        f.add("com", "suspended,20230403,SYN01,rain")
        f.play("BC", "11", "NP", pa=0, parsed=False)
        f.add("sub", "q", "Reliever", "1", "0", "1")
        f.play("BC.X", "11", "63", date="20230403", pitcher="q", outs=1)
        result = f.parse()
        self.assertEqual([p["lineage"]["event_date"] for p in result.pitches], [None, None, "20230403"])
        self.assertEqual([p["eligibility"]["swing"] for p in result.pitches], [False, False, True])
        for row in result.pitches[:2]:
            self.assertEqual((row["lineage"]["event_date_min"], row["lineage"]["event_date_max"]),
                             ("20230401", "20230403"))
            self.assertIn("ambiguous_suspension_prefix_timing", row["qa_exclusions"])
        self.assertEqual(result.pitches[-1]["features"]["balls"], 1)
        self.assertEqual(result.pitches[-1]["features"]["strikes"], 1)
        self.assertEqual(result.pitches[-1]["features"]["pitcher"], "q")

    def test_repeated_prior_prefix_after_suspension_keeps_known_dates(self):
        f = Fixture()
        f.play("BC", "11", "NP", pa=0, parsed=False)
        f.add("com", "suspended,20230403,SYN01,rain")
        f.play("BC.", "11", "NP", pa=0, parsed=False)
        f.play("BC..X", "11", "63", date="20230403", outs=1)
        result = f.parse()
        self.assertEqual([p["lineage"]["event_date"] for p in result.pitches],
                         ["20230401", "20230401", "20230403"])
        self.assertTrue(all(p["eligibility"]["swing"] for p in result.pitches))

    def test_source_count_conflict_quarantines_without_clipping(self):
        f = Fixture()
        f.play("BBBBB", "30", "W", bases=["b", "", ""])
        result = f.parse()
        self.assertEqual(result.pitches[-1]["features"]["balls"], 4)
        self.assertTrue(all(not p["eligibility"]["swing"] for p in result.pitches))
        self.assertEqual(result.stats["quarantined_pas"], 1)

    def test_structural_prefix_state_and_coverage_errors_fail_closed(self):
        for change in ("prefix", "state", "unconsumed"):
            f = Fixture()
            f.play("BC", "11", "NP", pa=0, parsed=False)
            f.play("BCX", "11", "63", outs=1)
            if change == "prefix":
                row = list(f.raw[-1].fields)
                row[5] = "CBX"
                f.raw[-1] = RawRecord("synthetic.EVN", 9, tuple(row))
                f.parsed[-1]["pitches"] = "CBX"
            elif change == "state":
                f.parsed[0]["score_v"] = "1"
            else:
                f.parsed.append(deepcopy(f.parsed[0]))
            with self.subTest(change=change), self.assertRaises(AlignmentError):
                f.parse()


class BaseballLeakageTest(unittest.TestCase):
    def test_future_suffix_cannot_change_current_features(self):
        a, b = Fixture(), Fixture()
        a.play("BCX", "11", "63", outs=1)
        b.play("BCFBX", "22", "S7", bases=["b", "", ""])
        # Both source rows agree on the prefix before pitch 3; all later
        # symbols, event, final base state, and contact/bunt labels may differ.
        pa, pb = a.parse().pitches, b.parse().pitches
        self.assertEqual([p["features"] for p in pa[:3]], [p["features"] for p in pb[:3]])
        self.assertEqual(tuple(pa[0]["features"]), FEATURE_FIELDS)
        self.assertNotIn("terminal_event", pa[0]["features"])
        self.assertNotIn("pitches", pa[0]["features"])

    def test_terminal_bunt_annotation_does_not_modify_any_feature(self):
        a, b = Fixture(), Fixture()
        a.play("BCX", "11", "63", outs=1)
        b.play("BCX", "11", "13/SH", outs=1, bunt=1)
        aa, bb = a.parse().pitches, b.parse().pitches
        self.assertEqual([p["features"] for p in aa], [p["features"] for p in bb])
        self.assertNotEqual(aa[-1]["eligibility"], bb[-1]["eligibility"])
        self.assertEqual(aa[0]["eligibility"], bb[0]["eligibility"])


if __name__ == "__main__":
    unittest.main()
