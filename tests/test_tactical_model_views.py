"""Synthetic-only aggregate-view tests. No runner, dataset, fit or evaluation.

All mock review/report/binding files are confined to TemporaryDirectory. They
are fixtures for fail-closed code paths, not research evidence or clearance.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from experiments.tactical import model_views as v
from experiments.tactical import workbench as w


def synthetic_view(task):
    """Invented values solely for unit/DOM tests; never write to project reports."""
    contract = v.CONTRACTS[task]
    targets = []
    for target_id in contract["targets"]:
        cohort = next(iter(contract["cohorts"]))
        cases, clusters = (571, 82) if task == "baseball_mechanics" else (548, 8) if task == "tennis_execution" else (200, 5 if task == "basketball" else 25)
        names = [name for name in contract["models"] if task != "soccer" or name.startswith(cohort + "_")][:2]
        metric = "macro_MAE" if task == "baseball_mechanics" else "joint_NLL_equal_player" if task == "tennis_execution" else "log_loss"
        identity = hashlib.sha256(f"SYNTHETIC TEST ONLY {task} {target_id}".encode()).hexdigest()
        models = [dict(id=name, case_set_sha256=identity,
                       metrics={metric: dict(value=.5 + index * .1, cases=cases, clusters=clusters, status="reported")})
                  for index, name in enumerate(names)]
        reliability = []
        if contract["classes"]:
            bins = [dict(n=0, clusters=0, mean_probability=None, observed_fraction=None) for _ in contract["bins"][:-1]]
            # One sparse and one supported bin, plus explicit empty bins.
            for index, n in ((0, 10), (1, cases - 10)):
                bins[index] = dict(n=n, clusters=min(n, clusters), mean_probability=(contract["bins"][index] + contract["bins"][index + 1]) / 2,
                                   observed_fraction=.1 + index * .1)
            reliability = [dict(model=names[0], **{"class": label}, bins=copy.deepcopy(bins)) for label in contract["classes"]]
        targets.append(dict(id=target_id, cohort=cohort, cases=cases, clusters=clusters, case_set_sha256=identity,
                            models=models, comparisons=[dict(model=names[1], reference=names[0], metric=metric, delta=.1,
                                interval=None, confidence=None, uncertainty="not_available", sensitivity_range=None, criterion_met=False)],
                            reliability=reliability))
    return dict(schema_version=1, task=task, phase="independently_verified_final_aggregate", targets=targets)


def synthetic_ui_view(task):
    """Direct test-only UI payload. This does not pass or open any real gate."""
    view = synthetic_view(task)
    metrics, definitions = v.metric_definitions(task)
    return {**view, "delivery_mode": "verified_local_final", "contract": {**v.CONTRACTS[task], "cluster_unit": v.CLUSTER_UNITS[task]},
            "metrics": metrics, "definitions": definitions, "notices": [v.SOURCE_QA, v.NO_CAUSAL]}


class SchemaTests(unittest.TestCase):
    def test_all_seven_synthetic_aggregate_shapes(self):
        for task in v.TASKS:
            with self.subTest(task=task):
                self.assertEqual(v.validate_view(task, synthetic_view(task))["task"], task)

    def reject(self, mutate, task="soccer"):
        value = synthetic_view(task); mutate(value)
        with self.assertRaises((ValueError, TypeError)):
            v.validate_view(task, value)

    def test_extra_identifiers_raw_rows_and_parameters_rejected_at_every_level(self):
        for field in ("player_id", "trial_id", "row_ids", "probabilities", "weights", "pickle", "source_path", "private_group_plan"):
            for level in ("root", "target", "model", "metric", "comparison", "series", "bin"):
                def mutate(value):
                    target = value["targets"][0]
                    obj = {"root": value, "target": target, "model": target["models"][0],
                           "metric": target["models"][0]["metrics"]["log_loss"], "comparison": target["comparisons"][0],
                           "series": target["reliability"][0], "bin": target["reliability"][0]["bins"][0]}[level]
                    obj[field] = "SYNTHETIC PRIVATE SENTINEL"
                with self.subTest(field=field, level=level): self.reject(mutate)

    def test_no_free_form_report_prose_or_models(self):
        self.reject(lambda x: x["targets"][0]["models"][0].update(id="<script>alert(1)</script>"))
        self.reject(lambda x: x.update(phase="development_complete"))
        self.reject(lambda x: x.update(schema_version=True))
        self.reject(lambda x: x.update(task="football"))
        self.reject(lambda x: x["targets"][0].update(cohort="private_player_1"))
        self.reject(lambda x: x["targets"][0].update(id="new_target"))

    def test_fixed_same_case_denominator_and_identity(self):
        self.reject(lambda x: x["targets"][0]["models"][0].update(case_set_sha256="f" * 64))
        self.reject(lambda x: x["targets"][0]["models"][0]["metrics"]["log_loss"].update(cases=100))
        self.reject(lambda x: x["targets"][0].update(clusters=201))
        self.reject(lambda x: x["targets"][0].update(cases=True))
        self.reject(lambda x: x["targets"][0].update(case_set_sha256="bad"))
        self.reject(lambda x: x["targets"][0]["models"][0].update(id="matched_A_raw"))

    def test_nonfinite_out_of_range_and_missing_metrics(self):
        for number in (float("nan"), float("inf"), float("-inf"), True, -.1):
            self.reject(lambda x: x["targets"][0]["models"][0]["metrics"]["log_loss"].update(value=number))
        for metric, value in (("accuracy", 1.1), ("brier", 1.01), ("auroc", -.1)):
            self.reject(lambda x: x["targets"][0]["models"][0]["metrics"].update({metric: dict(value=value, cases=200, clusters=25, status="reported")}))
        self.reject(lambda x: x["targets"][0]["models"][0].update(metrics={}))
        self.reject(lambda x: x["targets"][0]["models"][0]["metrics"].update(mph={}))

    def test_multiclass_brier_range_is_sum_not_average(self):
        view = synthetic_view("tennis")
        view["targets"][0]["models"][0]["metrics"]["brier"] = dict(value=1.5, cases=200, clusters=25, status="reported")
        v.validate_view("tennis", view)
        view["targets"][0]["models"][0]["metrics"]["brier"]["value"] = 2.1
        with self.assertRaises(ValueError): v.validate_view("tennis", view)

    def test_density_nll_can_be_negative_but_error_cannot(self):
        value = synthetic_view("tennis_execution")
        score = dict(value=-.5, cases=437, clusters=8, status="reported")
        value["targets"][0]["models"][0]["metrics"]["location_NLL_equal_player"] = score
        v.validate_view("tennis_execution", value)
        value["targets"][0]["models"][0]["metrics"]["euclidean_error_equal_player"] = score
        with self.assertRaises(ValueError): v.validate_view("tennis_execution", value)

    def test_unavailable_procedure_never_has_invented_result_or_difference(self):
        value = synthetic_view("baseball")
        target = value["targets"][0]
        target["models"][1]["metrics"]["log_loss"].update(value=None, status="procedure_unavailable")
        target["comparisons"][0].update(delta=None, criterion_met=None)
        v.validate_view("baseball", value)
        target["models"][1]["metrics"]["log_loss"]["value"] = .9
        with self.assertRaises(ValueError): v.validate_view("baseball", value)

    def test_comparison_delta_support_and_interpretation(self):
        self.reject(lambda x: x["targets"][0]["comparisons"][0].update(delta=-.1))
        self.reject(lambda x: x["targets"][0]["comparisons"][0].update(criterion_met=True))
        self.reject(lambda x: x["targets"][0]["models"][1]["metrics"]["log_loss"].update(clusters=20))
        self.reject(lambda x: x["targets"][0]["comparisons"][0].update(metric="accuracy"))
        self.reject(lambda x: x["targets"][0]["comparisons"].append(copy.deepcopy(x["targets"][0]["comparisons"][0])))

    def test_unsupported_success_claim_is_rejected_even_for_favorable_gap(self):
        view = synthetic_view("baseball")
        target = view["targets"][0]
        target["models"][1]["metrics"]["log_loss"]["value"] = .499999
        target["comparisons"][0].update(delta=-.000001, criterion_met=True)
        with self.assertRaises(ValueError): v.validate_view("baseball", view)
        target["comparisons"][0]["criterion_met"] = None
        v.validate_view("baseball", view)

    def test_only_task_scoped_uncertainty(self):
        self.reject(lambda x: x["targets"][0]["comparisons"][0].update(uncertainty="paired_player_bootstrap"))
        self.reject(lambda x: x["targets"][0]["comparisons"][0].update(interval=[-.1, .2], confidence=.95))
        self.reject(lambda x: x["targets"][0]["comparisons"][0].update(uncertainty="paired_match_bootstrap", interval=[.2, -.1], confidence=.95))
        self.reject(lambda x: x["targets"][0]["comparisons"][0].update(uncertainty="paired_match_bootstrap", interval=[-.1, .2], confidence=.95), "tennis")
        view = synthetic_view("tennis")
        view["targets"][0]["comparisons"][0].update(uncertainty="paired_match_bootstrap", interval=[-.1, .2], confidence=.9875)
        v.validate_view("tennis", view)

    def test_five_game_range_is_not_a_confidence_interval(self):
        view = synthetic_view("basketball")
        row = view["targets"][0]["comparisons"][0]
        row.update(uncertainty="five_game_leave_one_out", sensitivity_range=[-.1, .2])
        v.validate_view("basketball", view)
        row.update(interval=[-.1, .2], confidence=.95)
        with self.assertRaises(ValueError): v.validate_view("basketball", view)

    def test_reliability_empty_sparse_and_same_case_support(self):
        self.reject(lambda x: x["targets"][0]["reliability"][0]["bins"][0].update(n=11))
        self.reject(lambda x: x["targets"][0]["reliability"][0]["bins"][0].update(mean_probability=.8))
        self.reject(lambda x: x["targets"][0]["reliability"][0]["bins"][2].update(mean_probability=.1))
        self.reject(lambda x: x["targets"][0]["reliability"][0]["bins"][0].update(clusters=0))
        self.reject(lambda x: x["targets"][0]["reliability"][0]["bins"][0].update(clusters=11))
        self.reject(lambda x: x["targets"][0]["reliability"][0].update(**{"class": "unknown"}))
        self.reject(lambda x: x["targets"][0]["reliability"].append(copy.deepcopy(x["targets"][0]["reliability"][0])))

    def test_fixed_lab_cohorts_and_all_eight_records_suppressed(self):
        self.reject(lambda x: x["targets"][0].update(cases=643), "baseball_mechanics")
        self.reject(lambda x: x["targets"][0].update(clusters=93), "baseball_mechanics")
        self.reject(lambda x: x["targets"][0].update(cases=567), "tennis_execution")
        self.reject(lambda x: x["targets"][0].update(clusters=7), "tennis_execution")
        for field in ("players", "folds", "sessions", "player_results", "private_player_label"):
            self.reject(lambda x: x["targets"][0].update({field: [{"P": i} for i in range(8)]}), "tennis_execution")
        self.reject(lambda x: x["targets"][0]["models"][0]["metrics"].update(location_NLL_equal_player=dict(value=.2, cases=548, clusters=8, status="reported")), "tennis_execution")

    def test_scoped_definitions_and_exact_frozen_edges(self):
        self.assertGreater(v.CONTRACTS["football"]["bins"][3], .3)
        self.assertGreater(v.CONTRACTS["tennis"]["bins"][6], .6)
        self.assertEqual(v.CONTRACTS["baseball"]["bins"][3], .3)
        for task in v.TASKS:
            _, definitions = v.metric_definitions(task)
            self.assertIn(v.CRITERIA[task], definitions)
        self.assertIn("class 0", " ".join(v.metric_definitions("basketball")[1]))
        self.assertIn("including exact ties", " ".join(v.metric_definitions("football")[1]))
        self.assertIn("no division by three", " ".join(v.metric_definitions("tennis")[1]))


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic-model-view-test-")
        self.root = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def write(self, path, data):
        dest = self.root / path; dest.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(data, sort_keys=True).encode() if not isinstance(data, bytes) else data
        dest.write_bytes(raw); return hashlib.sha256(raw).hexdigest()
    def install_test_evidence(self, task="soccer"):
        # This helper is never called on a project directory or real reports.
        assert self.root.name.startswith("synthetic-model-view-test-")
        body = dict(task=task, evaluation_cohort=list(v.TASKS), metadata={"artifact_id": "b" * 64}, synthetic_test_only=True)
        binding_hash = v._digest(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
        binding = {**body, "binding_sha256": binding_hash}
        report = dict(phase="frozen_evaluation", synthetic_test_only=True)
        if task == "basketball": report.update(phase="evaluation_complete", new_model_selection=False)
        elif task == "tennis": report.update(stage="locked_2025_evaluation", as_of="20260122")
        elif task == "baseball": report.update(task=task, targets={"swing": {}, "contact_given_swing": {}})
        elif task in ("baseball_mechanics", "tennis_execution"): report.update(task=task, status="evaluation_complete", new_model_selection=False)
        review = dict(schema_version=1, review_type="independent_final_model_view_review", status="cleared",
                      reviewer="SYNTHETIC TEST ONLY, NOT AN APPROVAL", independent=True,
                      implementation_sha256={path: self.write(path, (v.LIVE_ROOT / path).read_bytes()) for path in v.IMPLEMENTATION},
                      tasks={task: dict(status="verified_final", binding_sha256=binding_hash,
                            binding_file_sha256=self.write(f"artifacts/tactical/{task}/run_binding.json", binding),
                            final_report_sha256=self.write(v._final_path(task, binding), report),
                            view_sha256=self.write(f"{v.VIEW_DIRECTORY}/{task}.json", synthetic_view(task)),
                            checks={check: True for check in v.CHECKS})})
        review["seven_task_completion"] = {name: dict(status="verified_final", binding_sha256="e" * 64,
            final_report_sha256="f" * 64, independent_result_review_sha256="") for name in v.TASKS}
        review["seven_task_completion"][task].update(binding_sha256=binding_hash, final_report_sha256=review["tasks"][task]["final_report_sha256"])
        selections = {name: self.write(f"artifacts/tactical/{name}/SELECTION_FREEZE.json", {"task": name, "synthetic_test_only": True}) for name in v.TASKS}
        freeze = dict(schema_version=1, tasks={name: dict(binding_sha256=record["binding_sha256"],
            selection_path=f"artifacts/tactical/{name}/SELECTION_FREEZE.json", selection_sha256=selections[name])
            for name, record in review["seven_task_completion"].items()})
        audit = dict(schema_version=1, review_type="tactical_final_numerical_review", status="verified_final", independent=True,
                     reviewer="SYNTHETIC NUMERICAL AUDIT TEST ONLY, NOT APPROVAL", evaluation_freeze_sha256=self.write(v.GLOBAL_FREEZE, freeze),
                     tasks={name: dict(status="verified_final", binding_sha256=record["binding_sha256"],
                        selection_sha256=selections[name], final_report_sha256=record["final_report_sha256"],
                        checks={check: True for check in v.NUMERICAL_CHECKS}) for name, record in review["seven_task_completion"].items()})
        audit_hash = self.write(v.NUMERICAL_REVIEW, audit)
        for record in review["seven_task_completion"].values(): record["independent_result_review_sha256"] = audit_hash
        self.write(v.REVIEW, review)
        return review, binding
    def rebind_synthetic_audit(self, review):
        audit = json.loads((self.root / v.NUMERICAL_REVIEW).read_text())
        freeze = json.loads((self.root / v.GLOBAL_FREEZE).read_text())
        for name, record in review["seven_task_completion"].items():
            audit["tasks"][name].update({field: record[field] for field in ("binding_sha256", "final_report_sha256")})
            freeze["tasks"][name]["binding_sha256"] = record["binding_sha256"]
        audit["evaluation_freeze_sha256"] = self.write(v.GLOBAL_FREEZE, freeze)
        digest = self.write(v.NUMERICAL_REVIEW, audit)
        for record in review["seven_task_completion"].values(): record["independent_result_review_sha256"] = digest

    def test_numerical_audit_must_be_semantically_complete_even_if_rehashed(self):
        mutations = [lambda x: x.clear(), lambda x: x.update(status="pending"), lambda x: x.update(review_type="source_only"),
                     lambda x: x.update(independent=False), lambda x: x["tasks"].pop("baseball"),
                     lambda x: x["tasks"]["soccer"].update(binding_sha256="0" * 64),
                     lambda x: x["tasks"]["baseball"].update(status="development_complete"),
                     lambda x: x["tasks"]["soccer"]["checks"].update(saved_prediction_metrics_recomputed=False)]
        for change in mutations:
            review, _ = self.install_test_evidence()
            audit = json.loads((self.root / v.NUMERICAL_REVIEW).read_text()); change(audit)
            digest = self.write(v.NUMERICAL_REVIEW, audit)
            for record in review["seven_task_completion"].values(): record["independent_result_review_sha256"] = digest
            self.write(v.REVIEW, review)
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))

    def test_global_and_all_seven_selection_bytes_are_bound(self):
        for path in (v.GLOBAL_FREEZE, *[f"artifacts/tactical/{task}/SELECTION_FREEZE.json" for task in v.TASKS]):
            self.install_test_evidence()
            with (self.root / path).open("ab") as stream: stream.write(b" ")
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None), path)

    def test_rehashed_global_freeze_cannot_change_seven_study_metadata(self):
        mutations = [lambda x: x["tasks"].pop("baseball"), lambda x: x.update(schema_version=True),
                     lambda x: x["tasks"]["tennis"].update(selection_path="data/private.json"),
                     lambda x: x["tasks"]["tennis"].update(selection_sha256="0" * 64),
                     lambda x: x["tasks"]["tennis"].update(binding_sha256="0" * 64)]
        for change in mutations:
            review, _ = self.install_test_evidence()
            freeze = json.loads((self.root / v.GLOBAL_FREEZE).read_text()); change(freeze)
            audit = json.loads((self.root / v.NUMERICAL_REVIEW).read_text())
            audit["evaluation_freeze_sha256"] = self.write(v.GLOBAL_FREEZE, freeze)
            digest = self.write(v.NUMERICAL_REVIEW, audit)
            for record in review["seven_task_completion"].values(): record["independent_result_review_sha256"] = digest
            self.write(v.REVIEW, review)
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))

    def test_numerical_audit_narrative_is_ignored_and_never_served(self):
        review, _ = self.install_test_evidence()
        audit = json.loads((self.root / v.NUMERICAL_REVIEW).read_text())
        audit["limitations"] = ["SYNTHETIC PRIVATE AUDIT NARRATIVE"]
        digest = self.write(v.NUMERICAL_REVIEW, audit)
        for record in review["seven_task_completion"].values(): record["independent_result_review_sha256"] = digest
        self.write(v.REVIEW, review)
        status, view = v.load_verified_view(self.root, "soccer")
        self.assertEqual(status, "verified_final_available")
        self.assertNotIn("SYNTHETIC PRIVATE AUDIT NARRATIVE", json.dumps(view))

    def test_absent_review_never_opens_any_report_or_private_file(self):
        with patch.object(v, "_bytes", side_effect=AssertionError("No reads permitted without review")):
            for task in v.TASKS:
                self.assertEqual(v.response(self.root, task), dict(status="awaiting_independent_final_review", view=None))
    def test_completed_bound_aggregate_for_all_seven_mock_tasks(self):
        for task in v.TASKS:
            self.install_test_evidence(task)
            before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
            status, view = v.load_verified_view(self.root, task)
            self.assertEqual(status, "verified_final_available")
            self.assertEqual(view["task"], task)
            self.assertNotIn("reviewer", json.dumps(view))
            self.assertNotIn("synthetic_test_only", json.dumps(view))
            self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
    def test_every_implementation_report_binding_and_projection_mutation_closes(self):
        for path in (*v.IMPLEMENTATION, v.NUMERICAL_REVIEW, "artifacts/tactical/soccer/run_binding.json", "reports/tactical/soccer/model/evaluation.json", f"{v.VIEW_DIRECTORY}/soccer.json"):
            self.install_test_evidence()
            with (self.root / path).open("ab") as stream: stream.write(b" ")
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None), path)
    def test_missing_checks_independence_and_boolean_schema_close(self):
        for change in (lambda x: x.update(independent=False), lambda x: x.update(status="pending"),
                       lambda x: x.update(schema_version=True), lambda x: x["tasks"]["soccer"]["checks"].update(independent_metric_recomputation=False),
                       lambda x: x["tasks"]["soccer"].update(status="development_only")):
            review, _ = self.install_test_evidence(); change(review); self.write(v.REVIEW, review)
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))
    def test_final_phase_required_even_with_hash_match(self):
        review, _ = self.install_test_evidence()
        review["tasks"]["soccer"]["final_report_sha256"] = self.write("reports/tactical/soccer/model/evaluation.json", {"phase": "development_complete"})
        review["seven_task_completion"]["soccer"]["final_report_sha256"] = review["tasks"]["soccer"]["final_report_sha256"]
        self.rebind_synthetic_audit(review)
        self.write(v.REVIEW, review)
        self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))
    def test_rehashed_subset_cohort_and_wrong_binding_identity_close(self):
        review, binding = self.install_test_evidence()
        binding["evaluation_cohort"] = ["soccer"]
        binding["binding_sha256"] = v._digest(json.dumps({k: val for k, val in binding.items() if k != "binding_sha256"}, sort_keys=True, separators=(",", ":")).encode())
        entry = review["tasks"]["soccer"]; entry["binding_sha256"] = binding["binding_sha256"]
        entry["binding_file_sha256"] = self.write("artifacts/tactical/soccer/run_binding.json", binding)
        review["seven_task_completion"]["soccer"]["binding_sha256"] = binding["binding_sha256"]
        self.rebind_synthetic_audit(review)
        self.write(v.REVIEW, review)
        self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))
    def test_local_review_requires_all_seven_completion_attestations(self):
        for change in (lambda x: x["seven_task_completion"].pop("baseball"),
                       lambda x: x["seven_task_completion"]["baseball"].update(status="development_only"),
                       lambda x: x["seven_task_completion"]["soccer"].update(binding_sha256="1" * 64),
                       lambda x: x["seven_task_completion"]["soccer"].update(final_report_sha256="2" * 64)):
            review, _ = self.install_test_evidence(); change(review); self.write(v.REVIEW, review)
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))

    def test_nonobject_hash_bound_binding_fails_closed(self):
        for value in ([], None, 7, "binding"):
            review, _ = self.install_test_evidence()
            review["tasks"]["soccer"]["binding_file_sha256"] = self.write("artifacts/tactical/soccer/run_binding.json", value)
            self.write(v.REVIEW, review)
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))

    def test_reviewed_alternate_root_must_match_live_code_and_served_assets(self):
        for path in v.IMPLEMENTATION:
            review, _ = self.install_test_evidence()
            review["implementation_sha256"][path] = self.write(path, b"DIFFERENT REVIEWED COPY, NOT THE LIVE IMPLEMENTATION")
            self.write(v.REVIEW, review)
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None), path)
        self.install_test_evidence()
        with patch.object(v, "RUNNING_CODE_SHA256", {path: "0" * 64 for path in v.RUNNING_CODE_SHA256}):
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))

    def test_extra_projected_private_records_fail_closed_even_if_hash_bound(self):
        review, _ = self.install_test_evidence("tennis_execution")
        view = synthetic_view("tennis_execution"); view["players"] = [{"private_label": str(i)} for i in range(8)]
        review["tasks"]["tennis_execution"]["view_sha256"] = self.write(f"{v.VIEW_DIRECTORY}/tennis_execution.json", view)
        self.write(v.REVIEW, review)
        self.assertEqual(v.load_verified_view(self.root, "tennis_execution"), ("invalid_final_artifact", None))
    def test_only_fixed_evidence_paths_are_read(self):
        self.install_test_evidence()
        with patch.object(v, "_bytes", wraps=v._bytes) as reader:
            self.assertEqual(v.load_verified_view(self.root, "soccer")[0], "verified_final_available")
        paths = {args.args[1] for args in reader.call_args_list}
        self.assertEqual(paths, {v.REVIEW, v.NUMERICAL_REVIEW, v.GLOBAL_FREEZE, *v.IMPLEMENTATION, *[f"artifacts/tactical/{task}/SELECTION_FREEZE.json" for task in v.TASKS], "artifacts/tactical/soccer/run_binding.json", "reports/tactical/soccer/model/evaluation.json", f"{v.VIEW_DIRECTORY}/soccer.json"})
    def test_json_duplicate_nonfinite_large_and_symlink_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.assertRaises(ValueError): v._json(raw)
        self.write("large.json", b" " * (v.MAX_BYTES + 1))
        with self.assertRaises(ValueError): v._bytes(self.root, "large.json")
        with tempfile.TemporaryDirectory() as other:
            (self.root / "escape").symlink_to(other, target_is_directory=True)
            with self.assertRaises(ValueError): v._path(self.root, "escape/x")
        for path in ("../private", "/tmp/private"):
            with self.assertRaises(ValueError): v._path(self.root, path)
    def test_large_final_report_requires_exact_hash_and_does_not_expand_served_view(self):
        review, binding = self.install_test_evidence("football")
        path = v._final_path("football", binding)
        raw = (self.root / path).read_bytes().ljust(3_627_586, b" ")
        digest = self.write(path, raw)
        self.assertEqual(v.load_verified_view(self.root, "football"), ("invalid_final_artifact", None))
        review["tasks"]["football"]["final_report_sha256"] = digest
        review["seven_task_completion"]["football"]["final_report_sha256"] = digest
        self.rebind_synthetic_audit(review); self.write(v.REVIEW, review)
        status, payload = v.load_verified_view(self.root, "football")
        self.assertEqual(status, "verified_final_available")
        self.assertLess(len(json.dumps(payload)), v.MAX_BYTES)
        # A correctly hash-bound normalized view still has the smaller cap.
        view_path = f"{v.VIEW_DIRECTORY}/football.json"
        view_raw = (self.root / view_path).read_bytes().ljust(v.MAX_BYTES + 1, b" ")
        review["tasks"]["football"]["view_sha256"] = self.write(view_path, view_raw)
        self.write(v.REVIEW, review)
        self.assertEqual(v.load_verified_view(self.root, "football"), ("invalid_final_artifact", None))
    def test_not_reviewed_task_stays_closed_and_unknown_task_rejected(self):
        self.install_test_evidence()
        self.assertEqual(v.load_verified_view(self.root, "football"), ("awaiting_independent_final_review", None))
        with self.assertRaises(KeyError): v.load_verified_view(self.root, "other")


class EvidenceSizeTests(unittest.TestCase):
    """Both file readers, entirely synthetic files under a temporary root."""
    setUp = EvidenceTests.setUp
    tearDown = EvidenceTests.tearDown
    def readers(self):
        from experiments.tactical import model_view_projection as p
        return (v._bytes, p._read)
    def sized_file(self, relative, size):
        path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as stream: stream.truncate(size)
        return path
    def test_only_seven_fixed_original_report_families_get_8mib(self):
        self.assertEqual(v.MAX_BYTES, 2_000_000)
        self.assertEqual(v.FINAL_REPORT_MAX_BYTES, 8 * 1024 * 1024)
        for task in v.TASKS:
            relative = v._final_path(task, {"metadata": {"artifact_id": "b" * 64}})
            self.assertEqual(v._evidence_limit(relative), v.FINAL_REPORT_MAX_BYTES)
            path = self.sized_file(relative, v.FINAL_REPORT_MAX_BYTES)
            for reader in self.readers():
                with self.subTest(task=task, reader=reader.__module__):
                    self.assertEqual(len(reader(self.root, relative)), v.FINAL_REPORT_MAX_BYTES)
            with path.open("ab") as stream: stream.write(b" ")
            for reader in self.readers():
                with self.assertRaises(ValueError): reader(self.root, relative)
    def test_review_view_metadata_and_path_lookalikes_keep_2mb_limit(self):
        paths = (v.REVIEW, v.SNAPSHOT_REVIEW, v.NUMERICAL_REVIEW, v.GLOBAL_FREEZE,
                 f"{v.VIEW_DIRECTORY}/football.json", "artifacts/tactical/football/run_binding.json",
                 "artifacts/tactical/football/SELECTION_FREEZE.json", v.IMPLEMENTATION[0],
                 "reports/tactical/unknown/model/evaluation.json", "reports/tactical/football/model/evaluation.json.bak",
                 "reports/tactical/football/model/development.json", "./reports/tactical/football/model/evaluation.json",
                 "reports//tactical/football/model/evaluation.json", "artifacts/tactical/baseball/evaluation.json",
                 "reports/tactical/basketball/model/not-a-hash/evaluation_report.json",
                 f"reports/tactical/basketball/model/{'B' * 64}/evaluation_report.json",
                 f"reports/tactical/basketball/model/{'b' * 63}/evaluation_report.json")
        for relative in paths:
            with self.subTest(path=relative):
                self.assertEqual(v._evidence_limit(relative), v.MAX_BYTES)
                path = self.sized_file(relative, v.MAX_BYTES)
                for reader in self.readers(): self.assertEqual(len(reader(self.root, relative)), v.MAX_BYTES)
                with path.open("ab") as stream: stream.write(b" ")
                for reader in self.readers():
                    with self.assertRaises(ValueError): reader(self.root, relative)
    def test_large_report_readers_reject_file_parent_aliases_and_fifo(self):
        relative = "reports/tactical/football/model/evaluation.json"
        path = self.sized_file(relative, v.MAX_BYTES + 1)
        hidden = self.root / "private_must_not_be_read.json"
        path.rename(hidden); path.symlink_to(hidden)
        for reader in self.readers():
            with self.assertRaises(ValueError): reader(self.root, relative)
        path.unlink(); hidden.rename(path)
        original = self.root / "reports"; moved = self.root / "private_reports"
        original.rename(moved); original.symlink_to(moved, target_is_directory=True)
        for reader in self.readers():
            with self.assertRaises(ValueError): reader(self.root, relative)
        original.unlink(); moved.rename(original)
        path.unlink(); os.mkfifo(path)
        for reader in self.readers():
            with self.assertRaises(ValueError): reader(self.root, relative)


class SnapshotEvidenceTests(unittest.TestCase):
    setUp = EvidenceTests.setUp
    tearDown = EvidenceTests.tearDown
    write = EvidenceTests.write
    def install_snapshot_test_evidence(self, task="soccer"):
        # As with local fixtures, write only to this isolated synthetic temp root.
        assert self.root.name.startswith("synthetic-model-view-test-")
        review = dict(schema_version=1, review_type="independent_aggregate_snapshot_review", status="cleared",
                      reviewer="SYNTHETIC SNAPSHOT TEST ONLY, NOT AN APPROVAL", independent=True,
                      distribution_scope="local_noncommercial_aggregate_snapshot", local_final_review_sha256="a" * 64,
                      implementation_sha256={path: self.write(path, (v.LIVE_ROOT / path).read_bytes()) for path in v.IMPLEMENTATION},
                      seven_task_completion={name: dict(status="verified_final", binding_sha256="b" * 64, final_report_sha256="c" * 64,
                                                          independent_result_review_sha256="d" * 64) for name in v.TASKS},
                      tasks={task: dict(status="verified_final", view_sha256=self.write(f"{v.VIEW_DIRECTORY}/{task}.json", synthetic_view(task)),
                                        checks={check: True for check in v.CHECKS | {"sanitized_snapshot_verified", "aggregate_distribution_authorized"}})})
        self.write(v.SNAPSHOT_REVIEW, review)
        return review
    def test_detached_snapshot_reads_no_private_run_or_original_report(self):
        self.install_snapshot_test_evidence()
        with patch.object(v, "_bytes", wraps=v._bytes) as reader:
            status, view = v.load_verified_view(self.root, "soccer")
        self.assertEqual(status, "verified_final_available")
        self.assertEqual(view["delivery_mode"], "audited_aggregate_snapshot")
        self.assertEqual({c.args[1] for c in reader.call_args_list}, {v.SNAPSHOT_REVIEW, *v.IMPLEMENTATION, f"{v.VIEW_DIRECTORY}/soccer.json"})
        self.assertFalse((self.root / "artifacts").exists())
    def test_snapshot_requires_all_seven_completed_provenance(self):
        for change in (lambda x: x["seven_task_completion"].pop("baseball"),
                       lambda x: x["seven_task_completion"]["baseball"].update(status="terminal_blocked"),
                       lambda x: x["seven_task_completion"]["baseball"].update(final_report_sha256=""),
                       lambda x: x.update(local_final_review_sha256="")):
            review = self.install_snapshot_test_evidence(); change(review); self.write(v.SNAPSHOT_REVIEW, review)
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))
    def test_snapshot_requires_explicit_distribution_privacy_and_schema_clearance(self):
        for change in (lambda x: x.update(distribution_scope="public_live_models"), lambda x: x.update(independent=False),
                       lambda x: x["tasks"]["soccer"]["checks"].update(aggregate_distribution_authorized=False),
                       lambda x: x["tasks"]["soccer"]["checks"].update(sanitized_snapshot_verified=False),
                       lambda x: x.update(private_memberships=[])):
            review = self.install_snapshot_test_evidence(); change(review); self.write(v.SNAPSHOT_REVIEW, review)
            self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))
    def test_snapshot_mutation_and_missing_implementation_close(self):
        self.install_snapshot_test_evidence()
        (self.root / v.IMPLEMENTATION[0]).unlink()
        self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))
        self.install_snapshot_test_evidence()
        with (self.root / f"{v.VIEW_DIRECTORY}/soccer.json").open("ab") as stream: stream.write(b" ")
        self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))
    def test_invalid_full_local_review_never_falls_back_to_snapshot(self):
        self.install_snapshot_test_evidence()
        self.write(v.REVIEW, {"status": "invalid local review"})
        self.assertEqual(v.load_verified_view(self.root, "soccer"), ("invalid_final_artifact", None))
    def test_unreviewed_snapshot_task_remains_closed(self):
        self.install_snapshot_test_evidence()
        self.assertEqual(v.load_verified_view(self.root, "football"), ("awaiting_independent_final_review", None))


class OfflineRouteTests(unittest.TestCase):
    """Exercise the real handler without creating any OS socket or browser."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        with patch.object(w, "ThreadingHTTPServer", side_effect=lambda address, handler: (address, handler)):
            self.address, self.handler = w.make_server(self.root, 8765)
    def tearDown(self): self.tmp.cleanup()
    def call(self, path, method="GET", headers=None):
        handler = self.handler.__new__(self.handler)
        handler.path = path; handler.server = SimpleNamespace(server_port=8765)
        handler.headers = headers or {"Host": "127.0.0.1:8765"}
        captured = []
        handler.json = lambda code, value: captured.append((code, value))
        handler.respond = lambda code, data, kind: captured.append((code, kind))
        getattr(handler, "do_" + method)()
        return captured[0]
    def test_routes_closed_and_loopback_only(self):
        self.assertEqual(self.address, ("127.0.0.1", 8765))
        for task in v.TASKS:
            code, body = self.call("/api/model-view/" + task)
            self.assertEqual((code, body), (409, {"status": "awaiting_independent_final_review", "view": None}))
        for path in ("/api/model-view/unknown", "/api/model-view/../../private", "/artifacts/tactical/tennis_execution/private_evaluation_details.json", "/api/probabilities/tennis", "/models/frozen.pkl", "/data/private.json"):
            self.assertEqual(self.call(path)[0], 404)
        for headers in ({"Host": "evil.example"}, {"Host": "127.0.0.1:8765", "Origin": "https://evil.example"}, {"Host": "127.0.0.1:8765", "Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.call("/api/model-view/tennis", headers=headers)[0], 403)
        self.assertEqual(self.call("/api/model-view/tennis?file=x")[0], 400)
    def test_read_only_and_descriptive_fallback_catalog(self):
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            self.assertEqual(self.call("/api/model-view/tennis", method)[0], 405)
        code, catalog = self.call("/api/catalog")
        self.assertEqual(code, 200); self.assertEqual(len(catalog["sports"]), 5)
        self.assertTrue(all(sport["predictive_status"] == "awaiting_independent_final_review" for sport in catalog["sports"]))
        self.assertEqual(self.call("/")[0], 200)
        self.assertEqual(self.call("/app.js")[0], 200)
    def test_method_route_serves_safe_execution_stages_only(self):
        safe = "docs/tactical/EXECUTION_STAGES.md"
        historical = "docs/research/INDEPENDENT_METHOD_REVIEW.md"
        self.assertEqual(w.DOCUMENTS["method"], safe)
        self.assertNotIn(historical, w.DOCUMENTS.values())
        for relative, content in ((safe, "SYNTHETIC SAFE STAGES"), (historical, "SYNTHETIC PRIVATE HISTORICAL REVIEW")):
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
        self.assertEqual(self.call("/api/document/method"), (200, {"title": "method", "text": "SYNTHETIC SAFE STAGES"}))
        self.assertEqual(self.call("/" + historical)[0], 404)
        self.assertEqual((self.root / historical).read_text(), "SYNTHETIC PRIVATE HISTORICAL REVIEW")
    def test_numerical_notice_routes_are_fixed_local_documents(self):
        expected={"license_scope": "docs/tactical/notices/DERIVED_MATERIAL_LICENSES.md",
                  "statsbomb_notice": "docs/tactical/notices/STATSBOMB_NOTICE.md",
                  "skillcorner_notice": "docs/research/notices/SKILLCORNER_BASKETBALL_MIT.txt",
                  "retrosheet_notice": "docs/tactical/notices/RETROSHEET_NOTICE.txt",
                  "nflverse_ftn_notice": "docs/tactical/notices/NFLVERSE_FTN_NOTICE.md",
                  "nflverse_pbp_notice": "docs/tactical/notices/NFLVERSE_PBP_NOTICE.md",
                  "mcp_notice": "docs/tactical/notices/MCP_NOTICE.md",
                  "openbiomechanics_license": "docs/tactical/notices/OPENBIOMECHANICS_DATA_LICENSE.md",
                  "mechanics_attribution": "docs/tactical/notices/MECHANICS_ATTRIBUTION.md",
                  "byu_license": "docs/tactical/notices/BYU_MIT.txt"}
        for key, relative in expected.items():
            self.assertEqual(w.DOCUMENTS[key], relative)
            path=self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("SYNTHETIC NOTICE " + key)
            self.assertEqual(self.call("/api/document/" + key), (200, {"title": key, "text": "SYNTHETIC NOTICE " + key}))
        self.assertEqual(self.call("/api/document/../../private_license")[0], 404)
        self.assertEqual(self.call("/docs/tactical/notices/private_license.txt")[0], 404)
    def test_malformed_descriptive_index_keeps_catalog_available(self):
        path = self.root / w.INDEX; path.parent.mkdir(parents=True)
        for reports in ([], {"soccer": []}, {"soccer": "not a record"}):
            path.write_text(json.dumps(dict(schema_version=1, phase="descriptive_only", reports=reports)))
            status, body = self.call("/api/catalog")
            self.assertEqual(status, 200)
            self.assertEqual(body["sports"][0]["status"], "invalid_artifact")
            self.assertEqual(self.call("/api/summary/soccer")[0], 409)

    def test_malformed_generator_provenance_rejected_as_controlled_error(self):
        for field in ("source", "provenance", "parser_dependencies_sha256"):
            with self.assertRaises(ValueError): w.verify_generator(self.root, "soccer", {field: []})

    def test_pinned_packaged_logo_fallback_and_changed_raw_logo_rejected(self):
        raw = b"SYNTHETIC LOGO BYTES FOR HASH-PIN TEST ONLY"
        path = self.root / w.PACKAGED_STATSBOMB_LOGO; path.parent.mkdir(parents=True); path.write_bytes(raw)
        with patch.object(w, "STATSBOMB_LOGO_SHA", w.sha256(raw)):
            self.assertEqual(self.call("/provider/statsbomb-logo.png")[0], 200)
            source = self.root / w.STATSBOMB_LOGO; source.parent.mkdir(parents=True); source.write_bytes(b"changed")
            self.assertEqual(self.call("/provider/statsbomb-logo.png")[0], 404)
            source.unlink(); path.write_bytes(b"changed")
            self.assertEqual(self.call("/provider/statsbomb-logo.png")[0], 404)

    def test_security_headers_without_network(self):
        handler = self.handler.__new__(self.handler); handler.wfile = io.BytesIO()
        headers = {}; statuses = []
        handler.send_response = statuses.append; handler.send_header = lambda name, value: headers.update({name: value}); handler.end_headers = lambda: None
        handler.respond(409, b"{}")
        self.assertEqual(statuses, [409]); self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("connect-src 'self'", headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)


if __name__ == "__main__": unittest.main()
