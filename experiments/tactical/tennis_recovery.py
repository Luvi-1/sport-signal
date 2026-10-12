"""Separately approved, no-repeat recovery of the interrupted tennis development.

Inspection/preparation hash bytes and parse bookkeeping only. The original
model, parser, metrics, protocol and gate files are never modified. See
TENNIS_RECOVERY.md for the deliberately narrow recovery contract.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import time
import uuid

from . import gates
from . import tennis_model as m

ORIGINAL_BINDING = "38d558b3d1847367cacf76a7e314e16fc85fb062b38c4f2d9c0a4c661210c7b6"
WRAPPER_FILES = ("experiments/tactical/tennis_recovery.py",
                 "tests/test_tactical_tennis_recovery.py", "docs/tactical/TENNIS_RECOVERY.md")
LOST_ID = "A2_m:L:0.1:initial"
COMPLETED_CELLS = ("A1_m", "A1_w")
REMAINING_CELLS = ("A2_m", "A2_w")
SUFFIXES = ("_selected.pkl", "_selection.json", "_selection_predictions.npz")
CPU_CAP = 5400.0
RSS_CAP = 4 * 1024**3


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def aware(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Recovery timestamps must be timezone-aware; naive fit timestamps are not UTC")
    return result


def digest(path):
    return gates.digest_file(Path(path))


def read_json(path):
    return json.loads(Path(path).read_text())


def durable_bytes(path, data, *, immutable=False):
    """Fsync data and directory; a published checkpoint is never partially visible."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        if path.read_bytes() != data:
            raise PermissionError("Refusing to replace immutable recovery artifact: " + str(path))
        return
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    with temp.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_json(path, value, *, immutable=False):
    durable_bytes(path, gates.canonical_bytes(value) + b"\n", immutable=immutable)


def recovery_dir(root):
    return m.artifact_dir(root) / "recovery"


def operation_id(cell, family, parameter, retry=False):
    if family == "temperature":
        return f"{cell}:temperature:{parameter}"
    return f"{cell}:{family}:{parameter}:{'retry' if retry else 'initial'}"


def attempt_allowlist():
    attempts = []
    for cell in REMAINING_CELLS:
        for family, parameters in (("L", (1.0, 10.0) if cell == "A2_m" else m.L_GRID), ("N", m.N_GRID)):
            for parameter in parameters:
                attempts.append({"operation_id": operation_id(cell, family, parameter),
                                 "cell": cell, "family": family, "parameter": parameter,
                                 "retry": False, "condition": "unreserved_original_candidate"})
                if family == "L":
                    attempts.append({"operation_id": operation_id(cell, family, parameter, True),
                                     "cell": cell, "family": family, "parameter": parameter,
                                     "retry": True, "condition": "same_initial_convergence_warning_only"})
    for cell in map(m.cell_name, m.CELLS):
        for family in ("B0", "B1", "L", "N"):
            attempts.append({"operation_id": operation_id(cell, "temperature", family),
                             "cell": cell, "family": "temperature", "parameter": family,
                             "retry": False, "condition": "all_four_candidates_frozen_and_family_selected_and_support_sufficient"})
    return attempts


def journal(root):
    path = m.artifact_dir(root) / "development_operations.jsonl"
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise PermissionError("Incomplete shared journal record")
    records = [json.loads(line) for line in data.splitlines()]
    previous = None
    for number, record in enumerate(records, 1):
        body = {k: v for k, v in record.items() if k != "record_sha256"}
        if (record.get("previous_record_sha256") != previous or
                m.json_hash(body) != record.get("record_sha256") or
                record.get("attempt") != number or record.get("limit") != 49 or
                record.get("binding_sha256") != ORIGINAL_BINDING or
                record.get("task") != "tennis" or record.get("stage") != "development"):
            raise PermissionError("Shared operation journal integrity failure")
        aware(record["reserved_at_utc"])
        previous = record["record_sha256"]
    ids = [r["operation_id"] for r in records]
    if len(ids) != len(set(ids)) or len(records) > 49:
        raise PermissionError("Duplicate operation or shared ceiling exceeded")
    return data, records


