"""Local descriptive StatsBomb WSL shot-context parser. No fits or predictions.

python -m experiments.tactical.soccer --fetch
All raw/derived rows and summaries remain excluded from publication.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
import math
from pathlib import Path

from .shot_sources import pinned_blob, sha256_file, write_json

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '4b73468fc5b0f1950f9f66fada70ad3a4f9327cb'
DEVELOPMENT_SEASONS = (4, 42, 90)
QA_SEASON = 281
GOAL = (120.0, 40.0)
POSTS = ((120.0, 36.0), (120.0, 44.0))
OUTCOMES = frozenset(('Goal', 'Blocked', 'Off T', 'Post', 'Saved', 'Wayward', 'Saved Off Target', 'Saved to Post'))
CAVEAT = ('Recorded relevant-player subset, not complete defense or a visibility polygon. '
          'Coordinates and identities can be inaccurate. Nearest recorded opponent is not a strict physical bound. '
          'No motion, body orientation or joint mechanics is measured here.')


def finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_location(value) -> bool:
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(finite_number(v) for v in value)
            and 0 <= value[0] <= 120 and 0 <= value[1] <= 80)


def goal_geometry(location) -> dict:
    if not valid_location(location):
        raise ValueError('Location must be within the standardized 120 x 80 grid')
    x, y = location
    vectors = [(px - x, py - y) for px, py in POSTS]
    a, b = vectors
    width = None if any(math.hypot(*v) == 0 for v in vectors) else math.atan2(
        abs(a[0] * b[1] - a[1] * b[0]), a[0] * b[0] + a[1] * b[1])
    distance = math.hypot(GOAL[0] - x, GOAL[1] - y)
    return {'x_native': x, 'y_native': y, 'distance_native': distance,
            'goal_angular_width_rad': width,
            'goal_bearing_rad': math.atan2(GOAL[1] - y, GOAL[0] - x) if distance else None,
            'lateral_offset_native': y - 40}


def in_goal_triangle(location, shot_location) -> bool:
    """Closed geometric triangle, no invented player radius or metre conversion."""
    if not valid_location(location) or not valid_location(shot_location):
        return False
    a, b, c = tuple(shot_location), POSTS[0], POSTS[1]
    def cross(p, q, r):
        return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    if abs(cross(a, b, c)) < 1e-12:
        return False
    signs = [cross(a, b, location), cross(b, c, location), cross(c, a, location)]
    return min(signs) >= -1e-12 or max(signs) <= 1e-12


def recorded_defense(event: dict) -> tuple[dict, dict]:
    raw = event['shot'].get('freeze_frame')
    frame = raw if isinstance(raw, list) else []
    valid, invalid, unknown_team = [], 0, 0
    for player in frame:
        if not isinstance(player, dict) or not valid_location(player.get('location')):
            invalid += 1
        elif not isinstance(player.get('teammate'), bool):
            unknown_team += 1
        elif player['teammate'] is False:
            valid.append(player)
    keepers = [p for p in valid if p.get('position', {}).get('id') == 1]
    defender = [p for p in valid if isinstance(p.get('position', {}).get('id'), int) and p['position']['id'] > 1]
    unknown_role = sum(not isinstance(p.get('position', {}).get('id'), int) or p['position']['id'] < 1 for p in valid)
    present = bool(frame)
    features = {'recorded_opponent_count': len(valid) if present else None,
                'recorded_outfield_opponent_count': len(defender) if present else None,
                'nearest_recorded_opponent_native': min((math.dist(event['location'], p['location']) for p in valid), default=None),
                'recorded_opponents_in_goal_triangle': sum(in_goal_triangle(p['location'], event['location']) for p in valid) if present else None,
                'recorded_outfield_in_goal_triangle': sum(in_goal_triangle(p['location'], event['location']) for p in defender) if present else None,
                'keeper_depth_native': 120 - keepers[0]['location'][0] if len(keepers) == 1 else None,
                'keeper_lateral_offset_native': keepers[0]['location'][1] - 40 if len(keepers) == 1 else None}
    quality = {'freeze_frame_present': present, 'recorded_players': len(frame),
               'invalid_recorded_player_locations': invalid, 'unknown_teammate_flags': unknown_team,
               'recorded_opposition_keeper_count': len(keepers), 'unknown_opponent_role_count': unknown_role,
               'complete_defense_established': False, 'visible_area_available': False}
    return features, quality


def exclusion_reason(event: dict) -> str | None:
    if event.get('type', {}).get('name') != 'Shot':
        return 'not_a_shot'
    if event.get('period') == 5:
        return 'shootout'
    if not isinstance(event.get('period'), int) or isinstance(event.get('period'), bool) or not 1 <= event['period'] <= 4:
        return 'invalid_period'
    if not isinstance(event.get('shot'), dict):
        return 'missing_shot_object'
    if not isinstance(event['shot'].get('type'), dict) or not event['shot']['type'].get('name'):
        return 'missing_shot_type'
    if event['shot']['type']['name'] == 'Penalty':
        return 'penalty'
    if not valid_location(event.get('location')):
        return 'invalid_or_missing_location'
    return None


def extract_context(event: dict) -> dict | None:
    """Allowlist only: no outcome, endpoint, provider xG, assist or future lookup."""
    if exclusion_reason(event) is not None:
        return None
    features, quality = recorded_defense(event)
    body = event['shot'].get('body_part', {}).get('name')
    broad_body = body if body in ('Head', 'Left Foot', 'Right Foot') else 'Other/unknown'
    return {'event_id': event.get('id'), 'event_index': event.get('index'),
            'period': event.get('period'), 'timestamp': event.get('timestamp'),
            'features': {**goal_geometry(event['location']), **features,
                         'body_part': broad_body,
                         'shot_type': event['shot'].get('type', {}).get('name'),
                         'play_pattern': event.get('play_pattern', {}).get('name')},
            'quality': quality}


def extract_target(event: dict) -> dict:
    """Separate target path, called only for approved development seasons."""
    outcome = event.get('shot', {}).get('outcome', {}).get('name')
    return {'event_id': event.get('id'), 'goal': int(outcome == 'Goal') if outcome in OUTCOMES else None,
            'target_available': outcome in OUTCOMES}


def cohort_for(season_id: int, date: str) -> str:
    if season_id in DEVELOPMENT_SEASONS:
        return 'development'
    if season_id == QA_SEASON:
        return 'calibration_qa_only' if date < '2024-01-01' else 'test_qa_only'
    raise ValueError('Season is outside the fixed WSL source cohort')


def summarize_development(contexts: list[dict], targets: dict) -> dict:
    groups = defaultdict(lambda: [0, 0, 0])
    for row in contexts:
        if row['cohort'] != 'development':
            raise ValueError('Later-cohort descriptions are not permitted')
        f = row['features']; target = targets.get(row['event_id'], {}).get('goal')
        d = f['distance_native']
        distance_bin = next((label for edge, label in ((6,'[0,6)'),(12,'[6,12)'),(18,'[12,18)'),(24,'[18,24)'),(36,'[24,36)')) if d < edge), '[36,infinity)')
        angle = f['goal_angular_width_rad']
        angle_bin = 'missing' if angle is None else next((label for edge, label in ((.25,'[0,0.25)'),(.5,'[0.25,0.5)'),(1,'[0.5,1)')) if angle < edge), '[1,pi]')
        nearest = f['nearest_recorded_opponent_native']
        nearest_bin = 'missing' if nearest is None else next((label for edge, label in ((2,'[0,2)'),(4,'[2,4)'),(8,'[4,8)')) if nearest < edge), '[8,infinity)')
        for kind, label in [('distance_native', distance_bin), ('goal_angular_width_rad', angle_bin),
                            ('nearest_recorded_opponent_native', nearest_bin), ('body_part', f['body_part']),
                            ('opposition_keeper_recorded', str(row['quality']['recorded_opposition_keeper_count'] == 1))]:
            bucket = groups[kind, label]; bucket[0] += 1
            bucket[1] += target is not None; bucket[2] += target == 1
    return {kind: [{'category': label, 'shots': n, 'target_available': available, 'observed_goals': goals}
                   for (k,label),(n,available,goals) in sorted(groups.items()) if k == kind]
            for kind in sorted({key[0] for key in groups})}


def development_plot(contexts: list[dict], targets: dict, limit: int = 200) -> dict:
    if any(r.get('cohort') != 'development' for r in contexts):
        raise ValueError('Only development shots can enter the local plot')
    selected = sorted(contexts, key=lambda r: hashlib.sha256(r['event_id'].encode()).hexdigest())[:max(0,min(limit,200))]
    return {'sample_method':'First 200 SHA256(event UUID) order; deterministic development-only subset, not outcome-selected',
            'population_shots':len(contexts),'sample_shots':len(selected),'coordinate_units':'native standardized 120x80; not metres',
            'attacking_goal':[120,40],'goalposts':[[120,36],[120,44]],
            'points':[{'x':r['features']['x_native'],'y':r['features']['y_native'],
                       'observed_goal':targets.get(r['event_id'],{}).get('goal'),
                       'nearest_recorded_opponent':r['features']['nearest_recorded_opponent_native'],
                       'defensive_snapshot_available':r['quality']['freeze_frame_present'],
                       'unique_keeper_recorded':r['quality']['recorded_opposition_keeper_count']==1,
                       'complete_defense_established':False} for r in selected]}


def build(root: Path = ROOT, fetch: bool = False, workers: int = 6) -> dict:
    root = root.resolve(); staging = root / 'data/tactical/soccer'
    tree = json.loads((root/'data/research_source_docs/statsbomb_open-data_tree.json').read_text())
    def source(relative):
        return pinned_blob(relative, tree=tree, commit=COMMIT, repository='statsbomb/open-data',
                           cache=root/'data/research/statsbomb_open-data', staging=staging/'source', root=root, fetch=fetch)
    sources, matches = [], []
    for season in (*DEVELOPMENT_SEASONS, QA_SEASON):
        path, record = source(f'data/matches/37/{season}.json'); sources.append(record)
        for match in json.loads(path.read_text()):
            if match['competition']['competition_id'] != 37 or match['season']['season_id'] != season:
                raise ValueError('Match index differs from declared competition/season')
            matches.append((season, match))
    expected = Counter(season for season, _ in matches)
    if expected != {4:107,42:87,90:131,281:132}:
        raise ValueError(f'Pinned WSL population changed: {expected}')
    matches.sort(key=lambda p:(p[1]['match_date'],p[1]['match_id']))
    relatives = [f"data/events/{m['match_id']}.json" for _,m in matches]
    # Downloads write only into the ignored tactical source directory, bounded concurrency.
    with ThreadPoolExecutor(max_workers=max(1,min(workers,8))) as pool:
        event_sources = list(pool.map(source, relatives))
    sources.extend(record for _, record in event_sources)
    dev_context, targets, counts, exclusions, quality = [], {}, Counter(), Counter(), Counter()
    cohorts = defaultdict(Counter); seen = set()
    staging.mkdir(parents=True,exist_ok=True)
    with (staging/'contexts.jsonl').open('w') as rows, (staging/'development_targets.jsonl').open('w') as labels:
        for (season, match), (path, _) in zip(matches,event_sources):
            cohort = cohort_for(season,match['match_date']); cohorts[cohort]['games'] += 1
            for event in json.loads(path.read_text()):
                if event.get('type',{}).get('name') != 'Shot': continue
                counts['recorded_shots'] += 1; cohorts[cohort]['recorded_shots'] += 1
                reason = exclusion_reason(event)
                if reason:
                    exclusions[reason] += 1; cohorts[cohort]['excluded_'+reason] += 1; continue
                if not event.get('id') or event['id'] in seen: raise ValueError('Missing/duplicate shot UUID')
                seen.add(event['id'])
                context = extract_context(event)
                context.update(match_id=match['match_id'],season_id=season,match_date=match['match_date'],cohort=cohort)
                counts['eligible_nonpenalty_shots'] += 1; cohorts[cohort]['eligible_nonpenalty_shots'] += 1
                q = context['quality']
                for key in ['freeze_frame_present','invalid_recorded_player_locations','unknown_teammate_flags','unknown_opponent_role_count']:
                    quality[key] += q[key]
                quality['unique_opposition_keeper_recorded'] += q['recorded_opposition_keeper_count'] == 1
                quality['multiple_opposition_keepers'] += q['recorded_opposition_keeper_count'] > 1
                rows.write(json.dumps(context,allow_nan=False)+'\n')
                if cohort == 'development':
                    target = extract_target(event); targets[event['id']] = target; dev_context.append(context)
                    labels.write(json.dumps(target)+'\n')
    notice = 'Data: StatsBomb Open Data, modified through original local descriptive parsing. Custom noncommercial research agreement; attribution and supplied logo required for any permitted publication.'
    logo_path, logo = source('img/SB - Icon Lockup - Colour positive.png'); sources.append(logo)
    # Keep a verified original provider asset local. The adapter never invents or redraws branding.
    agreement = root/'data/research_source_docs/statsbomb_open-data/LICENSE.pdf'
    summary = {'schema_version':1,'sport':'soccer','task':'recorded_nonpenalty_shot_context','phase':'descriptive',
               'source_commit':COMMIT,'sources':sources,'parser_sha256':sha256_file(Path(__file__)),
             'parser_dependencies_sha256':{f'experiments/tactical/{Path(__file__).name}':sha256_file(Path(__file__)),
                                          'experiments/tactical/shot_sources.py':sha256_file(Path(__file__).with_name('shot_sources.py'))},
               'contract_sha256':sha256_file(root/'docs/research/TACTICAL_MEASUREMENT_CONTRACT.json'),
               'population':'FA Women\'s Super League; fixed seasons 2018/19, 2019/20, 2020/21 development; 2023/24 eligibility QA only',
               'units':{'coordinates':'standardized 120x80 native grid, not metres','distances':'native standardized grid units','angles':'radians'},
               'denominators':dict(counts),'exclusions':dict(exclusions),'quality':dict(quality),
               'cohorts':[{'cohort':key,**dict(value)} for key,value in sorted(cohorts.items())],
               'development_scope':{'season_ids':list(DEVELOPMENT_SEASONS),'games':325,'eligible_shots':len(dev_context),
                                    'unknown_targets':sum(t['goal'] is None for t in targets.values())},
               'development_distributions':summarize_development(dev_context,targets),
               'development_plot':development_plot(dev_context,targets),
               'measurement_caveats':[CAVEAT,'Offline event annotation does not establish a live at-contact data feed.',
                                       'Shot-conditioned descriptions do not establish causal coaching effects or value of unchosen actions.'],
               'publication':{'status':'local_only','attribution':notice,'logo_path':str(logo_path.relative_to(root)),
                              'logo_sha256':logo['sha256'],'agreement_sha256':sha256_file(agreement)},
               'predictive_gate':{'status':'closed','fitting_allowed':False},
               'predictive_status':'not_fitted; exact protocol review and parent approval required'}
    write_json(staging/'source_manifest.json',{'commit':COMMIT,'files':sources})
    write_json(root/'reports/tactical/soccer/summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--fetch',action='store_true'); parser.add_argument('--workers',type=int,default=6)
    args=parser.parse_args(); result=build(args.root,args.fetch,args.workers)
    print(json.dumps({'sport':result['sport'],'phase':result['phase'],'denominators':result['denominators'],'cohorts':result['cohorts']},indent=2))

if __name__ == '__main__': main()
