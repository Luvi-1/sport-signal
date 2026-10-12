"""Fixed-budget, independently gated NFL realized-dropback benchmark.

All source reads are pinned and role checked before dataframe parsing. The
protected descriptive parser remains unmodified and cannot unlock this runner.
"""
from __future__ import annotations
from collections import defaultdict
import itertools
import json
from pathlib import Path

from . import _soccer_football_common as common

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from . import football as parser
from .shot_sources import sha256_file, write_json

SPORT = 'football'
PROTOCOL = 'docs/tactical/FOOTBALL_PROTOCOL_DRAFT.md'
PINS = {**parser.PINNED_HASHES, 'play_by_play_2024.csv.gz': '23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06'}
BINS = np.linspace(0, 1, 11).tolist()
A = ('down', 'ydstogo', 'yardline_100', 'qtr', 'quarter_seconds_remaining', 'half_seconds_remaining',
     'game_seconds_remaining', 'score_differential', 'posteam_timeouts_remaining', 'defteam_timeouts_remaining', 'no_huddle', 'offense_is_home')
B = A + ('formation', 'offense_rb', 'offense_te', 'offense_wr', 'offense_ol', 'offense_qb', 'offense_other',
         'defense_dl', 'defense_lb', 'defense_db', 'defense_other')
C = B + ('motion', 'defenders_in_box', 'offense_backfield', 'starting_hash')
BLOCKS = {'A': A, 'B': B, 'C': C}
CATEGORY_LEVELS = {'down': ['1', '2', '3', '4'], 'qtr': ['1', '2', '3', '4', 'OT'],
                   'no_huddle': ['0', '1'], 'offense_is_home': ['0', '1'],
                   'formation': ['SHOTGUN', 'UNDER_CENTER', 'PISTOL'], 'motion': ['0', '1'],
                   'starting_hash': ['left', 'middle', 'right'], 'two_minute_half': ['0', '1']}
ROLES = {'initial': (2023, 1, 18), 'selection': (2024, 1, 9), 'calibration': (2024, 10, 18), 'test': (2025, 1, 18)}
EXPECTED = {'initial': (33836, 272), 'selection': (16824, 138), 'calibration': (16511, 134), 'test': (32813, 272)}


def _guard(root, stage, approval_path=None, **evidence):
    return common.require_stage(root, SPORT, stage, approval_path, **evidence)


def distance_band(value):
    if pd.isna(value): return 'MISSING'
    return '0-2' if value <= 2 else '3-5' if value <= 5 else '6-10' if value <= 10 else '11+'


def _category(name, value):
    if pd.isna(value): return 'MISSING'
    if name == 'qtr' and isinstance(value, (int, float, np.integer, np.floating)) and value >= 5: return 'OT'
    if isinstance(value, (bool, int, float, np.integer, np.floating)) and float(value).is_integer(): value = str(int(value))
    return str(value) if str(value) in CATEGORY_LEVELS[name] else 'UNKNOWN'


def basis(features, block):
    if block not in BLOCKS: raise ValueError('Unapproved feature block')
    frame = features.loc[:, BLOCKS[block]].copy()
    for name in ('ydstogo', 'yardline_100', 'qtr', 'half_seconds_remaining', 'game_seconds_remaining', 'score_differential'):
        frame[name] = pd.to_numeric(frame[name], errors='coerce')
    frame['log_distance'] = np.log1p(frame.ydstogo.astype(float))
    frame['goal_distance_squared'] = (frame.yardline_100.astype(float)/100)**2
    frame['two_minute_half'] = ((frame.qtr.between(1, 4)) & (frame.half_seconds_remaining <= 120)).astype(float)
    frame.loc[frame.qtr.isna() | frame.half_seconds_remaining.isna(), 'two_minute_half'] = np.nan
    frame['late_game_score'] = np.where((frame.qtr == 4) & (frame.game_seconds_remaining <= 300), frame.score_differential, 0.)
    frame.loc[frame[['qtr', 'game_seconds_remaining', 'score_differential']].isna().any(axis=1), 'late_game_score'] = np.nan
    return frame


