"""Invented ACB fixtures. Every estimator is a mock; no numerical model is fitted."""
from copy import deepcopy
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.tactical import basketball as parser
from experiments.tactical import basketball_model as model

PROJECT = Path(__file__).resolve().parents[1]


def invented_shot(game, index):
    return {"id": f"invented-{game}-{index}", "gameId": game, "period": 1,
            "startFrame": 10 + index, "startWallClock": 400 + index * 40,
            "startGameClock": 590. - index, "location": [-40.75 + 3. * index, float(index)],
            "shotClock": None if index == 1 else float(3 + index), "three": index % 2 == 1,
            "closestDefDist": 1. + index, "shooterId": 1, "closestDefId": 6,
            "offTeamId": 10, "defTeamId": 20, "outcome": index % 2 == 1,
            "fouled": index == 0, "shotQuality": .999, "assisted": True, "contested": True}


def context(shot):
    result = parser.extract_context(shot)
    result["cohort"] = "development" if shot["gameId"] in model.DEVELOPMENT_GAMES else "forward_qa_only"
    result["raw_quality"] = {key: result["event_geometry_eligible"] for key in model.QUALITY_MASKS}
    result["raw_quality"].update(rotation=-1, rotation_inferred_retrospectively=True)
    return result


class SyntheticFixture:
    def __init__(self, root, mutate=None, mutate_staged=None):
        self.root = Path(root)
        for relative in list(model.CODE_PATHS) + [model.PROTOCOL, "docs/research/TACTICAL_MEASUREMENT_CONTRACT.json"]:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT / relative, target)
        records, contexts, targets, cohorts = [], [], [], []
        for game in model.ALL_GAMES:
            shots = [invented_shot(game, index) for index in range(6)]
            shots[-1]["location"] = None  # retained all-release fallback, never dropped
            if mutate:
                mutate(game, shots)
            for suffix, value in (("dynamic_events.json", {"shots": shots}), ("game_data.json", {"gameId": game}), ("tracking_data.jsonl.gz", {"synthetic": "not tracking; never parsed by model"})):
                relative = f"data/research/SkillCorner_opendata-basketball/data/matches/{game}/{game}_{suffix}"
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
                records.append({"path": relative, "url": f"https://example.invalid/{parser.COMMIT}/{game}/{suffix}",
                                "bytes": path.stat().st_size, "sha256": model.sha256_file(path)})
            contexts.extend(context(shot) for shot in shots)
            if game in model.DEVELOPMENT_GAMES:
                targets.extend(parser.extract_target(shot) for shot in shots)
            cohorts.append({"game_id": game, "recorded_releases": len(shots)})
        if mutate_staged:
            mutate_staged(targets)
        for relative, values in ((model.CONTEXT_PATH, contexts), (model.TARGET_PATH, targets)):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("".join(json.dumps(value) + "\n" for value in values))
        self.contexts = contexts
        for relative, value in ((model.SOURCE_MANIFEST, {"commit": parser.COMMIT, "files": records}),
                                ("data/tactical/basketball/orientation_qa.json", [])):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(value))
        (self.root / "data/tactical/basketball/SKILLCORNER_BASKETBALL_MIT.txt").write_text("Synthetic test notice")
        summary = {"source_commit": parser.COMMIT,
                   "parser_sha256": model.sha256_file(self.root / "experiments/tactical/basketball.py"),
                   "parser_dependencies_sha256": {relative: model.sha256_file(self.root / relative) for relative in ("experiments/tactical/basketball.py", "experiments/tactical/shot_sources.py")},
                   "contract_sha256": model.sha256_file(self.root / "docs/research/TACTICAL_MEASUREMENT_CONTRACT.json"),
                   "cohorts": cohorts}
        path = self.root / model.PARSER_SUMMARY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary))

    def prepare(self):
        return model.prepare(self.root)


class MockEstimator:
    """Deterministic stand-in; does not optimize or call any real estimator."""
    calls = []

    def __init__(self, **kwargs):
        if kwargs != model.LOGISTIC_CONFIG:
            raise AssertionError("Unexpected logistic hyperparameters")

    def fit(self, x, y):
        type(self).calls.append((x.copy(), y.copy()))
        self.coef_ = np.full((1, x.shape[1]), .01, dtype=np.float64)
        self.intercept_ = np.array([0.], dtype=np.float64)
        self.classes_ = np.array([0, 1])
        self.n_iter_ = np.array([1])
        return self