def cpu_debit(records, attempts, absence_utc):
    """Overcharge overlap using last completed reservation, never naive fit time."""
    if len(records) != 12 or len(attempts) != 12:
        raise PermissionError("Recovery requires the exact twelve-attempt interruption")
    if records[-1]["operation_id"] != LOST_ID or attempts[-1].get("status") != "started":
        raise PermissionError("The declared lost attempt is not the sole unfinished tail")
    if any(r.get("status") != "succeeded" for r in attempts[:-1]):
        raise PermissionError("Expected eleven succeeded attempts before interruption")
    for attempt, reservation in zip(attempts, records):
        if operation_id(attempt["cell"], attempt["family"], attempt["parameter"], attempt["retry"]) != reservation["operation_id"]:
            raise PermissionError("Fit and operation ledgers disagree")
    start = records[-2]["reserved_at_utc"]
    seconds = (aware(absence_utc) - aware(start)).total_seconds()
    if seconds < 0 or aware(absence_utc) < aware(records[-1]["reserved_at_utc"]):
        raise ValueError("Absence check precedes interruption")
    recorded = max(float(r.get("stage_cpu_seconds", 0)) for r in attempts)
    charged = recorded + 4 * seconds
    if not math.isfinite(charged) or charged < 0:
        raise ValueError("Invalid CPU debit")
    return {"recorded_cpu_seconds": recorded, "uncertain_window_start_utc": start,
            "conservative_absence_accounting_bound_utc": absence_utc, "uncertain_wall_seconds": seconds,
            "threads_charged": 4, "conservative_unobserved_cpu_seconds": 4 * seconds,
            "baseline_cpu_seconds": charged, "remaining_cpu_seconds": max(0., CPU_CAP - charged),
            "cpu_limit_seconds": CPU_CAP, "overlap_deliberately_double_charged": True}


def preserved_paths(root):
    dest = m.artifact_dir(root)
    files = [dest / name for name in ("run_binding.json", "development_rows.json", "development_history.pkl",
                                      "training_actors.pkl", "resource_probe.json")]
    files += [dest / (cell + suffix) for cell in COMPLETED_CELLS for suffix in SUFFIXES]
    files += sorted((dest / "rows" / "train").rglob("*"))
    files += sorted((dest / "rows" / "selection").rglob("*"))
    # Original forecasts and all completed tactical freezes are preserved byte-for-byte.
    for sport in ("baseball", "football", "soccer", "tennis"):
        files += [Path(root) / f"artifacts/{sport}/holdout_predictions.csv"]
    files += sorted((Path(root) / "artifacts/tactical").glob("*/SELECTION_FREEZE.json"))
    return sorted({path for path in files if path.is_file()})


def inspect(root, *, process_absence_utc, absence_evidence_path):
    """Read-only: no unpickle, Dataset, source reader, fitting, or disposition write."""
    root = Path(root).resolve()
    checked = gates.require_stage(root, "tennis", "development")
    if checked["binding_sha256"] != ORIGINAL_BINDING:
        raise PermissionError("Recovery cannot rebind the original development")
    dest = m.artifact_dir(root)
    if (dest / "CANDIDATE_FREEZE.json").exists() or (dest / "SELECTION_FREEZE.json").exists():
        raise PermissionError("Initial recovery preparation is only for the interrupted pre-freeze stage")
    if any((dest / (cell + suffix)).exists() for cell in REMAINING_CELLS for suffix in SUFFIXES):
        raise PermissionError("Unexpected completed remaining-cell artifact")
    data, records = journal(root)
    attempts = read_json(dest / "fit_attempts.json")
    debit = cpu_debit(records, attempts, process_absence_utc)
    probe = read_json(dest / "resource_probe.json")
    if not probe.get("admitted") or probe.get("status") != "succeeded":
        raise PermissionError("The original admitted probe must be reused")
    evidence = gates.resolve(root, absence_evidence_path)
    # The lead/reviewer attests this evidence; preparation does not infer absence.
    evidence_value = read_json(evidence)
    if evidence_value.get("conservative_absence_accounting_bound_utc") != process_absence_utc:
        raise PermissionError("Absence accounting endpoint differs from the saved evidence")
    if aware(evidence_value["current_executor_process_check_observation_utc"]) > aware(process_absence_utc):
        raise PermissionError("Accounting endpoint predates observed process absence")
    paths = preserved_paths(root)
    expected = {dest / (cell + suffix) for cell in COMPLETED_CELLS for suffix in SUFFIXES}
    if not expected.issubset(paths):
        raise PermissionError("Missing completed-cell artifacts")
    return {"schema_version": 1, "original_binding_sha256": ORIGINAL_BINDING,
            "original_journal_records": 12, "original_journal_bytes": len(data),
            "original_journal_sha256": hashlib.sha256(data).hexdigest(),
            "original_attempts_sha256": digest(dest / "fit_attempts.json"),
            "wrapper_files_sha256": {p: digest(root / p) for p in WRAPPER_FILES},
            "preserved_files_sha256": {str(p.relative_to(root)): digest(p) for p in paths},
            "absence_evidence": {"path": str(evidence.relative_to(root)), "sha256": digest(evidence)},
            "cpu_debit": debit, "allowed_attempts": attempt_allowlist(),
            "lost_attempt": {"operation_id": LOST_ID, "number": 12, "cell": "A2_m", "family": "L",
                             "parameter": 0.1, "status": "interrupted_no_result", "retry_permitted": False,
                             "score_reconstructed": False, "slot_consumed": True},
            "original_development_approval_sha256": m.json_hash(checked["approval"]),
            "completed_cells": list(COMPLETED_CELLS), "probe_policy": "reuse_original_no_repeat",
            "calibration_policy": "original_16_family_allowlist_after_all_four_candidate_freeze"}


