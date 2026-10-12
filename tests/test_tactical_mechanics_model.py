"""Pure formulas and mocked numerical runners. No provider data or real fits.

Every Ridge.fit call here is a mock. Full lifecycle fixtures are fabricated;
source CSV loading is patched out, and approvals exist only inside TemporaryDirectory.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from experiments.tactical import gates as g, mechanics as source, mechanics_model as m


def fake_ridge(x, y, groups, alpha):
    return {"kind": "mean", "value": float(np.average(y, weights=m.athlete_weights(groups))), "selected_alpha": alpha}


def fake_cohort(task):
    spec = m.SPECS[task]
    rows, contexts, labels = [], [], []
    size = spec["rows"]
    for i in range(size):
        group = f"fabricated-participant-{i % spec['groups']}"
        rows.append(SimpleNamespace(group=group))
        row = {"row": i, "group": source.opaque_group(spec["sport"], group),
               "session": f"fabricated-session-{i % 8}"}
        if spec["sport"] == "baseball":
            x = [float(i % 11), float(i % 7), float(i % 5), float(i % 3)]
            row.update(context=x, augmented=x + [float(i % 13), 4., 5., float(i % 19)])
            labels.append(float(40 + i % 29))
        else:
            row.update(period=1 + i % 2, region=source.REGIONS[(i // 2) % 4], target=[4., 2.])
            labels.append({"net": i < 111, "error": None if i < 111 else [float((i % 7) - 3) / 10, float((i % 5) - 2) / 10]})
        contexts.append(row)
    return contexts, m.LabelStore(labels), source.split_plan(rows, spec["sport"]), copy.deepcopy(spec["counts"])


class FormulaTests(unittest.TestCase):
    def test_equal_athlete_training_weights(self):
        weights = m.athlete_weights(["a", "a", "a", "b"])
        np.testing.assert_allclose(weights, [2/3, 2/3, 2/3, 2])
        self.assertAlmostEqual(weights.sum(), 4)
        self.assertAlmostEqual(weights[:3].sum(), weights[3])

    def test_fold_weighted_population_variance_and_zero_exclusion(self):
        x = [[0., 9.], [2., 9.], [4., 9.], [12., 9.]]
        weights = m.athlete_weights(["a", "a", "a", "b"])
        prep = m.weighted_standardizer(x, weights)
        self.assertEqual(prep["mean"], [7., 9.])
        self.assertAlmostEqual(prep["variance"][0], 79/3)
        self.assertEqual(prep["active"], [True, False])
        self.assertEqual(prep["zero_variance_columns"], 1)
        before = copy.deepcopy(prep)
        transformed = m.transform([[1000., -999.]], prep)
        self.assertEqual(transformed.shape, (1, 1))
        self.assertEqual(prep, before)
        self.assertAlmostEqual(transformed[0, 0], (1000 - 7) / math.sqrt(79/3))

    def test_uneven_weighted_decimal_constants_are_exactly_inactive(self):
        examples = [(571, [f"g{i % 82}" for i in range(571)], 65.0),
                    (17, ["a"] * 7 + ["b"] * 10, 1.1)]
        for count, groups, constant in examples:
            matrix = np.column_stack([np.arange(count, dtype=float), np.full(count, constant)])
            prep = m.weighted_standardizer(matrix, m.athlete_weights(groups))
            self.assertEqual(prep["variance"][1], 0.0)
            self.assertEqual(prep["mean"][1], constant)
            self.assertEqual(prep["active"], [True, False])
            self.assertEqual(prep["zero_variance_columns"], 1)
            original = m.transform([[1., constant]], prep)
            changed = m.transform([[1., constant + 1e6]], prep)
            np.testing.assert_array_equal(original, changed)
            self.assertEqual(original.shape, (1, 1))

    def test_macro_rmse_square_root_precedes_group_mean(self):
        scores = m.regression_metrics([0., 0., 0.], [0., 2., 4.], ["a", "a", "b"])
        self.assertAlmostEqual(scores["macro_MAE"], 2.5)
        self.assertAlmostEqual(scores["macro_RMSE"], (math.sqrt(2) + 4) / 2)
        self.assertNotAlmostEqual(scores["macro_RMSE"], math.sqrt((2 + 16)/2))
        self.assertAlmostEqual(scores["row_MAE"], 2)

    def test_alpha_tie_is_larger_alpha_and_requires_exact_grid(self):
        self.assertEqual(m.choose_alpha({.1: 1., 1.: 1. + 5e-13, 10.: 2., 100.: 1. + 9e-13}), 100.)
        self.assertEqual(m.choose_alpha({.1: 1., 1.: 2., 10.: 3., 100.: 1. + 2e-12}), .1)
        with self.assertRaises(ValueError):
            m.choose_alpha({1.: 1.})

    def test_mocked_ridge_exact_estimator_config_and_json_parity(self):
        estimator = Mock()
        estimator.coef_ = np.array([2.])
        estimator.intercept_ = 3.
        estimator.predict.side_effect = lambda x: x[:, 0] * 2 + 3
        with patch.object(m, "Ridge", return_value=estimator) as constructor:
            model = m._ridge_fit([[1., 7.], [3., 7.]], [10., 14.], ["a", "b"], 10.)
        constructor.assert_called_once_with(alpha=10., fit_intercept=True, solver="svd", copy_X=True)
        estimator.fit.assert_called_once()
        np.testing.assert_array_equal(estimator.fit.call_args.kwargs["sample_weight"], [1., 1.])
        clone = json.loads(json.dumps(model))
        np.testing.assert_array_equal(m.predict_regression(model, [[5., -999.]]), m.predict_regression(clone, [[5., 42.]]))
        self.assertEqual(m.predict_regression(clone, [[5., 42.]]).tolist(), [9.])

    def test_nonfinite_and_constant_support_fail_before_fit(self):
        with patch.object(m, "Ridge") as estimator:
            with self.assertRaises(ValueError):
                m._ridge_fit([[1.], [1.]], [2., 3.], ["a", "b"], 1.)
            with self.assertRaises(ValueError):
                m._ridge_fit([[float("nan")], [1.]], [2., 3.], ["a", "b"], 1.)
            estimator.assert_not_called()

    def _small_hurdle(self):
        contexts = [{"period": 1, "region": "deuce wide", "target": [3., 2.]},
                    {"period": 1, "region": "deuce wide", "target": [3., 2.]},
                    {"period": 2, "region": "ad wide", "target": [4., -2.]}]
        labels = [{"net": False, "error": [1., 2.]}, {"net": False, "error": [3., 4.]}, {"net": True, "error": None}]
        return contexts, labels

    def test_hurdle_raw_moments_n_denominator_and_fixed_diagonal(self):
        contexts, labels = self._small_hurdle()
        model = m.hurdle_parameters(contexts, labels, "B0")
        self.assertEqual(model["pooled"]["p_net"], 2/5)
        np.testing.assert_allclose(model["pooled"]["mu"], [2., 3.])
        np.testing.assert_allclose(model["pooled"]["Q"], [[5., 7.], [7., 10.]])
        np.testing.assert_allclose(model["pooled"]["covariance"], [[1.0025, 1.], [1., 1.0025]])
        prediction = m.predict_hurdle(model, contexts)
        self.assertEqual(prediction[0]["mean_bounce"], [5., 5.])
        self.assertEqual(prediction[2]["mean_bounce"], [6., 1.])

    def test_shrinkage_raw_moments_and_algebraic_empty_cell(self):
        contexts, labels = self._small_hurdle()
        model = m.hurdle_parameters(contexts, labels, "B1")
        cell = next(x for x in model["cells"] if x["period"] == 1 and x["region"] == "deuce wide")
        self.assertAlmostEqual(cell["p_net"], (0 + 20 * .4)/22)
        np.testing.assert_allclose(cell["mu"], [2., 3.])
        empty = next(x for x in model["cells"] if x["period"] == 2 and x["region"] == "ad tee")
        for field in ("p_net", "mu", "Q", "covariance"):
            np.testing.assert_allclose(empty[field], model["pooled"][field])
        netonly = next(x for x in model["cells"] if x["period"] == 2 and x["region"] == "ad wide")
        self.assertTrue(netonly["empty_bounce_cell"])
        self.assertFalse(netonly["empty_attempt_cell"])
        self.assertAlmostEqual(netonly["p_net"], 9/21)

    def test_shrinkage_uses_second_moment_not_averaged_covariances(self):
        rows = [{"period": 1, "region": "deuce wide"}, {"period": 2, "region": "ad wide"}]
        labels = [{"net": False, "error": [0., 0.]}, {"net": False, "error": [4., 0.]}]
        model = m.hurdle_parameters(rows, labels, "B1")
        cell = model["cells"][0]
        expected_mu = np.array([40/21, 0.])
        expected_q = np.array([[160/21, 0.], [0., 0.]])
        np.testing.assert_allclose(cell["mu"], expected_mu)
        np.testing.assert_allclose(cell["covariance"], expected_q - np.outer(expected_mu, expected_mu) + .0025*np.eye(2))

    def test_net_nll_never_reads_gaussian_or_fabricates_bounce(self):
        with patch.object(m, "_validate_gaussian", side_effect=AssertionError("net cannot evaluate a Gaussian")):
            loss = m.hurdle_losses([{"net": True, "error": None}], [{"p_net": .25}])
        self.assertAlmostEqual(loss["joint_NLL"][0], -math.log(.25))
        self.assertEqual(loss["location_NLL"], [None])
        self.assertAlmostEqual(loss["net_Brier"][0], .75**2)
        with self.assertRaises(ValueError):
            m.hurdle_losses([{"net": True, "error": [0., 0.]}], [{"p_net": .25}])

    def test_continuous_nll_can_be_negative_and_ellipse_cutoff_is_fixed(self):
        pred = {"p_net": .1, "mu": [0., 0.], "covariance": [[.0025, 0.], [0., .0025]]}
        loss = m.hurdle_losses([{"net": False, "error": [0., 0.]}], [pred])
        expected = -math.log(.9) + math.log(2 * math.pi * .0025)
        self.assertAlmostEqual(loss["joint_NLL"][0], expected)
        self.assertLess(expected, 0)
        self.assertEqual(loss["ellipse90_covered"], [1.])
        self.assertEqual(m.ELLIPSE_CUTOFF, -2 * math.log(.1))
        pred["covariance"] = [[1., 2.], [2., 1.]]
        with self.assertRaises(ValueError):
            m.hurdle_losses([{"net": False, "error": [0., 0.]}], [pred])

    def test_prediction_ignores_ids_targets_speed_outcomes(self):
        contexts, labels = self._small_hurdle()
        model = m.hurdle_parameters(contexts, labels, "B1")
        original = m.predict_hurdle(model, contexts)
        mutated = copy.deepcopy(contexts)
        for row in mutated:
            row.update(group="changed", speed=100000., clear_net=False, let=True, error=[999., 999.], filename="target_999.csv")
        self.assertEqual(original, m.predict_hurdle(model, mutated))
        self.assertEqual(original, m.predict_hurdle(json.loads(json.dumps(model)), contexts))

    def test_bootstrap_exact_pcg64_array_and_whole_group_units(self):
        groups = ["a", "a", "a", "b", "c", "d", "e", "f", "g", "h"]
        difference = [1., 2., 3., 2., 3., 4., 5., 6., 7., 8.]
        actual = m.cluster_bootstrap(difference, groups, 8)
        means = np.array([2., 2., 3., 4., 5., 6., 7., 8.])
        draws = np.random.Generator(np.random.PCG64(20261011)).integers(0, 8, (2000, 8))
        expected = np.quantile(means[draws].mean(axis=1), [.025, .975], method="linear")
        np.testing.assert_allclose(actual["interval95"], expected, rtol=0, atol=0)
        self.assertEqual(actual["difference"], means.mean())
        with self.assertRaises(ValueError):
            m.cluster_bootstrap(difference, groups, 82)

    def test_complete_exact_operation_grids(self):
        baseball = m.operation_schedule("baseball_mechanics")
        self.assertEqual(len(baseball), 175)
        self.assertEqual(sum(x["kind"] == "analytic_mean" for x in baseball.values()), 5)
        self.assertEqual(sum(x["kind"] == "ridge_fit" for x in baseball.values()), 160)
        self.assertEqual(sum(x["kind"] == "ridge_refit" for x in baseball.values()), 10)
        self.assertEqual(len(m.operation_schedule("tennis_execution")), 16)

    def test_frozen_group_membership_is_target_independent_and_disjoint(self):
        for task in m.SPECS:
            contexts, labels, plan, _ = fake_cohort(task)
            m._validate_plan_structure(plan, task)
            changed = copy.deepcopy(plan)
            changed["folds"][0]["test_groups"].append(changed["folds"][0]["training_groups"][0])
            with self.assertRaises(ValueError):
                m._validate_plan_structure(changed, task)
            if task == "baseball_mechanics":
                for fold in plan["folds"]:
                    self.assertEqual(set(fold["inner_assignment"]), set(fold["training_groups"]))

    def test_label_store_refuses_unapproved_fold_index(self):
        store = m.LabelStore([1., 2., 3.])
        with self.assertRaises(PermissionError):
            store.take([2], allowed=[0, 1], purpose="train")
        self.assertEqual(store.accesses, [])

    def test_baseball_outer_outcome_mutation_cannot_change_fold_models(self):
        contexts, labels, plan, _ = fake_cohort("baseball_mechanics")
        runner = m.Runner(Path("/tmp"), "baseball_mechanics")
        fold = plan["folds"][0]
        changed = list(labels._labels)
        for row in contexts:
            if row["group"] in fold["test_groups"]:
                changed[row["row"]] = 1e9
        with patch.object(runner, "_reserve"), patch.object(m, "_ridge_fit", side_effect=fake_ridge):
            first = runner._train_baseball_fold(contexts, labels, fold)
            second = runner._train_baseball_fold(contexts, m.LabelStore(changed), fold)
        self.assertEqual(first, second)
        heldout = {r["row"] for r in contexts if r["group"] in fold["test_groups"]}
        for access in labels.accesses:
            self.assertNotIn("evaluation", access["purpose"])
        self.assertEqual(len(heldout), len(first[1]["row_ids"]))

    def test_tennis_outer_outcome_mutation_cannot_change_fold_models(self):
        contexts, labels, plan, _ = fake_cohort("tennis_execution")
        runner = m.Runner(Path("/tmp"), "tennis_execution")
        fold = plan["folds"][0]
        changed = copy.deepcopy(labels._labels)
        changed = list(changed)
        for row in contexts:
            if row["group"] in fold["test_groups"]:
                changed[row["row"]] = {"net": False, "error": [1e6, -1e6]}
        with patch.object(runner, "_reserve"):
            first = runner._train_tennis_fold(contexts, labels, fold)
            second = runner._train_tennis_fold(contexts, m.LabelStore(changed), fold)
        self.assertEqual(first, second)

    def test_split_plan_rejects_valid_partition_with_changed_hash_order(self):
        for task in m.SPECS:
            _, _, plan, _ = fake_cohort(task)
            changed = copy.deepcopy(plan)
            changed["folds"][0]["training_groups"].reverse()
            with self.assertRaises(ValueError):
                m._validate_plan_structure(changed, task)
        _, _, plan, _ = fake_cohort("baseball_mechanics")
        inner = plan["folds"][0]["inner_assignment"]
        first = next(iter(inner))
        inner[first] = (inner[first] + 1) % 4
        with self.assertRaises(ValueError):
            m._validate_plan_structure(plan, "baseball_mechanics")

    def test_every_declared_cohort_count_is_fail_closed(self):
        for task, spec in m.SPECS.items():
            m._check_counts(spec["counts"], task)
            for key in spec["counts"]:
                changed = copy.deepcopy(spec["counts"])
                changed[key] += 1
                with self.assertRaises(ValueError):
                    m._check_counts(changed, task)

    def test_mocked_parser_conversion_has_exact_feature_allowlist(self):
        # Synthetic adapter outputs only; read_csv and all gate/source I/O are mocks.
        task = "baseball_mechanics"
        spec = m.SPECS[task]
        records = []
        for i in range(571):
            records.append(source.Swing(f"fabricated-participant-{i % 82}", str(i % 82),
                {**{field: float(j) for j, field in enumerate(m.BODY)}, "bat_velocity_alias": 1e12},
                {**{field: float(j + 10) for j, field in enumerate(m.CONTEXT)}, "exit_velo_mph": 1e12},
                {"exit_velocity": float(i), "marker_contact_speed": 1e12}))
        plan = source.split_plan(records, "baseball")
        calls = []
        paths = {key: Path("synthetic.csv") for key in ("baseball_hitting/data/metadata.csv", "baseball_hitting/data/poi/poi_metrics.csv", "baseball_hitting/data/poi/hittrax.csv")}
        with patch.object(g, "require_stage", side_effect=lambda *_: calls.append("gate")), \
             patch.object(source, "validate_sources", return_value=(paths, {})), \
             patch.object(source, "read_csv", side_effect=lambda *a, **kw: calls.append("csv") or []), \
             patch.object(source, "adapt_baseball", return_value=(records, spec["counts"])), \
             patch.object(m, "_read", return_value=plan):
            contexts, labels, _, _ = m._load_cohort(Path("/tmp"), task, "development")
        self.assertEqual(calls[0], "gate")
        self.assertEqual(calls.count("csv"), 3)
        self.assertEqual(contexts[0]["context"], [10., 11., 12., 13.])
        self.assertEqual(contexts[0]["augmented"], [10., 11., 12., 13., 0., 1., 2., 3.])
        self.assertNotIn("bat_velocity_alias", json.dumps(contexts))
        self.assertNotIn("fabricated-participant", json.dumps(contexts))
        self.assertEqual(labels._labels[0], 0.)

    def test_tennis_training_support_failure_precedes_parameter_fit(self):
        contexts, labels, plan, _ = fake_cohort("tennis_execution")
        runner = m.Runner(Path("/tmp"), "tennis_execution")
        allnet = m.LabelStore([{"net": True, "error": None} for _ in contexts])
        with patch.object(runner, "_reserve") as reserve, patch.object(m, "hurdle_parameters") as fitted:
            with self.assertRaises(ValueError):
                runner._train_tennis_fold(contexts, allnet, plan["folds"][0])
            reserve.assert_not_called(); fitted.assert_not_called()


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for path, text in [("docs/protocol.md", "SYNTHETIC ONLY"), ("docs/review.json", '{"synthetic":true}'),
                           ("experiments/tactical/gates.py", "# synthetic fixture"),
                           ("experiments/tactical/model.py", "# synthetic fixture"), ("data/source.txt", "OPAQUE MOCK")]:
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text)

    def tearDown(self):
        self.temp.cleanup()

    def binding(self, task):
        return g.prepare_binding(self.root, task, "docs/protocol.md",
                                 ["experiments/tactical/gates.py", "experiments/tactical/model.py"], ["data/source.txt"],
                                 metadata={"synthetic_fixture_only": True}, evaluation_cohort=(task,))

    def approve(self, task, binding, stage="development"):
        path = self.root / g.APPROVAL_PATH
        value = json.loads(path.read_text()) if path.exists() else {"schema_version": 1, "tasks": {}}
        review = {"schema_version": 1, "review_type": "tactical_numerical_binding_review", "status": "cleared",
                  "tasks": {task: {"binding_sha256": binding["binding_sha256"], "cleared_stages": ["development", "evaluation"]}},
                  "synthetic_fixture_only": True}
        (self.root / "docs/review.json").write_text(json.dumps(review))
        record = {"status": "approved", "binding_sha256": binding["binding_sha256"],
                  "review_manifest_path": "docs/review.json", "review_manifest_sha256": g.digest_file(self.root / "docs/review.json"),
                  "approved_at_utc": "2026-10-11T00:00:00+00:00"}
        if stage == "evaluation":
            selection = f"artifacts/tactical/{task}/SELECTION_FREEZE.json"
            global_value = {"schema_version": 1, "tasks": {task: {"binding_sha256": binding["binding_sha256"],
                           "selection_path": selection, "selection_sha256": g.digest_file(self.root / selection)}}}
            (self.root / g.GLOBAL_FREEZE_PATH).write_text(json.dumps(global_value))
            record["global_freeze_sha256"] = g.digest_file(self.root / g.GLOBAL_FREEZE_PATH)
        value["tasks"].setdefault(task, {})[stage] = record
        path.write_text(json.dumps(value))

    def run_development(self, task):
        binding = self.binding(task)
        self.approve(task, binding)
        with patch.object(m, "_load_cohort", side_effect=lambda *_: fake_cohort(task)), \
             patch.object(m, "_ridge_fit", side_effect=fake_ridge) as fitted, \
             patch.object(m, "score_baseball", side_effect=AssertionError("No outer score in development")), \
             patch.object(m, "score_tennis", side_effect=AssertionError("No outer score in development")), \
             patch.object(m, "Ridge", side_effect=AssertionError("No real estimator may run")):
            result = m.develop(self.root, task)
        self.assertEqual(fitted.call_count, 170 if task == "baseball_mechanics" else 0)
        return binding, result

    def test_gate_denial_precedes_any_csv_or_model_access(self):
        with patch.object(source, "read_csv", side_effect=AssertionError("No CSV allowed")) as reader, \
             patch.object(m, "_ridge_fit", side_effect=AssertionError("No fit allowed")) as fitted:
            for task in m.SPECS:
                for stage in ("development", "evaluation"):
                    with self.assertRaises(PermissionError):
                        m._load_cohort(self.root, task, stage)
                with self.assertRaises(PermissionError):
                    m.develop(self.root, task)
                with self.assertRaises(PermissionError):
                    m.evaluate(self.root, task)
            reader.assert_not_called(); fitted.assert_not_called()

    def test_failed_reserved_stage_cannot_retry(self):
        task = "tennis_execution"
        self.approve(task, self.binding(task))
        with patch.object(m, "_load_cohort", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                m.develop(self.root, task)
        with patch.object(m, "_load_cohort") as load:
            with self.assertRaises(FileExistsError):
                m.develop(self.root, task)
            load.assert_not_called()

    def test_fixed_fit_cap_unknown_and_duplicate_slots(self):
        task = "tennis_execution"
        self.approve(task, self.binding(task))
        runner = m.Runner(self.root, task)
        with self.assertRaises(PermissionError):
            runner._reserve("outer0/B0", {"shrinkage": 30})
        for slot in runner.schedule:
            runner._reserve(slot)
        with self.assertRaises(PermissionError):
            runner._reserve("outer0/B0")
        with self.assertRaises(PermissionError):
            runner._reserve("outer0/B2")
        with self.assertRaises(PermissionError):
            g.record_operation(self.root, task, "development", "extra", {}, 16)
        ledger = self.root / f"artifacts/tactical/{task}/development_operations.jsonl"
        self.assertEqual(len(ledger.read_text().splitlines()), 16)

    def test_source_mutation_blocks_stage_before_loader(self):
        task = "tennis_execution"
        self.approve(task, self.binding(task))
        (self.root / "data/source.txt").write_text("CHANGED")
        with patch.object(m, "_load_cohort") as loader:
            with self.assertRaises(PermissionError):
                m.develop(self.root, task)
            loader.assert_not_called()

    def test_full_mocked_baseball_development_freezes_all_predictions_no_scores(self):
        task = "baseball_mechanics"
        binding, result = self.run_development(task)
        self.assertFalse(result["outer_scores_computed"])
        freeze = m.Runner(self.root, task)._verified_freeze(binding)
        self.assertEqual(len(freeze["outer_folds"]), 5)
        self.assertEqual(freeze["operation_count"], 175)
        self.assertEqual(freeze["fit_count"], 170)
        details = json.loads((self.root / freeze["details"]["path"]).read_text())
        inner = [record for fold in details["fold_details"] for block in ("context", "augmented")
                 for record in fold["details"][block]["saved_inner_models_and_predictions"]]
        self.assertEqual(len(inner), 160)
        self.assertTrue(all(len(r["validation_row_ids"]) == len(r["predictions"]) for r in inner))
        self.assertFalse((self.root / f"artifacts/tactical/{task}/evaluation_report.json").exists())
        with patch.object(m, "_load_cohort") as loader:
            with self.assertRaises(PermissionError):
                m.evaluate(self.root, task)
            loader.assert_not_called()
        with patch.object(m, "_load_cohort") as loader:
            with self.assertRaises(FileExistsError):
                m.develop(self.root, task)
            loader.assert_not_called()

    def test_full_tennis_lifecycle_private_participant_outputs_and_parity(self):
        task = "tennis_execution"
        binding, result = self.run_development(task)
        self.assertEqual(result["fit_count"], 16)
        self.approve(task, binding, "evaluation")
        with patch.object(m, "_load_cohort", side_effect=lambda *_: fake_cohort(task)):
            final = m.evaluate(self.root, task)
        report = final["summary"]
        self.assertEqual(report["rows"], 548)
        self.assertEqual(report["observed_bounces"], 437)
        self.assertEqual(report["net_censored"], 111)
        self.assertNotIn("players_in_fixed_fold_order_not_ranked", report)
        self.assertNotIn("private_player_label", json.dumps(report))
        self.assertNotIn("fabricated-participant", json.dumps(report))
        self.assertEqual(report["primary"]["draw_shape"], [2000, 8])
        self.assertFalse((self.root / "reports").exists())
        private = json.loads((self.root / f"artifacts/tactical/{task}/private_evaluation_details.json").read_text())
        self.assertEqual(len(private["players_in_fixed_fold_order_not_ranked"]), 8)
        self.assertTrue(all(x["remaining_players"] == 7 for x in private["session_exclusion"]))

    def test_complete_mocked_baseball_evaluation_exact_denominators(self):
        task = "baseball_mechanics"
        binding, _ = self.run_development(task)
        self.approve(task, binding, "evaluation")
        with patch.object(m, "_load_cohort", side_effect=lambda *_: fake_cohort(task)):
            report = m.evaluate(self.root, task)["summary"]
        self.assertEqual(report["rows"], 571)
        self.assertEqual(report["athletes"], 82)
        self.assertEqual(report["primary"]["draw_shape"], [2000, 82])
        self.assertEqual(len(report["outer_folds"]), 5)
        self.assertEqual(report["primary"]["difference"], 0.)
        self.assertFalse(report["practical_threshold_met"])

    def test_saved_prediction_mutation_blocks_before_label_loader(self):
        task = "tennis_execution"
        binding, _ = self.run_development(task)
        self.approve(task, binding, "evaluation")
        prediction = self.root / f"artifacts/tactical/{task}/predictions/outer0.json"
        prediction.write_text(prediction.read_text() + " ")
        with patch.object(m, "_load_cohort") as loader:
            with self.assertRaises(PermissionError):
                m.evaluate(self.root, task)
            loader.assert_not_called()

    def test_saved_model_mutation_blocks_before_label_loader(self):
        task = "tennis_execution"
        binding, _ = self.run_development(task)
        self.approve(task, binding, "evaluation")
        path = self.root / f"artifacts/tactical/{task}/models/outer0.json"
        model = json.loads(path.read_text()); model["B0"]["pooled"]["mu"][0] += 1
        path.write_text(json.dumps(model))
        with patch.object(m, "_load_cohort") as loader:
            with self.assertRaises(PermissionError):
                m.evaluate(self.root, task)
            loader.assert_not_called()

    def test_prepare_reads_no_target_csv_and_binds_existing_private_plan(self):
        task = "tennis_execution"
        spec = m.SPECS[task]
        for path in (*m.CODE_PATHS, *m.REVIEW_PATHS, "docs/research/tennis/source_manifest.json", f"docs/tactical/{spec['protocol']}"):
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("synthetic fixture")
        plan_path = self.root / "data/tactical/mechanics/tennis_split_manifest.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(fake_cohort(task)[2]))
        source_path = self.root / "data/source.txt"
        notice = {"manifest_sha256": g.digest_file(self.root / "docs/research/tennis/source_manifest.json"), "files": []}
        summary = {"population": {"counts": spec["counts"]},
                   "protocol": {"sha256": g.digest_file(self.root / f"docs/tactical/{spec['protocol']}")},
                   "split_description": {"private_membership_sha256": g.digest_file(plan_path)},
                   "source": {**notice, "adapter_sha256": g.digest_file(self.root / "experiments/tactical/mechanics.py")}}
        summary_path = self.root / "reports/tactical/mechanics/tennis_summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary))
        before = plan_path.read_bytes()
        with patch.object(source, "validate_sources", return_value=({"data/serves.csv": source_path}, notice)), \
             patch.object(source, "BYU_HASHES", {"data/serves.csv": g.digest_file(source_path)}), \
             patch.object(source, "read_csv", side_effect=AssertionError("No target CSV in preparation")) as reader:
            binding = m.prepare(self.root, task)
            self.assertEqual(binding, m.prepare(self.root, task))
        reader.assert_not_called()
        self.assertEqual(before, plan_path.read_bytes())
        self.assertIn("data/tactical/mechanics/tennis_split_manifest.json", binding["data"])
        self.assertIn("reports/tactical/mechanics/tennis_summary.json", binding["data"])
        self.assertFalse((self.root / g.APPROVAL_PATH).exists())


if __name__ == "__main__":
    unittest.main()
