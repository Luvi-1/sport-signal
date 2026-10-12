"""Source QA only; no predictive model fitting. See docs/research/RESEARCH_PUBLICATION_POLICY.md. Requires separately acquired pinned source files."""
import json, pathlib, collections, math, gzip, statistics, hashlib
root=pathlib.Path(__file__).resolve().parents[2]/'data/research/SkillCorner_opendata-basketball/data'
report={'source_commit':'4bbed2e35e8fdd2cf083e8c8b280b3e5381a2c66','files':[],'tables':collections.Counter(),'shot_fields':{},'games':[]}
shots=[]
for fp in sorted((root/'matches').glob('*/*dynamic_events.json')):
 d=json.loads(fp.read_text());m=json.loads(fp.with_name(fp.name.replace('dynamic_events','game_data')).read_text());mid=int(fp.parent.name)
 report['tables'].update({k:len(v) for k,v in d.items()});ss=d['shots'];shots+=ss
 score=collections.Counter()
 for s in ss:
  if s['outcome']:score[s['offTeamId']]+=3 if s['three'] else 2
 for s in d['free_throws']:
  if s['outcome']:score[s.get('offTeamId',s.get('teamId'))]+=1
 report['games'].append({'id':mid,'metadata':m,'shots':len(ss),'fouled_makes':sum(s['fouled'] and s['outcome'] for s in ss),'fouled_misses':sum(s['fouled'] and not s['outcome'] for s in ss),'score_from_shots_and_free_throws':dict(score)})
for k in sorted({k for s in shots for k in s}):
 values=[s.get(k) for s in shots];nonnull=[v for v in values if v is not None]
 o={'missing':len(values)-len(nonnull),'types':dict(collections.Counter(type(v).__name__ for v in values))}
 if nonnull and all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in nonnull):o.update({'min':min(nonnull),'max':max(nonnull),'median':statistics.median(nonnull)})
 elif nonnull and isinstance(nonnull[0],(str,bool)):o['value_counts']=dict(collections.Counter(nonnull)) if len(set(nonnull))<30 else {'nunique':len(set(nonnull))}
 report['shot_fields'][k]=o
report['shot_count']=len(shots);report['unique_shot_ids']=len({s['id'] for s in shots});report['shot_makes']=sum(s['outcome'] for s in shots)
report['fouled_makes']=sum(s['fouled'] and s['outcome'] for s in shots);report['fouled_misses']=sum(s['fouled'] and not s['outcome'] for s in shots)
report['box_score_fga_if_exclude_fouled_misses']=len(shots)-report['fouled_misses'];report['shot_date_range']=['2025-10-11','2026-05-29']
# Only inspect release and t-1, t-5, t-25 frames, without storing or printing player records.
ss=[s for s in shots if s['gameId']==114243];needed={s['startFrame']-k for s in ss for k in [0,1,5,25]};frames={};count=0;empty=0;det=collections.Counter();maxidx=0;dims=collections.Counter()
fp=root/'matches/114243/114243_tracking_data.jsonl.gz'
with gzip.open(fp,'rt') as f:
 for line in f:
  row=json.loads(line);count+=1;maxidx=max(maxidx,row['frameIdx'])
  players=row['homePlayers']+row['awayPlayers'];dims[len(players)]+=1
  if not players:empty+=1
  for p in players:det[p['isDetected']]+=1
  if row['frameIdx'] in needed:frames[row['frameIdx']]=row
report['tracking_sample']={'game_id':114243,'frames':count,'empty_player_frames':empty,'players_per_frame':dict(dims),'detection_counts':dict(det),'max_frame':maxidx,'requested_frames':len(needed),'available_frames':len(frames)}
# Compare event shot loc against shooter at exact startFrame, nearest defender raw coordinates and sign flips.
errs=[];dist_errors=[];miss=[];rel=[]
for s in ss:
 r=frames.get(s['startFrame'])
 if r is None:miss.append(s['id']);continue
 hp={p['playerId']:p for p in r['homePlayers']};ap={p['playerId']:p for p in r['awayPlayers']};allp=hp|ap
 if s['shooterId'] not in allp or s['location'] is None:miss.append(s['id']);continue
 p=allp[s['shooterId']]; xy=p['xyz'][:2];loc=s['location'];signerrs={str(sign):math.dist([sign*x for x in xy],loc) for sign in [1,-1]};sign=min(signerrs,key=signerrs.get);err=signerrs[sign];errs.append(err)
 if s['closestDefId'] in allp and s['closestDefDist'] is not None:
  q=allp[s['closestDefId']];dd=math.dist(xy,q['xyz'][:2]);dist_errors.append(abs(dd-s['closestDefDist']))
 rel.append({'frame':s['startFrame'],'coordinate_rotation':int(sign),'location_error':err,'shooter_detected':p['isDetected'],'shooter_pred_error':p['predError']})
report['release_frame_audit']={'nshots':len(ss),'matched_shooter':len(errs),'unmatched':len(miss),'location_min_rotation_abs_error_median':statistics.median(errs),'location_max_error':max(errs),'defender_distance_n':len(dist_errors),'defender_distance_abs_error_median':statistics.median(dist_errors),'defender_distance_max_error':max(dist_errors),'rotation_counts':dict(collections.Counter(x['coordinate_rotation'] for x in rel)),'release_shooter_detected_counts':dict(collections.Counter(x['shooter_detected'] for x in rel))}
manifest=pathlib.Path(__file__).resolve().parents[2]/'data/research_source_docs/skillcorner_basketball_sample_manifest.json'
if manifest.exists():
 report['files']=[{**r, 'path':r['path'].split('/sports-analytics/')[-1]} for r in json.loads(manifest.read_text())]
path=pathlib.Path(__file__).resolve().parents[2]/'reports/research_skillcorner_basketball_audit.json';path.write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['files','games','shot_fields']},indent=2));print('SHOT_FIELDS',json.dumps(report['shot_fields'],indent=2))
