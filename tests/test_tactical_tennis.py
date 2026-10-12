"""Synthetic offline tests; no copyrighted match rows are embedded."""
import csv
from dataclasses import replace
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from experiments.tactical import tennis as t


def metadata(**changes):
    row = dict(zip(t.MATCH_COLUMNS, ["20200101-M-Synthetic-F-Alpha-Beta", "Alpha", "Beta", "R", "L", "20200101", "Synthetic", "F", "", "", "Hard", "", "3", "1", "Synthetic coder"]))
    row.update(changes)
    return row


def point(meta=None, state=None, winner=None, **changes):
    meta, state = meta or metadata(), state or t.ScoreState()
    winner = winner or state.server
    row = {"match_id": meta["match_id"], **t.expected_source_score(meta, state),
           "1st": "6*" if winner == state.server else "4f1*", "2nd": "", "Notes": "", "PtWinner": str(winner)}
    row.update(changes)
    return row


def make_match(winners, meta=None):
    meta = meta or metadata()
    state, rows = t.ScoreState(), []
    for winner in winners:
        rows.append(point(meta, state, winner))
        state = t.advance_score(meta, state, winner)
    return rows, state


def write_csv(path, columns, rows=()):
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


class ServePrefixTest(unittest.TestCase):
    def test_documented_direction_fault_and_modifiers(self):
        for code, expected in (("4", "wide"), ("5", "body"), ("6", "T")):
            parsed = t.parse_serve(code + "+n")
            self.assertEqual((parsed.direction, parsed.outcome, parsed.fault), (expected, "fault", "net"))
            self.assertEqual(parsed.modifiers, "+")
        for code, expected in t.FAULTS.items():
            self.assertEqual(t.parse_serve("5" + code).fault, expected)

    def test_unknown_unobserved_penalty_violation_missing_distinct(self):
        cases = {"0n": ("explicit_unknown", "fault"), "g": ("omitted", "fault"),
                 "S": ("unobserved", "unobserved_server"), "R": ("unobserved", "unobserved_receiver"),
                 "P": ("not_applicable", "penalty_server"), "Q": ("not_applicable", "penalty_receiver"),
                 "V": ("not_applicable", "first_serve_time_violation"), "": ("missing", "missing")}
        for text, expected in cases.items():
            with self.subTest(text=text):
                parsed = t.parse_serve(text)
                self.assertIsNone(parsed.direction)
                self.assertEqual((parsed.direction_status, parsed.outcome), expected)

    def test_repeated_lets_preserve_offsets_and_are_not_shots(self):
        parsed = t.parse_serve(" cc4+efuture ")
        self.assertEqual(parsed.lets, 2)
        self.assertEqual(parsed.start, 1)
        self.assertEqual(parsed.raw_prefix, "cc4+e")
        self.assertEqual(parsed.end, 6)
        self.assertEqual(parsed.outcome, "unsupported")
        self.assertIn("unexpected_fault_suffix", parsed.flags)

    def test_serve_prefix_preserves_full_rally_as_unparsed(self):
        parsed = t.parse_serve("cc6+f29b3*")
        self.assertEqual((parsed.raw_prefix, parsed.end, parsed.suffix_start), ("cc6+", 4, 4))
        self.assertEqual(parsed.outcome, "in_play_or_unspecified")
        self.assertIn("rally_suffix_not_parsed", parsed.flags)
        self.assertNotIn("f29", parsed.raw_prefix)

    def test_immediate_terminals_and_challenge(self):
        self.assertEqual(t.parse_serve("5*").outcome, "ace")
        self.assertEqual(t.parse_serve("6#").outcome, "unreturned")
        self.assertIn("wrong_challenge_in_unparsed_suffix", t.parse_serve("6b29C").flags)
        self.assertEqual(t.parse_serve("4*garbage").outcome, "unsupported")

    def test_unsupported_starts_are_not_coerced(self):
        for code in ("3*", "f3*", "?", "8n", "N", "&*"):
            self.assertEqual(t.parse_serve(code).outcome, "unsupported")
            self.assertIsNone(t.parse_serve(code).direction)