def fit_transform(features, block):
    frame = basis(features, block)
    categorical = [col for col in frame if col in CATEGORY_LEVELS]
    numeric = [col for col in frame if col not in CATEGORY_LEVELS]
    x = frame[numeric].to_numpy(dtype=float, na_value=np.nan)
    if np.isinf(x).any(): raise ValueError('Infinite numeric feature')
    medians = np.array([np.median(column[np.isfinite(column)]) if np.isfinite(column).any() else 0. for column in x.T])
    imputed = np.where(np.isnan(x), medians, x); mean = imputed.mean(axis=0); scale = imputed.std(axis=0); scale[scale == 0] = 1
    columns = numeric + [f'{c}__missing' for c in numeric] + [f'{c}={v}' for c in categorical for v in CATEGORY_LEVELS[c]+['MISSING', 'UNKNOWN']]
    state = {'block': block, 'numeric': numeric, 'categorical': categorical, 'medians': medians.tolist(),
             'mean': mean.tolist(), 'scale': scale.tolist(), 'columns': columns,
             'categories': {c: CATEGORY_LEVELS[c]+['MISSING', 'UNKNOWN'] for c in categorical}, 'class_order': [0, 1]}
    return transform(features, state), state


def transform(features, state):
    frame = basis(features, state['block']); x = frame[state['numeric']].to_numpy(dtype=float, na_value=np.nan)
    missing = np.isnan(x); numeric = (np.where(missing, state['medians'], x)-state['mean'])/state['scale']
    dummies = []
    for name in state['categorical']:
        values = frame[name].map(lambda v: _category(name, v)).to_numpy()
        dummies.extend((values == level).astype(float) for level in state['categories'][name])
    result = np.column_stack([numeric, missing.astype(float), *dummies]).astype(np.float64)
    if not np.isfinite(result).all(): raise ValueError('Nonfinite inference matrix')
    return result


def grid(family):
    if family == 'logistic': return [{'C': c} for c in (.1, 1., 10.)]
    if family == 'tree': return [{'learning_rate': lr, 'max_leaf_nodes': leaves, 'l2_regularization': l2}
                                for lr, leaves, l2 in itertools.product((.05, .10), (7, 15), (0., 10.))]
    raise ValueError('Unapproved family')


def tie_key(family, config):
    return (config['C'],) if family == 'logistic' else (config['max_leaf_nodes'], -config['l2_regularization'], config['learning_rate'])


def select_candidate(family, candidates):
    if len(candidates) != len(grid(family)) or any(c['status'] != 'complete' for c in candidates):
        raise ValueError('Reduced or failed candidate grid cannot be selected')
    minimum = min(c['log_loss'] for c in candidates)
    return min((c for c in candidates if c['log_loss'] <= minimum+1e-6), key=lambda c: tie_key(family, c['config']))


def build_counts(features, y, kind):
    y = common.binary_targets(y); m = float((y.sum()+.5)/(len(y)+1))
    if kind == 'constant': return {'kind': kind, 'global': m}
    if kind != 'context': raise ValueError('Unknown reference')
    downs, cells = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for d, distance, target in zip(features.down, features.ydstogo, y):
        down = _category('down', d); key = (down, distance_band(distance))
        downs[down][0] += 1; downs[down][1] += int(target); cells[key][0] += 1; cells[key][1] += int(target)
    rates = {key: (s+50*m)/(n+50) for key, (n, s) in downs.items()}
    return {'kind': kind, 'global': m, 'downs': rates, 'cells': {key: (s+50*rates[key[0]])/(n+50) for key, (n, s) in cells.items()}}


def count_prediction(features, state):
    if state['kind'] == 'constant': return np.full(len(features), state['global'])
    return np.array([state['cells'].get((_category('down', d), distance_band(distance)), state['downs'].get(_category('down', d), state['global']))
                     for d, distance in zip(features.down, features.ydstogo)])


def planned_operations():
    return [f'initial_reference_{kind}' for kind in ('constant', 'context')] + \
           [f'initial_{family}_{block}_{i}' for family in ('logistic', 'tree') for block in BLOCKS for i, _ in enumerate(grid(family))] + \
           [f'refit_{family}_{block}' for family in ('logistic', 'tree') for block in BLOCKS] + \
           [f'refit_reference_{kind}' for kind in ('constant', 'context')] + \
           [f'calibrate_{name}' for name in ['context', *[f'{family}_{block}' for family in ('logistic', 'tree') for block in BLOCKS]]]


