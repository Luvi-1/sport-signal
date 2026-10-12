"""Local operational gates for frozen research, not an authentication boundary.

No approval is created by this module. The project lead records owner-approved,
independently reviewed bindings locally. Importing this file never reads labels,
fits a model or unlocks evaluation. Source bytes may be hashed without parsing.
"""
from __future__ import annotations
import fcntl
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import sys
import uuid
from datetime import datetime, timezone

SCHEMA_VERSION = 1
APPROVAL_PATH = "artifacts/tactical/APPROVALS.json"
GLOBAL_FREEZE_PATH = "artifacts/tactical/EVALUATION_FREEZE.json"
PACKAGES = ("numpy", "pandas", "scipy", "scikit-learn", "joblib")
EVALUATION_COHORT = ("baseball", "baseball_mechanics", "basketball", "football",
                     "soccer", "tennis", "tennis_execution")


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest_file(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def resolve(root: Path, relative):
    root=Path(root).resolve();path=Path(relative)
    path=(root/path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(root):
        raise ValueError("Binding path escapes project")
    return path


def relative_path(root: Path, path):
    return str(resolve(root,path).relative_to(Path(root).resolve()))


def task_dir(root: Path, task: str):
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,60}",task):
        raise ValueError("Invalid task identifier")
    return resolve(root,f"artifacts/tactical/{task}")


def runtime_fingerprint():
    return {"python":sys.version, "packages":{p:version(p) for p in PACKAGES},
            "thread_environment":{k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS")}}


def _atomic_json(path: Path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+"."+uuid.uuid4().hex+".partial")
    temporary.write_bytes(canonical_bytes(value)+b"\n")
    temporary.replace(path)


def prepare_binding(root: Path, task: str, protocol_path, code_paths, data_files, metadata=None,
                    *, evaluation_cohort=EVALUATION_COHORT):
    """Freeze protocol/code/input fingerprints without parsing any data labels.

    data_files is a list of paths or a path→expected-SHA mapping. A supplied
    expected SHA must match, preventing changed downloads from being re-blessed.
    No existing differing binding is overwritten, even before approval.
    """
    root=Path(root).resolve();out=task_dir(root,task)/"run_binding.json"
    cohort=list(evaluation_cohort)
    if (not cohort or len(set(cohort)) != len(cohort) or task not in cohort
            or any(not isinstance(name,str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,60}", name) for name in cohort)):
        raise ValueError("An exact evaluation cohort containing this task is required")
    cohort=sorted(cohort)
    protocol=relative_path(root,protocol_path)
    paths=sorted({relative_path(root,p) for p in code_paths})
    if not paths or "experiments/tactical/gates.py" not in paths:
        raise ValueError("The runner and shared gate implementation must be bound")
    data_map=data_files if isinstance(data_files,dict) else {p:None for p in data_files}
    inputs={}
    for path,expected in sorted(data_map.items(),key=lambda item:str(item[0])):
        relative=relative_path(root,path);actual=digest_file(resolve(root,relative))
        if expected is not None and expected!=actual:
            raise ValueError(f"Expected source fingerprint mismatch: {relative}")
        inputs[relative]=actual
    if not inputs:
        raise ValueError("At least one immutable input fingerprint is required")
    body={"schema_version":SCHEMA_VERSION,"task":task,"evaluation_cohort":cohort,
          "protocol":{"path":protocol,"sha256":digest_file(resolve(root,protocol))},
          "code":{p:digest_file(resolve(root,p)) for p in paths},"data":inputs,
          "runtime":runtime_fingerprint(),"metadata":metadata or {}}
    binding={**body,"binding_sha256":hashlib.sha256(canonical_bytes(body)).hexdigest()}
    if out.exists():
        existing=json.loads(out.read_text())
        if existing!=binding:
            raise PermissionError("An immutable run binding already exists with different contents; preserve it and request a reviewed revision")
        return existing
    _atomic_json(out,binding)
    return binding


def verify_binding(root: Path, task: str, *, include_data=True, check_runtime=True):
    root=Path(root).resolve();path=task_dir(root,task)/"run_binding.json"
    if not path.exists():
        raise PermissionError("No reviewed run binding is prepared")
    binding=json.loads(path.read_text())
    body={k:v for k,v in binding.items() if k!="binding_sha256"}
    if binding.get("schema_version")!=SCHEMA_VERSION or binding.get("task")!=task or hashlib.sha256(canonical_bytes(body)).hexdigest()!=binding.get("binding_sha256"):
        raise PermissionError("Run binding identity/hash is invalid")
    cohort=binding.get("evaluation_cohort")
    if (not isinstance(cohort,list) or not cohort or any(not isinstance(name,str) for name in cohort)
            or cohort!=sorted(set(cohort)) or task not in cohort):
        raise PermissionError("Run binding lacks its exact evaluation cohort")
    if check_runtime and binding.get("runtime")!=runtime_fingerprint():
        raise PermissionError("Runtime/thread settings changed since the binding")
    protocol=binding["protocol"]
    if digest_file(resolve(root,protocol["path"]))!=protocol["sha256"]:
        raise PermissionError("Protocol changed since the binding")
    if "experiments/tactical/gates.py" not in binding.get("code",{}):
        raise PermissionError("Gate implementation is not bound")
    for path,expected in binding["code"].items():
        if digest_file(resolve(root,path))!=expected:
            raise PermissionError(f"Bound code changed: {path}")
    if include_data:
        for path,expected in binding["data"].items():
            if digest_file(resolve(root,path))!=expected:
                raise PermissionError(f"Bound input changed: {path}")
    return binding


def _approval(root: Path, task: str, stage: str, binding):
    if stage not in {"development","evaluation"}:
        raise PermissionError("Unsupported numerical stage")
    path=resolve(root,APPROVAL_PATH)
    if not path.exists():
        raise PermissionError("No project-owner stage approval is recorded")
    approvals=json.loads(path.read_text())
    record=approvals.get("tasks",{}).get(task,{}).get(stage,{})
    if approvals.get("schema_version")!=SCHEMA_VERSION or record.get("status")!="approved" or record.get("binding_sha256")!=binding["binding_sha256"]:
        raise PermissionError("This exact task/binding/stage is not approved")
    if not record.get("review_manifest_sha256") or not record.get("review_manifest_path") or not record.get("approved_at_utc"):
        raise PermissionError("Approval lacks its review/time provenance")
    try:
        approved_at = datetime.fromisoformat(record["approved_at_utc"])
        if approved_at.tzinfo is None:
            raise ValueError("Timezone missing")
        review = resolve(root, record["review_manifest_path"])
        if digest_file(review) != record["review_manifest_sha256"]:
            raise ValueError("Review fingerprint changed")
        reviewed = json.loads(review.read_text())
        task_review = reviewed.get("tasks",{}).get(task,{})
        if (reviewed.get("schema_version") != SCHEMA_VERSION
                or reviewed.get("review_type") != "tactical_numerical_binding_review"
                or reviewed.get("status") != "cleared"
                or task_review.get("binding_sha256") != binding["binding_sha256"]
                or stage not in task_review.get("cleared_stages",[])):
            raise ValueError("Review does not clear this exact numerical binding and stage")
    except (OSError, ValueError, TypeError) as exc:
        raise PermissionError("Review/time provenance is invalid") from exc
    return record


def _verify_global_freeze(root: Path, task: str, record: dict, *, include_data: bool):
    path=resolve(root,GLOBAL_FREEZE_PATH)
    if not path.exists() or digest_file(path)!=record.get("global_freeze_sha256"):
        raise PermissionError("The approved global selection freeze is absent or changed")
    global_freeze=json.loads(path.read_text())
    tasks=global_freeze.get("tasks",{})
    current=verify_binding(root,task,include_data=False,check_runtime=False)
    expected_cohort=current["evaluation_cohort"]
    if (global_freeze.get("schema_version")!=SCHEMA_VERSION or not isinstance(tasks,dict)
            or sorted(tasks)!=expected_cohort):
        raise PermissionError("Incomplete global evaluation freeze")
    for name,item in tasks.items():
        other=verify_binding(root,name,include_data=include_data,check_runtime=False)
        if other["evaluation_cohort"]!=expected_cohort:
            raise PermissionError("Tasks disagree on their reviewed evaluation cohort")
        expected_path=f"artifacts/tactical/{name}/SELECTION_FREEZE.json"
        if item.get("binding_sha256")!=other["binding_sha256"] or item.get("selection_path")!=expected_path:
            raise PermissionError("Global selection binding/path mismatch")
        if digest_file(resolve(root,expected_path))!=item.get("selection_sha256"):
            raise PermissionError("A task selection/calibration freeze changed")


def require_stage(root: Path, task: str, stage: str):
    """Call before any stage-specific label read or real fit, never afterward."""
    root=Path(root).resolve()
    binding=verify_binding(root,task)
    record=_approval(root,task,stage,binding)
    if stage=="evaluation":
        _verify_global_freeze(root,task,record,include_data=True)
    return {"task":task,"stage":stage,"binding_sha256":binding["binding_sha256"],"binding":binding,
            "approval":record,"verified_at_utc":datetime.now(timezone.utc).isoformat()}


def record_operation(root: Path, task: str, stage: str, operation_id: str, config: dict,
                     limit: int, kind="fit"):
    """Durably reserve one attempt BEFORE estimation; failed attempts still count.

    The runner owns its exact permitted configuration list and retry semantics.
    This ledger enforces unique attempt IDs, total cap and unchanged code/approval.
    Full source integrity is checked by require_stage at the stage entry point.
    """
    if not isinstance(operation_id,str) or not operation_id or len(operation_id)>240 or not isinstance(limit,int) or limit<1:
        raise ValueError("Invalid operation identity/budget")
    root=Path(root).resolve();binding=verify_binding(root,task,include_data=False)
    approval=_approval(root,task,stage,binding)
    if stage=="evaluation":
        _verify_global_freeze(root,task,approval,include_data=False)
    directory=task_dir(root,task);directory.mkdir(parents=True,exist_ok=True)
    path=directory/f"{stage}_operations.jsonl"
    with path.open("a+") as stream:
        fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
        stream.seek(0);rows=[json.loads(line) for line in stream if line.strip()]
        previous_hash=None
        for row in rows:
            body={k:v for k,v in row.items() if k!="record_sha256"}
            if row.get("previous_record_sha256")!=previous_hash or hashlib.sha256(canonical_bytes(body)).hexdigest()!=row.get("record_sha256"):
                raise PermissionError("Operation journal hash chain is invalid")
            if row.get("limit")!=limit:
                raise PermissionError("Operation budget changed")
            previous_hash=row["record_sha256"]
        if any(r.get("binding_sha256")!=binding["binding_sha256"] or r.get("stage")!=stage for r in rows):
            raise PermissionError("Operation journal mixes incompatible bindings")
        if any(r.get("operation_id")==operation_id for r in rows):
            raise PermissionError("This operation attempt was already reserved; no silent repeat")
        if len(rows)>=limit:
            raise PermissionError("The declared operation-attempt budget is exhausted")
        previous=rows[-1]["record_sha256"] if rows else None
        record={"task":task,"stage":stage,"operation_id":operation_id,"kind":kind,"config":config,
                "binding_sha256":binding["binding_sha256"],"attempt":len(rows)+1,"limit":limit,
                "reserved_at_utc":datetime.now(timezone.utc).isoformat(),"previous_record_sha256":previous}
        record["record_sha256"]=hashlib.sha256(canonical_bytes(record)).hexdigest()
        stream.write(canonical_bytes(record).decode()+"\n");stream.flush();os.fsync(stream.fileno())
        fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
    return len(rows)+1
