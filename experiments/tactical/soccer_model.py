"""Gated fixed-budget WSL numerical runner. Nothing runs on import.

prepare is target-blind; develop, calibrate, predict and evaluate have separate
fail-closed approvals. No CLI unlock flag exists. Source-specific publication is
not authorized by a numerical-stage approval.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from urllib.parse import unquote

from . import _soccer_football_common as common

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

from . import soccer as parser
from .shot_sources import sha256_file, write_json

SPORT = 'soccer'
PROTOCOL = 'docs/tactical/SOCCER_PROTOCOL_DRAFT.md'
BINS = [0, .05, .1, .2, .4, .6, 1]
CS = (.1, 1., 10.)
STREAMS = ('full_G', 'matched_G', 'matched_R')
ROLE_MAP = {'development': 'development', 'calibration_qa_only': 'calibration', 'test_qa_only': 'test'}
DISTANCE_EDGES = [6, 12, 18, 24, 36]
ANGLE_EDGES = [.25, .5, 1]
SOURCE_BUILD_PINS = {
    'data/tactical/soccer/source_manifest.json':'11347046317b47cf42a714c4f049daea0b162090685c8f39a5ac3bfabe99ecbe',
    'reports/tactical/soccer/summary.json':'4d3809797d7365b7e7669094f4c5de9d6268cf6ea2a4b617cccbca8b6af4490c',
    'data/tactical/soccer/contexts.jsonl':'b69c5f7e4e2a1fb0cffdba0937b231bc131dd96c3a5650ff98a80df01ba92635',
    'data/tactical/soccer/development_targets.jsonl':'18a65151f6a8321f09f8260e2573b1dd4fb951d98e3ed46df09c1ccc65b0a67a',
}


def verified_source_index(root):
    """Recheck reviewed bytes and match lineage without parsing event outcomes."""
    root = Path(root).resolve()
    for path, expected in SOURCE_BUILD_PINS.items():
        if sha256_file(root/path) != expected:
            raise ValueError('Reviewed soccer source/derivative bytes changed: '+path)
    manifest = json.loads((root/'data/tactical/soccer/source_manifest.json').read_text())
    summary = json.loads((root/'reports/tactical/soccer/summary.json').read_text())
    if manifest.get('commit') != parser.COMMIT or summary.get('source_commit') != parser.COMMIT:
        raise ValueError('Unexpected soccer source pin')
    dependencies = {p:sha256_file(root/p) for p in
                    ('experiments/tactical/soccer.py','experiments/tactical/shot_sources.py')}
    if (summary.get('parser_dependencies_sha256') != dependencies
            or summary.get('parser_sha256') != dependencies['experiments/tactical/soccer.py']
            or summary.get('contract_sha256') != sha256_file(root/'docs/research/TACTICAL_MEASUREMENT_CONTRACT.json')
            or summary.get('sources') != manifest.get('files')):
        raise ValueError('Soccer staged artifact provenance changed')
    prefix = f'https://raw.githubusercontent.com/statsbomb/open-data/{parser.COMMIT}/'
    entries = {}
    for entry in manifest.get('files',[]):
        if not entry.get('url','').startswith(prefix):
            raise ValueError('Unpinned soccer source URL')
        relative = unquote(entry['url'][len(prefix):])
        if relative in entries:
            raise ValueError('Duplicate soccer source')
        path = (root/entry['path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Soccer source path escapes root')
        if path.stat().st_size != entry['bytes'] or sha256_file(path) != entry['sha256']:
            raise ValueError('Soccer source bytes changed')
        entries[relative] = entry
    matches = {}
    for season, expected in ((4,107),(42,87),(90,131),(281,132)):
        key=f'data/matches/37/{season}.json'
        if key not in entries:
            raise ValueError('Missing fixed WSL match index')
        index=json.loads((root/entries[key]['path']).read_text())
        if len(index)!=expected:
            raise ValueError('WSL match index population changed')
        for item in index:
            mid=item['match_id']
            if (mid in matches or item['competition']['competition_id']!=37
                    or item['season']['season_id']!=season):
                raise ValueError('Duplicate or inconsistent match-index lineage')
            matches[mid]=(season,item['match_date'],parser.cohort_for(season,item['match_date']))
    expected_paths = {f'data/matches/37/{s}.json' for s in (4,42,90,281)}
    expected_paths |= {f'data/events/{mid}.json' for mid in matches}
    expected_paths.add('img/SB - Icon Lockup - Colour positive.png')
    if len(entries)!=462 or set(entries)!=expected_paths:
        raise ValueError('Soccer source set is not the exact reviewed 462 files')
    return manifest, summary, matches


def verify_context_lineage(rows, match_index):
    for row in rows:
        observed=(row['season_id'],row['match_date'],row['cohort'])
        if match_index.get(row['match_id']) != observed:
            raise ValueError('Soccer context differs from its unique pinned match-index lineage')


def _guard(root, stage, approval, **evidence):
    return common.require_stage(root, SPORT, stage, approval, **evidence)


def role(row):
    expected = ROLE_MAP[parser.cohort_for(row['season_id'], row['match_date'])]
    if ROLE_MAP.get(row.get('cohort')) != expected:
        raise ValueError('Soccer role and frozen season/date disagree')
    return expected


def body_group(value):
    return 'Head' if value == 'Head' else 'Foot' if value in ('Left Foot', 'Right Foot') else 'Other-or-unknown'


def cohort_flags(row):
    f, q = row['features'], row['quality']
    full = all(parser.finite_number(f.get(k)) for k in ('distance_native', 'goal_angular_width_rad'))
    checks = {'full_geometry': full, 'exactly_one_keeper': q.get('recorded_opposition_keeper_count') == 1,
              'nearest_opponent_finite': parser.finite_number(f.get('nearest_recorded_opponent_native')),
              'valid_player_coordinates': q.get('invalid_recorded_player_locations') == 0,
              'known_team_flags': q.get('unknown_teammate_flags') == 0,
              'known_opponent_roles': q.get('unknown_opponent_role_count') == 0,
              'defined_triangle_count': parser.finite_number(f.get('recorded_outfield_in_goal_triangle')),
              'finite_keeper_geometry': all(parser.finite_number(f.get(k)) for k in ('keeper_depth_native', 'keeper_lateral_offset_native'))}
    return {'full': full, 'matched': all(checks.values()), 'requirements': checks}


def _feature_values(row, defense):
    f = row['features']; bearing = f.get('goal_bearing_rad')
    numeric = [math.log1p(f['distance_native']), f['goal_angular_width_rad'],
               abs(bearing) if parser.finite_number(bearing) else 0., abs(f['lateral_offset_native'])]
    names = ['log1p_distance_native', 'goal_angular_width_rad', 'abs_goal_bearing_rad', 'abs_lateral_offset_native']
    if defense:
        numeric += [f['keeper_depth_native'], abs(f['keeper_lateral_offset_native']),
                    math.log1p(f['nearest_recorded_opponent_native']), f['recorded_outfield_in_goal_triangle']]
        names += ['keeper_depth_native', 'abs_keeper_lateral_offset_native',
                  'log1p_nearest_recorded_opponent_native', 'recorded_outfield_in_goal_triangle']
    categories = [body_group(f.get('body_part')), f.get('shot_type') or 'Missing', f.get('play_pattern') or 'Missing']
    return numeric, [int(not parser.finite_number(bearing))], categories, names


def fit_transform(rows, defense=False):
    if not rows:
        raise ValueError('Empty soccer training cohort')
    values = [_feature_values(row, defense) for row in rows]
    x = np.asarray([v[0] for v in values], dtype=np.float64)
    if not np.isfinite(x).all():
        raise ValueError('Nonfinite geometry in fixed cohort')
    vocab = [sorted({v[2][i] for v in values}) for i in range(3)]
    scale = x.std(axis=0); scale[scale == 0] = 1
    columns = [*values[0][3], 'bearing_missing']
    columns += [f'{name}={level}' for name, levels in zip(('body_group', 'shot_type', 'play_pattern'), vocab) for level in levels]
    state = {'defense': defense, 'mean': x.mean(axis=0).tolist(), 'scale': scale.tolist(),
             'categories': vocab, 'columns': columns, 'class_order': [0, 1]}
    return transform(rows, state), state


def transform(rows, state):
    values = [_feature_values(row, state['defense']) for row in rows]
    if not values:
        return np.empty((0, len(state['columns'])), dtype=np.float64)
    numeric = (np.asarray([v[0] for v in values], dtype=np.float64)-state['mean'])/state['scale']
    binary = np.asarray([v[1] for v in values], dtype=np.float64)
    dummy = np.asarray([[float(v[2][i] == level) for i, levels in enumerate(state['categories']) for level in levels] for v in values])
    result = np.column_stack((numeric, binary, dummy)).astype(np.float64)
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite inference matrix')
    return result


def cell(row):
    f = row['features']
    return (int(np.searchsorted(DISTANCE_EDGES, f['distance_native'], side='right')),
            int(np.searchsorted(ANGLE_EDGES, f['goal_angular_width_rad'], side='right')), body_group(f.get('body_part')))


def build_baselines(rows, y):
    y = common.binary_targets(y); global_rate = float((y.sum()+1)/(len(y)+2))
    cells = defaultdict(lambda: [0, 0])
    for row, target in zip(rows, y):
        cells[cell(row)][0] += 1; cells[cell(row)][1] += int(target)
    return {'global_rate': global_rate, 'cells': {key: (s+20*global_rate)/(n+20) for key, (n, s) in cells.items()}}


def baseline_prediction(rows, state, kind):
    return np.array([state['global_rate'] if kind == 'A' else state['cells'].get(cell(row), state['global_rate']) for row in rows])


def select_c(scores):
    best = min(scores.values())
    return min(c for c, loss in scores.items() if loss <= best + 1e-6)


def planned_operations():
    return [f'inner_{stream}_{c}_{fold}' for stream in STREAMS for c in CS for fold in (0, 1)] + \
           [f'refit_{stream}' for stream in STREAMS] + [f'calibrate_{stream}' for stream in STREAMS]


def prepare(root=parser.ROOT, approval_path=None):
    """Verify target-blind context cache and raw byte pins; freeze whole-match membership."""
    root = Path(root); _guard(root, 'prepare', approval_path)
    staging = root/'data/tactical/soccer'; out = root/'artifacts/tactical/soccer/model'; out.mkdir(parents=True, exist_ok=True)
    manifest, summary, match_index = verified_source_index(root)
    rows = [json.loads(line) for line in (staging/'contexts.jsonl').read_text().splitlines()]
    verify_context_lineage(rows, match_index)
    rows.sort(key=lambda r: (r['season_id'], r['match_date'], r['match_id'], r['event_id']))
    if len({r['event_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate soccer event IDs')
    for r in rows:
        role(r)
        if 'goal' in r or 'target' in r:
            raise ValueError('Target in target-blind context cache')
    games = {s: len({r['match_id'] for r in rows if role(r) == s}) for s in ('development', 'calibration', 'test')}
    counts=Counter(role(r) for r in rows)
    if games != {'development': 325, 'calibration': 60, 'test': 72} or counts != {'development':8204,'calibration':1651,'test':1855}:
        raise ValueError('Frozen soccer support differs from reviewed protocol')
    split = [{'season_id': r['season_id'], 'match_id': r['match_id'], 'event_id': r['event_id'], 'role': role(r),
              'full': cohort_flags(r)['full'], 'matched': cohort_flags(r)['matched']} for r in rows]
    membership = {r['match_id']: role(r) for r in rows}
    if any(membership[r['match_id']] != role(r) for r in rows):
        raise ValueError('Match split across roles')
    prepared = {'fingerprint': common.fingerprint(root, SPORT, PROTOCOL, ['experiments/tactical/shot_sources.py']),
                'sources': manifest, 'contexts_sha256': sha256_file(staging/'contexts.jsonl'),
                'split_sha256': common.digest(split), 'membership': split, 'games': games,
                'coverage': {s: {'eligible': sum(role(r) == s for r in rows),
                    'full': sum(role(r) == s and cohort_flags(r)['full'] for r in rows),
                    'matched': sum(role(r) == s and cohort_flags(r)['matched'] for r in rows),
                    'matched_requirement_failures': dict(Counter(k for r in rows if role(r) == s
                         for k, valid in cohort_flags(r)['requirements'].items() if not valid))} for s in games}}
    path = out/'prepared.json'
    if path.exists() and common.digest(json.loads(path.read_text())) != common.digest(prepared):
        raise ValueError('Preparation already frozen with different bytes; review required')
    write_json(path, prepared)
    from . import gates
    data = {record['path']: record['sha256'] for record in manifest['files']}
    for relative in ('data/tactical/soccer/contexts.jsonl', 'data/tactical/soccer/development_targets.jsonl',
                     'data/tactical/soccer/source_manifest.json', 'reports/tactical/soccer/summary.json',
                     'artifacts/tactical/soccer/model/prepared.json'):
        data[relative] = sha256_file(root/relative)
    gates.prepare_binding(root, SPORT, PROTOCOL, [*prepared['fingerprint']['files'],
         'docs/research/TACTICAL_MEASUREMENT_CONTRACT.json'], data,
         {'split_sha256': prepared['split_sha256'], 'fit_budget': 24, 'coverage': prepared['coverage']})
    return prepared


def _prepared(root):
    root = Path(root); out = root/'artifacts/tactical/soccer/model'
    info = json.loads((out/'prepared.json').read_text())
    if info['fingerprint'] != common.fingerprint(root, SPORT, PROTOCOL, ['experiments/tactical/shot_sources.py']):
        raise ValueError('Frozen source code/protocol/environment changed')
    path = root/'data/tactical/soccer/contexts.jsonl'
    if sha256_file(path) != info['contexts_sha256']:
        raise ValueError('Frozen context cache changed')
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows.sort(key=lambda r: (r['season_id'], r['match_date'], r['match_id'], r['event_id']))
    return out, info, rows


def _labels(root, rows, stage, approval_path, **evidence):
    _guard(root, stage, approval_path, **evidence)
    if stage == 'evaluate': common.verify_prediction_evidence(root, SPORT, evidence.get('prediction_sha256'))
    allowed = {'develop': {'development'}, 'calibrate': {'calibration'}, 'evaluate': {'test'}}
    if stage not in allowed or any(role(r) not in allowed[stage] for r in rows):
        raise PermissionError('Target reader rejects unapproved soccer role')
    ids = {r['event_id'] for r in rows}; targets = {}
    if stage == 'develop':
        path = Path(root)/'data/tactical/soccer/development_targets.jsonl'
        for line in path.read_text().splitlines():
            item = json.loads(line)
            if item['event_id'] in targets:
                raise ValueError('Duplicate development target')
            targets[item['event_id']] = item['goal']
        source_files = [str(path)]
    else:
        manifest = json.loads((Path(root)/'data/tactical/soccer/source_manifest.json').read_text())
        matches = {r['match_id'] for r in rows}; source_files = []
        for match in sorted(matches):
            entries = [x for x in manifest['files'] if x['path'].endswith(f'/events/{match}.json')]
            if len(entries) != 1:
                raise ValueError('Missing/ambiguous match source')
            record = entries[0]; path = Path(root)/record['path']
            if sha256_file(path) != record['sha256']:
                raise ValueError('Changed label source')
            source_files.append(str(path))
            for event in json.loads(path.read_text()):
                if event.get('id') in ids:
                    targets[event['id']] = parser.extract_target(event)['goal']
    audit = {'stage': stage, 'roles': sorted({role(r) for r in rows}), 'columns': ['goal' if stage == 'develop' else 'shot.outcome.name'],
             'source_files': source_files, 'requested_ids_sha256': common.digest(sorted(ids))}
    write_json(Path(root)/f'artifacts/tactical/soccer/model/target_read_{stage}.json', audit)
    invalid = [r for r in rows if targets.get(r['event_id']) not in (0, 1)]
    if invalid:
        write_json(Path(root)/f'artifacts/tactical/soccer/model/invalid_targets_{stage}.json',
                   [{'event_id': r['event_id'], 'match_id': r['match_id']} for r in invalid])
    return common.binary_targets([targets.get(r['event_id']) for r in rows], lineage=f'soccer {stage}')


def _fit(rows, y, c, defense, guard):
    guard(); x, state = fit_transform(rows, defense)
    if len(np.unique(y)) == 1:
        return {'transform': state, 'constant': float((y.sum()+1)/(len(y)+2)), 'fallback': 'prespecified_single_class_beta_1_1'}
    model = LogisticRegression(C=c, penalty='l2', solver='lbfgs', fit_intercept=True,
                               max_iter=2000, tol=1e-8, class_weight=None, warm_start=False, random_state=common.SEED)
    return {'transform': state, 'model': common.checked_fit(model, x, y, guard), 'C': c}


def _predict(rows, artifact):
    if 'constant' in artifact:
        return np.full(len(rows), artifact['constant'])
    return common.learned_prediction(artifact['model'], transform(rows, artifact['transform']))


def develop(root=parser.ROOT, approval_path=None):
    root = Path(root); _guard(root, 'develop', approval_path, fresh=True)
    guard = lambda: _guard(root, 'develop', approval_path)
    out, info, all_rows = _prepared(root)
    if (out/'DEVELOPMENT_FREEZE.json').exists():
        manifest = common.verify_development(out, common.digest(info), planned_operations())
        return {'stage':'development_complete','artifact_sha256':manifest['sha256'], 'reused':True}
    rows = [r for r in all_rows if role(r) == 'development' and cohort_flags(r)['full']]
    labels = _labels(root, rows, 'develop', approval_path)
    ledger = common.OperationLedger(out/'operations', planned_operations(), root=root, task=SPORT)
    chosen, candidates, models, baselines = {}, [], {}, {}
    for stream in STREAMS:
        selected = np.array([not stream.startswith('matched') or cohort_flags(r)['matched'] for r in rows])
        own = [r for r, valid in zip(rows, selected) if valid]; y = labels[selected]
        scores = {}
        for c in CS:
            total_loss, n = 0., 0
            for fold, (train_seasons, validation) in enumerate([((4,), 42), ((4, 42), 90)]):
                train = np.array([r['season_id'] in train_seasons for r in own]); val = np.array([r['season_id'] == validation for r in own])
                train_rows = [r for r, valid in zip(own, train) if valid]; val_rows = [r for r, valid in zip(own, val) if valid]
                op = f'inner_{stream}_{c}_{fold}'
                signature = common.digest({'prepared': common.digest(info), 'operation': op, 'train_ids': [r['event_id'] for r in train_rows]})
                artifact = ledger.run(op, signature, lambda: _fit(train_rows, y[train], c, stream.endswith('_R'), guard), guard)
                prediction = _predict(val_rows, artifact); loss = common.mean_loss(y[val], prediction)
                total_loss += loss*len(val_rows); n += len(val_rows)
                candidates.append({'stream': stream, 'C': c, 'fold': fold, 'n': len(val_rows), 'log_loss': loss,
                                   'status': 'complete', 'fallback': artifact.get('fallback')})
                write_json(out/'development_candidates.json', candidates)
            scores[c] = total_loss/n
        chosen[stream] = select_c(scores)
        write_json(out/'selection_progress.json', {'selected_C': chosen, 'completed_stream': stream, 'selection': 'pooled shot-weighted expanding-fold log loss'})
        op = f'refit_{stream}'
        models[stream] = ledger.run(op, common.digest({'prepared': common.digest(info), 'operation': op, 'C': chosen[stream]}),
                                  lambda: _fit(own, y, chosen[stream], stream.endswith('_R'), guard), guard)
    for cohort in ('full', 'matched'):
        mask = np.array([cohort == 'full' or cohort_flags(r)['matched'] for r in rows])
        guard(); baselines[cohort] = build_baselines([r for r, valid in zip(rows, mask) if valid], labels[mask])
    bundle = {'models': models, 'baselines': baselines, 'selected_C': chosen, 'prepared_sha256': common.digest(info),
              'training_ids_sha256': common.digest([r['event_id'] for r in rows]), 'class_order': [0, 1]}
    sha = common.save_object(out/'developed.joblib', bundle)
    common.write_once_json(out/'selection.json', {'selected_C':chosen, 'selection':'pooled shot-weighted expanding-fold log loss'})
    write_json(out/'development_manifest.json', {'artifact': 'developed.joblib', 'sha256': sha,
                                               'selected_C': chosen, 'prepared_sha256': common.digest(info),
                                               'selection_sha256':sha256_file(out/'selection.json')})
    common.freeze_development(out, common.digest(info), planned_operations())
    return {'stage': 'development_complete', 'selected_C': chosen, 'artifact_sha256': sha, 'test_labels_read': False}


def _calibration_fit(y, p, guard):
    guard(); y = common.binary_targets(y); z = common.logit(p)
    if len(y) < 100 or y.sum() < 10 or (1-y).sum() < 10:
        return {'a': 0., 'b': 1., 'status': 'identity_insufficient_support'}
    def objective(theta):
        a, b = theta; eta = a+b*z
        loss = np.logaddexp(0, eta).sum()-np.dot(y, eta)+.5*(a*a+(b-1)**2)
        residual = expit(eta)-y
        return loss, np.array([residual.sum()+a, np.dot(residual, z)+(b-1)])
    with threadpool_limits(limits=1):
        fit = minimize(objective, [0., 1.], jac=True, method='L-BFGS-B', bounds=[(-10, 10), (0, 5)],
                       options={'maxiter': 2000, 'ftol': 1e-10, 'gtol': 1e-8})
    if not fit.success or not np.isfinite(fit.x).all():
        return {'a': 0., 'b': 1., 'status': 'identity_numerical_failure', 'message': str(fit.message)}
    return {'a': float(fit.x[0]), 'b': float(fit.x[1]), 'status': 'fitted', 'iterations': int(fit.nit)}


def calibrated(p, state):
    return expit(state['a']+state['b']*common.logit(p))


def calibrate(root=parser.ROOT, approval_path=None):
    root = Path(root); _guard(root, 'calibrate', approval_path, fresh=True)
    guard = lambda: _guard(root, 'calibrate', approval_path)
    out, info, all_rows = _prepared(root)
    manifest = common.verify_development(out, common.digest(info), planned_operations())
    bundle = common.load_object(out/manifest['artifact'], manifest['sha256'])
    if bundle.get('prepared_sha256') != common.digest(info) or bundle.get('selected_C') != manifest.get('selected_C'):
        raise PermissionError('Developed model/selection belongs to another prepared population')
    rows = [r for r in all_rows if role(r) == 'calibration' and cohort_flags(r)['full']]
    y = _labels(root, rows, 'calibrate', approval_path)
    ledger = common.OperationLedger(out/'operations', planned_operations(), root=root, task=SPORT); calibration = {}
    for stream in STREAMS:
        mask = np.array([not stream.startswith('matched') or cohort_flags(r)['matched'] for r in rows])
        own = [r for r, valid in zip(rows, mask) if valid]; p = _predict(own, bundle['models'][stream])
        op = f'calibrate_{stream}'
        calibration[stream] = ledger.run(op, common.digest({'development': manifest['sha256'], 'operation': op}),
                                        lambda: _calibration_fit(y[mask], p, guard), guard)
    bundle.update(calibration=calibration, calibration_ids_sha256=common.digest([r['event_id'] for r in rows]))
    sha = common.save_object(out/'frozen.joblib', bundle)
    # Mandatory batch/single parity before any holdout construction.
    parity = {}
    for stream in STREAMS:
        own = [r for r in rows if not stream.startswith('matched') or cohort_flags(r)['matched']]
        batch = _predict(own, bundle['models'][stream])
        single = np.array([_predict([r], bundle['models'][stream])[0] for r in own])
        if not np.allclose(batch, single, rtol=0, atol=1e-12):
            raise ValueError('Single-row inference parity failed')
        parity[stream] = float(np.max(np.abs(batch-single))) if len(batch) else 0.
    frozen = {'artifact': 'frozen.joblib', 'sha256': sha, 'prepared_sha256': common.digest(info), 'calibrators': calibration,
              'class_order': [0, 1], 'parity_max_absolute_error': parity, 'protocol_sha256': info['fingerprint']['files'][PROTOCOL],
              'serialization': 'local joblib; exact environment and file SHA256 required; never accept untrusted pickle',
              'reporting': {'primary': 'matched_R_calibrated minus matched_G_calibrated', 'epsilon': common.EPSILON, 'bins': BINS,
                            'bootstrap_replicates': 2000, 'seed': common.SEED, 'quantile_method': 'linear'},
              'training_ids_sha256': bundle['training_ids_sha256'], 'calibration_ids_sha256': bundle['calibration_ids_sha256']}
    write_json(out/'frozen_manifest.json', frozen)
    write_json(root/'artifacts/tactical/soccer/SELECTION_FREEZE.json',
               {'task': SPORT, 'frozen_manifest_sha256': sha256_file(out/'frozen_manifest.json'),
                'artifact_sha256': sha, 'prepared_sha256': common.digest(info),
                'selection_sha256': sha256_file(out/'selection.json'), 'class_order': [0, 1]})
    return frozen


def predict(root=parser.ROOT, approval_path=None):
    root = Path(root); _guard(root, 'predict', approval_path, fresh=True)
    out, info, all_rows = _prepared(root); manifest = common.verify_frozen(root, SPORT, common.digest(info))
    bundle = common.load_object(out/manifest['artifact'], manifest['sha256'])
    rows = [r for r in all_rows if role(r) == 'test']
    records = {r['event_id']: {'event_id': r['event_id'], 'match_id': r['match_id'], 'full': cohort_flags(r)['full'],
                 'matched': cohort_flags(r)['matched'], 'body_group': body_group(r['features'].get('body_part')),
                 'distance_bin': int(np.searchsorted(DISTANCE_EDGES, r['features']['distance_native'], side='right'))} for r in rows}
    for cohort in ('full', 'matched'):
        own = [r for r in rows if cohort_flags(r)[cohort]]
        for kind in ('A', 'B'):
            for r, p in zip(own, baseline_prediction(own, bundle['baselines'][cohort], kind)):
                records[r['event_id']][f'{cohort}_{kind}_raw'] = float(p)
    for stream in STREAMS:
        own = [r for r in rows if cohort_flags(r)['matched' if stream.startswith('matched') else 'full']]
        raw = _predict(own, bundle['models'][stream]); cal = calibrated(raw, bundle['calibration'][stream])
        for r, p, q in zip(own, raw, cal):
            records[r['event_id']][stream+'_raw'] = float(p); records[r['event_id']][stream+'_calibrated'] = float(q)
    predictions = list(records.values()); path = out/'test_predictions.json'
    if path.exists():
        raise FileExistsError('Immutable predictions already exist; verify rather than overwrite')
    write_json(path, predictions)
    result = {'prediction_file': path.name, 'prediction_sha256': sha256_file(path), 'frozen_manifest_sha256': sha256_file(out/'frozen_manifest.json'),
              'split_sha256': info['split_sha256'], 'n_eligible': len(rows), 'labels_joined': False}
    write_json(out/'prediction_manifest.json', result)
    return result


def evaluate(root=parser.ROOT, approval_path=None):
    root = Path(root); out = root/'artifacts/tactical/soccer/model'
    manifest = json.loads((out/'prediction_manifest.json').read_text())
    _guard(root, 'evaluate', approval_path, fresh=True, prediction_sha256=manifest['prediction_sha256'])
    _, info, all_rows = _prepared(root)
    if sha256_file(out/manifest['prediction_file']) != manifest['prediction_sha256']:
        raise ValueError('Frozen prediction hash mismatch')
    if sha256_file(out/'frozen_manifest.json') != manifest['frozen_manifest_sha256']:
        raise ValueError('Frozen model manifest changed')
    destination = root/'reports/tactical/soccer/model/evaluation.json'
    if destination.exists():
        raise FileExistsError('One-shot evaluation already exists')
    predictions = json.loads((out/manifest['prediction_file']).read_text()); pred = {p['event_id']: p for p in predictions}
    rows = [r for r in all_rows if role(r) == 'test' and cohort_flags(r)['full']]
    y = _labels(root, rows, 'evaluate', approval_path, prediction_sha256=manifest['prediction_sha256'])
    columns = sorted({k for p in predictions for k in p if k.endswith(('_raw', '_calibrated'))})
    streams = {}
    for column in columns:
        mask = np.array([column in pred[r['event_id']] for r in rows]); own = [r for r, valid in zip(rows, mask) if valid]
        streams[column] = common.summarize(y[mask], [pred[r['event_id']][column] for r in own], [r['match_id'] for r in own], BINS, 50)
    mask = np.array([cohort_flags(r)['matched'] for r in rows]); matched = [r for r, valid in zip(rows, mask) if valid]
    left = [pred[r['event_id']]['matched_R_calibrated'] for r in matched]
    right = [pred[r['event_id']]['matched_G_calibrated'] for r in matched]; groups = [r['match_id'] for r in matched]
    primary = common.paired(y[mask], left, right, groups)
    slices = {}
    for field in ('body_group', 'distance_bin'):
        slices[field] = []
        for value in sorted({pred[r['event_id']][field] for r in matched}):
            m = np.array([pred[r['event_id']][field] == value for r in matched])
            slices[field].append({'value': value, 'R': common.summarize(y[mask][m], np.array(left)[m], np.array(groups)[m], BINS, 50),
                                 'G': common.summarize(y[mask][m], np.array(right)[m], np.array(groups)[m], BINS, 50)})
    report = {'phase': 'frozen_evaluation', 'streams': streams, 'primary': primary, 'coverage': info['coverage'], 'slices': slices,
              'equal_game_weighted_sensitivity': common.paired(y[mask], left, right, groups, weighting='group'),
              'usefulness_yardstick_met': primary['log_loss']['difference'] <= -.005 and primary['brier']['difference'] <= 0,
              'prediction_sha256': manifest['prediction_sha256'], 'conditional_sampling_uncertainty_only': True,
              'release': 'local only; source-specific publication and independent recomputation still required'}
    write_json(destination, report)
    return report