def _source_path(root, name):
    if name not in PINS: raise ValueError('Unpinned NFL basename')
    for directory in ('data/raw/tactical_research', 'data/tactical/football'):
        path = Path(root)/directory/name
        if path.is_file(): return path
    raise FileNotFoundError(name)


def _verify_source(path, season, source):
    names = {'pbp': f'play_by_play_{season}.csv.gz', 'participation': f'pbp_participation_{season}.csv', 'ftn': f'ftn_charting_{season}.csv'}
    if season not in (2023, 2024, 2025) or source not in names or path.name != names[source] or path.name not in PINS:
        raise ValueError('Pinned source/season/role mismatch before body read')
    release = {'pbp': 'pbp', 'participation': 'pbp_participation', 'ftn': 'ftn_charting'}[source]
    url = f'https://github.com/nflverse/nflverse-data/releases/download/{release}/{path.name}'
    return parser.verify_source(path, PINS[path.name], url)


def read_features(root, season):
    if season not in (2023, 2024, 2025): raise PermissionError('Season outside numerical feature contract')
    columns = {'pbp': [*parser.KEYS, *parser.PBP_CONTEXT, *parser.PBP_METADATA, *parser.PBP_ELIGIBILITY],
               'participation': ['nflverse_game_id', 'play_id', *parser.PART_PRESNAP],
               'ftn': ['nflverse_game_id', 'nflverse_play_id', *parser.FTN_PRESNAP]}
    names = {'pbp': f'play_by_play_{season}.csv.gz', 'participation': f'pbp_participation_{season}.csv', 'ftn': f'ftn_charting_{season}.csv'}
    frames, records, audit = {}, [], []
    for source, name in names.items():
        path = _source_path(root, name); record = _verify_source(path, season, source); record['path'] = str(path.relative_to(root)); records.append(record)
        frames[source] = pd.read_csv(path, usecols=columns[source], low_memory=False)
        audit.append({'filename': name, 'season': season, 'purpose': 'features_only', 'columns': columns[source], 'target_columns_loaded': False})
    raw = parser._canonical_keys(frames['pbp'], 'pbp', season)
    ordinal = {(r.game_id, r.play_id): int(i) for i, r in raw.iterrows()}
    panel = parser.build_panel(frames['pbp'], frames['participation'], frames['ftn'], season, include_targets=False)
    panel.metadata['_source_row'] = [ordinal[(r.game_id, r.play_id)] for r in panel.metadata.itertuples()]
    # Supplemental join diagnostics cannot consult play_type outside frozen cohort selection.
    if any('play_category' in key for source in panel.qa['joins'].values() for key in source):
        raise ValueError('Later-play-category join audit breached the firewall')
    return panel, records, audit


def prepare(root=parser.ROOT, approval_path=None):
    root = Path(root); _guard(root, 'prepare', approval_path)
    out = root/'artifacts/tactical/football/model'; out.mkdir(parents=True, exist_ok=True)
    panels, sources, audit = {}, [], []
    for season in (2023, 2024, 2025):
        panel, records, reads = read_features(root, season); panels[season] = panel; sources += records; audit += reads
    # 2022 participation/FTN pins remain schema-reference evidence only. Hash
    # their bytes/provenance without loading rows or adding a training season.
    for name in ('pbp_participation_2022.csv', 'ftn_charting_2022.csv'):
        path = _source_path(root, name)
        record = parser.verify_source(path, PINS[name], parser.source_url(name))
        record['path'] = str(path.relative_to(root)); record['role'] = 'schema_reference_only'
        sources.append(record)
    roles, split = {}, []
    for name, (season, low, high) in ROLES.items():
        panel = panels[season]; mask = panel.metadata.week.between(low, high)
        meta = panel.metadata.loc[mask].reset_index(drop=True); features = panel.features.loc[mask].reset_index(drop=True)
        order = meta.sort_values(['season', 'week', 'game_id', 'play_id']).index
        meta = meta.loc[order].reset_index(drop=True); features = features.loc[order].reset_index(drop=True)
        if (len(meta), meta.game_id.nunique()) != EXPECTED[name]: raise ValueError(f'Reviewed role support changed: {name}')
        if not meta.season_type.eq('REG').all(): raise ValueError('Non-REG role record')
        roles[name] = {'metadata': meta, 'features': features}
        split += [{**record, 'role': name} for record in meta[['season', 'week', 'game_id', 'play_id']].to_dict('records')]
    game_roles = defaultdict(set)
    for r in split: game_roles[r['game_id']].add(r['role'])
    if any(len(v) != 1 for v in game_roles.values()): raise ValueError('Game split between roles')
    split.sort(key=lambda r: (r['season'], r['week'], r['game_id'], r['play_id'], r['role']))
    feature_path = out/'prepared_features.joblib'
    if feature_path.exists():
        raise FileExistsError('Preparation artifact already exists; verify immutable binding instead of rebuilding')
    feature_hash = common.save_object(feature_path, roles)
    info = {'fingerprint': common.fingerprint(root, SPORT, PROTOCOL), 'sources': sources, 'source_reads': audit,
            'split_sha256': common.digest(split), 'membership': split, 'features_sha256': feature_hash,
            'support': {name: {'plays': len(role['metadata']), 'games': int(role['metadata'].game_id.nunique())} for name, role in roles.items()}}
    write_json(out/'prepared.json', info)
    from . import gates
    data = {s['path']: s['sha256'] for s in sources}
    for s in sources: data[s['path']+'.source.json'] = sha256_file(root/(s['path']+'.source.json'))
    for relative in ('artifacts/tactical/football/model/prepared_features.joblib', 'artifacts/tactical/football/model/prepared.json'):
        data[relative] = sha256_file(root/relative)
    gates.prepare_binding(root, SPORT, PROTOCOL, list(info['fingerprint']['files']), data,
                          {'split_sha256': info['split_sha256'], 'planned_operations': 50, 'maximum_attempts': 53, 'support': info['support']})
    return info