class ScoreTest(unittest.TestCase):
    def test_first_server_and_tbset_not_current_tiebreak(self):
        meta, state = metadata(), t.ScoreState()
        self.assertEqual(t.expected_source_score(meta, state)["TbSet"], "True")
        features = t.prediction_features(meta, state, "m", "A1")
        self.assertFalse(features["current_tiebreak"])
        self.assertEqual(features["serve_side"], "deuce")
        self.assertEqual(features["server"], "Alpha")

    def test_server_relative_score_side_and_deuce(self):
        meta = metadata()
        state = replace(t.ScoreState(), server=2, points=(3, 3), game_point_number=6)
        state = t.advance_score(meta, state, 2)
        self.assertEqual(t.point_score(meta, state), ("AD", "40"))
        self.assertEqual(t.prediction_features(meta, state, "m", "A1")["serve_side"], "ad")
        state = t.advance_score(meta, state, 1)
        self.assertEqual(t.point_score(meta, state), ("40", "40"))
        state = t.advance_score(meta, t.advance_score(meta, state, 1), 1)
        self.assertEqual((state.games, state.server, state.game_point_number), ((1, 0), 1, 0))

    def test_complete_ordinary_match(self):
        rows, state = make_match([1] * 48)
        states, reasons, checks, complete = t.audit_match(metadata(), rows)
        self.assertEqual(len(states), 48)
        self.assertFalse(reasons)
        self.assertTrue(complete)
        self.assertEqual(state.sets, (2, 0))
        self.assertEqual(checks["Svr_tested"], 48)

    def test_partial_match_is_not_completed(self):
        rows, _ = make_match([1, 2, 1])
        self.assertEqual(t.audit_match(metadata(), rows)[1], set())
        self.assertFalse(t.audit_match(metadata(), rows)[3])

    def test_tiebreak_service_pattern_and_relative_points(self):
        meta = metadata()
        state = replace(t.ScoreState(), games=(6, 6), game_number=13)
        servers = []
        for winner in [1, 2] * 4:
            servers.append(state.server)
            state = t.advance_score(meta, state, winner)
        self.assertEqual(servers, [1, 2, 2, 1, 1, 2, 2, 1])
        self.assertTrue(t.in_tiebreak(meta, state))
        self.assertEqual(t.point_score(meta, state), ("4", "4"))

    def test_tiebreak_set_end_next_server(self):
        meta = metadata()
        state = replace(t.ScoreState(), games=(6, 6), points=(6, 5), server=1,
                        game_point_number=11, tiebreak_first_server=1)
        state = t.advance_score(meta, state, 1)
        self.assertEqual((state.sets, state.games, state.server), ((1, 0), (0, 0), 2))

    def test_ten_point_tiebreak_final_set_only(self):
        meta = metadata(**{"Final TB?": "A"})
        state = replace(t.ScoreState(), sets=(1, 1), games=(6, 6), points=(8, 7),
                        game_point_number=15, tiebreak_first_server=1)
        self.assertEqual(t.tiebreak_rule(meta, state), (6, 10))
        state = t.advance_score(meta, state, 1)
        self.assertFalse(state.complete)
        state = t.advance_score(meta, state, 1)
        self.assertTrue(state.complete)
        self.assertEqual(t.tiebreak_rule(meta, t.ScoreState()), (6, 7))

    def test_documented_old_rules_not_invented(self):
        final = replace(t.ScoreState(), sets=(1, 1))
        self.assertIsNone(t.tiebreak_rule(metadata(**{"Final TB?": "0"}), final))
        self.assertIsNone(t.tiebreak_rule(metadata(**{"Final TB?": "V"}), t.ScoreState()))
        self.assertEqual(t.tiebreak_rule(metadata(**{"Final TB?": "W"}), final), (8, 7))
        self.assertEqual(t.tiebreak_rule(metadata(**{"Final TB?": "T"}), final), (12, 7))
        for rule in ("N", "S", "", "mystery"):
            self.assertIn("unsupported_or_missing_scoring_rules", t.metadata_errors(metadata(**{"Final TB?": rule})))
            self.assertEqual(t.audit_match(metadata(**{"Final TB?": rule}), [point()])[0], [])

    def test_score_and_server_mismatch_quarantines(self):
        for key in ("Svr", "Pts", "Gm1", "Set2", "Gm#", "TbSet", "Pt"):
            with self.subTest(key=key):
                row = point(**{key: "wrong"})
                self.assertIn("score_or_server_transition_mismatch", t.audit_match(metadata(), [row])[1])

    def test_direct_terminal_and_penalty_winner_audit(self):
        for first, second, winner in (("4*", "", "2"), ("4n", "6n", "1"), ("S", "", "2"), ("P", "", "1"), ("Q", "", "2")):
            row = point(**{"1st": first, "2nd": second, "PtWinner": winner})
            self.assertIn("direct_terminal_winner_mismatch", t.audit_match(metadata(), [row])[1])
        self.assertNotIn("direct_terminal_winner_mismatch", t.audit_match(metadata(), [point(**{"1st": "4f1*", "PtWinner": "2"})])[1])


