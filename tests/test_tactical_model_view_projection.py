"""Invented, schema-faithful aggregate reports only. No numerical runner imports."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.tactical import model_views as v
from experiments.tactical import model_view_projection as p


def support_record(task, target_id, cohort, cases=200, clusters=25):
    if task == "basketball": clusters = 5
    elif task == "baseball_mechanics": cases, clusters = 571, 82
    elif task == "tennis_execution": cases, clusters = 548, 8
    canonical = {"task": task, "target": target_id, "cohort": cohort,
                 "case_ids": sorted(json.dumps(["SYNTHETIC TEST ID", i], sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) for i in range(cases))}
    identity = v._digest(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode())
    return dict(id=target_id, cohort=cohort, cases=cases, clusters=clusters, case_set_sha256=identity)


def scalar_summary(task, support, loss=.5, with_groups=False):
    summary = dict(n=support["cases"], log_loss=loss, brier=.2, accuracy=.7, auroc=.8,
                   log_clip_epsilon=v.CONTRACTS[task]["epsilon"], log_loss_units="natural-log units per case",
                   brier_definition="mean sum of squared class errors" if task == "tennis" else "mean positive-class squared error")
    if task == "tennis": summary.update(match_macro_log_loss=loss + .2, server_macro_log_loss=loss + .3)
    if with_groups: summary["games"] = support["clusters"]
    buckets = []
    for index, _ in enumerate(v.CONTRACTS[task]["classes"]):
        cls = index if task == "tennis" else 1
        for number, (lower, upper) in enumerate(zip(v.CONTRACTS[task]["bins"], v.CONTRACTS[task]["bins"][1:])):
            n = support["cases"] if number == 0 else 0
            bucket = dict(**{"class": cls}, lower=lower, upper=upper, n=n,
                          mean_probability=(lower + upper) / 2 if n else None, observed_fraction=.2 if n else None)
            if with_groups: bucket["games"] = support["clusters"] if n else 0
            buckets.append(bucket)
    summary["reliability"] = buckets
    return summary


def interval(difference=.1, confidence=.95):
    return dict(difference=difference, interval=[difference - .05, difference + .05], confidence=confidence,
                groups=25, cases=200, status="computed", group_loss_differences=["PRIVATE SENTINEL"])


def source_report(task):
    """Mirror runner report-construction keys, never invoke scoring helpers."""
    support = [support_record(task, target_id, cohort) for target_id in v.CONTRACTS[task]["targets"] for cohort in v.CONTRACTS[task]["cohorts"]]
    if task == "soccer":
        streams = {}
        for cell in support:
            for name in v.CONTRACTS[task]["models"]:
                if name.startswith(cell["cohort"] + "_"):
                    streams[name] = scalar_summary(task, cell, .6 if name == "matched_R_calibrated" else .5, True)
        report = dict(phase="frozen_evaluation", streams=streams,
                      primary={"log_loss": interval(), "brier": interval(0)}, usefulness_yardstick_met=False,
                      equal_game_weighted_sensitivity={"PRIVATE SENTINEL": "not this estimand"}, slices=["PRIVATE SENTINEL"])
    elif task == "football":
        methods = {name: scalar_summary(task, support[0], .6 if name == "logistic_C_calibrated" else .5, True) for name in v.CONTRACTS[task]["models"]}
        report = dict(phase="frozen_evaluation", procedures=methods, primary_game_bootstrap={"log_loss": interval(), "brier": interval(0)},
                      week_dependence_sensitivity={"log_loss": interval(), "brier": interval(0)}, usefulness_yardstick_met=False)
    elif task == "basketball":
        cohorts = {cell["cohort"]: dict(status="scored", n=cell["cases"], candidates={name: scalar_summary(task, cell, .6 if name == "D" else .5) for name in "ABCD"},
                    D_minus_C_shot_weighted=dict(log_loss=.1, brier=0), D_minus_C_equal_game_weighted=dict(log_loss=.15, brier=.01),
                    per_game=["PRIVATE SENTINEL"], leave_one_game_out=["PRIVATE SENTINEL"]) for cell in support}
        report = dict(phase="evaluation_complete", new_model_selection=False, diagnostics=dict(cohorts=cohorts, exploratory_practical_yardstick=dict(met=False)))
    elif task == "baseball":
        targets = {}
        for cell in support:
            procedures = {}
            for name in ("constant", "context_table", "history_table", "context_logistic", "sequence_logistic"):
                procedures[name] = dict(fallback=None, model_status="fitted", calibration_status="fitted", raw_available=True, calibrated_available=True,
                    **{kind: scalar_summary(task, cell, .6 if name == "sequence_logistic" else .55 if name == "history_table" else .5) for kind in ("raw", "calibrated")})
            targets[cell["id"]] = dict(n=cell["cases"], games=cell["clusters"], procedures=procedures,
                eligibility_sha256="0" * 64, comparison=dict(available=True, useful_improvement_claim=False, **interval()),
                secondary_history_comparisons={f"history_minus_context_{kind}": interval(.05) for kind in ("raw", "calibrated")})
        report = dict(task=task, targets=targets)
    elif task == "tennis":
        cells = {}
        for cell in support:
            methods = {name: scalar_summary(task, cell, .6 if name.startswith("L_") else .5) for name in v.CONTRACTS[task]["models"]}
            contrasts = {kind: dict(main=f"L_{kind}", reference=f"B1_{kind}", demonstrated_improvement=False,
                        intervals={f"{method}_{weight}": interval(.1, .9875) for method in ("match", "tournament_year", "four_week") for weight in ("case", "group")}) for kind in ("uncalibrated", "calibrated")}
            cells[cell["id"]] = dict(status="evaluated", common_data=dict(n=cell["cases"], row_sha256="0" * 64), methods=methods, contrasts=contrasts)
        for cell in cells.values():
            for comparison in cell["contrasts"].values():
                comparison["intervals"]["tournament_year_group"].update(cases=25, original_points=200, matches=25)
                for weight in ("case", "group"):
                    comparison["intervals"][f"four_week_{weight}"] = dict(difference=.1, interval=[.05, .15], confidence=.9875,
                        calendar_bins=53, weeks_per_block=4, candidate_contiguous_blocks=50, populated_weeks=20, populated_blocks=40, weighting=weight)
        report = dict(stage="locked_2025_evaluation", as_of="20260122", class_order=["wide", "body", "T"], cells=cells)
    elif task == "baseball_mechanics":
        models = {name: dict(rows=571, groups=82, macro_MAE=.6 if name == "augmented" else .5, macro_RMSE=.8, row_MAE=.7, row_RMSE=.9) for name in ("mean", "context", "augmented")}
        report = dict(task=task, status="evaluation_complete", new_model_selection=False, rows=571, athletes=82, unit="mph", models=models,
                      primary=dict(difference=.1, interval95=[.05, .15], groups=82), practical_threshold_met=False, outer_folds=["PRIVATE SENTINEL"])
    else:
        models = {}
        for name in ("B0", "B1"):
            models[name] = {metric: dict(attempt_weighted=.6 if name == "B1" and metric == "joint_NLL" else .5,
                equal_player=.6 if name == "B1" and metric == "joint_NLL" else .5,
                attempts=548 if metric in ("joint_NLL", "net_Brier") else 437, players=8)
                for metric in ("joint_NLL", "net_Brier", "location_NLL", "euclidean_error", "ellipse90_covered")}
        report = dict(task=task, status="evaluation_complete", new_model_selection=False, rows=548, players=8,
                      observed_bounces=437, net_censored=111, lets_excluded=19, unit="nats per recorded non-let attempt; density per square meter", models=models,
                      primary=dict(difference=.1, interval95=[.05, .15], groups=8), attempt_weighted_contrast=.1,
                      practical_threshold_met=False, session_exclusion={"PRIVATE SENTINEL": "ignored"}, participant_level_results="PRIVATE SENTINEL")
    return report, support


class ProjectionTests(unittest.TestCase):
    def test_all_seven_synthetic_report_schemas_project_deterministically(self):
        for task in v.TASKS:
            with self.subTest(task=task):
                report, support = source_report(task); original = copy.deepcopy((report, support))
                result = p.project_report(task, report, support)
                self.assertEqual(result["status"], "candidate_aggregate_projection")
                v.validate_view(task, result["view"])
                self.assertEqual(result, p.project_report(task, report, support))
                self.assertEqual((report, support), original)
                self.assertNotIn("PRIVATE SENTINEL", json.dumps(result))
    def test_missing_support_never_repurposes_other_hashes(self):
        for task in v.TASKS:
            report, _ = source_report(task)
            result = p.project_report(task, report, [])
            self.assertIsNone(result["view"]); self.assertEqual(result["status"], "aggregate_projection_unavailable")
            self.assertTrue(result["unavailable"])
    def test_count_or_identity_contract_mismatch_rejected(self):
        report, support = source_report("soccer")
        support[0]["cases"] += 1
        with self.assertRaises(ValueError): p.project_report("soccer", report, support)
        for field, value in (("case_set_sha256", "bad"), ("cohort", "player_1"), ("cases", True)):
            report, support = source_report("soccer"); support[0][field] = value
            with self.assertRaises(ValueError): p.project_report("soccer", report, support)
    def test_no_new_gaps_from_marginal_metrics(self):
        report, support = source_report("soccer"); report.pop("primary")
        result = p.project_report("soccer", report, support)
        self.assertTrue(all(not target["comparisons"] for target in result["view"]["targets"]))
        self.assertTrue(result["view"]["targets"][0]["models"][0]["metrics"]["log_loss"]["status"] == "reported")
    def test_success_flags_do_not_become_unsupported_claims(self):
        report, support = source_report("football"); report["usefulness_yardstick_met"] = True
        result = p.project_report("football", report, support)
        self.assertTrue(all(row["criterion_met"] is None for row in result["view"]["targets"][0]["comparisons"]))
    def test_inconsistent_reported_contrast_rejected_not_recomputed(self):
        report, support = source_report("football"); report["primary_game_bootstrap"]["log_loss"]["difference"] = .99
        with self.assertRaises(ValueError): p.project_report("football", report, support)
    def test_missing_procedure_and_explicit_fallback_are_unavailable(self):
        report, support = source_report("baseball")
        report["targets"]["swing"]["procedures"]["sequence_logistic"]["fallback"] = "context_table"
        result = p.project_report("baseball", report, support)
        target = result["view"]["targets"][0]
        model = next(model for model in target["models"] if model["id"] == "sequence_logistic_calibrated")
        self.assertTrue(all(score["status"] == "procedure_unavailable" and score["value"] is None for score in model["metrics"].values()))
        self.assertFalse(any(row["model"] == model["id"] for row in target["comparisons"]))
        report, support = source_report("tennis"); report["cells"]["A1_m"]["methods"].pop("N_calibrated")
        result = p.project_report("tennis", report, support)
        model = next(model for model in result["view"]["targets"][0]["models"] if model["id"] == "N_calibrated")
        self.assertTrue(all(score["status"] == "not_reported" for score in model["metrics"].values()))
    def test_tennis_absent_evaluation_cell_stays_unavailable(self):
        report, support = source_report("tennis"); report["cells"]["A1_m"] = dict(status="no_available_evaluation_rows")
        result = p.project_report("tennis", report, support)
        self.assertEqual(len(result["view"]["targets"]), 3)
        self.assertIn("reported_aggregate_unavailable:A1_m:eligible", result["unavailable"])
    def test_reliability_exact_edges_no_invented_clusters_or_empty_bins(self):
        report, support = source_report("baseball")
        result = p.project_report("baseball", report, support)
        self.assertTrue(all(bucket["clusters"] is None for bucket in result["view"]["targets"][0]["reliability"][0]["bins"]))
        report["targets"]["swing"]["procedures"]["constant"]["raw"]["reliability"].pop()
        result = p.project_report("baseball", report, support)
        self.assertFalse(any(series["model"] == "constant_raw" for series in result["view"]["targets"][0]["reliability"]))
        report, support = source_report("football")
        report["procedures"]["constant_raw"]["reliability"][2]["upper"] = .3
        with self.assertRaises(ValueError): p.project_report("football", report, support)
    def test_contradictory_metric_conventions_rejected(self):
        report, support = source_report("tennis"); report["class_order"] = ["T", "body", "wide"]
        with self.assertRaises(ValueError): p.project_report("tennis", report, support)
        for key, value in (("log_clip_epsilon", .1), ("brier_definition", "mean squared class errors divided by classes"),
                           ("accuracy_tie_rule", "predict zero at p=.5"), ("log_loss_units", "bits per case")):
            report, support = source_report("football"); report["procedures"]["constant_raw"][key] = value
            with self.assertRaises(ValueError): p.project_report("football", report, support)

    def test_mechanics_units_and_metric_definitions_cannot_be_relabelled(self):
        for task, key, value in (("baseball_mechanics", "unit", "m/s"),
                                 ("baseball_mechanics", "macro_RMSE_definition", "sqrt of macro MSE"),
                                 ("tennis_execution", "unit", "nats per attempt with density per square foot"),
                                 ("tennis_execution", "ellipse90_mahalanobis_squared_cutoff", 2)):
            report, support = source_report(task); report[key] = value
            with self.assertRaises(ValueError): p.project_report(task, report, support)

    def test_contrast_case_and_group_support_uses_method_semantics(self):
        report, support = source_report("soccer"); report["primary"]["log_loss"]["cases"] = 99
        with self.assertRaises(ValueError): p.project_report("soccer", report, support)
        report, support = source_report("football"); report["week_dependence_sensitivity"]["log_loss"]["groups"] = 18
        p.project_report("football", report, support)  # weeks are not games
        report["primary_game_bootstrap"]["log_loss"]["groups"] = 18
        with self.assertRaises(ValueError): p.project_report("football", report, support)
        report, support = source_report("tennis")
        report["cells"]["A1_m"]["contrasts"]["calibrated"]["intervals"]["tournament_year_group"]["cases"] = 200
        with self.assertRaises(ValueError): p.project_report("tennis", report, support)
        report, support = source_report("tennis")
        report["cells"]["A1_m"]["contrasts"]["calibrated"]["intervals"]["four_week_case"]["weeks_per_block"] = 2
        with self.assertRaises(ValueError): p.project_report("tennis", report, support)

    def test_missing_uncertainty_support_does_not_invent_an_interval(self):
        report, support = source_report("soccer"); report["primary"]["log_loss"].pop("groups")
        result = p.project_report("soccer", report, support)
        row = result["view"]["targets"][1]["comparisons"][0]
        self.assertEqual((row["interval"], row["confidence"], row["uncertainty"]), (None, None, "paired_match_bootstrap"))
        self.assertEqual(row["delta"], .1)

    def test_multiple_unsupported_intervals_retain_distinct_declared_methods(self):
        report, support = source_report("football")
        for key in ("primary_game_bootstrap", "week_dependence_sensitivity"):
            for value in report[key].values(): value.pop("cases"); value.pop("groups")
        result = p.project_report("football", report, support)
        comparisons = result["view"]["targets"][0]["comparisons"]
        self.assertEqual(len(comparisons), 4)
        self.assertTrue(all(row["interval"] is None for row in comparisons))
        self.assertEqual({row["uncertainty"] for row in comparisons}, {"paired_game_bootstrap", "paired_week_bootstrap"})
        report, support = source_report("tennis")
        for section in report["cells"].values():
            for contrast in section["contrasts"].values():
                for value in contrast["intervals"].values():
                    for key in ("cases", "groups", "calendar_bins"): value.pop(key, None)
        result = p.project_report("tennis", report, support)
        self.assertTrue(all(row["interval"] is None for target in result["view"]["targets"] for row in target["comparisons"]))
        self.assertEqual(len(result["view"]["targets"][0]["comparisons"]), 12)

    def test_tennis_optional_tie_metadata_must_be_multiclass(self):
        report, support = source_report("tennis")
        summary = report["cells"]["A1_m"]["methods"]["B0_calibrated"]
        summary["accuracy_tie_rule"] = "class 1 when p >= 0.5, including exact ties"
        with self.assertRaises(ValueError): p.project_report("tennis", report, support)
        summary["accuracy_tie_rule"] = "argmax; ties choose the first class in [wide, body, T]"
        p.project_report("tennis", report, support)

    def test_contrast_weighting_metadata_cannot_change_the_estimand(self):
        report, support = source_report("soccer"); report["primary"]["log_loss"]["weighting"] = "group"
        with self.assertRaises(ValueError): p.project_report("soccer", report, support)
        report["primary"]["log_loss"]["weighting"] = "case"
        p.project_report("soccer", report, support)
        report, support = source_report("tennis")
        contrast = report["cells"]["A1_m"]["contrasts"]["calibrated"]["intervals"]["tournament_year_group"]
        contrast["weighting"] = "group"
        with self.assertRaises(ValueError): p.project_report("tennis", report, support)
        contrast["weighting"] = "match_macro_with_event_clusters"
        p.project_report("tennis", report, support)
        report, support = source_report("baseball")
        report["targets"]["swing"]["comparison"]["weighting"] = "group"
        with self.assertRaises(ValueError): p.project_report("baseball", report, support)
        report["targets"]["swing"]["comparison"]["weighting"] = "pitch-weighted whole-game resampling"
        p.project_report("baseball", report, support)
        report, support = source_report("tennis_execution"); report["primary"]["weighting"] = "case"
        with self.assertRaises(ValueError): p.project_report("tennis_execution", report, support)

    def test_no_per_group_records_are_traversed(self):
        class Forbidden:
            def __iter__(self): raise AssertionError("Private group records traversed")
            def get(self, *args): raise AssertionError("Private group records traversed")
        for task in ("basketball", "baseball_mechanics", "tennis_execution"):
            report, support = source_report(task)
            if task == "basketball":
                for section in report["diagnostics"]["cohorts"].values(): section["per_game"] = section["leave_one_game_out"] = Forbidden()
            elif task == "baseball_mechanics": report["outer_folds"] = Forbidden()
            else: report["session_exclusion"] = report["participant_level_results"] = Forbidden()
            self.assertIsNotNone(p.project_report(task, report, support)["view"])
    def test_bounce_denominator_and_density_units_retained(self):
        report, support = source_report("tennis_execution")
        report["models"]["B0"]["location_NLL"]["equal_player"] = -.3
        result = p.project_report("tennis_execution", report, support)
        score = result["view"]["targets"][0]["models"][0]["metrics"]["location_NLL_equal_player"]
        self.assertEqual((score["value"], score["cases"], score["clusters"]), (-.3, 437, 8))
        report["models"]["B0"]["location_NLL"]["attempts"] = 548
        with self.assertRaises(ValueError): p.project_report("tennis_execution", report, support)
    def test_censoring_counts_cannot_change_while_metrics_stay_constant(self):
        for key, value in (("observed_bounces", 436), ("net_censored", 112), ("lets_excluded", 0)):
            report, support = source_report("tennis_execution"); report[key] = value
            with self.assertRaises(ValueError): p.project_report("tennis_execution", report, support)

    def test_full_nonlet_metrics_require_all_eight_players(self):
        report, support = source_report("tennis_execution"); report["models"]["B0"]["net_Brier"]["players"] = 1
        with self.assertRaises(ValueError): p.project_report("tennis_execution", report, support)

    def test_incomplete_bounce_metric_stays_missing(self):
        report, support = source_report("tennis_execution"); report["models"]["B0"]["location_NLL"].pop("players")
        result = p.project_report("tennis_execution", report, support)
        self.assertIsNone(result["view"]["targets"][0]["models"][0]["metrics"]["location_NLL_equal_player"]["value"])
    def test_not_completed_report_refused(self):
        report, support = source_report("soccer"); report["phase"] = "development_complete"
        with self.assertRaises(ValueError): p.project_report("soccer", report, support)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic-projection-test-"); self.root = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def write(self, path, value):
        dest = self.root / path; dest.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(value, sort_keys=True).encode(); dest.write_bytes(raw); return v._digest(raw)
    def install(self):
        tasks, freeze = {}, {"schema_version": 1, "tasks": {}}
        for task in v.TASKS:
            report, support = source_report(task)
            body = dict(task=task, evaluation_cohort=list(v.TASKS), metadata=dict(artifact_id="b" * 64), synthetic_test_only=True)
            binding_hash = v._digest(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
            binding = dict(body, binding_sha256=binding_hash)
            self.write(f"artifacts/tactical/{task}/run_binding.json", binding)
            selection_path = f"artifacts/tactical/{task}/SELECTION_FREEZE.json"
            selection_hash = self.write(selection_path, {"synthetic_test_only": True, "task": task})
            freeze["tasks"][task] = dict(binding_sha256=binding_hash, selection_path=selection_path, selection_sha256=selection_hash)
            tasks[task] = dict(status="verified_final", binding_sha256=binding_hash, selection_sha256=selection_hash,
                              final_report_sha256=self.write(v._final_path(task, binding), report),
                              checks={key: True for key in v.NUMERICAL_CHECKS}, aggregate_view_support=support)
        audit = dict(schema_version=1, review_type="tactical_final_numerical_review", status="verified_final", independent=True,
                     reviewer="SYNTHETIC TEST ONLY, NOT APPROVAL", evaluation_freeze_sha256=self.write(v.GLOBAL_FREEZE, freeze), tasks=tasks)
        self.write(v.NUMERICAL_REVIEW, audit)
        return audit
    def test_missing_or_pending_audit_reads_no_final_report(self):
        paths = []
        with patch.object(p, "_read", side_effect=lambda root, path: paths.append(path) or (_ for _ in ()).throw(FileNotFoundError())):
            with self.assertRaises(FileNotFoundError): p.prepare_candidates(self.root)
        self.assertEqual(paths, [v.NUMERICAL_REVIEW])
        self.write(v.NUMERICAL_REVIEW, dict(status="pending"))
        with patch.object(p, "_read", wraps=p._read) as read:
            with self.assertRaises(ValueError): p.prepare_candidates(self.root)
        self.assertEqual([call.args[1] for call in read.call_args_list], [v.NUMERICAL_REVIEW])
    def test_full_driver_writes_only_candidate_paths_without_review(self):
        self.install()
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        candidates = p.prepare_candidates(self.root)
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})
        paths = p.write_candidates(self.root, candidates)
        self.assertEqual(set(paths), set(v.TASKS))
        self.assertTrue(all(path.startswith(p.CANDIDATE_DIRECTORY + "/") for path in paths.values()))
        self.assertFalse((self.root / v.REVIEW).exists()); self.assertFalse((self.root / v.SNAPSHOT_REVIEW).exists())
        self.assertFalse((self.root / v.VIEW_DIRECTORY).exists())
        with self.assertRaises(FileExistsError): p.write_candidates(self.root, candidates)
    def test_every_read_path_is_metadata_or_final_aggregate(self):
        self.install()
        with patch.object(p, "_read", wraps=p._read) as read: p.prepare_candidates(self.root)
        paths = [call.args[1] for call in read.call_args_list]
        self.assertEqual(len(paths), 23)  # audit, global freeze, seven selection/binding/report streams
        self.assertFalse(any(token in path for path in paths for token in ("predictions", "targets", "private", ".pkl", ".joblib", ".npz")))
        first_report = next(i for i, path in enumerate(paths) if path.endswith(("evaluation.json", "evaluation_report.json", "EVALUATION.json")))
        self.assertTrue(all(f"artifacts/tactical/{task}/run_binding.json" in paths[:first_report] for task in v.TASKS))
    def test_wrong_binding_closes_before_report_access(self):
        self.install(); self.write("artifacts/tactical/tennis/run_binding.json", [])
        with patch.object(p, "_read", wraps=p._read) as read:
            with self.assertRaises(ValueError): p.prepare_candidates(self.root)
        self.assertFalse(any(call.args[1].endswith(("evaluation.json", "evaluation_report.json", "EVALUATION.json")) for call in read.call_args_list))
    def test_changed_final_report_rejected_without_candidate_write(self):
        self.install(); path = self.root / "reports/tactical/soccer/model/evaluation.json"; path.write_text(path.read_text() + " ")
        with self.assertRaises(ValueError): p.prepare_candidates(self.root)
        self.assertFalse((self.root / p.CANDIDATE_DIRECTORY).exists())
    def test_large_final_report_projects_only_after_exact_rebinding(self):
        audit = self.install()
        path = self.root / "reports/tactical/football/model/evaluation.json"
        raw = path.read_bytes().ljust(3_627_586, b" "); path.write_bytes(raw)
        with self.assertRaises(ValueError): p.prepare_candidates(self.root)
        self.assertFalse((self.root / p.CANDIDATE_DIRECTORY).exists())
        audit["tasks"]["football"]["final_report_sha256"] = v._digest(raw)
        self.write(v.NUMERICAL_REVIEW, audit)
        candidates = p.prepare_candidates(self.root)
        self.assertIsNotNone(candidates["football"]["view"])
        self.assertLess(len(json.dumps(candidates["football"]["view"])), v.MAX_BYTES)
        self.assertFalse((self.root / p.CANDIDATE_DIRECTORY).exists())
        with path.open("wb") as stream: stream.truncate(v.FINAL_REPORT_MAX_BYTES + 1)
        with self.assertRaises(ValueError): p.prepare_candidates(self.root)
        self.assertFalse((self.root / p.CANDIDATE_DIRECTORY).exists())
    def test_candidate_writer_rechecks_authority_and_exact_contents(self):
        self.install(); candidates = p.prepare_candidates(self.root)
        candidates["soccer"]["view"]["targets"][0]["models"][0]["metrics"]["log_loss"]["value"] = .01
        with self.assertRaises(ValueError): p.write_candidates(self.root, candidates)
        self.assertFalse((self.root / p.CANDIDATE_DIRECTORY).exists())
        candidates = p.prepare_candidates(self.root)
        (self.root / v.NUMERICAL_REVIEW).unlink()
        with self.assertRaises(FileNotFoundError): p.write_candidates(self.root, candidates)
        self.assertFalse((self.root / p.CANDIDATE_DIRECTORY).exists())

    def test_fixed_read_paths_reject_file_and_parent_aliases(self):
        for relative in (v.NUMERICAL_REVIEW, v.GLOBAL_FREEZE, "artifacts/tactical/baseball/SELECTION_FREEZE.json",
                         "artifacts/tactical/baseball/run_binding.json", "reports/tactical/soccer/model/evaluation.json"):
            self.install()
            allowed = self.root / relative
            hidden = self.root / "private_must_not_be_opened.json"
            allowed.rename(hidden); allowed.symlink_to(hidden)
            with self.assertRaises(ValueError): p.prepare_candidates(self.root)
            allowed.unlink(); hidden.rename(allowed)
        self.install()
        directory = self.root / "reports"; hidden = self.root / "private_reports"; directory.rename(hidden)
        directory.symlink_to(hidden, target_is_directory=True)
        with self.assertRaises(ValueError): p.prepare_candidates(self.root)
        self.assertFalse((self.root / p.CANDIDATE_DIRECTORY).exists())

    def test_candidate_directory_alias_cannot_write_served_views(self):
        self.install(); candidates = p.prepare_candidates(self.root)
        served = self.root / v.VIEW_DIRECTORY; served.mkdir(parents=True)
        (self.root / p.CANDIDATE_DIRECTORY).symlink_to(served, target_is_directory=True)
        with self.assertRaises(ValueError): p.write_candidates(self.root, candidates)
        self.assertEqual(list(served.iterdir()), [])

    def test_candidate_parent_and_file_aliases_are_rejected(self):
        self.install(); candidates = p.prepare_candidates(self.root)
        original = self.root / "artifacts"; moved = self.root / "moved_artifacts"; original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(ValueError): p.write_candidates(self.root, candidates)
        original.unlink(); moved.rename(original)
        directory = self.root / p.CANDIDATE_DIRECTORY; directory.mkdir(parents=True)
        (directory / "soccer.json").symlink_to(self.root / v.VIEW_DIRECTORY / "soccer.json")
        with self.assertRaises(ValueError): p.write_candidates(self.root, candidates)
        self.assertFalse((self.root / v.VIEW_DIRECTORY).exists())

    def test_no_support_creates_no_candidate_numbers(self):
        audit = self.install()
        for record in audit["tasks"].values(): record.pop("aggregate_view_support")
        self.write(v.NUMERICAL_REVIEW, audit)
        candidates = p.prepare_candidates(self.root)
        self.assertTrue(all(result["view"] is None for result in candidates.values()))
        self.assertEqual(p.write_candidates(self.root, candidates), {})
        self.assertFalse((self.root / p.CANDIDATE_DIRECTORY).exists())


if __name__ == "__main__": unittest.main()
