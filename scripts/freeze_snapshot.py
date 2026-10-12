"""Maintainer utility: freeze only after reviewing provider changes and rerunning audits."""
import json
from pathlib import Path
import hashlib
def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
root=Path(__file__).resolve().parents[1]
records=[]
for metadata in sorted((root/"data"/"raw").glob("*/*.source.json")):
    data=json.loads(metadata.read_text())
    path=Path(str(metadata).removesuffix(".source.json"))
    if sha256(path)!=data["sha256"]:raise ValueError(f"Hash mismatch: {path}")
    records.append({"sport":path.parent.name,"path":str(path.relative_to(root)),"url":data["url"],"sha256":data["sha256"],"bytes":data["bytes"]})
(root/"data_manifest.json").write_text(json.dumps({"schema_version":1,"purpose":"Exact input byte snapshot; mutable upstream revisions must be reviewed","files":records},indent=2)+"\n")
print(f"Locked {len(records)} provider/evidence files")
