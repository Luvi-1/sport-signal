"""Licensed normalized snapshot adapter, distinct from original upstream bytes."""
from pathlib import Path
import gzip,hashlib,io,json
import pandas as pd
from sportslab.data import validate_events
ROOT=Path(__file__).resolve().parents[1]

def load_snapshot(end_season=2025,root=None):
    root=Path(root) if root is not None else ROOT
    if end_season not in (2024,2025):raise ValueError('Frozen NFL snapshot supports end seasons 2024 or 2025 only')
    metadata=json.loads((root/'snapshots/nfl_regular_2010_2025.json').read_text())
    payload=(root/'snapshots/nfl_regular_2010_2025.csv.gz').read_bytes()
    if hashlib.sha256(payload).hexdigest()!=metadata['sha256_gzip']:raise ValueError('Bundled NFL compressed hash mismatch')
    data=gzip.decompress(payload)
    if hashlib.sha256(data).hexdigest()!=metadata['sha256_uncompressed']:raise ValueError('Bundled NFL normalized hash mismatch')
    frame=validate_events(pd.read_csv(io.BytesIO(data),dtype={'event_id':str,'side_a':str,'side_b':str,'season':str},float_precision='round_trip'),'football')
    frame=frame.loc[frame.season.astype(int)<=end_season].reset_index(drop=True)
    if hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()!=metadata['processed_sha256_by_end_season'][str(end_season)]:
        raise ValueError('Bundled NFL transformation differs from recorded normalized result')
    frame.attrs['snapshot_provenance']=metadata
    return frame
