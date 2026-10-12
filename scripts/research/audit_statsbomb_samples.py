"""Source QA only; no predictive model fitting. See docs/research/RESEARCH_PUBLICATION_POLICY.md. Requires separately acquired pinned source files."""
import json,pathlib,collections,statistics,hashlib
b=pathlib.Path(str(pathlib.Path(__file__).resolve().parents[2]));root=b/'data/research/statsbomb_open-data';meta=json.load(open(b/'data/research_source_docs/statsbomb_sample_manifest.json'));mapmeta={r['match_id']:r for r in meta if '/events/' in r['url']};out=[]
for fp in sorted((root/'data/events').glob('*.json')):
 mid=int(fp.stem);es=json.load(open(fp));ss=[e for e in es if e['type']['name']=='Shot'];c=collections.Counter();ffsize=[];gk=[];f360={};f=root/f'data/three-sixty/{mid}.json'
 if f.exists():f360={r['event_uuid']:r for r in json.load(open(f))}
 for s in ss:
  c['shots']+=1;c['goals']+=s['shot']['outcome']['name']=='Goal';c['penalties']+=s['shot']['type']['name']=='Penalty';c['shootout_shots']+=s['period']==5;c['missing_location']+='location' not in s;c['missing_shot_freeze_frame']+=not bool(s['shot'].get('freeze_frame'));c['missing_provider_xg']+='statsbomb_xg' not in s['shot']
  ff=s['shot'].get('freeze_frame',[]);ffsize.append(len(ff));ngk=sum(not r['teammate'] and r['position']['id']==1 for r in ff);gk.append(ngk);c['missing_opposition_gk']+=ngk==0;c['multiple_opposition_gk']+=ngk>1
  sf=f360.get(s['id']);c['shots_with_360']+=sf is not None
  if sf:
   c['360_visible_area_empty']+=not bool(sf.get('visible_area'));c['360_actor_missing']+=not any(r['actor'] for r in sf['freeze_frame']);c['360_actor_multiple']+=sum(r['actor'] for r in sf['freeze_frame'])>1
 r={'match_id':mid,'date':mapmeta[mid]['match_date'],'competition':mapmeta[mid]['competition'],'season':mapmeta[mid]['season'],'event_count':len(es),'counts':dict(c),'shot_freeze_frame_size_min':min(ffsize) if ffsize else None,'shot_freeze_frame_size_median':statistics.median(ffsize) if ffsize else None,'shot_keys':sorted({k for s in ss for k in s['shot']})};out.append(r)
 print(r['competition'],r['season'],mid,r['date'],len(es),dict(c),'FFmedian',r['shot_freeze_frame_size_median'])
(b/'reports/research_statsbomb_sample_audit.json').write_text(json.dumps({'commit':'4b73468fc5b0f1950f9f66fada70ad3a4f9327cb','sampling':'First, midpoint, last chronological match in each selected competition-season; source QA only, not a random prevalence estimate or model evaluation.','matches':out},indent=2))