def _prepared(root):
    out = Path(root)/'artifacts/tactical/football/model'; info = json.loads((out/'prepared.json').read_text())
    if info['fingerprint'] != common.fingerprint(root, SPORT, PROTOCOL): raise ValueError('Frozen protocol/code/environment changed')
    roles = common.load_object(out/'prepared_features.joblib', info['features_sha256'])
    return out, info, roles


def _labels(root, role_name, metadata, stage, approval_path=None, **evidence):
    _guard(root, stage, approval_path, **evidence)
    if stage == 'evaluate': common.verify_prediction_evidence(root, SPORT, evidence.get('prediction_sha256'))
    permitted = {'develop': {'initial', 'selection'}, 'calibrate': {'calibration'}, 'evaluate': {'test'}}
    if role_name not in permitted.get(stage, set()): raise PermissionError('Target reader rejects unapproved NFL role')
    season, low, high = ROLES[role_name]
    if not metadata.season.eq(season).all() or not metadata.week.between(low, high).all() or not metadata.season_type.eq('REG').all():
        raise ValueError('Target metadata role mismatch before body read')
    path = _source_path(root, f'play_by_play_{season}.csv.gz'); _verify_source(path, season, 'pbp')
    # Read only approved source row ordinals. Calibration/final targets cannot enter
    # development dataframes even though the source file also contains those rows.
    ordinals = set(metadata['_source_row'].astype(int))
    columns = [*parser.KEYS, 'season', 'week', *parser.PBP_TARGETS]
    frame = pd.read_csv(path, usecols=columns, skiprows=lambda i: i > 0 and i-1 not in ordinals, low_memory=False)
    frame = parser._canonical_keys(frame, 'target', season)
    if not pd.to_numeric(frame.season).eq(season).all() or not pd.to_numeric(frame.week).between(low, high).all():
        raise ValueError('Loaded target source rows cross the approved role')
    joined = metadata[parser.KEYS].merge(frame, on=parser.KEYS, how='left', validate='one_to_one', sort=False, indicator=True)
    if len(frame) != len(metadata) or not joined['_merge'].eq('both').all(): raise ValueError('Target row identity mismatch')
    flags = np.column_stack([parser._boolean(joined[c]).to_numpy(dtype=object) for c in parser.PBP_TARGETS])
    invalid = [i for i, row in enumerate(flags) if any(pd.isna(v) or v not in (0, 1) for v in row)]
    out = Path(root)/'artifacts/tactical/football/model'
    write_json(out/f'target_read_{role_name}.json', {'role': role_name, 'stage': stage, 'filename': path.name,
             'columns': columns, 'loaded_rows': len(frame), 'requested_ids_sha256': common.digest(metadata[parser.KEYS].to_dict('records'))})
    if invalid:
        write_json(out/f'invalid_targets_{role_name}.json', metadata.iloc[invalid][parser.KEYS].to_dict('records'))
        raise ValueError(f'{len(invalid)} eligible rows have unknown/nonbinary target flags; cohort retained and stage stopped')
    return common.binary_targets(np.any(flags.astype(int) == 1, axis=1).astype(int))


