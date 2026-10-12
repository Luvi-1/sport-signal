"""Source QA only; no predictive model fitting. See docs/research/RESEARCH_PUBLICATION_POLICY.md. Requires separately acquired pinned source files."""
import json,hashlib
from pathlib import Path
base=Path(__file__).resolve().parents[2];p=base/'data/research_source_docs';root=base/'data/research/statsbomb_open-data'
tree=json.load(open(p/'statsbomb_open-data_tree.json'));paths={r['path']:r for r in tree['tree']}
comps=json.load(open(p/'statsbomb_open-data/data/competitions.json'));rows=[];manifest=[]
for c in comps:
 fn=root/f"data/matches/{c['competition_id']}/{c['season_id']}.json"
 matches=json.load(open(fn)); b=fn.read_bytes();manifest.append({'url':f"https://raw.githubusercontent.com/statsbomb/open-data/{tree['sha']}/data/matches/{c['competition_id']}/{c['season_id']}.json",'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'path':str(fn)})
 n360=sum(f"data/three-sixty/{m['match_id']}.json" in paths for m in matches)
 r={'competition_id':c['competition_id'],'season_id':c['season_id'],'competition':c['competition_name'],'season':c['season_name'],'gender':c['competition_gender'],'matches':len(matches),'matches_360':n360,'first_date':min(m['match_date'] for m in matches),'last_date':max(m['match_date'] for m in matches),'events_bytes':sum(paths.get(f"data/events/{m['match_id']}.json",{}).get('size',0) for m in matches),'360_bytes':sum(paths.get(f"data/three-sixty/{m['match_id']}.json",{}).get('size',0) for m in matches),'metadata_versions':list({json.dumps(m.get('metadata',{}),sort_keys=True) for m in matches})}
 rows.append(r)
 print(c['competition_name'],c['season_name'],r['matches'],n360,r['first_date'],r['last_date'],round(r['events_bytes']/1e6,1),round(r['360_bytes']/1e6,1))
(p/'statsbomb_match_list_manifest.json').write_text(json.dumps(manifest,indent=2))
(base/'reports/research_statsbomb_coverage.json').write_text(json.dumps({'source_commit':tree['sha'],'competitions':rows},indent=2))