class AvailabilityTest(unittest.TestCase):
    def test_a1_is_invariant_to_current_and_future_point_fields(self):
        meta, state = metadata(), t.ScoreState()
        base = point()
        expected = t.target_record(meta, base, state, "m", "A1")["features"]
        for changes in ({"1st": "4n", "2nd": "5f29b3*"}, {"1st": "S"},
                        {"1st": "cc0n", "2nd": "garbage", "Notes": "Future injury and score 6-0", "PtWinner": "2"},
                        {"Notes": "retrospective outcome"}, {"Svr": "2", "Pts": "AD-40"}):
            mutated = {**base, **changes}
            self.assertEqual(t.target_record(meta, mutated, state, "m", "A1")["features"], expected)

    def test_a2_depends_only_on_first_fault_not_second_suffix(self):
        meta, state = metadata(), t.ScoreState()
        base = point(**{"1st": "4n", "2nd": "6*"})
        expected = t.target_record(meta, base, state, "m", "A2")["features"]
        for second in ("5n", "4b39f1*", "cc6#", "", "S", "future strings"):
            mutated = {**base, "2nd": second, "Notes": "future", "PtWinner": "2"}
            self.assertEqual(t.target_record(meta, mutated, state, "m", "A2")["features"], expected)
        self.assertEqual(expected["first_fault_direction"], "wide")
        self.assertEqual(expected["first_fault_type"], "net")
        self.assertNotEqual(t.target_record(meta, {**base, "1st": "5d"}, state, "m", "A2")["features"], expected)

    def test_a2_requires_known_fault_not_full_first_serve_rally(self):
        for code in ("4b3n@", "V", "S", "4nfuture"):
            record = t.target_record(metadata(), point(**{"1st": code, "2nd": "6*"}), t.ScoreState(), "m", "A2")
            self.assertFalse(record["eligible"])
            self.assertIsNone(record["features"])

    def test_unknown_first_fault_is_preserved_for_a2(self):
        for code, status in (("0n", "explicit_unknown"), ("n", "omitted")):
            record = t.target_record(metadata(), point(**{"1st": code, "2nd": "6n"}), t.ScoreState(), "m", "A2")
            self.assertTrue(record["eligible"])
            self.assertIsNone(record["features"]["first_fault_direction"])
            self.assertEqual(record["features"]["first_fault_direction_status"], status)

    def test_faults_and_second_aces_rallies_double_faults_eligible(self):
        for second in ("6*", "5f29b3*", "4n"):
            row = point(**{"1st": "4n", "2nd": second})
            for task in ("A1", "A2"):
                self.assertTrue(t.target_record(metadata(), row, t.ScoreState(), "m", task)["eligible"])

    def test_let_exclusion_target_specific(self):
        row = point(**{"1st": "cc4n", "2nd": "6*"})
        self.assertFalse(t.target_record(metadata(), row, t.ScoreState(), "m", "A1")["eligible"])
        self.assertTrue(t.target_record(metadata(), row, t.ScoreState(), "m", "A2")["eligible"])
        row = point(**{"1st": "4n", "2nd": "c6*"})
        self.assertTrue(t.target_record(metadata(), row, t.ScoreState(), "m", "A1")["eligible"])
        self.assertFalse(t.target_record(metadata(), row, t.ScoreState(), "m", "A2")["eligible"])

    def test_notes_quality_never_predictor_and_left_hand_not_geometry(self):
        record = t.target_record(metadata(), point(Notes="Possible reconstructed point"), t.ScoreState(), "m", "A1")
        self.assertTrue(record["quality"]["notes_present"])
        self.assertEqual(record["features"]["returner_hand"], "L")
        self.assertEqual(record["target"], "T")
        for forbidden in ("Notes", "notes_present", "PtWinner", "1st", "2nd", "raw_prefix", "angle", "x", "y", "speed", "rally_length"):
            self.assertNotIn(forbidden, record["features"])

    def test_current_winner_changes_only_subsequent_replayed_state(self):
        meta = metadata()
        row = point(**{"1st": "4b3*"})
        current = t.prediction_features(meta, t.ScoreState(), "m", "A1")
        for winner in (1, 2):
            states, _, _, _ = t.audit_match(meta, [{**row, "PtWinner": str(winner)}])
            self.assertEqual(t.prediction_features(meta, states[0], "m", "A1"), current)
        self.assertNotEqual(t.advance_score(meta, t.ScoreState(), 1), t.advance_score(meta, t.ScoreState(), 2))


class SourceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_schema_fail_closed(self):
        path = self.root / "bad.csv"
        write_csv(path, ["not", "the", "contract"])
        with self.assertRaisesRegex(ValueError, "schema"):
            list(t.read_csv(path, t.POINT_COLUMNS))

    def test_numeric_sort_exact_dedup_conflicting_match_quarantine(self):
        base = point()
        for filename in t.POINT_FILES:
            write_csv(self.root / filename, t.POINT_COLUMNS)
        rows = [{**base, "Pt": str(n)} for n in (10, 2, 1)]
        rows += [rows[1].copy(), {**rows[1], "1st": "5*"}, {**rows[1], "1st": "5*"}]
        write_csv(self.root / t.POINT_FILES[0], t.POINT_COLUMNS, ([r[k] for k in t.POINT_COLUMNS] for r in rows))
        db, provenance = sqlite3.connect(":memory:"), io.StringIO()
        stats, invalid = t.ingest_points(self.root, db, provenance)
        self.assertEqual([r[0] for r in db.execute("SELECT pt FROM points ORDER BY pt")], [1, 2, 10])
        self.assertEqual(stats["raw_rows"], 6)
        self.assertEqual(stats["exact_duplicate_extra_rows"], 2)
        self.assertEqual(stats["conflicting_point_keys"], 1)
        self.assertIn("conflicting_point_key", invalid[("m", base["match_id"])])
        self.assertEqual(len(provenance.getvalue().splitlines()), 3)
        db.close()

    def test_metadata_malformed_conflict_and_rules_are_not_guessed(self):
        for corpus in "mw":
            write_csv(self.root / f"charting-{corpus}-matches.csv", t.MATCH_COLUMNS)
        good = metadata()
        changed = {**good, "Player 2": "Someone else"}
        write_csv(self.root / "charting-m-matches.csv", t.MATCH_COLUMNS,
                  [[r[k] for k in t.MATCH_COLUMNS] for r in (good, good, changed)] + [["broken", "short"]])
        matches, invalid, counts = t.load_metadata(self.root)
        self.assertIn("metadata_conflict", invalid[("m", good["match_id"])])
        self.assertIn("metadata_malformed_csv", invalid[("m", "broken")])
        self.assertEqual(counts["exact_duplicate_extra_rows"], 1)

    def fake_pins(self):
        cache = self.root / "data/research/tennis/source-samples"
        cache.mkdir(parents=True)
        manifest_path = self.root / "docs/research/tennis/source_manifest.json"
        manifest_path.parent.mkdir(parents=True)
        files = []
        for name in sorted(t.REQUIRED_FILES):
            path = cache / name
            path.write_text("synthetic fixture")
            files.append(dict(file=name, sha256=t.digest(path), bytes=path.stat().st_size,
                              source_commit=t.MCP_COMMIT, url=f"https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/{t.MCP_COMMIT}/{t.quote(name)}"))
        manifest = {"sources": [dict(id="mcp", commit=t.MCP_COMMIT, commit_utc="synthetic", license="CC-BY-NC-SA-4.0", repository=t.MCP_REPOSITORY, files=files)]}
        manifest_path.write_text(json.dumps(manifest))
        return cache, manifest_path, manifest

    def test_hash_tampering_rejected_before_processing(self):
        cache, _, _ = self.fake_pins()
        self.assertEqual(t.validate_sources(self.root)["commit"], t.MCP_COMMIT)
        (cache / "README.md").write_text("changed")
        with self.assertRaisesRegex(ValueError, "hash/size mismatch"):
            t.validate_sources(self.root)

    def test_wrong_source_commit_rejected(self):
        _, path, manifest = self.fake_pins()
        manifest["sources"][0]["commit"] = "different"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "pin/license"):
            t.validate_sources(self.root)

    def test_import_is_standard_library_only(self):
        code = "import sys; import experiments.tactical.tennis; assert not ({'numpy','pandas','sklearn','torch'} & set(sys.modules))"
        subprocess.run([sys.executable, "-c", code], check=True)