def _fit(features, y, family, block, config, guard):
    guard(); x, state = fit_transform(features, block)
    if family == 'logistic':
        estimator = LogisticRegression(**config, penalty='l2', solver='lbfgs', fit_intercept=True,
                          max_iter=2000, tol=1e-6, class_weight=None, warm_start=False, random_state=common.SEED)
    elif family == 'tree':
        estimator = HistGradientBoostingClassifier(**config, loss='log_loss', max_iter=150, min_samples_leaf=200,
                           max_depth=None, max_bins=255, max_features=1., early_stopping=False, warm_start=False,
                           class_weight=None, monotonic_cst=None, interaction_cst=None, categorical_features=None,
                           random_state=common.SEED)
    else: raise ValueError('Unapproved model family')
    return {'model': common.checked_fit(estimator, x, y, guard), 'transform': state, 'family': family, 'block': block, 'config': config}


def _predict(features, artifact):
    return common.learned_prediction(artifact['model'], transform(features, artifact['transform']))


def support_records(features, metadata):
    frame = pd.DataFrame({'down': features.down.map(lambda v: _category('down', v)), 'distance': features.ydstogo.map(distance_band),
                          'formation': features.formation.map(lambda v: _category('formation', v)),
                          'motion': features.motion.map(lambda v: _category('motion', v)), 'game_id': metadata.game_id})
    return frame.groupby(['down', 'distance', 'formation', 'motion'], sort=True).agg(plays=('game_id', 'size'), games=('game_id', 'nunique')).reset_index().to_dict('records')


def personnel_tuple(row):
    return '|'.join('MISSING' if pd.isna(row[c]) else str(int(row[c])) for c in ('offense_rb', 'offense_te', 'offense_wr'))


