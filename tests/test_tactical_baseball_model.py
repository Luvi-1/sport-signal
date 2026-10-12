"""Invented rows and mocked optimizers only. Never fit a real sports estimator."""
from contextlib import contextmanager
from copy import deepcopy
import csv
import gzip
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning

from experiments.tactical import baseball_model as model
from experiments.tactical import gates

PROJECT = Path(__file__).resolve().parents[1]
GAMES = {"initial": "AAA202306010", "selection": "BBB202406010", "calibration": "CCC202407020",
         "boundary_exclusion": "BOS202406260", "test": "DDD202506010"}


def invented_row(gid, index, *, role="initial"):
    symbols = "BSFBCX"
    history = list(symbols[:index - 1])
    symbol = symbols[index - 1]
    f = dict(zip(model.parser.FEATURE_FIELDS, (1, 0, 1, int(role == "selection"), False, False, False, 0, 0, 0,
        min(index // 2, 3), min(index // 3, 2), "batter", "pitcher", "L", "R", "roster", index,
        history[-1] if history else "START", history[-3:])))
    target = model.parser.classify_target(symbol)
    date = gid[3:11]
    return {"lineage": {"gid": gid, "pa": 1, "event_date": date, "event_date_min": date,
                       "event_date_max": date, "source_record_date": date, "event_date_status": "raw_record_date"},
            "features": f, "target": target, "eligibility": {"swing": True, "contact_given_swing": target["swing"] == 1}, "qa_exclusions": []}


class Fixture:
    def __init__(self, root, mutate=None):
        self.root = Path(root)
        for relative in (*model.CODE_PATHS, model.PROTOCOL):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT / relative, path)
        self.spans = {}
        self.rows = {}
        self.pins = {}
        self.expected = {}
        for year in (2023, 2024, 2025):
            games = [(role, gid) for role, gid in GAMES.items() if gid[3:7] == str(year)]
            rows = []
            for role, gid in games:
                for i in range(1, 7):
                    row = invented_row(gid, i, role=role)
                    if mutate:
                        mutate(role, row)
                    rows.append(row)
            self.rows[year] = rows
            path = self.root / f"data/tactical/baseball/{year}_pitches.jsonl.gz"
            path.parent.mkdir(parents=True, exist_ok=True)
            with model._gzip_once(path) as stream:
                for row in rows:
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
            self.pins[str(path.relative_to(self.root))] = gates.digest_file(path)
            self.expected[year] = (len(rows), len(rows), sum(row["eligibility"]["contact_given_swing"] for row in rows))
            raw = []
            dates = []
            for role, gid in games:
                date = gid[3:11]
                raw += [f"id,{gid}\n", f"info,date,{date[:4]}/{date[4:6]}/{date[6:]}\n",
                        'play,1,0,batter,00,DO_NOT_PARSE_TARGET,POISON\n']
                dates.append([gid, date, "regular", "DO_NOT_MATERIALIZE"])
                if role == "boundary_exclusion":
                    raw.append('com,"suspended,20240826,source boundary"\n')
                    dates.append([gid, "20240826", "regular", "DO_NOT_MATERIALIZE"])
            directory = self.root / "data/tactical/baseball/sources"
            directory.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(directory / f"{year}eve.zip", "w") as archive:
                archive.writestr(f"{year}TEST.EVA", "".join(raw))
            csv_text = io.StringIO()
            writer = csv.writer(csv_text)
            writer.writerow(["gid", "date", "gametype", "target"])
            writer.writerows(dates)
            with zipfile.ZipFile(directory / f"{year}plays.zip", "w") as archive:
                archive.writestr(f"{year}plays.csv", csv_text.getvalue())
            for kind in ("eve", "plays"):
                path = directory / f"{year}{kind}.zip"
                self.pins[str(path.relative_to(self.root))] = gates.digest_file(path)

    def prepare(self):
        original_binding = gates.prepare_binding
        def synthetic_binding(*args, **kwargs):
            return original_binding(*args, **kwargs, evaluation_cohort=("baseball",))
        with patch.object(gates, "prepare_binding", side_effect=synthetic_binding), patch.object(model, "_source_contract", return_value=self.pins), \
             patch.object(model, "EXPECTED_ROWS", self.expected), \
             patch.object(model, "EXPECTED_GAMES", {role: 1 for role in GAMES}):
            return model.prepare(self.root)

    def approve(self, evaluation=False):
        binding = gates.verify_binding(self.root, "baseball")
        review = self.root / "review.json"
        review.write_text(json.dumps({"schema_version": 1, "review_type": "tactical_numerical_binding_review",
            "status": "cleared", "synthetic": True, "tasks": {"baseball": {"binding_sha256": binding["binding_sha256"],
            "cleared_stages": ["development", "evaluation"]}}}))
        approval = {"status": "approved", "binding_sha256": binding["binding_sha256"],
                    "review_manifest_path": "review.json", "review_manifest_sha256": gates.digest_file(review),
                    "approved_at_utc": "2026-10-11T10:00:00+00:00"}
        value = {"schema_version": 1, "tasks": {"baseball": {"development": approval}}}
        if evaluation:
            freeze = {"schema_version": 1, "tasks": {"baseball": {"binding_sha256": binding["binding_sha256"],
                "selection_path": model.BASE + "/SELECTION_FREEZE.json",
                "selection_sha256": gates.digest_file(model._path(self.root, "SELECTION_FREEZE.json"))}}}
            global_path = self.root / gates.GLOBAL_FREEZE_PATH
            global_path.write_text(json.dumps(freeze))
            value["tasks"]["baseball"]["evaluation"] = {**approval, "global_freeze_sha256": gates.digest_file(global_path)}
        (self.root / gates.APPROVAL_PATH).write_text(json.dumps(value))