class EventStreamTest(unittest.TestCase):
    def test_repeated_lets_two_serves_and_offsets(self):
        row = point(**{"1st": "cc4n", "2nd": "c6*"})
        events = t.serve_events(row)
        self.assertEqual([e["raw_token"] for e in events], ["c", "c", "4n", "c", "6*"])
        self.assertEqual([e["serve_period"] for e in events], [1, 1, 1, 2, 2])
        self.assertEqual([e["event_ordinal"] for e in events], [1, 2, 3, 4, 5])
        for event in events:
            self.assertEqual(row[event["source_field"]][event["source_start"]:event["source_end"]], event["raw_token"])
        self.assertEqual(events[0]["direction_status"], "unrecorded_for_let")
        self.assertEqual(events[2]["direction"], "wide")

    def test_unsupported_start_retains_let_offsets(self):
        row = point(**{"1st": " cc3*"})
        events = t.serve_events(row)
        self.assertEqual([e["raw_token"] for e in events], ["c", "c", "3"])
        for event in events:
            self.assertEqual(row["1st"][event["source_start"]:event["source_end"]], event["raw_token"])
        self.assertIsNone(events[-1]["physical_contact"])

    def test_penalty_unobserved_violation_not_fabricated_contacts(self):
        for code in ("P", "Q", "S", "R", "V"):
            events = t.serve_events(point(**{"1st": code}))
            self.assertEqual(len(events), 1)
            self.assertFalse(events[0]["physical_contact"])
            self.assertIsNone(events[0]["striker"])
            self.assertIsNone(events[0]["direction"])


class EndToEndTest(unittest.TestCase):
    setUp = SourceTest.setUp
    fake_pins = SourceTest.fake_pins

    def test_development_only_patterns_and_rows_are_reproducible(self):
        cache, manifest_path, manifest = self.fake_pins()
        metas = [metadata(), metadata(**{"match_id": "20250101-M-Synthetic-F-Gamma-Delta", "Date": "20250101", "Player 1": "Gamma", "Player 2": "Delta"})]
        write_csv(cache / "charting-m-matches.csv", t.MATCH_COLUMNS, ([m[k] for k in t.MATCH_COLUMNS] for m in metas))
        write_csv(cache / "charting-w-matches.csv", t.MATCH_COLUMNS)
        for filename in t.POINT_FILES:
            write_csv(cache / filename, t.POINT_COLUMNS)
        points = [point(metas[0], **{"1st": "4n", "2nd": "5*"}), point(metas[1], **{"1st": "6n", "2nd": "6*"})]
        write_csv(cache / "charting-m-points-2020s.csv", t.POINT_COLUMNS, ([p[k] for k in t.POINT_COLUMNS] for p in points))
        for entry in manifest["sources"][0]["files"]:
            path = cache / entry["file"]
            entry.update(sha256=t.digest(path), bytes=path.stat().st_size)
        manifest_path.write_text(json.dumps(manifest))
        report = t.run(self.root, write_rows=True)
        self.assertEqual(report["targets"]["A1"]["counts"]["eligible_rows"], 2)
        self.assertEqual(report["targets"]["A2"]["counts"]["development_eligible_rows"], 1)
        self.assertEqual(report["development_direction_counts"][0]["counts"], {"wide": 1})
        self.assertEqual(report["development_direction_counts"][1]["counts"], {"body": 1})
        self.assertEqual(report["row_output"]["development_rows_written"], 2)
        rows_path = self.root / "data/tactical/tennis/development_prediction_rows.jsonl.gz"
        with t.gzip.open(rows_path, "rt") as stream:
            rows = [json.loads(line) for line in stream]
        self.assertEqual({row["match_id"] for row in rows}, {metas[0]["match_id"]})
        self.assertEqual(report["targets"]["A2"]["counts"]["target_opportunities_before_quality_exclusions"], 2)
        summary = self.root / "reports/tactical/tennis/summary.json"
        old_summary, old_rows = summary.read_bytes(), rows_path.read_bytes()
        t.run(self.root, write_rows=True)
        self.assertEqual(summary.read_bytes(), old_summary)
        self.assertEqual(rows_path.read_bytes(), old_rows)


if __name__ == "__main__":
    unittest.main()


class EmbargoAndDateQATests(unittest.TestCase):
    def test_known_source_date_contradiction_is_quarantined(self):
        row=metadata(**{"match_id":"20210701-M-Wimbledon-QF-Hubert_Hurkacz-Roger_Federer", "Date":"20210701"})
        self.assertIn("verified_source_date_contradiction", t.metadata_errors(row))

    def test_multiday_match_is_not_next_day_history(self):
        self.assertFalse(t.history_available_before("20100622", "20100623"))
        self.assertFalse(t.history_available_before("20100622", "20100624"))
        self.assertEqual(str(t.assumed_available_date("20100622")), "2010-07-13")
        self.assertFalse(t.history_available_before("20100622", "20100713"))
        self.assertTrue(t.history_available_before("20100622", "20100714"))

    def test_year_end_labels_must_clear_same_embargo(self):
        self.assertFalse(t.history_available_before("20231231", "20240101"))
        self.assertFalse(t.history_available_before("20231211", "20240101"))
        self.assertTrue(t.history_available_before("20231210", "20240101"))
