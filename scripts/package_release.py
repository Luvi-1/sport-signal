"""Build an allowlisted source/report archive; include only the explicitly licensed normalized NFL input, never raw downloads or models."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES={"README.md","LICENSE","DATA_LICENSES.md","pyproject.toml","data_manifest.json",".gitignore", "snapshots/README.md", "snapshots/LICENSE.nflverse.md",
            "snapshots/nfl_regular_2010_2025.csv.gz", "snapshots/nfl_regular_2010_2025.json"}
TREE_SUFFIXES={"sportslab":{'.py'},"experiments":{'.py'},"scripts":{'.py','.sh'},"tests":{'.py'},
               "docs":{'.md'},"reports":{'.md','.json','.svg'},".github":{'.yml','.yaml'}}

def release_files():
    paths=[ROOT/name for name in ROOT_FILES]
    for directory,suffixes in TREE_SUFFIXES.items():
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts)
    return sorted(set(paths),key=lambda p:str(p.relative_to(ROOT)))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-pending',action='store_true',help='For a clearly labeled preliminary snapshot only')
    args=parser.parse_args()
    laya=ROOT/'reports'/'laya'/'evaluation.json'
    if (not laya.exists() or json.loads(laya.read_text()).get('status')!='completed') and not args.allow_pending:
        parser.error('Laya experiment is pending; final release must wait or explicitly be preliminary')
    if (ROOT/'experiments'/'v2').exists() and not args.allow_pending:
        for sport in ('soccer','baseball','football','tennis'):
            report=ROOT/'reports'/'v2'/sport/'evaluation.json'
            if not report.exists() or json.loads(report.read_text()).get('status')!='completed_single_new_holdout_evaluation':
                parser.error(f'V2 {sport} evaluation pending; final expanded release must wait')
        for path in ['reports/v2/RESULTS.md','reports/v2/source_manifest.json','reports/v2/selection_freeze.json']:
            if not (ROOT/path).is_file():parser.error(f'Final report missing: {path}')
    paths=release_files()
    records=[]
    for path in paths:
        if not path.is_file() or path.is_symlink():raise ValueError(f'Not a regular release file: {path}')
        content=path.read_bytes()
        if len(content)>2_000_000:raise ValueError(f'Unexpectedly large source/report file: {path}')
        records.append({'path':str(path.relative_to(ROOT)),'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    output=ROOT/'artifacts'/'release';output.mkdir(parents=True,exist_ok=True)
    manifest={'schema_version':1,'status':'preliminary' if args.allow_pending else 'final',
              'scope':'Original code, documentation, aggregate reports and source/selection hashes; no upstream raw datasets, per-match feature/prediction tables, weights, environments, credentials or caches; includes one CC-BY-4.0 licensed normalized NFL input snapshot',
              'file_count':len(records),'total_uncompressed_bytes':sum(r['bytes'] for r in records),'files':records}
    payload=json.dumps(manifest,indent=2).encode()+b'\n'
    (output/'publish-manifest.json').write_bytes(payload)
    destination=output/'sports-analytics-source.zip'
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in paths:
            info=zipfile.ZipInfo('sports-analytics/'+str(path.relative_to(ROOT)),date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o755 if path.suffix=='.sh' else 0o644)<<16
            archive.writestr(info,path.read_bytes())
        archive.writestr('sports-analytics/PUBLISH_MANIFEST.json',payload)
    print(json.dumps({'archive':str(destination),'files':len(records),'bytes':destination.stat().st_size,
                      'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'status':manifest['status']},indent=2))
if __name__=='__main__':main()
