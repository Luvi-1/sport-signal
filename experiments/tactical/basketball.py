"""Local descriptive SkillCorner ACB release-context parser; no predictive fits.

Raw compressed tracking is streamed once per game; only release frames are held.
python -m experiments.tactical.basketball
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import json
import hashlib
import math
from pathlib import Path
from statistics import median

from .shot_sources import manifest_file, sha256_file, write_json

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '4bbed2e35e8fdd2cf083e8c8b280b3e5381a2c66'
DEVELOPMENT_GAMES = (114243,114234,114169,114099,114086)
QA_GAMES = (178442,179612,184439,188630,191313)
HOOP = (-40.75,0.0)
PRIMARY_TOLERANCE_FT = 0.1
SENSITIVITY_TOLERANCE_FT = 1.0


def finite_number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def valid_xy(value):
    # A deliberately coarse, outcome-independent corruption guard, not court accuracy.
    return (isinstance(value,(list,tuple)) and len(value) == 2
            and all(finite_number(v) and abs(v) <= 100 for v in value))


def raw_xy(player):
    xyz = player.get('xyz') if isinstance(player,dict) else None
    return list(xyz[:2]) if isinstance(xyz,(list,tuple)) and len(xyz) == 3 and valid_xy(xyz[:2]) else None


def normalize_xy(xy, rotation):
    """180-degree rotation of BOTH axes from camera coordinates to offense left."""
    if rotation not in (-1,1) or isinstance(rotation,bool) or not valid_xy(xy):
        raise ValueError('Valid feet coordinates and explicit +/-1 rotation required')
    return [rotation * xy[0],rotation * xy[1]]


def court_geometry(location):
    if not valid_xy(location):
        raise ValueError('Missing, nonfinite or grossly out-of-support coordinates')
    dx,dy = location[0]-HOOP[0],location[1]-HOOP[1]
    distance=math.hypot(dx,dy)
    return {'x_ft':location[0],'y_ft':location[1],'distance_ft':distance,
            'absolute_hoop_bearing_rad':abs(math.atan2(dy,dx)) if distance else None}


def extract_context(shot: dict) -> dict:
    """Semantic allowlist; labels/post-release fields never enter this path."""
    location=shot.get('location'); distance=shot.get('closestDefDist'); clock=shot.get('shotClock')
    three=shot.get('three')
    quality={'location_valid':valid_xy(location),
             'nearest_defender_distance_valid':finite_number(distance) and distance >= 0,
             'three_flag_valid':isinstance(three,bool),
             'shot_clock_valid_or_missing':clock is None or (finite_number(clock) and 0 <= clock <= 24),
             'period_valid':isinstance(shot.get('period'),int) and not isinstance(shot.get('period'),bool) and shot['period'] >= 1,
             'release_frame_valid':isinstance(shot.get('startFrame'),int) and not isinstance(shot.get('startFrame'),bool) and shot['startFrame'] >= 0}
    features = court_geometry(location) if quality['location_valid'] else {
        'x_ft':None,'y_ft':None,'distance_ft':None,'absolute_hoop_bearing_rad':None}
    features.update(three=three if isinstance(three,bool) else None,
                    shot_clock_seconds=clock if quality['shot_clock_valid_or_missing'] else None,
                    nearest_defender_distance_ft=distance if quality['nearest_defender_distance_valid'] else None)
    supplied=shot.get('distance')
    quality['event_hoop_distance_error_ft']=(abs(features['distance_ft']-supplied)
        if features['distance_ft'] is not None and finite_number(supplied) else None)
    quality['outside_94x50_reference_rectangle']=bool(valid_xy(location) and (abs(location[0]) > 47 or abs(location[1]) > 25))
    # The reference rectangle is a diagnostic, not a FIBA accuracy/eligibility claim.
    return {'shot_id':shot.get('id'),'game_id':shot.get('gameId'),'period':shot.get('period'),
            'release_frame':shot.get('startFrame'),'release_wall_clock_ms':shot.get('startWallClock'),
            'release_game_clock_seconds':shot.get('startGameClock'),
            'shooter_id':shot.get('shooterId'),'offense_team_id':shot.get('offTeamId'),
            'defense_team_id':shot.get('defTeamId'),'named_defender_id':shot.get('closestDefId'),
            'features':features,'quality':quality,
            'event_geometry_eligible':all(quality[k] for k in ('location_valid','nearest_defender_distance_valid','three_flag_valid','period_valid','release_frame_valid'))}


def extract_target(shot: dict) -> dict:
    outcome=shot.get('outcome')
    return {'shot_id':shot.get('id'),'make':int(outcome) if isinstance(outcome,bool) else None,
            'fouled':shot.get('fouled') if isinstance(shot.get('fouled'),bool) else None}


def read_release_frames(path: Path, needed: set[int]) -> tuple[dict,dict]:
    """No decompressed multi-GB file, DataFrame, or all-frame list is produced."""
    frames={}; counts=Counter(); previous=None
    with gzip.open(path,'rt') as stream:
        for line in stream:
            frame=json.loads(line); index=frame.get('frameIdx')
            if not isinstance(index,int) or isinstance(index,bool):
                raise ValueError('Invalid frame index')
            counts['tracking_frames'] += 1
            if previous is not None:
                counts['missing_frame_indices'] += max(0,index-previous-1)
                counts['nonincreasing_indices'] += index <= previous
            previous=index
            players=frame.get('homePlayers',[])+frame.get('awayPlayers',[])
            counts['empty_player_frames'] += not players
            if index in needed:
                if index in frames: raise ValueError('Duplicate release frame')
                frames[index]=frame
    counts['requested_release_frames']=len(needed); counts['retained_release_frames']=len(frames)
    return frames,dict(counts)


def player_index(frame: dict | None) -> tuple[dict,dict,dict]:
    if frame is None:return {},{}, {'duplicate_player_ids':False}
    home=frame.get('homePlayers',[]);away=frame.get('awayPlayers',[])
    identifiers=[p.get('playerId') for p in home+away]
    return ({p['playerId']:p for p in home if p.get('playerId') is not None},
            {p['playerId']:p for p in away if p.get('playerId') is not None},
            {'duplicate_player_ids':len(identifiers)!=len(set(identifiers))})


def infer_rotations(contexts: list[dict], frames: dict) -> dict:
    """Outcome-free, retrospective per-team/period representation alignment.

    Later releases can inform this metadata inference; it is NOT a live feature.
    Only decisive <=1ft matched votes count; min 2, >=80% agreement. Abstain otherwise.
    """
    votes=defaultdict(Counter)
    for row in contexts:
        key=(row['game_id'],row['offense_team_id'],row['period']); votes[key]
        home,away,_=player_index(frames.get(row['release_frame']))
        xy=raw_xy((home|away).get(row['shooter_id'])); location=[row['features']['x_ft'],row['features']['y_ft']]
        if xy is None or not valid_xy(location):continue
        errors={sign:math.dist(normalize_xy(xy,sign),location) for sign in (-1,1)}
        best=min(errors,key=errors.get)
        if errors[best] <= 1 and errors[-best]-errors[best] > 1:
            votes[key][best] += 1
    result={}
    for key,count in votes.items():
        total=sum(count.values()); best=max(count,key=count.get) if count else None
        fraction=count[best]/total if total else None
        result[key]={'rotation':best if total >= 2 and fraction >= .8 else None,
                     'decisive_votes':total,'agreement_fraction':fraction,'inferred':True}
    return result


def release_quality(context: dict, frame: dict | None, metadata: dict, orientation: dict) -> dict:
    q={'release_frame_present':frame is not None,'rotation':orientation.get('rotation'),
       'rotation_inferred_retrospectively':True,'raw_consistent_0p1ft':False,
       'raw_consistent_1ft':False,'raw_consistent_and_directly_detected_0p1ft':False}
    if frame is None:return q
    home,away,index_q=player_index(frame);q.update(index_q)
    all_players=home|away;shooter=all_players.get(context['shooter_id']);defender=all_players.get(context['named_defender_id'])
    htid=metadata['homeTeam']['teamId'];atid=metadata['awayTeam']['teamId']
    offense=home if context['offense_team_id']==htid else away if context['offense_team_id']==atid else {}
    opponents=away if context['defense_team_id']==atid else home if context['defense_team_id']==htid else {}
    q.update(release_has_10_unique_players=len(all_players)==10 and not index_q['duplicate_player_ids'],
             release_has_five_players_per_team=len(home)==5 and len(away)==5,
             release_period_matches=frame.get('period')==context['period'],
             release_wall_clock_matches=frame.get('wallClock')==context['release_wall_clock_ms'],
             release_shooter_present=shooter is not None,release_named_defender_present=defender is not None,
             shooter_on_offense=context['shooter_id'] in offense,
             named_defender_on_defense=context['named_defender_id'] in opponents,
             shooter_directly_detected=bool(shooter and shooter.get('isDetected')==1),
             named_defender_directly_detected=bool(defender and defender.get('isDetected')==1),
             shooter_provider_error_ft=shooter.get('predError') if shooter and finite_number(shooter.get('predError')) else None,
             defender_provider_error_ft=defender.get('predError') if defender and finite_number(defender.get('predError')) else None,
             physical_accuracy_established=False)
    a,b=raw_xy(shooter),raw_xy(defender);rotation=orientation.get('rotation');f=context['features']
    loc=[f['x_ft'],f['y_ft']];location_error=None;named_error=None;nearest_error=None
    if a is not None and rotation is not None and valid_xy(loc):
        location_error=math.dist(normalize_xy(a,rotation),loc)
    if a is not None and b is not None and f['nearest_defender_distance_ft'] is not None:
        named_error=abs(math.dist(a,b)-f['nearest_defender_distance_ft'])
    coords=[raw_xy(p) for p in opponents.values()];coords=[p for p in coords if p is not None]
    if a is not None and coords and f['nearest_defender_distance_ft'] is not None:
        nearest=min(math.dist(a,p) for p in coords);nearest_error=abs(nearest-f['nearest_defender_distance_ft'])
        q['nearest_recorded_raw_opponent_ft']=nearest
        q['named_defender_is_nearest_within_0p01ft']=bool(b is not None and math.dist(a,b) <= nearest+.01)
    q.update(location_error_ft=location_error,named_defender_distance_error_ft=named_error,
             nearest_recorded_opponent_distance_error_ft=nearest_error)
    structural=(context['event_geometry_eligible'] and not q['duplicate_player_ids']
                and q['release_period_matches'] and q['release_wall_clock_matches']
                and q['shooter_on_offense'] and q['named_defender_on_defense']
                and context['offense_team_id'] != context['defense_team_id'])
    for tolerance,key in [(.1,'raw_consistent_0p1ft'),(1,'raw_consistent_1ft')]:
        q[key]=bool(structural and location_error is not None and named_error is not None
                    and location_error <= tolerance and named_error <= tolerance)
    q['raw_consistent_and_directly_detected_0p1ft']=bool(q['raw_consistent_0p1ft'] and q['shooter_directly_detected'] and q['named_defender_directly_detected'])
    return q


def summarize_development(contexts: list[dict], targets: dict) -> dict:
    groups=defaultdict(lambda:[0,0,0])
    for row in contexts:
        if row.get('cohort')!='development' or row['game_id'] not in DEVELOPMENT_GAMES:
            raise ValueError('Later game outcomes/context patterns are locked')
        if not row['event_geometry_eligible']:continue
        f=row['features'];d=f['distance_ft'];defender=f['nearest_defender_distance_ft']
        distance_bin=next((label for edge,label in [(6,'[0,6)'),(14,'[6,14)'),(22,'[14,22)')] if d < edge),'[22,infinity)')
        defender_bin=next((label for edge,label in [(2,'[0,2)'),(4,'[2,4)'),(6,'[4,6)')] if defender < edge),'[6,infinity)')
        target=targets.get(row['shot_id'],{}).get('make')
        angle=f['absolute_hoop_bearing_rad']
        bearing_bin='missing' if angle is None else next((label for edge,label in [(math.pi/6,'[0,pi/6)'),(math.pi/3,'[pi/6,pi/3)'),(math.pi/2,'[pi/3,pi/2)')] if angle < edge),'[pi/2,pi]')
        for kind,label in [('distance_ft',distance_bin),('absolute_hoop_bearing_rad',bearing_bin),('nearest_defender_distance_ft',defender_bin),('three',str(f['three']))]:
            group=groups[kind,label];group[0]+=1;group[1]+=target is not None;group[2]+=target==1
    return {kind:[{'category':label,'releases':n,'target_available':available,'observed_makes':makes}
                  for (k,label),(n,available,makes) in sorted(groups.items()) if k==kind]
            for kind in sorted({key[0] for key in groups})}


def development_plot(contexts: list[dict], targets: dict, limit: int=200) -> dict:
    if any(r.get('cohort') != 'development' or r['game_id'] not in DEVELOPMENT_GAMES for r in contexts):
        raise ValueError('Only first-five-game development shots can enter the local plot')
    eligible=[r for r in contexts if r['quality']['location_valid']]
    selected=sorted(eligible,key=lambda r:hashlib.sha256(r['shot_id'].encode()).hexdigest())[:max(0,min(limit,200))]
    return {'sample_method':'First 200 SHA256(shot ID) order among location-valid development releases; no outcome selection',
            'population_releases':len(contexts),'location_valid_releases':len(eligible),
            'sample_releases':len(selected),'coordinate_units':'feet','offense_normalized_hoop':list(HOOP),
            'points':[{'x':r['features']['x_ft'],'y':r['features']['y_ft'],
                       'observed_make':targets.get(r['shot_id'],{}).get('make'),
                       'three':r['features']['three'],
                       'nearest_defender_distance_ft':r['features']['nearest_defender_distance_ft'],
                       'geometry_eligible':r['event_geometry_eligible'],
                       'raw_consistent_0p1ft':r.get('raw_quality',{}).get('raw_consistent_0p1ft',False),
                       'shooter_directly_detected':r.get('raw_quality',{}).get('shooter_directly_detected',False)} for r in selected]}


def build(root: Path=ROOT) -> dict:
    root=root.resolve();source=root/'data/research/SkillCorner_opendata-basketball/data/matches'
    staging=root/'data/tactical/basketball';staging.mkdir(parents=True,exist_ok=True)
    manifests=[]
    for name in ['skillcorner_basketball_sample_manifest.json','skillcorner_all_tracking_manifest.json']:
        manifests.extend(json.loads((root/'data/research_source_docs'/name).read_text()))
    # The sample manifest may repeat the first game's tracking file. Deduplicate identical records only.
    unique={}
    for record in manifests:
        key=Path(record['path']).name
        if key in unique and unique[key]['sha256']!=record['sha256']:raise ValueError('Conflicting source manifests')
        unique[key]=record
    manifests=list(unique.values())
    sources=[];counts=Counter();quality=Counter();games=[];dev=[];targets={};seen=set();orientations=[]
    with (staging/'contexts.jsonl').open('w') as rows,(staging/'development_targets.jsonl').open('w') as labels:
        for game in (*DEVELOPMENT_GAMES,*QA_GAMES):
            folder=source/str(game);paths=[folder/f'{game}_{suffix}' for suffix in ['dynamic_events.json','game_data.json','tracking_data.jsonl.gz']]
            sources.extend(manifest_file(path,root,manifests,COMMIT) for path in paths)
            shots=json.loads(paths[0].read_text())['shots'];metadata=json.loads(paths[1].read_text())
            if metadata['gameId']!=game:raise ValueError('Game metadata identity mismatch')
            contexts=[extract_context(s) for s in shots]
            if any(r['game_id']!=game for r in contexts):raise ValueError('Event game identity mismatch')
            needed={r['release_frame'] for r in contexts if r['quality']['release_frame_valid']}
            frames,tracking_qa=read_release_frames(paths[2],needed);rotations=infer_rotations(contexts,frames)
            orientations.extend({'game_id':key[0],'team_id':key[1],'period':key[2],**value} for key,value in sorted(rotations.items()))
            gc=Counter();cohort='development' if game in DEVELOPMENT_GAMES else 'forward_qa_only'
            for shot,context in zip(shots,contexts):
                if not context['shot_id'] or context['shot_id'] in seen:raise ValueError('Missing/duplicate shot id')
                seen.add(context['shot_id']);context['cohort']=cohort
                key=(game,context['offense_team_id'],context['period'])
                raw_q=release_quality(context,frames.get(context['release_frame']),metadata,rotations[key])
                context['raw_quality']=raw_q
                gc['recorded_releases']+=1;gc['event_geometry_eligible']+=context['event_geometry_eligible']
                for qkey in ('raw_consistent_0p1ft','raw_consistent_1ft','raw_consistent_and_directly_detected_0p1ft'):
                    gc[qkey]+=raw_q[qkey]
                for qkey,value in {**context['quality'],**raw_q}.items():
                    if isinstance(value,bool):quality[qkey]+=value
                rows.write(json.dumps(context,allow_nan=False)+'\n')
                if cohort=='development':
                    target=extract_target(shot);targets[context['shot_id']]=target;dev.append(context)
                    labels.write(json.dumps(target)+'\n')
            counts.update(gc);games.append({'game_id':game,'cohort':cohort,**dict(gc),'tracking':tracking_qa})
            print(f'Parsed game {game}: {dict(gc)}',flush=True)
    notice=root/'docs/research/notices/SKILLCORNER_BASKETBALL_MIT.txt'
    (staging/'SKILLCORNER_BASKETBALL_MIT.txt').write_bytes(notice.read_bytes())
    summary={'schema_version':1,'sport':'basketball','task':'recorded_field_goal_release_context','phase':'descriptive',
             'source_commit':COMMIT,'sources':sources,'parser_sha256':sha256_file(Path(__file__)),
             'parser_dependencies_sha256':{f'experiments/tactical/{Path(__file__).name}':sha256_file(Path(__file__)),
                                          'experiments/tactical/shot_sources.py':sha256_file(Path(__file__).with_name('shot_sources.py'))},
             'contract_sha256':sha256_file(root/'docs/research/TACTICAL_MEASUREMENT_CONTRACT.json'),
             'population':'Ten sampled Liga ACB 2025/26 games; all recorded field-goal releases, including fouled misses',
             'units':{'coordinates_and_distances':'feet','angles':'radians','wall_clock':'milliseconds since video origin',
                      'game_and_shot_clocks':'seconds remaining','tracking_rate_hz':25},
             'denominators':dict(counts),
             'exclusions':{'excluded_from_event_geometry':counts['recorded_releases']-counts['event_geometry_eligible'],
                           'fouled_misses_excluded_from_release_population':0},
             'quality':dict(quality),'cohorts':games,
             'development_scope':{'game_ids':list(DEVELOPMENT_GAMES),'releases':len(dev),
                                  'fouled_misses_retained':sum(t['fouled'] is True and t['make']==0 for t in targets.values()),
                                  'unknown_targets':sum(t['make'] is None for t in targets.values())},
             'development_distributions':summarize_development(dev,targets),
             'development_plot':development_plot(dev,targets),
             'source_qa':{'orientation_method':'Outcome-free majority of decisive per-team/period 180-degree rotation matches; inferred retrospectively, not live available',
                          'orientation_cells':len(orientations),'ambiguous_orientation_cells':sum(r['rotation'] is None for r in orientations),
                          'primary_representation_tolerance_ft':PRIMARY_TOLERANCE_FT,
                          'sensitivity_representation_tolerance_ft':SENSITIVITY_TOLERANCE_FT},
             'measurement_caveats':['Event/raw agreement measures representation consistency, not independent physical accuracy.',
                  'Direct detections and extrapolations are distinguished; provider error radii are not calibrated by these checks.',
                  'Recorded releases include fouled misses; immediate field-goal scoring omits free throws, rebounds and continuation.',
                  'Ten games do not establish general NBA transfer, defender skill or optimal shot selection.',
                  'Release-only positions are not joint mechanics or validated movement windows.'],
             'publication':{'status':'local_only_pending_specific_release_review','attribution':'Data: SkillCorner; original local descriptive parsing modified from source',
                            'license':'MIT','notice_sha256':sha256_file(notice)},
             'predictive_gate':{'status':'closed','fitting_allowed':False},
               'predictive_status':'not_fitted; exact protocol review and parent approval required'}
    write_json(staging/'source_manifest.json',{'commit':COMMIT,'files':sources});write_json(staging/'orientation_qa.json',orientations)
    write_json(root/'reports/tactical/basketball/summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args();result=build(args.root)
    print(json.dumps({'sport':result['sport'],'phase':result['phase'],'denominators':result['denominators'],'source_qa':result['source_qa']},indent=2))

if __name__=='__main__':main()