def prepare(root, *, process_absence_utc, absence_evidence_path):
    """Create immutable bookkeeping snapshot only; no recovery state is applied."""
    root = Path(root).resolve()
    body = inspect(root, process_absence_utc=process_absence_utc, absence_evidence_path=absence_evidence_path)
    dest = m.artifact_dir(root)
    out = recovery_dir(root)
    snapshots = {}
    for name in ("fit_attempts.json", "development_operations.jsonl"):
        payload = (dest / name).read_bytes()
        expected = body["original_attempts_sha256" if name == "fit_attempts.json" else "original_journal_sha256"]
        if hashlib.sha256(payload).hexdigest() != expected:
            raise PermissionError("Pre-recovery state changed during snapshot")
        path = out / "pre_recovery" / name
        durable_bytes(path, payload, immutable=True)
        snapshots[str(path.relative_to(root))] = expected
    body["pre_recovery_snapshot_sha256"] = snapshots
    manifest = {**body, "recovery_binding_sha256": m.json_hash(body)}
    durable_json(out / "RECOVERY_BINDING.json", manifest, immutable=True)
    return manifest


def verify_recovery(root, *, require_approval=True):
    root = Path(root).resolve()
    checked = gates.require_stage(root, "tennis", "development")
    out = recovery_dir(root)
    value = read_json(out / "RECOVERY_BINDING.json")
    body = {k: v for k, v in value.items() if k != "recovery_binding_sha256"}
    if (m.json_hash(body) != value.get("recovery_binding_sha256") or
            checked["binding_sha256"] != ORIGINAL_BINDING or value.get("original_binding_sha256") != ORIGINAL_BINDING or
            value.get("allowed_attempts") != attempt_allowlist() or
            value.get("original_development_approval_sha256") != m.json_hash(checked["approval"])):
        raise PermissionError("Recovery binding or original approval is stale")
    for group in ("wrapper_files_sha256", "preserved_files_sha256", "pre_recovery_snapshot_sha256"):
        for relative, expected in value[group].items():
            if digest(gates.resolve(root, relative)) != expected:
                raise PermissionError("Recovery-bound bytes changed: " + relative)
    evidence = value["absence_evidence"]
    if digest(gates.resolve(root, evidence["path"])) != evidence["sha256"]:
        raise PermissionError("Process-absence evidence changed")
    data, records = journal(root)
    prefix = (out / "pre_recovery/development_operations.jsonl").read_bytes()
    if not data.startswith(prefix) or len(prefix) != value["original_journal_bytes"]:
        raise PermissionError("Original twelve-record shared journal prefix changed")
    initial_attempts = read_json(out / "pre_recovery/fit_attempts.json")
    if cpu_debit(records[:12], initial_attempts, value["cpu_debit"]["conservative_absence_accounting_bound_utc"]) != value["cpu_debit"]:
        raise PermissionError("Conservative CPU debit changed")
    allowed = {item["operation_id"] for item in value["allowed_attempts"]}
    if any(record["operation_id"] not in allowed for record in records[12:]):
        raise PermissionError("Recovery reserved an undeclared attempt")
    current = read_json(m.artifact_dir(root) / "fit_attempts.json")
    if len(current) < 12 or current[:11] != initial_attempts[:11]:
        raise PermissionError("Completed fit ledger prefix changed")
    expected_lost = {**initial_attempts[11], **disposition(value)}
    if current[11] not in (initial_attempts[11], expected_lost):
        raise PermissionError("Lost attempt disposition changed")
    if len(current) > len(records):
        raise PermissionError("Fit attempts exceed reserved operations")
    for number, attempt in enumerate(current[12:], 13):
        if (attempt.get("number") != number or
                operation_id(attempt["cell"], attempt["family"], attempt["parameter"], attempt["retry"]) != records[number-1]["operation_id"]):
            raise PermissionError("Recovery fit attempts disagree with shared reservations")
    if require_approval:
        approval = read_json(out / "RECOVERY_APPROVAL.json")
        if (approval.get("schema_version") != 1 or approval.get("status") != "approved" or
                approval.get("recovery_binding_sha256") != value["recovery_binding_sha256"] or
                approval.get("original_binding_sha256") != ORIGINAL_BINDING or not approval.get("approval_reference")):
            raise PermissionError("Exact recovery lacks explicit lead approval")
        aware(approval["approved_at_utc"])
        path = gates.resolve(root, approval["review_manifest_path"])
        if digest(path) != approval.get("review_manifest_sha256"):
            raise PermissionError("Recovery independent review changed")
        review = read_json(path)
        if (review.get("schema_version") != 1 or review.get("review_type") != "tennis_recovery_review" or
                review.get("status") != "cleared" or review.get("recovery_binding_sha256") != value["recovery_binding_sha256"] or
                review.get("original_binding_sha256") != ORIGINAL_BINDING or
                "development" not in review.get("cleared_stages", [])):
            raise PermissionError("Independent review does not clear this exact recovery")
        aware(review["reviewed_at_utc"])
    return value


def disposition(binding):
    return {"status": "interrupted_no_result", "recovery_binding_sha256": binding["recovery_binding_sha256"],
            "disposition_path": "recovery/LOST_ATTEMPT_DISPOSITION.json", "slot_consumed": True,
            "retry_permitted": False, "score_reconstructed": False}


def apply_disposition(root, binding):
    verify_recovery(root)
    out = recovery_dir(root)
    durable_json(out / "LOST_ATTEMPT_DISPOSITION.json", {**binding["lost_attempt"],
                 **disposition(binding), "cpu_debit": binding["cpu_debit"]}, immutable=True)
    path = m.artifact_dir(root) / "fit_attempts.json"
    records = read_json(path)
    records[11].update(disposition(binding))
    durable_json(path, records)


class RecoveryLedger(m.AttemptLedger):
    """Retain original estimator/config guards and add the exact recovery scope."""
    def __init__(self, root, binding):
        self.root = Path(root)
        self.binding = binding
        super().__init__(m.artifact_dir(root) / "fit_attempts.json")
        self.prior_stage_cpu = max(self.prior_stage_cpu, binding["cpu_debit"]["baseline_cpu_seconds"])
        self.allowed = {item["operation_id"]: item for item in binding["allowed_attempts"]}
        path = recovery_dir(root) / "resource_checkpoint.json"
        if path.exists():
            self.prior_stage_cpu = max(self.prior_stage_cpu, read_json(path)["cpu_seconds"])

    def _check(self, cell, family, parameter, retry):
        identity = operation_id(cell, family, parameter, retry)
        if identity not in self.allowed or (cell == "A2_m" and family == "L" and parameter == .1):
            raise PermissionError("Candidate is permanently barred or absent from exact recovery allowlist")
        if family == "temperature":
            candidate = m.verify_selection_freeze(self.root, calibrated=False)
            if candidate.get("recovery_binding_sha256") != self.binding["recovery_binding_sha256"]:
                raise PermissionError("Calibration requires all four recovery-bound frozen cells")
            report = candidate["cells"][cell]
            if parameter not in report.get("selected_parameters", {}):
                raise PermissionError("Calibration family was not frozen")
        super()._check(cell, family, parameter, retry)

    def check_budget(self):
        totals = super().check_budget()
        debit = self.binding["cpu_debit"]["conservative_unobserved_cpu_seconds"]
        measured = max(0., totals["cpu_seconds"] - debit)
        pre_restart = self.binding["cpu_debit"]["recorded_cpu_seconds"]
        totals.update(measured_completed_cpu_seconds=measured,
                      measured_pre_restart_cpu_seconds=pre_restart,
                      measured_recovery_cpu_seconds=max(0., measured - pre_restart),
                      conservative_unobserved_cpu_debit_seconds=debit,
                      budget_charged_cpu_seconds=totals["cpu_seconds"],
                      cpu_seconds_interpretation="Compatibility field is budget-charged CPU, including conservative unobserved debit; not measured runtime")
        return totals

    @contextmanager
    def attempt(self, cell, family, parameter, *, retry=False):
        try:
            with super().attempt(cell, family, parameter, retry=retry) as record:
                yield record
        finally:
            # Individual cpu_seconds remains the original measured attempt time.
            if self.records and self.records[-1].get("stage_cpu_seconds") is not None:
                record = self.records[-1]
                debit = self.binding["cpu_debit"]["conservative_unobserved_cpu_seconds"]
                record.update(stage_budget_charged_cpu_seconds=record["stage_cpu_seconds"],
                              stage_measured_completed_cpu_seconds=max(0., record["stage_cpu_seconds"] - debit),
                              conservative_unobserved_cpu_debit_seconds=debit,
                              stage_cpu_seconds_interpretation="Budget-charged total including unobserved debit")
                durable_json(self.path, self.records)

    def persist_resources(self):
        totals = self.check_budget()
        durable_json(recovery_dir(self.root) / "resource_checkpoint.json", totals)
        return totals


