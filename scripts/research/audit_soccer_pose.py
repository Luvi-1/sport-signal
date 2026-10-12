"""Source QA only; no predictive model fitting. See docs/research/RESEARCH_PUBLICATION_POLICY.md. Requires separately acquired pinned source files."""
import zipfile,json,csv,pathlib,collections,math,statistics
base=pathlib.Path(str(pathlib.Path(__file__).resolve().parents[2])); docs=base/'data/research_source_docs/SkillCorner_opendata';rows=list(csv.DictReader(open(docs/'data/matches/1925299/1925299_dynamic_events.csv'))); shots=[r for r in rows if r['event_type']=='player_possession' and r['end_type']=='shot']; needed={int(math.floor(2.5*int(r['frame_end']))) for r in shots}; saved={};cnt=collections.Counter();errors=[];frames=[];last=None
with zipfile.ZipFile(base/'data/research/skillcorner_bodypose/1925299.jsonl.zip') as z:
 print('ZIP',z.namelist(),flush=True)
 with z.open('1925299.jsonl') as f:
  for l in f:
   r=json.loads(l);cnt['frames']+=1;cnt['frames_with_pose']+=any(p['joints'] for p in r['player_data']);cnt['player_records']+=len(r['player_data']);cnt['players_with_pose']+=sum(bool(p['joints']) for p in r['player_data']);cnt['detected_records']+=sum(p['is_detected'] for p in r['player_data']);cnt['period_'+str(r['period'])]+=1
   if r['frame'] in needed:saved[r['frame']]=r
   if cnt['frames']==1:frames.append({'frame':r['frame'],'timestamp':r['timestamp']})
   last={'frame':r['frame'],'timestamp':r['timestamp']}
   for p in r['player_data']:
    if p['joints']:
     cnt['joint_observations']+=len(p['joints']);cnt['pose_but_not_detected']+=not p['is_detected'];cnt['joint_count_'+str(len(p['joints']))]+=1
   if cnt['frames']%30000==0:print(cnt['frames'],flush=True)
shotrows=[]
for s in shots:
 fid=int(math.floor(2.5*int(s['frame_end'])));r=saved.get(fid);p=next((p for p in r['player_data'] if p['player_id']==int(s['player_id'])),None) if r else None
 shotrows.append({'event_id':s['event_id'],'player_id':int(s['player_id']),'tracking_frame_end':int(s['frame_end']),'pose_frame_not_later':fid,'frame_present':bool(r),'player_present':bool(p),'player_detected':p['is_detected'] if p else None,'has_pose':bool(p and p['joints']),'time_end':s['time_end']})
report={'source_hf_revision':'a62e1ec1e3b82952042a7f7fa9dafd77c0e0822a','source_sha256':'0415665098d594fb5681815000f7a6312037788a3237910a9f41bb8de5c336a0','match_id':1925299,'counts':dict(cnt),'first_last_frames':frames+[last],'candidate_shot_end_windows':shotrows,'caveat':'Dynamic event player-possession end_type=shot is an action annotation; alignment to true ball contact has not been independently verified. Presence counts are not proof of pre-contact prediction availability. Roster-level player records include off-camera and possibly inactive players; denominator is not 22 active players.'}
(base/'reports/research_skillcorner_soccer_pose_audit.json').write_text(json.dumps(report,indent=2));print('TOTAL',dict(cnt),'SHOT WINDOWS',len(shots),sum(s['has_pose'] for s in shotrows),flush=True)
