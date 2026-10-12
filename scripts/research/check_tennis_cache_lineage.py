"""Reproduce cache representation and match QA only, with no numerical targets/features.

No target_record(), direction summary, predictor, fit, calibration or performance
function is called. Original caches stay read-only. Encoded source payloads are
compared exactly and discarded, never printed or exported in the aggregate report.
"""
from pathlib import Path
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.tactical import tennis


def digest_rows(connection):
    digest=hashlib.sha256();n=0
    for row in connection.execute('SELECT corpus,match_id,pt,payload,source_file,source_row FROM points ORDER BY corpus,match_id,pt'):
        digest.update((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode());n+=1
    return digest.hexdigest(),n


def run(root):
    started=time.monotonic();root=Path(root).resolve()
    provenance=tennis.validate_sources(root)
    directory=root/'artifacts/tactical/tennis/cache_lineage_check'
    directory.mkdir(parents=True,exist_ok=True)
    output=directory/'rebuilt_source_index.sqlite3'
    if output.exists():raise FileExistsError('Preserve previous source QA run; no silent overwrite')
    cache=root/'data/research/tennis/source-samples'
    source=root/'data/tactical/tennis/source_index.sqlite3'
    original=sqlite3.connect(f'file:{source}?mode=ro',uri=True)
    rebuilt=sqlite3.connect(output)
    rebuilt.execute('PRAGMA journal_mode=OFF');rebuilt.execute('PRAGMA temp_store=FILE');rebuilt.execute('PRAGMA cache_size=-16384')
    matches,invalid_meta,meta_stats=tennis.load_metadata(cache)
    source_stats,invalid_points=tennis.ingest_points(cache,rebuilt)
    before=tennis.digest(source)
    old_hash,old_n=digest_rows(original);new_hash,new_n=digest_rows(rebuilt)
    if (old_hash,old_n)!=(new_hash,new_n):raise ValueError('Raw-to-SQLite canonical source-row fidelity failed')
    expected_path=root/'data/tactical/tennis/match_quality.jsonl'
    rebuilt_quality=directory/'rebuilt_match_quality.jsonl'
    count=0
    with rebuilt_quality.open('x') as out:
        for corpus,match_id in rebuilt.execute('SELECT DISTINCT corpus,match_id FROM points ORDER BY corpus,match_id'):
            records=rebuilt.execute('SELECT payload FROM points WHERE corpus=? AND match_id=? ORDER BY pt',(corpus,match_id)).fetchall()
            rows=[dict(zip(tennis.POINT_COLUMNS,json.loads(record[0]))) for record in records]
            meta=matches.get((corpus,match_id))
            reasons=set(invalid_points.get((corpus,match_id),()))|set(invalid_meta.get((corpus,match_id),()))
            if meta is None:reasons.add('metadata_missing')
            if [int(row['Pt']) for row in rows]!=list(range(1,len(rows)+1)):
                reasons.add('point_ordinal_not_consecutive_from_one')
            checks=Counter();complete=False
            if not reasons:
                _,score_reasons,checks,complete=tennis.audit_match(meta,rows)
                reasons.update(score_reasons)
            out.write(json.dumps({'corpus':corpus,'match_id':match_id,'point_count':len(rows),
                'quarantined':bool(reasons),'reasons':sorted(reasons),'score_checks':dict(checks),
                'complete_match_by_score':complete},sort_keys=True)+'\n')
            count+=1
    if tennis.digest(rebuilt_quality)!=tennis.digest(expected_path):
        raise ValueError('Regenerated whole-match QA differs from the reviewed cache')
    original.close();rebuilt.close()
    if tennis.digest(source)!=before:raise ValueError('Original cache changed during read-only QA')
    summary_path=root/'reports/tactical/tennis/summary.json'
    summary=json.loads(summary_path.read_text())
    if summary['source_counts']!=source_stats or summary['metadata_counts']!=meta_stats:
        raise ValueError('Source/metadata representation counts disagree with summary')
    report={'schema_version':1,'status':'verified','completed_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Exact source-row cache regeneration and existing match score/rule QA; no direction-rate aggregation, model features, fitting or performance scores',
        'source_manifest_sha256':provenance['manifest_sha256'],'parser_code_sha256':provenance['parser_code_sha256'],
        'checker_sha256':tennis.digest(Path(__file__)),'raw_files_sha256':{f['file']:f['sha256'] for f in provenance['files']},
        'canonical_source_rows':old_n,'canonical_ordered_rows_sha256':old_hash,'match_quality_records':count,
        'source_counts_match':True,'metadata_counts_match':True,'original_cache_unchanged':True,
        'files_sha256':{str(p.relative_to(root)):tennis.digest(p) for p in (source,expected_path,summary_path,output,rebuilt_quality)},
        'wall_seconds':time.monotonic()-started}
    report_path=directory/'verification.json'
    with report_path.open('x') as out:json.dump(report,out,sort_keys=True,indent=2);out.write('\n')
    return {k:report[k] for k in ('status','canonical_source_rows','match_quality_records','wall_seconds')}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path('.'))
    args=parser.parse_args();print(json.dumps(run(args.root),sort_keys=True))