def checkpoint_path(root, identity):
    return recovery_dir(root) / "checkpoints" / (hashlib.sha256(identity.encode()).hexdigest() + ".pkl")


def save_checkpoint(root, binding, identity, value, ledger):
    """One durable, self-contained result before another optimizer is admitted."""
    payload = {"schema_version": 1, "operation_id": identity,
               "recovery_binding_sha256": binding["recovery_binding_sha256"],
               "completed_at_utc": utc_now(), "cpu_seconds": ledger.used_cpu(), "result": value}
    path = checkpoint_path(root, identity)
    durable_bytes(path, pickle.dumps(payload, protocol=5), immutable=True)
    durable_json(path.with_suffix(".json"), {k: payload[k] for k in payload if k != "result"} | {"sha256": digest(path)}, immutable=True)
    ledger.persist_resources()
    return value


def load_checkpoint(root, binding, identity):
    path = checkpoint_path(root, identity)
    if not path.exists():
        return None
    meta = read_json(path.with_suffix(".json"))
    if (meta.get("sha256") != digest(path) or meta.get("operation_id") != identity or
            meta.get("recovery_binding_sha256") != binding["recovery_binding_sha256"]):
        raise PermissionError("Result checkpoint integrity failure")
    payload = m._load_local_pickle(path)
    if any(payload.get(k) != v for k, v in meta.items() if k != "sha256"):
        raise PermissionError("Result checkpoint metadata mismatch")
    return payload["result"]


def reserved_ids(root):
    return {r["operation_id"] for r in journal(root)[1]}


def require_unreserved_or_checkpoint(root, binding, identity):
    result = load_checkpoint(root, binding, identity)
    if result is None and identity in reserved_ids(root):
        raise PermissionError("Reserved attempt has no durable result; never retry. A new reviewed interruption disposition is required: " + identity)
    if result is not None and identity not in reserved_ids(root):
        raise PermissionError("Result has no matching reserved operation")
    return result


