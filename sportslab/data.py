"""Auditable downloads and strict common schema validation."""
from __future__ import annotations
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

SPORTS = ("soccer", "baseball", "football", "tennis")
REQUIRED = ("event_id", "date", "season", "side_a", "side_b", "score_a", "score_b")

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fetch(url: str, path: Path) -> Path:
    """Cache bytes, verify cached provenance, and fail loudly on HTTP errors.

    No authentication, cookies, source execution, or archive extraction.
    GitHub datasets are pinned in their individual adapters; mutable providers
    additionally use the published snapshot lock for an exact reproduction.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = path.with_suffix(path.suffix + ".source.json")
    if path.exists():
        if not meta.exists():
            raise ValueError(f"Cached file lacks provenance: {path}; move it aside and retry")
        record = json.loads(meta.read_text())
        if record["url"] != url or record["sha256"] != sha256(path):
            raise ValueError(f"Cached file provenance mismatch: {path}")
        return path
    request = urllib.request.Request(url, headers={"User-Agent": "sportslab-research/0.1 (public historical data)"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read(40_000_001)
        if len(payload) > 40_000_000:
            raise ValueError(f"Unexpected download exceeds 40 MB: {url}")
    temp = path.with_suffix(path.suffix + ".partial")
    temp.write_bytes(payload)
    temp.replace(path)
    meta.write_text(json.dumps({"url": url, "sha256": sha256(path), "bytes": len(payload),
        "fetched_at_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    return path

def validate_events(frame: pd.DataFrame, sport: str) -> pd.DataFrame:
    if sport not in SPORTS:
        raise ValueError(f"Unknown sport: {sport}")
    missing = set(REQUIRED) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("No completed events")
    out = frame.copy()
    for col in ("date", "available_date"):
        if col not in out:
            out[col] = out["date"]
        out[col] = pd.to_datetime(out[col], errors="raise").dt.normalize()
        if out[col].isna().any():
            raise ValueError(f"Null {col}")
    if (out.available_date < out.date).any():
        raise ValueError("Results cannot be available before event date")
    for col in ("event_id", "side_a", "side_b", "season"):
        if out[col].isna().any() or out[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Missing identity: {col}")
        out[col] = out[col].astype(str)
    if out.event_id.duplicated().any():
        raise ValueError("Duplicate event IDs; source changes require review")
    if out.side_a.eq(out.side_b).any():
        raise ValueError("A participant cannot play itself")
    for col in ("score_a", "score_b"):
        out[col] = pd.to_numeric(out[col], errors="raise")
        if not np.isfinite(out[col]).all() or (out[col] < 0).any():
            raise ValueError(f"Invalid final score: {col}")
    if sport != "soccer" and out.score_a.eq(out.score_b).any():
        raise ValueError("Binary adapters must explicitly exclude ties")
    out["neutral"] = out.get("neutral", False)
    if not out.neutral.isin([True, False, 0, 1]).all():
        raise ValueError("neutral must be a boolean")
    out["neutral"] = out.neutral.astype(bool)
    out["surface"] = out.get("surface", "all")
    out["surface"] = out.surface.fillna("unknown").astype(str)
    return out.sort_values(["date", "event_id"], kind="stable").reset_index(drop=True)

def load_adapter(sport: str):
    import importlib
    if sport not in SPORTS:
        raise ValueError(sport)
    return importlib.import_module(f"sportslab.adapters.{sport}")

def prepare(sport: str, root: Path = Path("."), download: bool = True) -> pd.DataFrame:
    adapter = load_adapter(sport)
    raw = root / "data" / "raw" / sport
    if download:
        adapter.download(raw)
    frame = validate_events(adapter.load(raw), sport)
    path = root / "data" / "processed" / f"{sport}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame
