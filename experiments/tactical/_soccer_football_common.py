"""Private deterministic I/O and numerical utilities for the two binary runners.

No import-time data access or estimation. All real fits and target reads require
an independently approved stage; absent shared gates always fail closed.
"""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import warnings

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import joblib
import numpy as np
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from . import metrics
from .shot_sources import sha256_file, write_json

EPSILON = 1e-6
SEED = 20261011


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


_PERMITS = {}


def require_stage(root, sport, stage, approval_path=None, *, fresh=False, **evidence):
    from . import gates
    if approval_path is not None:
        raise PermissionError('Approval location is lead-controlled; caller-supplied unlocks are forbidden')
    if stage == 'prepare':
        return None  # Target-blind bytes/metadata only; numerical calls never use this stage.
    mapped = {'develop': 'development', 'calibrate': 'development', 'predict': 'evaluation', 'evaluate': 'evaluation'}
    if stage not in mapped:
        raise PermissionError('Unsupported numerical stage')
    root = Path(root).resolve(); key = (str(root), sport, mapped[stage])
    if fresh or key not in _PERMITS:
        permit = gates.require_stage(root, sport, mapped[stage])
        permit['approval_file_sha256'] = sha256_file(root/gates.APPROVAL_PATH)
        _PERMITS[key] = permit
    permit = _PERMITS[key]
    binding = gates.verify_binding(root, sport, include_data=False)
    gates._approval(root, sport, mapped[stage], binding)
    if binding['binding_sha256'] != permit['binding_sha256'] or sha256_file(root/gates.APPROVAL_PATH) != permit['approval_file_sha256']:
        _PERMITS.pop(key, None)
        raise PermissionError('Numerical permit changed; full verification is required')
    if mapped[stage] == 'evaluation':
        if sha256_file(root/gates.GLOBAL_FREEZE_PATH) != permit['approval'].get('global_freeze_sha256'):
            raise PermissionError('Global evaluation freeze changed')
    return permit


def verify_frozen(root, task, prepared_sha256=None):
    root = Path(root); out = root/f'artifacts/tactical/{task}/model'
    selection = json.loads((root/f'artifacts/tactical/{task}/SELECTION_FREEZE.json').read_text())
    if selection.get('task') != task or sha256_file(out/'frozen_manifest.json') != selection['frozen_manifest_sha256']:
        raise ValueError('Selection-bound frozen manifest changed')
    if sha256_file(out/'selection.json') != selection.get('selection_sha256'):
        raise ValueError('Selection-bound candidate choice changed')
    frozen = json.loads((out/'frozen_manifest.json').read_text())
    if frozen.get('artifact') != 'frozen.joblib' or frozen['sha256'] != selection['artifact_sha256']:
        raise ValueError('Selection-bound model identity changed')
    if frozen.get('prepared_sha256') != selection.get('prepared_sha256') or (prepared_sha256 is not None and frozen['prepared_sha256'] != prepared_sha256):
        raise ValueError('Frozen model belongs to a different prepared population')
    if sha256_file(out/'frozen.joblib') != frozen['sha256']:
        raise ValueError('Frozen model bytes changed')
    return frozen


def verify_prediction_evidence(root, task, prediction_sha256=None):
    root = Path(root); out = root/f'artifacts/tactical/{task}/model'
    verify_frozen(root, task)
    manifest = json.loads((out/'prediction_manifest.json').read_text())
    if manifest.get('prediction_file') != 'test_predictions.json' or manifest.get('labels_joined') is not False:
        raise ValueError('Prediction manifest does not identify target-blind immutable predictions')
    actual = sha256_file(out/'test_predictions.json')
    if actual != manifest.get('prediction_sha256') or (prediction_sha256 is not None and actual != prediction_sha256):
        raise ValueError('Final-target read lacks matching immutable prediction evidence')
    if sha256_file(out/'frozen_manifest.json') != manifest.get('frozen_manifest_sha256'):
        raise ValueError('Predictions belong to a different frozen model')
    return manifest


def environment():
    return {'python': platform.python_version(), **{p: importlib.metadata.version(p) for p in
            ['numpy', 'pandas', 'scipy', 'scikit-learn', 'joblib']},
            'processes': 1, 'threads': 1, 'seed': SEED}


def binary_targets(values, lineage=None):
    """Reject unknown eligible targets; never silently shrink a denominator."""
    arr = np.asarray(values, dtype=object)
    valid = np.array([isinstance(v, (int, float, np.integer, np.floating, bool))
                      and np.isfinite(v) and v in (0, 1) for v in arr])
    if arr.ndim != 1 or not len(arr) or not valid.all():
        bad = np.flatnonzero(~valid).tolist() if arr.ndim == 1 else []
        raise ValueError(f'Every eligible target must be explicit finite binary; invalid indices={bad[:30]}; lineage={lineage}')
    return arr.astype(np.int64)


def probabilities(p):
    p = np.asarray(p, dtype=np.float64)
    if p.ndim != 1 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('Invalid binary probabilities')
    return p