def develop(root=parser.ROOT, approval_path=None):
    root = Path(root); _guard(root, 'develop', approval_path, fresh=True); guard = lambda: _guard(root, 'develop', approval_path)
    out, info, roles = _prepared(root)
    if (out/'DEVELOPMENT_FREEZE.json').exists():
        manifest = common.verify_development(out, common.digest(info), planned_operations())
        return {'stage':'development_complete','artifact_sha256':manifest['sha256'], 'reused':True}
    initial, selection = roles['initial'], roles['selection']; yi = _labels(root, 'initial', initial['metadata'], 'develop', approval_path)
    ys = _labels(root, 'selection', selection['metadata'], 'develop', approval_path)
    if any(len(np.unique(y)) != 2 for y in (yi, ys)): raise ValueError('Both target classes required in every development role')
    ledger = common.OperationLedger(out/'operations', planned_operations(), 3, root=root, task=SPORT)
    candidates, chosen, models, references, reference_development = [], {}, {}, {}, {}
    for kind in ('constant', 'context'):
        op = f'initial_reference_{kind}'
        state = ledger.run(op, common.digest({'prepared': common.digest(info), 'operation': op}),
                           lambda: build_counts(initial['features'], yi, kind), guard)
        reference_development[kind] = {'log_loss': common.mean_loss(ys, count_prediction(selection['features'], state)), 'n': len(ys)}
    for family in ('logistic', 'tree'):
        for block in BLOCKS:
            own = []
            for i, config in enumerate(grid(family)):
                op = f'initial_{family}_{block}_{i}'
                record = {'family': family, 'block': block, 'config': config, 'operation': op}
                try:
                    artifact = ledger.run(op, common.digest({'prepared': common.digest(info), 'operation': op, 'config': config}),
                                          lambda: _fit(initial['features'], yi, family, block, config, guard), guard)
                    record.update(log_loss=common.mean_loss(ys, _predict(selection['features'], artifact)), n=len(ys), status='complete')
                except BaseException as exc:
                    record.update(status='failed', error_type=type(exc).__name__, error=str(exc)); candidates.append(record)
                    write_json(out/'development_candidates.json', candidates); raise
                own.append(record); candidates.append(record); write_json(out/'development_candidates.json', candidates)
            chosen[f'{family}_{block}'] = select_candidate(family, own)['config']
    write_json(out/'selection.json', {'selected': chosen, 'references': reference_development,
                                     'selection_metric': '2024 weeks 1-9 unrounded mean natural log loss', 'tie_epsilon': 1e-6})
    xf = pd.concat([initial['features'], selection['features']], ignore_index=True); yf = np.concatenate([yi, ys])
    mf = pd.concat([initial['metadata'], selection['metadata']], ignore_index=True)
    for name, config in chosen.items():
        family, block = name.split('_'); op = f'refit_{name}'
        models[name] = ledger.run(op, common.digest({'prepared': common.digest(info), 'operation': op, 'config': config}),
                                 lambda: _fit(xf, yf, family, block, config, guard), guard)
    for kind in ('constant', 'context'):
        op = f'refit_reference_{kind}'
        references[kind] = ledger.run(op, common.digest({'prepared': common.digest(info), 'operation': op}), lambda: build_counts(xf, yf, kind), guard)
    personnel = pd.DataFrame({'tuple': initial['features'].apply(personnel_tuple, axis=1), 'game': initial['metadata'].game_id})
    counts = personnel.groupby('tuple').agg(plays=('game', 'size'), games=('game', 'nunique'))
    vocabulary = counts.index[(counts.plays >= 200) & (counts.games >= 10)].tolist()
    bundle = {'models': models, 'references': references, 'selected': chosen, 'personnel_vocabulary': vocabulary,
              'refit_context_support': support_records(xf, mf), 'prepared_sha256': common.digest(info),
              'train_ids_sha256': common.digest(mf[parser.KEYS].to_dict('records')), 'class_order': [0, 1]}
    sha = common.save_object(out/'developed.joblib', bundle)
    write_json(out/'development_manifest.json', {'artifact': 'developed.joblib', 'sha256': sha, 'selected': chosen,
                                               'prepared_sha256': common.digest(info), 'selection_sha256': sha256_file(out/'selection.json')})
    common.freeze_development(out, common.digest(info), planned_operations())
    return {'stage': 'development_complete', 'artifact_sha256': sha, 'selected': chosen, 'test_labels_read': False}


def _calibration_fit(y, p, guard):
    guard()
    if len(np.unique(y)) != 2: raise ValueError('Calibration role must contain both classes')
    estimator = LogisticRegression(C=1., penalty='l2', solver='lbfgs', fit_intercept=True, max_iter=2000,
                                    tol=1e-6, class_weight=None, warm_start=False, random_state=common.SEED)
    estimator = common.checked_fit(estimator, common.logit(p).reshape(-1, 1), y, guard)
    if estimator.coef_[0, 0] <= 0: raise ValueError('Nonpositive calibration slope; pause before holdout opening')
    return estimator


def calibrated(p, calibrator):
    return common.learned_prediction(calibrator, common.logit(p).reshape(-1, 1))