class BasketballModelTests(unittest.TestCase):
    def setUp(self):
        MockEstimator.calls = []
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, **kwargs):
        return SyntheticFixture(self.root, **kwargs)

    def mocked_run(self, fixture=None):
        fixture = fixture or self.fixture()
        prepared = fixture.prepare()
        runner = model.Runner(self.root, prepared["run_dir"])
        self.addCleanup(patch.stopall)
        patch.object(model, "_require_gate", return_value={"synthetic_test": True}).start()
        patch.object(model.gates, "record_operation", return_value=1).start()
        patch.object(model, "LogisticRegression", MockEstimator).start()
        return runner

    def test_prepare_parses_no_target_source_and_never_fits(self):
        fixture = self.fixture()
        original = model._read_json
        def guarded(path):
            if str(path).endswith("_dynamic_events.json") or str(path).endswith("development_targets.jsonl"):
                self.fail("prepare parsed a label-bearing source")
            return original(path)
        with patch.object(model, "_read_json", side_effect=guarded), patch.object(parser, "extract_target", side_effect=AssertionError("No target extraction")), patch.object(model, "LogisticRegression", side_effect=AssertionError("No estimator construction")):
            prepared = fixture.prepare()
        self.assertEqual(prepared["phase"], "prepared")
        manifest = model._read_json(Path(prepared["run_dir"]) / "manifest.json")
        self.assertEqual(len(manifest["freeze"]["sources"]), 30)
        self.assertIn(model.TARGET_PATH, manifest["freeze"]["files"])
        self.assertEqual(manifest["freeze"]["fit_limits"], {"development": 8, "evaluation": 10})
        self.assertTrue(manifest["binding_sha256"])

    def test_default_gate_blocks_before_labels_or_estimator(self):
        prepared = self.fixture().prepare()
        runner = model.Runner(self.root, prepared["run_dir"])
        with patch.object(runner, "_targets", side_effect=AssertionError("must not read targets")), patch.object(model, "LogisticRegression", side_effect=AssertionError("must not construct estimator")):
            with self.assertRaises(model.GateClosed):
                runner.develop()
        self.assertEqual(len(runner._events("phase_started")), 0)

    def test_preprocessing_training_only_and_fixed_fallbacks(self):
        rows = [context(invented_shot(model.DEVELOPMENT_GAMES[0], i)) for i in range(4)]
        rows[0]["features"]["shot_clock_seconds"] = None
        rows[1]["features"]["shot_clock_seconds"] = -1
        rows[2]["features"]["shot_clock_seconds"] = 10
        rows[3]["features"]["shot_clock_seconds"] = 14
        prep = model.Preprocessor.from_training(rows, "D")
        self.assertEqual(prep.shot_clock_median, 12)
        self.assertEqual(prep.feature_names, model.CONTEXT_FEATURES)
        matrix = prep.transform(rows)
        self.assertEqual(matrix.dtype, np.float64)
        for index, name in enumerate(prep.feature_names):
            if name not in model.BINARY_FEATURES:
                self.assertAlmostEqual(matrix[:, index].mean(), 0, places=13)
            else:
                self.assertEqual(prep.means[index], 0)
                self.assertEqual(prep.scales[index], 1)
        self.assertEqual(matrix[0, prep.feature_names.index("bearing_missing")], 1)
        raw = model._raw_matrix(rows, "D", 12)
        self.assertTrue(np.array_equal(raw[:, -1], raw[:, -2] * raw[:, 1]))
        held_out = deepcopy(rows)
        held_out[0]["features"]["shot_clock_seconds"] = 24
        before = prep.to_dict()
        prep.transform(held_out)
        self.assertEqual(before, prep.to_dict())
        for row in rows:
            row["features"]["shot_clock_seconds"] = None
        missing = model.Preprocessor.from_training(rows, "C")
        self.assertEqual(missing.shot_clock_median, 12)
        self.assertTrue(missing.no_valid_training_clock)
        self.assertEqual(missing.scales[missing.feature_names.index("shot_clock_seconds")], 1)

    def test_invalid_geometry_never_imputed_or_used_in_preprocessing(self):
        shot = invented_shot(model.DEVELOPMENT_GAMES[0], 0)
        shot["location"] = None
        with self.assertRaises(model.ProtocolError):
            model.Preprocessor.from_training([context(shot)], "C")

    def test_feature_quality_and_post_outcome_mutations_do_not_change_predictions(self):
        runner = self.mocked_run()
        runner.develop()
        saved = model._read_json(runner.run_dir / f"models/development_{model.DEVELOPMENT_GAMES[1]}.json")
        rows = runner._rows([model.DEVELOPMENT_GAMES[1]])
        before = model.predict(saved, rows)
        changed = deepcopy(rows)
        for row in changed:
            row.update(outcome=0, fouled=False, shotQuality=1, assisted=False, shooter_id=99999)
            row["raw_quality"].update(rotation=1, named_defender_distance_error_ft=999,
                                      rotation_inferred_retrospectively=False)
        self.assertEqual(before, model.predict(saved, changed))
        changed[0]["features"]["shotQuality"] = 1
        with self.assertRaises(model.ProtocolError):
            model.predict(saved, changed)

    def test_development_exact_eight_mocked_fits_and_no_future_label_reads(self):
        runner = self.mocked_run()
        original = model._read_json
        def guarded(path):
            if any(str(path).endswith(f"{game}_dynamic_events.json") for game in model.EVALUATION_GAMES):
                self.fail("Future event source was parsed during development")
            return original(path)
        with patch.object(model, "_read_json", side_effect=guarded):
            report = runner.develop()
        self.assertEqual(len(MockEstimator.calls), 8)
        self.assertEqual(report["fit_budget"]["estimator_fit_calls"], 8)
        self.assertEqual([fold["game_id"] for fold in report["folds"]], list(model.DEVELOPMENT_GAMES[1:]))
        for c, d in zip(MockEstimator.calls[::2], MockEstimator.calls[1::2]):
            self.assertTrue(np.array_equal(c[1], d[1]))
            self.assertTrue(np.array_equal(c[0], d[0][:, :len(model.BASE_FEATURES)]))
        self.assertTrue((self.root / model.ARTIFACT_DIRECTORY / "SELECTION_FREEZE.json").exists())
        self.assertEqual({e["game_id"] for e in runner._events("label_read")}, set(model.DEVELOPMENT_GAMES))
        with self.assertRaises(model.ProtocolError):
            runner.develop()
        self.assertEqual(len(MockEstimator.calls), 8)

    def test_baselines_all_releases_and_pooled_invalid_coordinate_fallback(self):
        runner = self.mocked_run()
        runner.develop()
        saved = model._read_json(runner.run_dir / f"models/development_{model.DEVELOPMENT_GAMES[1]}.json")
        self.assertEqual(saved["A"]["n"], 6)
        self.assertEqual(saved["A"]["makes"], 3)
        self.assertEqual(saved["A"]["probability"], .5)
        self.assertEqual(sum(cell["n"] for cell in saved["B"]["cells"].values()), 5)
        self.assertEqual(saved["B"]["cells"]["0:3"]["probability"], .5)
        for cell in saved["B"]["cells"].values():
            self.assertEqual(cell["probability"], (cell["makes"] + 20 * .5) / (cell["n"] + 20))
        result = model.predict(saved, runner._rows([model.DEVELOPMENT_GAMES[1]]))
        fallback = [row for row in result["rows"] if row["geometry_fallback"]]
        self.assertEqual(len(fallback), 1)
        self.assertEqual(set(fallback[0]["probabilities"].values()), {.5})
        self.assertTrue(all(fallback[0]["fallback"].values()))
        self.assertEqual(fallback[0]["immediate_field_goal_points"]["D"], 1.5)

    def test_single_class_deterministic_fallback_consumes_slots_without_fits(self):
        def mutate(game, shots):
            for shot in shots:
                shot["outcome"] = False
        runner = self.mocked_run(self.fixture(mutate=mutate))
        result = runner.develop()
        self.assertEqual(len(MockEstimator.calls), 0)
        self.assertEqual(result["fit_budget"]["slots_consumed"], 8)
        self.assertEqual(result["fit_budget"]["skipped_single_class_or_empty"], 8)
        saved = model._read_json(runner.run_dir / f"models/development_{model.DEVELOPMENT_GAMES[1]}.json")
        self.assertEqual(saved["C"]["status"], "pooled_fallback_single_class")
        self.assertEqual(saved["A"]["probability"], 1 / 8)

    def test_target_null_unknown_nonbinary_stop_even_fallback_rows(self):
        for bad in (None, "unknown", 2, float("nan")):
            rows = [context(invented_shot(model.DEVELOPMENT_GAMES[0], 0))]
            rows[0]["event_geometry_eligible"] = False
            with self.assertRaises(model.TargetValidityError):
                model._binary_targets(rows, {rows[0]["shot_id"]: bad})
        def mutate(game, shots):
            if game == model.DEVELOPMENT_GAMES[0]:
                shots[-1]["outcome"] = None
        runner = self.mocked_run(self.fixture(mutate=mutate))
        with self.assertRaises(model.TargetValidityError):
            runner.develop()
        self.assertEqual(len(MockEstimator.calls), 0)
        stop = runner._events("target_validity_stop")[0]
        self.assertEqual(len(stop["affected"]), 1)
        self.assertTrue(stop["source_sha256"])

    def test_staged_target_null_stops_without_implicit_source_replacement(self):
        fixture = self.fixture(mutate_staged=lambda rows: rows[0].update(make=None))
        runner = self.mocked_run(fixture)
        with self.assertRaises(model.TargetValidityError):
            runner.develop()
        self.assertEqual(len(MockEstimator.calls), 0)
        self.assertTrue(runner._events("target_validity_stop"))

    def test_future_null_checked_only_after_its_prediction_is_saved(self):
        def mutate(game, shots):
            if game == model.EVALUATION_GAMES[0]:
                shots[-1]["outcome"] = None
        runner = self.mocked_run(self.fixture(mutate=mutate))
        runner.develop()
        with self.assertRaises(model.TargetValidityError):
            runner.evaluate()
        self.assertEqual(len(MockEstimator.calls), 10)
        self.assertEqual(len(runner._events("prediction_saved")), 1)
        self.assertEqual(len(runner._events("scoring_started")), 0)
        first_prediction = runner._events("prediction_saved")[0]
        first_read = next(e for e in runner._events("label_read") if e["game_id"] == model.EVALUATION_GAMES[0])
        self.assertLess(first_prediction["sequence"], first_read["sequence"])

    def test_outer_ten_mocked_fits_strict_timing_and_final_hashes_before_scoring(self):
        runner = self.mocked_run()
        runner.develop()
        original_score = model.score_predictions
        score_calls = []
        def guarded_score(rows, labels, *, require_five_games):
            if require_five_games:
                self.assertEqual(len(runner._verified_predictions()), 5)
                self.assertEqual(len(runner._events("scoring_started")), 1)
                score_calls.append(True)
            return original_score(rows, labels, require_five_games=require_five_games)
        with patch.object(model, "score_predictions", side_effect=guarded_score):
            report = runner.evaluate()
        self.assertEqual(len(MockEstimator.calls), 18)
        self.assertEqual(score_calls, [True])
        self.assertEqual(report["fit_budget"]["estimator_fit_calls"], 10)
        self.assertEqual(len(report["prediction_sha256"]), 5)
        for game in model.EVALUATION_GAMES:
            prediction = next(e for e in runner._events("prediction_saved") if e["game_id"] == game)
            target = next(e for e in runner._events("label_read") if e["game_id"] == game)
            self.assertLess(prediction["sequence"], target["sequence"])
            self.assertEqual(prediction["training_game_ids"], list(model.ALL_GAMES[:model.ALL_GAMES.index(game)]))
            snapshot = model._read_json(runner.run_dir / prediction["path"])
            self.assertFalse(any("make" in row or "outcome" in row for row in snapshot["rows"]))
        primary = report["diagnostics"]["cohorts"]["event_geometry"]
        self.assertEqual(primary["n"], 25)
        self.assertEqual(len(primary["leave_one_game_out"]), 5)
        self.assertEqual(len(primary["candidates"]["D"]["reliability"]), 5)
        self.assertIsNone(report["diagnostics"]["headline_confidence_interval"])
        self.assertEqual(report["designated_model"], "D regardless of result")
        with self.assertRaises(model.ProtocolError):
            runner.evaluate()
        self.assertEqual(len(MockEstimator.calls), 18)

    def test_label_and_score_access_without_prior_prediction_fail(self):
        runner = self.mocked_run()
        runner._load_contexts()
        with self.assertRaises(model.GateClosed):
            runner._targets([model.EVALUATION_GAMES[0]], "development")
        with self.assertRaises(model.GateClosed):
            runner._targets([model.EVALUATION_GAMES[0]], "evaluation")
        with self.assertRaises(model.GateClosed):
            runner._score_outer()
        self.assertEqual(len(runner._events("label_read")), 0)

    def test_prediction_tampering_blocks_label_admission(self):
        runner = self.mocked_run()
        runner._load_contexts()
        path = runner.run_dir / "synthetic_prediction.json"
        digest = model._write_once(path, {"synthetic": True})
        runner.journal.append("prediction_saved", game_id=model.EVALUATION_GAMES[0], path=path.name, sha256=digest)
        path.write_text("tampered")
        with self.assertRaises(model.ProtocolError):
            runner._targets([model.EVALUATION_GAMES[0]], "evaluation")
        self.assertEqual(len(runner._events("label_read")), 0)

    def test_fit_failure_stops_and_no_retry_budget(self):
        runner = self.mocked_run()
        with patch.object(MockEstimator, "fit", side_effect=RuntimeError("synthetic optimizer failure")):
            with self.assertRaises(RuntimeError):
                runner.develop()
        self.assertEqual(runner._budget("development")["slots_consumed"], 1)
        self.assertEqual(len(runner._events("estimator_fit_failed")), 1)
        with self.assertRaises(model.ProtocolError):
            runner.develop()
        self.assertEqual(runner._budget("development")["slots_consumed"], 1)

    def test_fixed_slot_order_rejects_extra_and_out_of_order_fits(self):
        runner = self.mocked_run()
        with self.assertRaises(model.ProtocolError):
            runner._reserve_slot("development", model.DEVELOPMENT_GAMES[1], "D", model.DEVELOPMENT_GAMES[:1])
        with self.assertRaises(model.ProtocolError):
            runner._reserve_slot("development", model.DEVELOPMENT_GAMES[1], "C", model.DEVELOPMENT_GAMES[:2])
        runner.develop()
        with self.assertRaises(model.ProtocolError):
            runner._reserve_slot("development", model.DEVELOPMENT_GAMES[1], "C", model.DEVELOPMENT_GAMES[:1])

    def test_frozen_context_source_code_and_journal_hashes(self):
        prepared = self.fixture().prepare()
        runner = model.Runner(self.root, prepared["run_dir"])
        runner.verify_freeze()
        source = self.root / model._source_event_path(model.EVALUATION_GAMES[-1])
        source.write_text(source.read_text() + " ")
        with self.assertRaises(model.ProtocolError):
            runner.verify_freeze()
        journal = runner.journal.path
        event = json.loads(journal.read_text().splitlines()[0])
        event["fits"] = 999
        journal.write_text(json.dumps(event) + "\n")
        with self.assertRaises(model.ProtocolError):
            runner.journal.read()

    def test_metrics_exact_protocol_clipping_and_unclipped_brier(self):
        y = np.array([0, 1, 0, 1])
        p = np.array([1., 0., .2, .8])
        scores = model._stream_scores(y, p)
        self.assertTrue(np.array_equal(scores["brier"], (p-y)**2))
        self.assertAlmostEqual(scores["log_loss"][0], -math.log(1e-6), places=9)
        summary = model._candidate_summary(y, p)
        self.assertEqual(len(summary["reliability"]), 5)
        self.assertEqual([item["n"] for item in summary["reliability"]], [1, 1, 0, 0, 2])
        self.assertTrue(all(item["low_support"] for item in summary["reliability"]))
        self.assertIsNone(model._candidate_summary(np.array([0, 0]), np.array([.3, .4]))["auroc"])

    def test_output_write_is_exclusive(self):
        path = self.root / "once.json"
        digest = model._write_once(path, {"a": 1})
        self.assertEqual(digest, model.sha256_file(path))
        with self.assertRaises(FileExistsError):
            model._write_once(path, {"a": 2})
        self.assertEqual(model._read_json(path), {"a": 1})


if __name__ == "__main__":
    unittest.main()