def logit(p):
    p = np.clip(probabilities(p), EPSILON, 1-EPSILON)
    return np.log(p) - np.log1p(-p)


def mean_loss(y, p):
    return float(metrics.per_case_scores(binary_targets(y), probabilities(p), epsilon=EPSILON)['log_loss'].mean())


def learned_prediction(model, matrix):
    if list(model.classes_) != [0, 1]:
        raise ValueError('Unexpected class order; class 1 must be the declared target')
    with threadpool_limits(limits=1):
        return probabilities(model.predict_proba(np.asarray(matrix, dtype=np.float64))[:, 1])


def checked_fit(estimator, x, y, guard):
    guard()
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        estimator.fit(np.asarray(x, dtype=np.float64), binary_targets(y))
    learned_prediction(estimator, np.asarray(x, dtype=np.float64)[:1])
    for name in ('coef_', 'intercept_'):
        if hasattr(estimator, name) and not np.isfinite(getattr(estimator, name)).all():
            raise FloatingPointError('Nonfinite learned coefficient')
    return estimator


def save_object(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.partial')
    joblib.dump(value, temporary)
    temporary.replace(path)
    return sha256_file(path)


def load_object(path, expected_sha256):
    path = Path(path)
    if sha256_file(path) != expected_sha256:
        raise ValueError('Serialized artifact hash mismatch')
    # Only locally generated, manifest-bound joblib files are accepted by callers.
    return joblib.load(path)


def write_once_json(path, value):
    """Persist a stage commitment once; an identical repeat is read-only."""
    path = Path(path)
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise PermissionError('Immutable stage commitment already exists with different contents')
        return sha256_file(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    return sha256_file(path)


def freeze_development(out, prepared_sha256, planned_ids):
    """Bind complete candidate/selection/refit evidence before calibration access."""
    out = Path(out)
    operations = json.loads((out/'operations/operations.json').read_text())
    expected = {name for name in planned_ids if not name.startswith('calibrate_')}
    if operations['planned_ids'] != list(planned_ids):
        raise ValueError('Development operation grid changed')
    complete = {r['id']: r for r in operations['attempts'] if r['status'] == 'complete'}
    if set(complete) != expected or any(r['id'] not in expected for r in operations['attempts']):
        raise ValueError('Development has not completed the entire fixed grid/refit plan')
    for item in complete.values():
        if sha256_file(out/'operations'/item['artifact']) != item['sha256']:
            raise ValueError('Development operation artifact changed')
    write_once_json(out/'development_operations.json', operations)
    manifest = json.loads((out/'development_manifest.json').read_text())
    if manifest.get('artifact') != 'developed.joblib' or manifest.get('prepared_sha256') != prepared_sha256:
        raise ValueError('Development manifest is from another prepared population')
    if sha256_file(out/'developed.joblib') != manifest.get('sha256'):
        raise ValueError('Developed model hash mismatch')
    freeze = {'prepared_sha256': prepared_sha256, 'expected_operations': sorted(expected),
              'files': {name: sha256_file(out/name) for name in
                        ('development_manifest.json','development_candidates.json','selection.json',
                         'development_operations.json','developed.joblib')}}
    write_once_json(out/'DEVELOPMENT_FREEZE.json', freeze)
    return freeze


def verify_development(out, prepared_sha256, planned_ids):
    out = Path(out)
    freeze = json.loads((out/'DEVELOPMENT_FREEZE.json').read_text())
    expected = {name for name in planned_ids if not name.startswith('calibrate_')}
    names = {'development_manifest.json','development_candidates.json','selection.json',
             'development_operations.json','developed.joblib'}
    if (freeze.get('prepared_sha256') != prepared_sha256 or set(freeze.get('files',{})) != names
            or freeze.get('expected_operations') != sorted(expected)):
        raise PermissionError('Development freeze has the wrong population/grid/files')
    for name, sha in freeze['files'].items():
        if sha256_file(out/name) != sha:
            raise PermissionError('Candidate, selection, refit or development manifest changed')
    manifest = json.loads((out/'development_manifest.json').read_text())
    if (manifest.get('artifact') != 'developed.joblib' or manifest.get('prepared_sha256') != prepared_sha256
            or manifest.get('sha256') != freeze['files']['developed.joblib']
            or manifest.get('selection_sha256') != freeze['files']['selection.json']):
        raise PermissionError('Development artifact links disagree')
    ops = json.loads((out/'development_operations.json').read_text())
    complete = {r['id']:r for r in ops['attempts'] if r['status']=='complete'}
    if ops['planned_ids'] != list(planned_ids) or set(complete) != expected:
        raise PermissionError('Incomplete frozen candidate/refit grid')
    for item in complete.values():
        if sha256_file(out/'operations'/item['artifact']) != item['sha256']:
            raise PermissionError('Frozen development operation changed')
    return manifest


class OperationLedger:
    """Persist success per exact operation; never restart a fitted pipeline.

    Failures require review. Only explicit infrastructure-interrupted records may
    retry, with the same immutable signature and a global three-attempt NFL cap.
    """
    def __init__(self, directory, planned_ids, max_retries=0, *, root=None, task=None):
        self.root, self.task = root, task
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory/'operations.json'
        self.planned = tuple(planned_ids); self.max_retries = max_retries
        if len(self.planned) != len(set(self.planned)):
            raise ValueError('Repeated operation ID')
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {'planned_ids': list(self.planned), 'attempts': []}
        if self.data['planned_ids'] != list(self.planned):
            raise ValueError('Operation plan changed; review required')

    def run(self, operation_id, signature, action, guard):
        guard()
        if operation_id not in self.planned:
            raise ValueError('Unplanned estimation operation')
        history = [x for x in self.data['attempts'] if x['id'] == operation_id]
        for old in history:
            if old['signature'] != signature:
                raise ValueError('Operation inputs/configuration changed')
        if history and history[-1]['status'] == 'complete':
            return load_object(self.directory/history[-1]['artifact'], history[-1]['sha256'])
        if history and history[-1]['status'] != 'interrupted':
            raise PermissionError('Incomplete or failed operation requires explicit infrastructure/contract review')
        retries = len(self.data['attempts']) - len({x['id'] for x in self.data['attempts']})
        if history and retries >= self.max_retries:
            raise PermissionError('Global exact-operation retry budget exhausted')
        if len(self.data['attempts']) >= len(self.planned) + self.max_retries:
            raise PermissionError('Total operation-attempt budget exhausted')
        if self.root is not None:
            from . import gates
            gates.record_operation(self.root, self.task, 'development', f'{operation_id}/attempt{len(history)+1}',
                                   {'signature': signature}, len(self.planned)+self.max_retries,
                                   kind='count_build' if 'reference' in operation_id else 'fit')
        record = {'id': operation_id, 'signature': signature, 'status': 'running'}
        self.data['attempts'].append(record); write_json(self.path, self.data)
        try:
            result = action()
            name = operation_id.replace('/', '_') + '.joblib'
            record.update(status='complete', artifact=name, sha256=save_object(self.directory/name, result))
        except BaseException as exc:
            # No exception automatically grants permission to retry.
            record.update(status='failed', error_type=type(exc).__name__, error=str(exc))
            write_json(self.path, self.data)
            raise
        write_json(self.path, self.data)
        return result


def summarize(y, p, groups, bins, low_support=None):
    y = binary_targets(y); p = probabilities(p); groups = np.asarray(groups)
    report = metrics.classification_summary(y, p, epsilon=EPSILON, bin_edges=bins)
    clipped = np.clip(p, EPSILON, 1-EPSILON)
    reference_ll = float(np.mean(-y*np.log(clipped)-(1-y)*np.log1p(-clipped)))
    reference_brier = float(np.mean((p-y)**2))
    if not (np.isclose(report['log_loss'],reference_ll,rtol=0,atol=1e-12)
            and np.isclose(report['brier'],reference_brier,rtol=0,atol=1e-12)):
        raise ArithmeticError('Independent binary log-loss/Brier recomputation disagrees')
    report['independent_score_check'] = {'log_loss':reference_ll,'brier':reference_brier,
                                       'maximum_tolerance':1e-12,'passed':True}
    report['accuracy'] = float(((p >= .5).astype(int) == y).mean())
    report['accuracy_tie_rule'] = 'class 1 when p >= 0.5, including exact ties'
    report['auroc'] = float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None
    report.update(games=len(np.unique(groups)), mean_probability=float(p.mean()), observed_rate=float(y.mean()))
    report['reliability'] = [r for r in report['reliability'] if r['class'] == 1]
    indices = np.minimum(np.searchsorted(bins, p, side='right')-1, len(bins)-2)
    for i, row in enumerate(report['reliability']):
        row['games'] = len(np.unique(groups[indices == i]))
        if low_support is not None:
            row['low_support'] = row['n'] < low_support
    return report


def paired(y, left, right, groups, *, seed=SEED, weighting='case'):
    l = metrics.per_case_scores(binary_targets(y), probabilities(left), epsilon=EPSILON)
    r = metrics.per_case_scores(binary_targets(y), probabilities(right), epsilon=EPSILON)
    return {metric: metrics.paired_cluster_interval(l[metric]-r[metric], groups, replicates=2000,
            seed=seed, minimum_groups=1, weighting=weighting) for metric in ('log_loss', 'brier')}


def fingerprint(root, sport, protocol, extra_files=()):
    root = Path(root)
    paths = [f'experiments/tactical/{sport}.py', f'experiments/tactical/{sport}_model.py',
             'experiments/tactical/_soccer_football_common.py', 'experiments/tactical/metrics.py',
             'experiments/tactical/shot_sources.py', protocol, 'pyproject.toml', *extra_files]
    gate = root/'experiments/tactical/gates.py'
    if gate.exists():
        paths.append('experiments/tactical/gates.py')
    return {'files': {str(p): sha256_file(root/p) for p in paths}, 'environment': environment()}