class MockEstimator:
    calls = []
    root = None

    def __init__(self, **kwargs):
        if set(kwargs) != set(model.LOGISTIC_CONFIG) | {"C"} or kwargs["C"] not in model.CS:
            raise AssertionError("Unexpected estimator configuration")
        for key, expected in model.LOGISTIC_CONFIG.items():
            if kwargs[key] != expected:
                raise AssertionError("Altered fixed estimator configuration")
        self.c = kwargs["C"]

    def fit(self, x, y):
        records = [json.loads(line) for line in model._path(self.root, "development_operations.jsonl").read_text().splitlines()]
        if not records or records[-1]["kind"] not in ("initial", "refit"):
            raise AssertionError("Estimator attempted before durable reservation")
        type(self).calls.append((x.copy(), y.copy(), records[-1]["operation_id"]))
        self.coef_ = np.full((1, x.shape[1]), self.c * .001)
        self.intercept_ = np.array([-.1])
        self.classes_ = np.array([0, 1])
        self.n_iter_ = np.array([1])
        return self

    def predict_proba(self, x):
        p = expit(x @ self.coef_[0] + self.intercept_[0])
        return np.column_stack((1 - p, p))


def mocked_minimize(fun, start, *, args, method, jac, bounds, options):
    assert method == "L-BFGS-B" and jac is True
    assert bounds == ((0., 10.), (-10., 10.))
    assert options == {"maxiter": 200, "ftol": 1e-12}
    np.testing.assert_equal(start, [1., 0.])
    theta = np.array([.95, .1])
    value, gradient = fun(theta, *args)
    assert gradient.shape == (2,)
    return SimpleNamespace(x=theta, fun=value, success=True, nit=1, message="Synthetic optimizer; no actual minimization")


@contextmanager
def no_resource_changes(root, phase):
    yield
    model._write_once(model._path(root, f"resources_{phase}.json"), {"wall_seconds": 0.01, "synthetic": True})


class BaseballModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        MockEstimator.calls = []
        MockEstimator.root = self.root

    def fixture(self, **kwargs):
        return Fixture(self.root, **kwargs)

    @contextmanager
    def mocked(self):
        with patch.object(model, "LogisticRegression", MockEstimator), patch.object(model, "minimize", side_effect=mocked_minimize) as optimizer, \
             patch.object(model, "_resources", no_resource_changes):
            yield optimizer

    def development(self):
        fixture = self.fixture()
        fixture.prepare()
        fixture.approve()
        with self.mocked():
            model.develop(self.root)
        return fixture

    def test_projection_never_decodes_unrequested_target_value(self):
        original = model.json.loads
        def guarded(value, *args, **kwargs):
            if "LABEL_POISON" in value:
                self.fail("Target namespace reached JSON decoder")
            return original(value, *args, **kwargs)
        line = '{"target":{"LABEL_POISON":"escaped \\\" brace } comma ,"},"features":{"x":3},"lineage":{"gid":"x"}}'
        with patch.object(model.json, "loads", side_effect=guarded):
            self.assertEqual(model._project(line, ("features", "lineage")), {"features": {"x": 3}, "lineage": {"gid": "x"}})

    def test_prepare_projects_no_labels_and_freezes_game_pa_pitch_membership(self):
        fixture = self.fixture()
        original = model._project
        def projected(line, fields):
            self.assertNotIn("target", fields)
            return original(line, fields)
        with patch.object(model, "_project", side_effect=projected), patch.object(model, "LogisticRegression") as estimator:
            binding = fixture.prepare()
        estimator.assert_not_called()
        prepared = model._prepared(self.root)
        self.assertFalse(prepared["labels_decoded"])
        boundary = [row for row in prepared["game_membership"] if row["role"] == "boundary_exclusion"]
        self.assertEqual(boundary[0]["date_min"], "20240626")
        self.assertEqual(boundary[0]["date_max"], "20240826")
        self.assertIn(model.BASE + "/prepared/membership.jsonl.gz", binding["data"])
        with gzip.open(model._path(self.root, "prepared/membership.jsonl.gz"), "rt") as stream:
            membership = [json.loads(line) for line in stream]
        self.assertEqual(len(membership), 30)
        self.assertTrue(all(set(("id", "gid", "pa", "delivery_index", "role")).issubset(row) for row in membership))

    def test_unapproved_public_and_private_entries_stop_before_reader_or_fit(self):
        fixture = self.fixture()
        fixture.prepare()
        with patch.object(model, "_project") as reader, patch.object(model, "LogisticRegression") as estimator:
            for phase in (model.develop, model.calibrate, model.predict, model.evaluate):
                with self.assertRaises(PermissionError):
                    phase(self.root)
            cohort = model._load_cohort(self.root, ("test",), "swing")
            with self.assertRaises(PermissionError):
                model._labels(self.root, cohort, "develop")
            with self.assertRaises(PermissionError):
                model._fit(self.root, cohort, np.zeros(6), "initial", "constant", {"name": "constant", "family": "constant"})
        reader.assert_not_called()
        estimator.assert_not_called()

    def test_guard_checks_full_holdout_bytes_before_development(self):
        fixture = self.fixture()
        fixture.prepare()
        fixture.approve()
        with (self.root / "data/tactical/baseball/2025_pitches.jsonl.gz").open("ab") as stream:
            stream.write(b"changed")
        with patch.object(model, "_labels") as reader:
            with self.assertRaisesRegex(PermissionError, "Bound input changed"):
                model.develop(self.root)
        reader.assert_not_called()

    def test_prefix_features_ignore_current_outcome_future_suffix_actor_and_audit_ids(self):
        row = invented_row(GAMES["initial"], 4)
        before = model._features(row["features"])
        row["target"] = {"swing": 999, "contact_given_swing": -8, "symbol": "UNKNOWN"}
        row["lineage"]["terminal_event"] = "future"
        row["features"]["batter"] = "future_player"
        row["features"]["pitcher"] = "another_player"
        row["features"]["visitor_score"] = 999
        row["features"]["home_score"] = 999
        self.assertEqual(before, model._features(row["features"]))
        self.assertEqual(before[-3:], ("F", "S", "B"))
        self.assertEqual(model._features(invented_row(GAMES["initial"], 1)["features"])[-3:], ("START",) * 3)

    def test_unknown_hand_or_invalid_count_never_imputed(self):
        row = invented_row(GAMES["initial"], 1)
        for key, value in (("balls", 4), ("batter_hand", None), ("previous_pitch_outcome", "X")):
            altered = deepcopy(row["features"])
            altered[key] = value
            with self.assertRaises(model.ProtocolError):
                model._features(altered)

    def test_future_outcome_mutation_leaves_prepared_contexts_identical(self):
        baseline = self.fixture()
        baseline.prepare()
        first = {role: gates.digest_file(model._path(self.root, f"prepared/{role}.jsonl.gz")) for role in model.ROLES}
        with tempfile.TemporaryDirectory() as other:
            def mutate(role, row):
                if role in ("calibration", "test"):
                    row["target"] = {"unreadable_label": "NEVER DECODE"}
            second = Fixture(Path(other), mutate=mutate)
            second.prepare()
            for role, expected in first.items():
                self.assertEqual(gates.digest_file(model._path(Path(other), f"prepared/{role}.jsonl.gz")), expected)

    def test_exact_candidate_grid_ties_and_fallback(self):
        self.assertEqual(len(model.candidates()), 9)
        self.assertEqual(len(model.planned_operations()), 38)
        self.assertEqual(len(set(model.planned_operations())), 38)
        records = [{"config": c, "status": "fitted", "log_loss": .5 + (1e-7 if c.get("C") == .03 else 0)} for c in model.candidates()]
        self.assertEqual(model._select(records, "context_logistic")["C"], .03)
        for record in records:
            if record["config"]["family"] == "context_logistic":
                record["status"] = "failed"
        fallback = model._select(records, "context_logistic")
        self.assertEqual(fallback["family"], "context_table")
        self.assertFalse(fallback["comparison_available"])
        with self.assertRaises(model.ProtocolError):
            model._select(records[:-1], "sequence_logistic")

    def test_wrong_private_fit_role_or_configuration_or_labels_rejected(self):
        fixture = self.fixture()
        fixture.prepare()
        fixture.approve()
        initial = model._load_cohort(self.root, ("initial",), "swing")
        selection = model._load_cohort(self.root, ("selection",), "swing")
        initial_y = model._labels(self.root, initial, "develop")
        selection_y = model._labels(self.root, selection, "develop")
        config = model.candidates()[0]
        with patch.object(gates, "record_operation") as reserve:
            with self.assertRaises(model.ProtocolError):
                model._fit(self.root, selection, selection_y, "initial", "constant", config)
            with self.assertRaises(PermissionError):
                model._fit(self.root, initial, selection_y, "initial", "constant", config)
            with self.assertRaises(PermissionError):
                model._fit(self.root, initial, initial_y, "initial", "context_logistic_C0.03", {"name": "context_logistic_C0.03", "family": "context_logistic", "C": .04})
        reserve.assert_not_called()

    def test_tables_have_beta_one_prior_exact_hierarchical_smoothing_and_unseen_fallback(self):
        values = np.array([model._features(invented_row(GAMES["initial"], i)["features"]) for i in (1, 2, 3)], dtype=object)
        y = np.array([0, 1, 1])
        state = model._table(values, y, "history_table")
        self.assertAlmostEqual(state["constant"], 3 / 5)
        key = "0-0|LR"
        self.assertAlmostEqual(state["contexts"][key], 60 / 101)
        self.assertAlmostEqual(state["history"][key + "|START"], 100 * state["contexts"][key] / 101)
        fitted = {"status": "fitted", "config": {"family": "history_table"}, "state": state}
        altered = values[[0]].copy()
        altered[0, 9] = "UNKNOWN"
        self.assertAlmostEqual(model._predict(fitted, altered)[0], state["contexts"][key])
        altered[0, 1] = "RR"
        self.assertAlmostEqual(model._predict(fitted, altered)[0], .6)

    def test_mocked_development_counts_train_only_encoding_and_immutable_persistence(self):
        fixture = self.fixture()
        fixture.prepare()
        fixture.approve()
        original = model._project
        decoded = []
        def reader(line, fields):
            if "target" in fields:
                self.assertNotIn(GAMES["calibration"], line)
                self.assertNotIn(GAMES["test"], line)
                self.assertNotIn(GAMES["boundary_exclusion"], line)
                decoded.append(line)
            return original(line, fields)
        with self.mocked(), patch.object(model, "_project", side_effect=reader):
            model.develop(self.root)
        self.assertTrue(decoded)
        journal = [json.loads(line) for line in model._path(self.root, "development_operations.jsonl").read_text().splitlines()]
        self.assertEqual([row["operation_id"] for row in journal], model.planned_operations()[:28])
        self.assertEqual(len(MockEstimator.calls), 16)
        candidate = model._read_json(model._path(self.root, "candidates/swing/context_logistic_C0.03.json"))
        self.assertEqual(candidate["state"]["categories"][3], ["0"])
        self.assertEqual(candidate["inference_parity_max_absolute_error"], 0)
        self.assertFalse(any(cell["display_allowed"] for cell in candidate["support"].values()))
        selected = model._selected(self.root)
        self.assertEqual(selected["candidates"]["swing"][3]["unseen_categories"]["outs"]["unseen"], 6)
        with self.mocked(), patch.object(model, "_labels") as reader:
            with self.assertRaises(FileExistsError):
                model.develop(self.root)
        reader.assert_not_called()

    def test_calibration_reader_waits_for_all_refits(self):
        fixture = self.fixture()
        fixture.prepare()
        fixture.approve()
        cohort = model._load_cohort(self.root, ("calibration",), "swing")
        with patch.object(model, "_project") as reader:
            with self.assertRaises(FileNotFoundError):
                model._labels(self.root, cohort, "calibrate")
        reader.assert_not_called()

    def test_failed_optimizer_is_counted_and_never_retried(self):
        fixture = self.fixture()
        fixture.prepare()
        fixture.approve()
        cohort = model._load_cohort(self.root, ("initial",), "swing")
        y = model._labels(self.root, cohort, "develop")
        config = model.candidates()[3]
        with patch.object(model, "LogisticRegression") as constructor:
            constructor.return_value.fit.side_effect = ConvergenceWarning("mock nonconvergence")
            result = model._fit(self.root, cohort, y, "initial", config["name"], config)
            self.assertEqual(result["status"], "failed")
            with self.assertRaises(PermissionError):
                model._fit(self.root, cohort, y, "initial", config["name"], config)
            self.assertEqual(constructor.return_value.fit.call_count, 1)

    def test_calibration_gradient_matches_finite_difference(self):
        z = np.array([-2., 0., 3.])
        y = np.array([0, 1, 1])
        theta = np.array([.8, -.4])
        _, analytic = model._calibration_objective(theta, z, y)
        finite = []
        for j in range(2):
            delta = np.zeros(2)
            delta[j] = 1e-6
            finite.append((model._calibration_objective(theta + delta, z, y)[0] - model._calibration_objective(theta - delta, z, y)[0]) / 2e-6)
        np.testing.assert_allclose(analytic, finite, atol=1e-9, rtol=0)

    def test_mocked_full_flow_seals_all_predictions_before_holdout_label_read(self):
        fixture = self.development()
        with self.mocked() as optimizer:
            model.calibrate(self.root)
        self.assertEqual(optimizer.call_count, 10)
        journal = [json.loads(line) for line in model._path(self.root, "development_operations.jsonl").read_text().splitlines()]
        self.assertEqual([row["operation_id"] for row in journal], model.planned_operations())
        with self.assertRaises(PermissionError):
            model.predict(self.root)
        fixture.approve(evaluation=True)
        with patch.object(model, "_labels") as reader:
            predictions = model.predict(self.root)
        reader.assert_not_called()
        self.assertEqual(set(predictions["targets"]), set(model.TARGETS))
        self.assertTrue(all(set(t["procedures"]) == set(model.PROCEDURES) for t in predictions["targets"].values()))
        original = model._project
        target_reads = []
        def guarded(line, fields):
            if "target" in fields:
                self.assertTrue(model._path(self.root, "PREDICTIONS_SEALED.json").exists())
                self.assertIn(GAMES["test"], line)
                target_reads.append(line)
            return original(line, fields)
        with self.mocked(), patch.object(model, "_project", side_effect=guarded):
            report = model.evaluate(self.root)
        self.assertEqual(len(target_reads), 9)
        for target, expected in (("swing", 6), ("contact_given_swing", 3)):
            self.assertEqual(report["targets"][target]["n"], expected)
            for procedure in report["targets"][target]["procedures"].values():
                self.assertEqual(procedure["raw"]["n"], expected)
                self.assertEqual(procedure["calibrated"]["n"], expected)
                self.assertEqual(sum(row["n"] for row in procedure["raw"]["reliability"]), expected)
        self.assertFalse(report["targets"]["contact_given_swing"]["comparison"]["useful_improvement_claim"])

    def test_boundary_calibrator_keeps_raw_results_without_alternative_fit(self):
        fixture = self.development()
        cohort = model._load_cohort(self.root, ("calibration",), "swing")
        y = model._labels(self.root, cohort, "calibrate")
        fitted = model._read_json(model._path(self.root, "models/swing/constant.json"))
        boundary = SimpleNamespace(x=np.array([0., 1.]), fun=.5, success=True, nit=2, message="Boundary fixture")
        with patch.object(model, "minimize", return_value=boundary) as optimizer:
            result = model._fit_calibrator(self.root, cohort, y, "constant", fitted)
            self.assertEqual(result["status"], "boundary")
            self.assertFalse(result["available"])
            self.assertIsNone(model._calibrated(np.full(len(cohort), .5), result))
            with self.assertRaises(PermissionError):
                model._fit_calibrator(self.root, cohort, y, "constant", fitted)
        self.assertEqual(optimizer.call_count, 1)
        self.assertTrue(np.isfinite(model._predict(fitted, cohort.values)).all())

    def test_private_calibrator_rejects_initial_role_before_optimizer(self):
        fixture = self.development()
        cohort = model._load_cohort(self.root, ("initial",), "swing")
        labels = model._labels(self.root, cohort, "develop")
        fitted = model._read_json(model._path(self.root, "models/swing/constant.json"))
        with patch.object(model, "minimize") as optimizer:
            with self.assertRaises(model.ProtocolError):
                model._fit_calibrator(self.root, cohort, labels, "constant", fitted)
        optimizer.assert_not_called()

    def test_holdout_reader_requires_all_predictions_not_only_one_target(self):
        fixture = self.development()
        with self.mocked():
            model.calibrate(self.root)
        fixture.approve(evaluation=True)
        cohort = model._load_cohort(self.root, ("test",), "swing")
        with patch.object(model, "_project") as reader:
            with self.assertRaises(FileNotFoundError):
                model._labels(self.root, cohort, "evaluate")
        reader.assert_not_called()
        model.predict(self.root)
        sealed = model._read_json(model._path(self.root, "PREDICTIONS_SEALED.json"))
        sealed["targets"].pop("contact_given_swing")
        model._path(self.root, "PREDICTIONS_SEALED.json").write_text(json.dumps(sealed))
        with patch.object(model, "_project") as reader:
            with self.assertRaises(PermissionError):
                model._labels(self.root, cohort, "evaluate")
        reader.assert_not_called()

    def test_fixed_draw_bootstrap_is_game_paired_pitch_weighted_and_lexicographic(self):
        games = np.array(["z", "a", "z", "z", "b"])
        delta = np.array([.1, -.1, .2, .3, -.2])
        result = model._paired_comparisons({"first": delta, "second": 2 * delta}, games)
        rng = np.random.default_rng(model.SEED)
        sums = np.array([-.1, -.2, .6])
        counts = np.array([1, 1, 3])
        draws = []
        for _ in range(2000):
            chosen = rng.integers(0, 3, 3)
            draws.append(sums[chosen].sum() / counts[chosen].sum())
        np.testing.assert_allclose(result["first"]["interval"], np.quantile(draws, [.025, .975], method="linear"), atol=1e-16)
        np.testing.assert_allclose(result["second"]["interval"], 2 * np.asarray(result["first"]["interval"]), atol=1e-16)
        self.assertAlmostEqual(result["first"]["difference"], delta.mean())

    def test_bound_feature_mutation_is_rejected_before_private_fit(self):
        fixture = self.fixture()
        fixture.prepare()
        fixture.approve()
        cohort = model._load_cohort(self.root, ("initial",), "swing")
        labels = model._labels(self.root, cohort, "develop")
        cohort.values[0, 0] = "3-2"
        with patch.object(gates, "record_operation") as reserve:
            with self.assertRaises(model.ProtocolError):
                model._fit(self.root, cohort, labels, "initial", "constant", model.candidates()[0])
        reserve.assert_not_called()

    def test_persisted_finalist_cannot_expand_the_grid(self):
        self.development()
        path = model._path(self.root, "SELECTED.json")
        selected = model._read_json(path)
        selected["designated"]["swing"]["context_logistic"]["C"] = 10.
        path.write_text(json.dumps(selected))
        with self.assertRaises(PermissionError):
            model._selected(self.root)

    def test_metrics_binary_brier_epsilon_threshold_and_bins(self):
        y = np.array([1, 0, 1, 0])
        p = np.array([0., 1., .5, .1])
        result = model._summary(y, p, "swing")
        self.assertAlmostEqual(result["brier"], float(np.mean((p - y)**2)))
        q = np.clip(p, 1e-12, 1 - 1e-12)
        self.assertAlmostEqual(result["log_loss"], float(np.mean(-y * np.log(q) - (1 - y) * np.log1p(-q))))
        self.assertEqual(result["accuracy"], .5)
        self.assertEqual(result["reliability"][1]["n"], 1)
        self.assertEqual(result["reliability"][-1]["n"], 1)

    def test_reliability_decimal_boundaries_are_left_closed(self):
        probabilities = np.array([0., .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.])
        labels = np.arange(len(probabilities)) % 2
        result = model._summary(labels, probabilities, "swing")
        self.assertEqual([row["n"] for row in result["reliability"]], [1] * 9 + [2])
        for index in range(9):
            self.assertEqual(result["reliability"][index]["mean_probability"], probabilities[index])
        for index in (3, 6, 7):
            self.assertEqual(result["reliability"][index]["lower"], probabilities[index])
            self.assertEqual(result["reliability"][index]["observed_fraction"], labels[index])

    def test_role_rejects_out_of_season_or_reversed_dates(self):
        for year, low, high in ((2023, "20220101", "20231231"), (2023, "20230101", "20240101"),
                                (2024, "20230101", "20240630"), (2025, "20250101", "20260101"),
                                (2025, "20251231", "20250101"), (2022, "20220101", "20221231")):
            with self.subTest(year=year, low=low, high=high):
                with self.assertRaises(model.ProtocolError):
                    model._role(year, low, high)
        self.assertEqual(model._role(2023, "20230330", "20231001"), "initial")
        self.assertEqual(model._role(2024, "20240626", "20240826"), "boundary_exclusion")
        self.assertEqual(model._role(2024, "20240630", "20240630"), "selection")
        self.assertEqual(model._role(2024, "20240701", "20240701"), "calibration")
        self.assertEqual(model._role(2025, "20250301", "20251001"), "test")
        with self.assertRaises(model.ProtocolError):
            model._role(2025, "202511", "20251231")

    def test_write_once_never_overwrites_even_identical_content(self):
        path = self.root / "immutable.json"
        first = model._write_once(path, {"x": 1})
        with self.assertRaises(FileExistsError):
            model._write_once(path, {"x": 1})
        self.assertEqual(gates.digest_file(path), first)

    def test_adjudication_pin_fails_closed_before_reading_source_rows(self):
        path = self.root / model.ADJUDICATION
        path.parent.mkdir(parents=True)
        path.write_text('{}')
        with patch.object(model, "_project") as reader:
            with self.assertRaisesRegex(PermissionError, "exact accepted reference"):
                model.prepare(self.root)
        reader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
