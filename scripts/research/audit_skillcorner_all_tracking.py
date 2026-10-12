"""Source QA only; no predictive model fitting. See docs/research/RESEARCH_PUBLICATION_POLICY.md. Requires separately acquired pinned source files."""
import json,pathlib,collections,gzip,math,statistics,time
base=pathlib.Path(str(pathlib.Path(__file__).resolve().parents[2]));root=base/'data/research/SkillCorner_opendata-basketball/data/matches';out=[];allerrors=[]
def quant(a):
 a=sorted(a)
 return {'n':len(a),'median':statistics.median(a),'p95':a[int(.95*(len(a)-1))],'max':max(a)} if a else None
for fp in sorted(root.glob('*/*tracking_data.jsonl.gz')):
 mid=int(fp.parent.name);ev=json.load(open(fp.with_name(f'{mid}_dynamic_events.json')));ss=ev['shots'];needed={s['startFrame']-k for s in ss for k in [0,1,5,25]};frames={};n=0;empty=0;det=collections.Counter();last=-1;gaps=0;dups=0
 with gzip.open(fp,'rt') as f:
  for line in f:
   r=json.loads(line);n+=1;pi=r['homePlayers']+r['awayPlayers'];empty+=not bool(pi)
   if last>=0:gaps+=max(0,r['frameIdx']-last-1);dups+=r['frameIdx']<=last
   last=r['frameIdx'];det.update(p['isDetected'] for p in pi)
   if r['frameIdx'] in needed:frames[r['frameIdx']]=r
 c=collections.Counter();locerrors=[];deferrors=[];nearesterrors=[];rot=collections.Counter();sid=[]
 for s in ss:
  c['shots']+=1;r=frames.get(s['startFrame']);c['has_release_frame']+=r is not None
  if r is None:continue
  hp={p['playerId']:p for p in r['homePlayers']};ap={p['playerId']:p for p in r['awayPlayers']};ps=hp|ap;c['release_has_10_players']+=len(ps)==10;c['release_ball_present']+=bool(r['ball'])
  p=ps.get(s['shooterId']);q=ps.get(s['closestDefId']);c['release_shooter_present']+=p is not None;c['release_named_defender_present']+=q is not None
  if p:c['release_shooter_detected']+=p['isDetected']==1
  if q:c['release_named_defender_detected']+=q['isDetected']==1
  if p and q:c['release_both_detected']+=p['isDetected']==1 and q['isDetected']==1
  c['has_location']+=s['location'] is not None
  if p and s['location'] is not None:
   a=p['xyz'][:2];se={sign:math.dist([sign*x for x in a],s['location']) for sign in [1,-1]};sign=min(se,key=se.get);le=se[sign];locerrors.append(le);rot[sign]+=1
   if q and s['closestDefDist'] is not None:
    de=abs(math.dist(a,q['xyz'][:2])-s['closestDefDist']);deferrors.append(de);opp=ap if s['shooterId'] in hp else hp;nearest=min(math.dist(a,op['xyz'][:2]) for op in opp.values());ne=abs(nearest-s['closestDefDist']);nearesterrors.append(ne);c['named_defender_is_nearest_within_0p01ft']+=math.dist(a,q['xyz'][:2])<=nearest+.01;c['reported_distance_matches_nearest_within_0p1ft']+=ne<=.1;c['both_geometry_consistent_within_0p1ft']+=le<=.1 and de<=.1;c['both_geometry_consistent_within_1ft']+=le<=1 and de<=1;c['both_geometry_consistent_and_detected_within_0p1ft']+=le<=.1 and de<=.1 and p['isDetected']==1 and q['isDetected']==1
    if le>.1 or de>.1:allerrors.append({'gameId':mid,'shotId':s['id'],'location_error_ft':le,'named_defender_distance_error_ft':de,'nearest_any_defender_distance_error_ft':ne,'shooter_detected':p['isDetected'],'defender_detected':q['isDetected'],'is_heave':s['shotType']=='heave'})
   if all(s['startFrame']-k in frames and s['shooterId'] in {v['playerId'] for v in frames[s['startFrame']-k]['homePlayers']+frames[s['startFrame']-k]['awayPlayers']} for k in [0,1,5,25]):c['shooter_present_all_four_past_frames']+=1
   if all(s['startFrame']-k in frames and any(v['playerId']==s['shooterId'] and v['isDetected']==1 for v in frames[s['startFrame']-k]['homePlayers']+frames[s['startFrame']-k]['awayPlayers']) for k in [0,1,5,25]):c['shooter_detected_all_four_past_frames']+=1
 r={'game_id':mid,'tracking_frames':n,'empty_player_frames':empty,'player_detection_counts':dict(det),'missing_frame_indices_inside_file':gaps,'nonincreasing_indices':dups,'counts':dict(c),'location_error_ft':quant(locerrors),'named_defender_distance_error_ft':quant(deferrors),'nearest_any_defender_distance_error_ft':quant(nearesterrors),'location_error_gt_0p1ft':sum(x>.1 for x in locerrors),'location_error_gt_1ft':sum(x>1 for x in locerrors),'defender_error_gt_0p1ft':sum(x>.1 for x in deferrors),'defender_error_gt_1ft':sum(x>1 for x in deferrors),'rotation_counts':dict(rot)};out.append(r);print(mid,c['shots'],dict(c),'locerr',r['location_error_ft'],'deferr',r['named_defender_distance_error_ft'],flush=True)
report={'commit':'4bbed2e35e8fdd2cf083e8c8b280b3e5381a2c66','sampling':'All 10 published games; release and release-1/-5/-25 frames. Post-release frames never inspected for feature derivation. Data QA includes outcome counts elsewhere, not model evaluation.','games':out,'totals':dict(sum((collections.Counter(g['counts']) for g in out),collections.Counter())),'error_rows':allerrors}
(base/'reports/research_skillcorner_all_tracking_audit.json').write_text(json.dumps(report,indent=2));print('TOTALS',report['totals'])