def calibrate(root=parser.ROOT, approval_path=None):
    root = Path(root); _guard(root, 'calibrate', approval_path, fresh=True); guard = lambda: _guard(root, 'calibrate', approval_path)
    out, info, roles = _prepared(root)
    manifest = common.verify_development(out, common.digest(info), planned_operations())
    bundle = common.load_object(out/manifest['artifact'], manifest['sha256']); cal = roles['calibration']
    if bundle.get('prepared_sha256') != common.digest(info) or bundle.get('selected') != manifest.get('selected'):
        raise PermissionError('Developed model/selection belongs to another prepared population')
    y = _labels(root, 'calibration', cal['metadata'], 'calibrate', approval_path)
    if len(np.unique(y)) != 2: raise ValueError('Calibration role needs both classes')
    raw = {'context': count_prediction(cal['features'], bundle['references']['context'])}
    raw.update({name: _predict(cal['features'], model) for name, model in bundle['models'].items()})
    ledger = common.OperationLedger(out/'operations', planned_operations(), 3, root=root, task=SPORT); calibrators = {}
    for name, p in raw.items():
        op = f'calibrate_{name}'
        calibrators[name] = ledger.run(op, common.digest({'development': manifest['sha256'], 'operation': op}),
                                      lambda: _calibration_fit(y, p, guard), guard)
    diagnostics = {name: {'n': len(y), 'raw_log_loss': common.mean_loss(y, p),
                         'calibrated_log_loss': common.mean_loss(y, calibrated(p, calibrators[name])),
                         'interpretation': 'calibration fitting diagnostic, not independent performance'} for name, p in raw.items()}
    bundle.update(calibrators=calibrators, calibration_ids_sha256=common.digest(cal['metadata'][parser.KEYS].to_dict('records')))
    write_json(out/'calibration_diagnostics.json', diagnostics)
    sha = common.save_object(out/'frozen.joblib', bundle); parity = {}
    # Every learned procedure is checked in batch and single-row mode. Comparing
    # a fixed representative prefix is an inference check, not an extra fit.
    for name, model in bundle['models'].items():
        # Fixed first 32 canonical calibration keys, independent of targets.
        features = cal['features'].iloc[:32]; batch = _predict(features, model)
        single = np.array([_predict(features.iloc[[i]], model)[0] for i in range(len(features))])
        if not np.allclose(batch, single, rtol=0, atol=1e-12): raise ValueError('Frozen inference parity failed')
        parity[name] = float(np.max(np.abs(batch-single)))
    frozen = {'artifact': 'frozen.joblib', 'sha256': sha, 'prepared_sha256': common.digest(info), 'class_order': [0, 1],
              'selected': bundle['selected'], 'parity_max_absolute_error': parity,
              'parity_cases': 'first 32 canonical calibration keys, outcome-independent',
              'calibration_parameters': {name: {'intercept': float(c.intercept_[0]), 'slope': float(c.coef_[0, 0])} for name, c in calibrators.items()},
              'train_ids_sha256': bundle['train_ids_sha256'], 'calibration_ids_sha256': bundle['calibration_ids_sha256'],
              'serialization': 'local joblib; exact package environment/file hash required; never load untrusted pickle',
              'reporting': {'primary': 'logistic_C_calibrated minus logistic_A_calibrated', 'epsilon': common.EPSILON, 'bins': BINS,
                            'bootstrap_replicates': 2000, 'game_seed': common.SEED, 'week_seed': common.SEED+1, 'quantile_method': 'linear'}}
    write_json(out/'frozen_manifest.json', frozen)
    write_json(root/'artifacts/tactical/football/SELECTION_FREEZE.json',
               {'task': SPORT, 'frozen_manifest_sha256': sha256_file(out/'frozen_manifest.json'), 'artifact_sha256': sha,
                'prepared_sha256': common.digest(info), 'selection_sha256': sha256_file(out/'selection.json'), 'class_order': [0, 1]})
    return frozen


def predict(root=parser.ROOT, approval_path=None):
    root = Path(root); _guard(root, 'predict', approval_path, fresh=True)
    out, info, roles = _prepared(root); test = roles['test']; manifest = common.verify_frozen(root, SPORT, common.digest(info))
    bundle = common.load_object(out/manifest['artifact'], manifest['sha256']); x, m = test['features'], test['metadata']
    frame = m[['season', 'week', *parser.KEYS, 'posteam']].copy()
    frame['constant_raw'] = count_prediction(x, bundle['references']['constant'])
    raw = {'context': count_prediction(x, bundle['references']['context'])}
    raw.update({name: _predict(x, model) for name, model in bundle['models'].items()})
    for name, p in raw.items(): frame[name+'_raw'] = p; frame[name+'_calibrated'] = calibrated(p, bundle['calibrators'][name])
    path = out/'test_predictions.json'
    if path.exists(): raise FileExistsError('Immutable predictions already exist')
    write_json(path, frame.to_dict('records'))
    result = {'prediction_file': path.name, 'prediction_sha256': sha256_file(path), 'frozen_manifest_sha256': sha256_file(out/'frozen_manifest.json'),
              'split_sha256': info['split_sha256'], 'columns': frame.columns.tolist(), 'n': len(frame), 'labels_joined': False}
    write_json(out/'prediction_manifest.json', result); return result