@contextmanager
def exclusive_session(root, binding, ledger):
    """Unclean exits block automatic continuation and require new CPU accounting."""
    out = recovery_dir(root)
    with (out / "executor.lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PermissionError("A recovery executor is already active") from exc
        path = out / "executor_session.json"
        old = read_json(path) if path.exists() else None
        if old and old.get("status") == "running":
            raise PermissionError("Previous recovery executor did not close cleanly; obtain reviewed absence evidence and conservative additional CPU debit before resuming")
        state = {"status": "running", "started_at_utc": utc_now(), "recovery_binding_sha256": binding["recovery_binding_sha256"]}
        durable_json(path, state)
        try:
            yield
        finally:
            # Python exceptions are measured; abrupt process loss leaves 'running'.
            durable_json(out / "resource_checkpoint.json", {"cpu_seconds": ledger.used_cpu(), "peak_rss_bytes": m.rss_bytes()})
            durable_json(path, {**state, "status": "closed", "closed_at_utc": utc_now(), "cpu_seconds": ledger.used_cpu()})
            fcntl.flock(stream, fcntl.LOCK_UN)


def candidate_attempt(root, binding, ledger, cell, family, parameter, X, labels, *, retry=False):
    identity = operation_id(m.cell_name(cell), family, parameter, retry)
    result = require_unreserved_or_checkpoint(root, binding, identity)
    if result is not None:
        return result
    verify_recovery(root)
    try:
        model, status = m.fit_candidate(root, ledger, cell, family, parameter, X, labels, retry=retry)
        result = {"model": model, "status": status}
    except (ValueError, MemoryError, FloatingPointError, RuntimeError) as exc:
        if identity not in reserved_ids(root):
            raise
        result = {"model": None, "status": "failed", "reason": str(exc)}
    # Preserve fitted estimator even if selection scoring is interrupted later.
    return save_checkpoint(root, binding, identity, result, ledger)


def _save_npz(path, **arrays):
    path = Path(path)
    temp = path.with_name(path.name + ".partial")
    with temp.open("wb") as stream:
        m.np.savez_compressed(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def select_remaining(root, binding, ledger):
    dest = m.artifact_dir(root)
    reports = {cell: read_json(dest / (cell + "_selection.json")) for cell in COMPLETED_CELLS}
    probe = read_json(dest / "resource_probe.json")
    for name in REMAINING_CELLS:
        cell = tuple(name.split("_"))
        train = m.Dataset(dest / "rows/train" / name, root=root, stage="train")
        select = m.Dataset(dest / "rows/selection" / name, root=root, stage="selection")
        st, ss = train.supports("train"), select.supports("selection")
        report = {"training_support": st, "selection_support": ss}
        if not st["sufficient"] or not ss["sufficient"]:
            raise PermissionError("Recovery input support differs from approved remaining candidate scope")
        if m.matrix_estimate(train) > 3 * 1024**3:
            raise m.BudgetExceeded("Full-cell feature memory estimate exceeds declared envelope")
        prep = m.Preprocessor(cell[0]).fit(train.numeric, train.categorical, stage="train")
        scores = {"B0": {0: float(m.per_case_scores(select.labels, select.baselines[:, 0, :], epsilon=m.EPSILON)["log_loss"].mean())},
                  "B1": {i: float(m.per_case_scores(select.labels, select.baselines[:, i+1, :], epsilon=m.EPSILON)["log_loss"].mean()) for i in range(4)}}
        selected = {"B0": 0, "B1": m.choose_candidate(scores["B1"], "B1")}
        models, failures = {}, []
        if name == "A2_m":
            failures.append({**binding["lost_attempt"], "reason": "executor restart; no result; consumed original slot; no repeat or convergence retry"})
        for family, grid in (("L", m.L_GRID), ("N", m.N_GRID)):
            scores[family], fitted = {}, {}
            X = prep.transform(train.numeric, train.categorical, family=family)
            Xs = prep.transform(select.numeric, select.categorical, family=family)
            for parameter in grid:
                if name == "A2_m" and family == "L" and parameter == .1:
                    continue
                result = candidate_attempt(root, binding, ledger, cell, family, parameter, X, train.labels)
                if family == "L" and result["status"] == "convergence_warning":
                    result = candidate_attempt(root, binding, ledger, cell, family, parameter, X, train.labels, retry=True)
                model = result["model"]
                if model is None:
                    failures.append({"family": family, "parameter": parameter, "status": result["status"], **({"reason": result["reason"]} if "reason" in result else {})})
                    continue
                predictions = model.predict_proba(Xs)
                scores[family][parameter] = float(m.per_case_scores(select.labels, predictions, epsilon=m.EPSILON)["log_loss"].mean())
                fitted[parameter] = model
            chosen = m.choose_candidate(scores[family], family)
            if chosen is not None:
                selected[family], models[family] = chosen, fitted[chosen]
            del X, Xs, fitted
        family_losses = {family: scores[family][chosen] for family, chosen in selected.items()}
        main = m.designate(family_losses)
        bundle = {"cell": cell, "selected": selected, "models": models, "preprocessor": prep, "main": main}
        m._save_pickle(dest / (name + "_selected.pkl"), bundle)
        _save_npz(dest / (name + "_selection_predictions.npz"), **{family: m._family_probabilities(bundle, select, family) for family in selected})
        report.update(status="selected", all_candidate_selection_losses=scores, selected_parameters=selected,
                      family_selection_losses=family_losses, designated_main=main, failures=failures,
                      preprocessing=prep.manifest(), train_data=train.manifest, selection_data=select.manifest,
                      nonlinear_probe=probe, common_selection_rows=select.manifest["row_sha256"],
                      recovery_binding_sha256=binding["recovery_binding_sha256"])
        durable_json(dest / (name + "_selection.json"), report)
        reports[name] = report
    verify_recovery(root)
    totals = ledger.persist_resources()
    durable_json(dest / "candidate_resource_totals.json", totals)
    files = [dest / name for name in ("development_rows.json", "development_history.pkl", "training_actors.pkl", "candidate_resource_totals.json")]
    files += [dest / (m.cell_name(cell) + suffix) for cell in m.CELLS for suffix in SUFFIXES]
    files += recovery_provenance_files(root)
    files += sorted((recovery_dir(root) / "checkpoints").glob("*"))
    return m._freeze(root, "CANDIDATE_FREEZE.json", reports, files,
                     stage="selection_frozen_before_calibration", resource_totals=totals,
                     recovery_binding_sha256=binding["recovery_binding_sha256"], missing_candidate=binding["lost_attempt"])


def recovery_provenance_files(root):
    out = recovery_dir(root)
    # Review may be outside the tennis artifact directory; the exact digest/path
    # is carried by the frozen approval, and verified before each phase.
    return [out / name for name in ("RECOVERY_BINDING.json", "RECOVERY_APPROVAL.json", "LOST_ATTEMPT_DISPOSITION.json",
                                    "pre_recovery/fit_attempts.json", "pre_recovery/development_operations.jsonl")]


def calibration_attempt(root, binding, ledger, name, family, data, probabilities):
    identity = operation_id(name, "temperature", family)
    previous = require_unreserved_or_checkpoint(root, binding, identity)
    if previous is not None:
        return previous
    verify_recovery(root)
    ledger._check(name, "temperature", family, False)
    gates.record_operation(root, "tennis", "development", identity,
                           {"bounds": [-3, 3], "xatol": 1e-5, "maxiter": 100, "family": family, "rows": data.n}, 49, kind="calibration")
    try:
        with ledger.attempt(name, "temperature", family) as record:
            result = m.minimize_scalar(lambda logt: float(m.per_case_scores(data.labels, m.temperature_probabilities(probabilities, math.exp(logt)), epsilon=m.EPSILON)["log_loss"].mean()),
                                       method="bounded", bounds=(-3, 3), options={"xatol": 1e-5, "maxiter": 100})
            success = bool(result.success and m.np.isfinite(result.x) and m.np.isfinite(result.fun))
            record.update(status="succeeded" if success else "calibration_failed_identity", iterations=int(result.nfev))
        value = {"temperature": math.exp(float(result.x)) if success else 1.,
                 "status": "fitted" if success else "identity_optimizer_failed"}
    except (ValueError, FloatingPointError, RuntimeError, MemoryError) as exc:
        value = {"temperature": 1., "status": "identity_optimizer_failed: " + str(exc)}
    return save_checkpoint(root, binding, identity, value, ledger)


def calibrate_remaining(root, binding, ledger):
    verify_recovery(root)
    candidate = m.verify_selection_freeze(root, calibrated=False)
    if candidate.get("recovery_binding_sha256") != binding["recovery_binding_sha256"]:
        raise PermissionError("Missing all-four-cell recovery candidate freeze")
    dest = m.artifact_dir(root)
    if not (dest / "calibration_rows.json").exists():
        # Original source/parser implementation, after the original four-cell guard.
        m.build_rows(root, "calibration")
    reports = {}
    files = [dest / name for name in ("CANDIDATE_FREEZE.json", "calibration_rows.json", "calibration_history.pkl")]
    files += [dest / name for name in candidate["files"]]
    for cell in m.CELLS:
        name = m.cell_name(cell)
        selection = candidate["cells"][name]
        if selection["status"] != "selected":
            reports[name] = selection
            continue
        bundle = m._load_local_pickle(dest / (name + "_selected.pkl"))
        data = m.Dataset(dest / "rows/calibration" / name, root=root, stage="calibration")
        check = data.supports("calibration")
        temperatures, statuses, predictions = {}, {}, {}
        for family in bundle["selected"]:
            predictions[family] = m._family_probabilities(bundle, data, family)
            if not check["sufficient"]:
                temperatures[family], statuses[family] = 1., "identity_insufficient_calibration_support"
                continue
            result = calibration_attempt(root, binding, ledger, name, family, data, predictions[family])
            temperatures[family], statuses[family] = result["temperature"], result["status"]
        _save_npz(dest / (name + "_calibration_predictions.npz"), **predictions)
        report = {"status": "frozen", "designated_main": bundle["main"], "selected_parameters": bundle["selected"],
                  "temperatures": temperatures, "calibration_status": statuses, "calibration_support": check,
                  "calibration_data": data.manifest, "calibration_loss_is_performance_estimate": False, "model_reselection": False}
        durable_json(dest / (name + "_calibration.json"), report)
        reports[name] = report
        files += [dest / (name + suffix) for suffix in ("_calibration.json", "_calibration_predictions.npz")]
    verify_recovery(root)
    totals = ledger.persist_resources()
    durable_json(dest / "resource_totals.json", totals)
    files += [dest / "fit_attempts.json", dest / "resource_totals.json", dest / "development_operations.jsonl"]
    files += sorted((recovery_dir(root) / "checkpoints").glob("*"))
    return m._freeze(root, "SELECTION_FREEZE.json", reports, files,
                     stage="all_four_cells_selected_and_calibrated_2025_locked",
                     attempt_summary=dict(Counter(r["status"] for r in ledger.records)),
                     optimizer_attempts=len(ledger.records), resource_totals=totals,
                     recovery_binding_sha256=binding["recovery_binding_sha256"], missing_candidate=binding["lost_attempt"])


def run(root):
    """Only explicit recovery approval + independent review permit this entry."""
    root = Path(root).resolve()
    binding = verify_recovery(root)
    m.verify_runtime()
    dest = m.artifact_dir(root)
    if (dest / "SELECTION_FREEZE.json").exists():
        result = m.verify_selection_freeze(root, calibrated=True)
        if result.get("recovery_binding_sha256") != binding["recovery_binding_sha256"]:
            raise PermissionError("Selection freeze lacks recovery provenance")
        return result
    ledger = RecoveryLedger(root, binding)
    ledger.check_budget()
    with exclusive_session(root, binding, ledger):
        apply_disposition(root, binding)
        # Reload only after disposition, keeping the session's CPU start point.
        ledger.records = read_json(dest / "fit_attempts.json")
        if not (dest / "CANDIDATE_FREEZE.json").exists():
            select_remaining(root, binding, ledger)
        return calibrate_remaining(root, binding, ledger)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "prepare", "verify", "run"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--process-absence-utc")
    parser.add_argument("--absence-evidence-path")
    args = parser.parse_args()
    if args.command in ("inspect", "prepare"):
        if not args.process_absence_utc or not args.absence_evidence_path:
            parser.error("Inspection/preparation needs exact timezone-aware absence time and evidence path")
        result = globals()[args.command](args.root, process_absence_utc=args.process_absence_utc, absence_evidence_path=args.absence_evidence_path)
    else:
        result = verify_recovery(args.root) if args.command == "verify" else run(args.root)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
