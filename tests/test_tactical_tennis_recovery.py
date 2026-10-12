"""Synthetic/mocked recovery tests. Never open project target rows or fit models."""
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import pickle
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from experiments.tactical import tennis_model as m
from experiments.tactical import tennis_recovery as r


class FakeModel:
    def predict_proba(self, X):
        return np.full((len(X), 3), 1/3)


class FakePreprocessor:
    def __init__(self, task="A2"):
        self.task = task

    def fit(self, numeric, categorical, *, stage):
        assert stage == "train"
        return self

    def transform(self, numeric, categorical, *, family):
        return numeric

    def manifest(self):
        return {"fit_stage": "train", "synthetic": True}


class FakeDataset:
    def __init__(self, path, *, root, stage):
        assert stage in ("train", "selection", "calibration")
        self.n = 6
        self.numeric = np.zeros((6, len(m.NUMERIC_NAMES)))
        self.categorical = np.zeros((6, 10), dtype=np.int32)
        self.baselines = np.full((6, 5, 3), 1/3)
        self.labels = np.array([0, 1, 2, 0, 1, 2])
        self.manifest = {"row_sha256": "synthetic", "categorical_columns": 10}

    def supports(self, stage):
        return {"sufficient": True, "synthetic": True}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dest = m.artifact_dir(self.root)
        self.dest.mkdir(parents=True)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.approval = {"status": "approved", "binding_sha256": r.ORIGINAL_BINDING, "reference": "synthetic_original"}
        self.stack.enter_context(patch.object(r.gates, "require_stage", return_value={"binding_sha256": r.ORIGINAL_BINDING, "approval": self.approval}))
        self.stack.enter_context(patch.object(r.gates, "verify_binding", return_value={"binding_sha256": r.ORIGINAL_BINDING}))
        self.stack.enter_context(patch.object(m, "optimizer_resource_limits", side_effect=lambda *a: nullcontext()))
        self.stack.enter_context(patch.object(m, "threadpool_limits", side_effect=lambda **k: nullcontext()))
        for name in r.WRAPPER_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic frozen wrapper\n")
        protocol = self.root / m.PROTOCOL
        protocol.parent.mkdir(parents=True, exist_ok=True)
        protocol.write_text("synthetic frozen protocol\n")
        r.durable_json(self.dest / "run_binding.json", {"binding_sha256": r.ORIGINAL_BINDING})
        for name in ("development_rows.json", "development_history.pkl", "training_actors.pkl"):
            (self.dest / name).write_bytes(b"synthetic unchanged\n")
        r.durable_json(self.dest / "resource_probe.json", {"admitted": True, "status": "succeeded"})
        self.completed_bytes = {}
        for cell in r.COMPLETED_CELLS:
            bundle = {"cell": tuple(cell.split("_")), "selected": {"B0": 0, "B1": 0, "L": .1, "N": 15},
                      "models": {"L": FakeModel(), "N": FakeModel()}, "preprocessor": FakePreprocessor("A1"), "main": "B0"}
            m._save_pickle(self.dest / (cell + "_selected.pkl"), bundle)
            r.durable_json(self.dest / (cell + "_selection.json"), {"status": "selected", "selected_parameters": bundle["selected"]})
            (self.dest / (cell + "_selection_predictions.npz")).write_bytes(b"synthetic A1 predictions\n")
            for suffix in r.SUFFIXES:
                self.completed_bytes[cell+suffix] = (self.dest / (cell+suffix)).read_bytes()
        for stage in ("train", "selection"):
            for cell in map(m.cell_name, m.CELLS):
                directory = self.dest / "rows" / stage / cell
                directory.mkdir(parents=True)
                (directory / "labels.dat").write_bytes(b"opaque synthetic labels; never parsed by prepare")
        for sport in ("baseball", "football", "soccer", "tennis"):
            path = self.root / f"artifacts/{sport}/holdout_predictions.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"original forecast\n")
        for task in ("baseball_mechanics", "basketball", "football", "soccer", "tennis_execution"):
            path = self.root / f"artifacts/tactical/{task}/SELECTION_FREEZE.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"original completed freeze\n")
        self.attempts = []
        self.reservations = []
        order = [("A1_m", "probe", 15)]
        order += [(cell, family, p) for cell in r.COMPLETED_CELLS for family, grid in (("L", m.L_GRID), ("N", m.N_GRID)) for p in grid]
        order += [("A2_m", "L", .1)]
        start = datetime(2026, 10, 11, 10, 29, tzinfo=timezone.utc)
        for i, (cell, family, parameter) in enumerate(order, 1):
            status = "started" if i == 12 else "succeeded"
            self.attempts.append({"number": i, "cell": cell, "family": family, "parameter": parameter,
                                  "retry": False, "status": status, "started_utc": "2026-10-11T03:30:00",
                                  **({"stage_cpu_seconds": 223.448918327} if i == 11 else {})})
            self.append_operation(r.operation_id(cell, family, parameter), reserved_at=(start + timedelta(seconds=i)).isoformat(), write=False)
        r.durable_json(self.dest / "fit_attempts.json", self.attempts)
        (self.dest / "development_operations.jsonl").write_bytes(b"".join(r.gates.canonical_bytes(x)+b"\n" for x in self.reservations))
        self.original_journal = (self.dest / "development_operations.jsonl").read_bytes()
        self.original_fit = (self.dest / "fit_attempts.json").read_bytes()
        self.absence = "2026-10-11T10:40:00+00:00"
        self.evidence = "artifacts/tactical/tennis/interruption_evidence.json"
        r.durable_json(self.root / self.evidence, {"current_executor_process_check_observation_utc": "2026-10-11T10:39:51+00:00",
                                                "conservative_absence_accounting_bound_utc": self.absence})

    def append_operation(self, identity, *, reserved_at=None, write=True):
        if write:
            self.reservations = r.journal(self.root)[1]
        record = {"task": "tennis", "stage": "development", "operation_id": identity, "kind": "fit", "config": {},
                  "binding_sha256": r.ORIGINAL_BINDING, "attempt": len(self.reservations)+1, "limit": 49,
                  "reserved_at_utc": reserved_at or r.utc_now(),
                  "previous_record_sha256": self.reservations[-1]["record_sha256"] if self.reservations else None}
        record["record_sha256"] = m.json_hash(record)
        self.reservations.append(record)
        if write:
            with (self.dest / "development_operations.jsonl").open("ab") as stream:
                stream.write(r.gates.canonical_bytes(record)+b"\n")
        return len(self.reservations)

    def prepare(self):
        return r.prepare(self.root, process_absence_utc=self.absence, absence_evidence_path=self.evidence)

    def approve(self):
        binding = self.prepare()
        out = r.recovery_dir(self.root)
        review = {"schema_version": 1, "review_type": "tennis_recovery_review", "status": "cleared",
                  "recovery_binding_sha256": binding["recovery_binding_sha256"], "original_binding_sha256": r.ORIGINAL_BINDING,
                  "cleared_stages": ["development"], "reviewed_at_utc": r.utc_now()}
        path = out / "review.json"
        r.durable_json(path, review)
        approval = {"schema_version": 1, "status": "approved", "recovery_binding_sha256": binding["recovery_binding_sha256"],
                    "original_binding_sha256": r.ORIGINAL_BINDING, "approval_reference": "synthetic lead approval",
                    "approved_at_utc": r.utc_now(), "review_manifest_path": str(path.relative_to(self.root)), "review_manifest_sha256": r.digest(path)}
        r.durable_json(out / "RECOVERY_APPROVAL.json", approval)
        return binding

    def ledger(self):
        binding = self.approve()
        r.apply_disposition(self.root, binding)
        return binding, r.RecoveryLedger(self.root, binding)

    def fake_fit(self, root, ledger, cell, family, parameter, X, labels, *, retry=False):
        self.append_operation(r.operation_id(m.cell_name(cell), family, parameter, retry))
        with ledger.attempt(m.cell_name(cell), family, parameter, retry=retry):
            model = FakeModel()
        return model, "succeeded"

    def test_prepare_does_not_read_labels_or_mutate_original_state(self):
        with patch.object(m, "Dataset", side_effect=AssertionError("label read")), patch.object(m, "SourceReader", side_effect=AssertionError("source read")), patch.object(m, "fit_candidate", side_effect=AssertionError("fit")), patch.object(m, "_load_local_pickle", side_effect=AssertionError("unpickle")):
            binding = self.prepare()
        self.assertEqual((self.dest / "fit_attempts.json").read_bytes(), self.original_fit)
        self.assertEqual((self.dest / "development_operations.jsonl").read_bytes(), self.original_journal)
        self.assertFalse((r.recovery_dir(self.root) / "LOST_ATTEMPT_DISPOSITION.json").exists())
        self.assertEqual(len(binding["allowed_attempts"]), 30)
        self.assertEqual(len(binding["preserved_files_sha256"]), 28)
        self.assertEqual((r.recovery_dir(self.root) / "pre_recovery/fit_attempts.json").read_bytes(), self.original_fit)

    def test_exact_remaining_allowlist_and_missing_candidate_bar(self):
        binding, ledger = self.ledger()
        allowed = r.attempt_allowlist()
        self.assertEqual(sum(x["family"] == "temperature" for x in allowed), 16)
        self.assertEqual(sum(x["retry"] for x in allowed), 5)
        self.assertEqual(sum(x["family"] != "temperature" and not x["retry"] for x in allowed), 9)
        for retry in (False, True):
            with self.assertRaises(PermissionError): ledger._check("A2_m", "L", .1, retry)
        for spec in (("A1_m", "L", 1., False), ("A1_m", "probe", 15, False), ("A2_w", "N", 63, False)):
            with self.assertRaises(PermissionError): ledger._check(*spec)
        with self.assertRaises(RuntimeError): ledger._check("A2_w", "L", .1, True)
        ledger.records.append({"cell": "A2_w", "family": "L", "parameter": .1, "status": "convergence_warning"})
        ledger._check("A2_w", "L", .1, True)

    def test_explicit_approval_and_review_are_required(self):
        binding = self.prepare()
        with self.assertRaises((FileNotFoundError, PermissionError)): r.apply_disposition(self.root, binding)
        self.assertEqual((self.dest / "fit_attempts.json").read_bytes(), self.original_fit)
        binding = self.approve()
        r.verify_recovery(self.root)
        path = r.recovery_dir(self.root) / "review.json"
        path.write_text(path.read_text()+" ")
        with self.assertRaises(PermissionError): r.verify_recovery(self.root)

    def test_stale_wrapper_hash_and_snapshot_fail_closed(self):
        self.approve()
        path = self.root / r.WRAPPER_FILES[0]
        original = path.read_bytes()
        path.write_bytes(original+b"changed")
        with self.assertRaises(PermissionError): r.verify_recovery(self.root)
        path.write_bytes(original)
        path = r.recovery_dir(self.root) / "pre_recovery/fit_attempts.json"
        path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaises(PermissionError): r.verify_recovery(self.root)

    def test_disposition_preserves_shared_prefix_and_completed_artifacts(self):
        binding = self.approve()
        r.apply_disposition(self.root, binding)
        r.apply_disposition(self.root, binding)
        after = r.read_json(self.dest / "fit_attempts.json")
        self.assertEqual(after[:11], self.attempts[:11])
        self.assertEqual(after[11]["status"], "interrupted_no_result")
        self.assertNotIn("cpu_seconds", after[11])
        self.assertFalse(after[11]["retry_permitted"])
        self.assertEqual((self.dest / "development_operations.jsonl").read_bytes(), self.original_journal)
        for name, data in self.completed_bytes.items():
            self.assertEqual((self.dest/name).read_bytes(), data)
        path = self.dest / "A1_m_selected.pkl"
        path.write_bytes(path.read_bytes()+b"changed")
        with self.assertRaises(PermissionError): r.verify_recovery(self.root)

    def test_shared_journal_prefix_edit_or_undeclared_append_is_rejected(self):
        self.approve()
        self.append_operation("A2_m:L:0.1:retry")
        with self.assertRaises(PermissionError): r.verify_recovery(self.root)
        (self.dest / "development_operations.jsonl").write_bytes(b" "+self.original_journal)
        with self.assertRaises(PermissionError): r.verify_recovery(self.root)

    def test_conservative_cpu_budget_uses_aware_shared_time(self):
        debit = r.cpu_debit(self.reservations, self.attempts, self.absence)
        seconds = (r.aware(self.absence)-r.aware(self.reservations[10]["reserved_at_utc"])).total_seconds()
        self.assertEqual(debit["baseline_cpu_seconds"], 223.448918327+4*seconds)
        self.assertEqual(debit["uncertain_window_start_utc"], self.reservations[10]["reserved_at_utc"])
        with self.assertRaises(ValueError): r.cpu_debit(self.reservations, self.attempts, "2026-10-11T10:40:00")
        binding, ledger = self.ledger()
        totals = ledger.check_budget()
        self.assertAlmostEqual(totals["budget_charged_cpu_seconds"]-totals["measured_completed_cpu_seconds"], debit["conservative_unobserved_cpu_seconds"])
        ledger.prior_stage_cpu = 5401
        with self.assertRaises(m.BudgetExceeded): ledger.check_budget()
        with self.assertRaises(RuntimeError): ledger._check("A2_m", "L", 1., False)

    def test_model_checkpoint_resumes_without_duplicate_fit(self):
        binding, ledger = self.ledger()
        with patch.object(m, "fit_candidate", side_effect=self.fake_fit) as fitted:
            result = r.candidate_attempt(self.root, binding, ledger, ("A2", "m"), "L", 1., np.zeros((3, 2)), np.arange(3))
            new_ledger = r.RecoveryLedger(self.root, binding)
            restored = r.candidate_attempt(self.root, binding, new_ledger, ("A2", "m"), "L", 1., None, None)
            self.assertEqual(fitted.call_count, 1)
        self.assertEqual(restored["status"], result["status"])
        self.assertIsInstance(restored["model"], FakeModel)
        self.assertEqual(len(r.journal(self.root)[1]), 13)
        self.assertTrue((self.dest/"development_operations.jsonl").read_bytes().startswith(self.original_journal))

    def test_reserved_without_checkpoint_never_retries(self):
        binding, ledger = self.ledger()
        self.append_operation("A2_m:L:1.0:initial")
        with patch.object(m, "fit_candidate") as fitted:
            with self.assertRaisesRegex(PermissionError, "no durable result"):
                r.candidate_attempt(self.root, binding, ledger, ("A2", "m"), "L", 1., None, None)
            fitted.assert_not_called()

    def test_unclean_recovery_session_cannot_reset_cpu(self):
        binding, ledger = self.ledger()
        r.durable_json(r.recovery_dir(self.root)/"executor_session.json", {"status": "running"})
        with self.assertRaisesRegex(PermissionError, "additional CPU debit"):
            with r.exclusive_session(self.root, binding, ledger): pass

    def test_all_four_freeze_barrier_precedes_any_calibration(self):
        binding, ledger = self.ledger()
        with patch.object(m, "build_rows") as build, patch.object(m, "minimize_scalar") as optimizer:
            with self.assertRaises(PermissionError): r.calibrate_remaining(self.root, binding, ledger)
            build.assert_not_called(); optimizer.assert_not_called()
        with patch.object(m, "verify_selection_freeze", return_value={"recovery_binding_sha256": "stale"}):
            with self.assertRaises(PermissionError): ledger._check("A1_m", "temperature", "B0", False)

    def test_complete_mocked_run_preserves_a1_and_uses_exact_grid(self):
        binding = self.approve()
        def build_calibration(root, phase):
            self.assertEqual(phase, "calibration")
            frozen = m.verify_selection_freeze(root, calibrated=False)
            self.assertEqual(set(frozen["cells"]), set(map(m.cell_name, m.CELLS)))
            r.durable_json(self.dest/"calibration_rows.json", {"synthetic": True})
            (self.dest/"calibration_history.pkl").write_bytes(b"synthetic")
        def record_operation(root, task, stage, identity, config, limit, kind="fit"):
            self.assertEqual(limit, 49)
            return self.append_operation(identity)
        # Wiring-only fixture: production runtime pins remain independently enforced.
        synthetic_runtime = {"synthetic": True, "scope": "unit_test_only"}
        with patch.object(m, "verify_runtime", return_value=synthetic_runtime) as runtime_check, \
             patch.object(m, "Dataset", FakeDataset), patch.object(m, "Preprocessor", FakePreprocessor), patch.object(m, "fit_candidate", side_effect=self.fake_fit) as fitted, patch.object(m, "build_rows", side_effect=build_calibration), patch.object(r.gates, "record_operation", side_effect=record_operation), patch.object(m, "minimize_scalar", return_value=SimpleNamespace(success=True, x=0., fun=1., nfev=3)) as optimizer:
            frozen = r.run(self.root)
            second = r.run(self.root)
        runtime_check.assert_called()
        self.assertEqual(frozen["runtime"], synthetic_runtime)
        self.assertEqual(fitted.call_count, 9)
        self.assertEqual(optimizer.call_count, 16)
        self.assertEqual(m.json_hash(frozen), m.json_hash(second))
        self.assertEqual(frozen["optimizer_attempts"], 37)
        self.assertEqual(frozen["missing_candidate"]["operation_id"], r.LOST_ID)
        self.assertEqual(frozen["recovery_binding_sha256"], binding["recovery_binding_sha256"])
        self.assertEqual(frozen["attempt_summary"]["interrupted_no_result"], 1)
        self.assertTrue((self.dest/"development_operations.jsonl").read_bytes().startswith(self.original_journal))
        self.assertNotIn("0.1", r.read_json(self.dest/"A2_m_selection.json")["all_candidate_selection_losses"]["L"])
        for name, data in self.completed_bytes.items(): self.assertEqual((self.dest/name).read_bytes(), data)
        self.assertFalse((self.dest/"rows/evaluation").exists())


if __name__ == "__main__":
    unittest.main()