def _slice_labels(features, metadata, vocabulary):
    x = features
    time = np.select([x.qtr.ge(5).fillna(False).to_numpy(dtype=bool), x.qtr.between(1, 3).fillna(False).to_numpy(dtype=bool),
                      (x.qtr.eq(4) & x.game_seconds_remaining.gt(300)).fillna(False).to_numpy(dtype=bool),
                      (x.qtr.eq(4) & x.game_seconds_remaining.le(300)).fillna(False).to_numpy(dtype=bool)],
                     ['OT', 'qtr1-3', 'qtr4_above300', 'qtr4_last300'], default='MISSING')
    personnel = x.apply(personnel_tuple, axis=1).map(lambda v: v if v in vocabulary else 'OTHER')
    return {'down': x.down.map(lambda v: _category('down', v)), 'distance': x.ydstogo.map(distance_band),
            'formation': x.formation.map(lambda v: _category('formation', v)), 'motion': x.motion.map(lambda v: _category('motion', v)),
            'offensive_team': metadata.posteam.fillna('MISSING'), 'time_state': pd.Series(time), 'personnel': personnel,
            'score_state': x.score_differential.map(lambda v: 'MISSING' if pd.isna(v) else 'trailing' if v < 0 else 'leading' if v > 0 else 'tied')}


def evaluate(root=parser.ROOT, approval_path=None):
    root = Path(root); out = root/'artifacts/tactical/football/model'; manifest = json.loads((out/'prediction_manifest.json').read_text())
    _guard(root, 'evaluate', approval_path, fresh=True, prediction_sha256=manifest['prediction_sha256'])
    _, info, roles = _prepared(root); test = roles['test']
    if sha256_file(out/manifest['prediction_file']) != manifest['prediction_sha256']: raise ValueError('Prediction hash changed')
    if sha256_file(out/'frozen_manifest.json') != manifest['frozen_manifest_sha256']: raise ValueError('Frozen model manifest changed')
    destination = root/'reports/tactical/football/model/evaluation.json'
    if destination.exists(): raise FileExistsError('One-shot evaluation already exists')
    frame = pd.DataFrame(json.loads((out/manifest['prediction_file']).read_text()))
    if not frame[parser.KEYS].equals(test['metadata'][parser.KEYS]): raise ValueError('Identical-row prediction order failed')
    y = _labels(root, 'test', test['metadata'], 'evaluate', approval_path, prediction_sha256=manifest['prediction_sha256'])
    columns = [c for c in frame if c.endswith(('_raw', '_calibrated'))]; groups = frame.game_id.to_numpy()
    reports = {c: common.summarize(y, frame[c], groups, BINS) for c in columns}
    left, right = frame.logistic_C_calibrated.to_numpy(), frame.logistic_A_calibrated.to_numpy()
    primary = common.paired(y, left, right, groups); week = common.paired(y, left, right, frame.week.to_numpy(), seed=common.SEED+1)
    frozen = json.loads((out/'frozen_manifest.json').read_text()); bundle = common.load_object(out/frozen['artifact'], frozen['sha256'])
    slices = {}
    for field, labels in _slice_labels(test['features'], test['metadata'], bundle['personnel_vocabulary']).items():
        slices[field] = []
        for value in sorted(set(labels)):
            mask = np.asarray(labels == value); n, games = int(mask.sum()), len(np.unique(groups[mask]))
            entry = {'value': value, 'plays': n, 'games': games, 'status': 'insufficient_support' if n < 100 or games < 5 else 'descriptive'}
            if n >= 100 and games >= 5: entry['procedures'] = {c: common.summarize(y[mask], frame[c].to_numpy()[mask], groups[mask], BINS) for c in columns}
            slices[field].append(entry)
    useful = primary['log_loss']['difference'] <= -.005 and primary['log_loss']['interval'][1] < 0 and week['log_loss']['interval'][1] < 0 and primary['brier']['difference'] <= .001
    report = {'phase': 'frozen_evaluation', 'procedures': reports, 'primary_game_bootstrap': primary, 'week_dependence_sensitivity': week,
              'slices': slices, 'usefulness_yardstick_met': useful, 'prediction_sha256': manifest['prediction_sha256'],
              'designated_procedure': 'calibrated logistic C; no test fallback', 'conditional_sampling_uncertainty_only': True,
              'caveats': ['2024 selection/calibration missingness shift', '18 week clusters are few; repeated-team dependence remains',
                          'Retrospective realized dropback, not original intent or causal formation/motion effect',
                          'Performance-blind after source QA, not prospective or fully human-blind'],
              'release': 'local only; independent score recomputation and source-specific rights review required'}
    write_json(destination, report); return report
