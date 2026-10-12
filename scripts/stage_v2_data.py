#!/usr/bin/env python3
"""Stage v2 sources without deriving features, predictions, or target rates.

Only schema, identity, dates, source coverage, exclusions, and provenance are
audited. v1 adapters/files are read-only. ``sealed`` is a workflow boundary,
not encryption; do not load its outcomes for development/model selection.
"""
from __future__ import annotations

import argparse
import csv
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from zipfile import ZipFile

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sportslab.adapters import baseball, football, soccer, tennis
from sportslab.data import fetch, sha256, validate_events

SPORTS = ("baseball", "football", "soccer", "tennis")
HOLDOUT = {"baseball": "2025", "football": "2025", "soccer": "2025-26", "tennis": "2025"}
BOUNDARIES = {"baseball": ("2025-01-01", "2026-01-01"),
              "football": ("2025-03-01", "2026-03-01"),
              "soccer": ("2025-07-01", "2026-07-01"),
              "tennis": ("2025-01-01", "2026-01-01")}
MODULES = dict(zip(SPORTS, (baseball, football, soccer, tennis)))
RIGHTS = {
    "baseball": {"license": "Retrosheet copyright / required attribution", "url": "https://www.retrosheet.org/notice.txt"},
    "football": {"license": "CC-BY-4.0", "url": "https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md"},
    "soccer": {"license": "CC0-1.0", "url": f"https://github.com/openfootball/football.json/blob/{soccer.SOURCE_COMMIT}/LICENSE.md"},
    "tennis": {"license": "CC-BY-NC-SA-4.0", "url": f"https://github.com/Kadantte/tennis_atp/blob/{tennis.SOURCE_COMMIT}/README.md"},
}
EVIDENCE_URLS = {
    "2025-26-source-schema-audit.txt": f"{soccer.TEXT_SOURCE_BASE}/2025-26/1-premierleague.txt",
    "LICENSE.retrosheet.txt": "https://www.retrosheet.org/notice.txt",
    "LICENSE.nflverse.md": "https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md",
    "teams.retrosheet.zip": "https://www.retrosheet.org/teams.zip",
}
# Frozen on the structural audit date. A changed remote object must stop staging,
# even if it has a fresh internally-consistent provenance sidecar.
V2_ADDITIONS_SHA256 = {
    "gl2025.zip": "f8a36120bc5f6925ffc914f964167f745e61a3421be9318e2ee24a576392693a",
    "en.1-2025-26.json": "d6070bdf731546ccf97767f062e8af4bd26dd309dee69f6092025bf9c78f43c1",
    "atp_matches_2025.csv": "78c356ef9328b89ae58a17564d61c02cdad2a3a007f6b8af5cfc17992b11bb2d",
    "2025-26-source-schema-audit.txt": "38c1de56c9e9b6662c7efc1420b7e1fe00dddbb502fe72d8f759e773ba3c093b",
    "LICENSE.retrosheet.txt": "2218abe680e21d3308de06352c394baefbffc7618d36a821d38ed6e97c24105d",
    "LICENSE.nflverse.md": "2a82ac9bbc3e3ee066908381e8d373896db5a6025d083fbd59692fe9ccfb9111",
    "teams.retrosheet.zip": "8b71744e56df36cf3de00ceeab1808bed8ab0ec0f29a30c0f70b95d0f971b2b8",
}
SCHEDULE_REFERENCES = {
    "baseball": "https://www.mlb.com/press-release/press-release-mlb-announces-2025-regular-season-schedule",
    "football": "https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule",
    "soccer": "https://www.premierleague.com/en/news/4324273",
    "tennis": "https://www.atptour.com/en/news/what-is-the-2025-atp-tour-calendar",
}
NFL_NORMALIZED_SHA256 = {
    "all": "b0d565c308f62f0fc7bd6239b15784c2e34204f5c1ed4a58a5b063d5a643c206",
    "history": "c8d3e1ffb6bf0aae2ba576d0b22636ed988c9ef002f2840c497bc2566ecc9ab5",
    "pre_holdout_development": "c8d3e1ffb6bf0aae2ba576d0b22636ed988c9ef002f2840c497bc2566ecc9ab5",
    "sealed_holdout": "59030c6f5d178e1e853771a8379b6ee8eacc6659d3a9ee55cb72c41b842103a7",
}


@contextmanager
def override(module, **values):
    """Process-local configuration; restore even when parsing raises."""
    previous = {key: getattr(module, key) for key in values}
    try:
        for key, value in values.items():
            setattr(module, key, value)
        yield
    finally:
        for key, value in previous.items():
            setattr(module, key, value)


def file_record(path: Path, root: Path) -> dict:
    return {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256(path)}


def protected_v1(root: Path) -> dict[str, str]:
    files = []
    for name in ("data/raw", "data/processed", "sportslab/adapters"):
        files.extend(p for p in (root / name).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for sport in SPORTS:
        files.extend(p for p in (root / "reports" / sport).rglob("*") if p.is_file())
        # Laya experiments write separate artifacts concurrently; protect the
        # original v1 feature, model and prediction products by exact names.
        files.extend(root / "artifacts" / sport / name for name in
                     ("features.csv", "model.joblib", "holdout_predictions.csv")
                     if (root / "artifacts" / sport / name).is_file())
    for name in ("data_manifest.json", "reports/RESULTS.md"):
        if (root / name).exists():
            files.append(root / name)
    return {str(p.relative_to(root)): sha256(p) for p in sorted(files)}


def copy_verified_v1(root: Path, output: Path, frozen_nfl: bool = True) -> None:
    """Copy cached bytes and sidecars, never refresh a historical source."""
    lock = json.loads((root / "data_manifest.json").read_text())
    for record in lock["files"]:
        if frozen_nfl and record["sport"] == "football":
            continue  # Normalized snapshot provenance is verified separately.
        path = root / record["path"]
        if sha256(path) != record["sha256"] or path.stat().st_size != record["bytes"]:
            raise ValueError(f"Source differs from immutable v1 data manifest: {path.name}")
    for sport in SPORTS:
        if frozen_nfl and sport == "football":
            continue
        source = root / "data/raw" / sport
        target = output / "raw" / sport
        target.mkdir(parents=True, exist_ok=True)
        for path in sorted(source.iterdir()):
            if not path.is_file() or path.name.endswith(".source.json"):
                continue
            sidecar = path.with_suffix(path.suffix + ".source.json")
            metadata = json.loads(sidecar.read_text())
            if metadata["sha256"] != sha256(path) or metadata["bytes"] != path.stat().st_size:
                raise ValueError(f"Unverified v1 source: {path.name}")
            for item in (path, sidecar):
                dest = target / item.name
                if dest.exists() and sha256(dest) != sha256(item):
                    raise ValueError(f"Refusing to replace changed staging bytes: {dest.name}")
                if not dest.exists():
                    shutil.copy2(item, dest)


def get_file(url: str, path: Path, offline: bool) -> Path:
    if offline and not path.is_file():
        raise FileNotFoundError(f"Offline source missing: {path.name}")
    path = fetch(url, path)
    if sha256(path) != V2_ADDITIONS_SHA256[path.name]:
        raise ValueError(f"Source differs from frozen v2 structural-audit snapshot: {path.name}")
    return path


_OLD_SOCCER_SCORE = soccer._full_time_score


def v2_soccer_score(match: dict):
    """Normalize the audited two-integer bare full-time arrays, no inference."""
    score = match.get("score")
    if isinstance(score, list):
        return _OLD_SOCCER_SCORE({"score": {"ft": score}})
    return _OLD_SOCCER_SCORE(match)


def soccer_text_audit(raw: Path, evidence: Path) -> dict:
    """Verify representation/date equivalence without returning actual scores."""
    match_pattern = re.compile(r"^\s*(?:\d{1,2}:\d{2}\s+)?(.+?)\s+(\d+)-(\d+)\s+\((\d+)-(\d+)\)\s+(.+?)\s*$")
    date_pattern = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ")
    aliases = {"Bournemouth": "AFC Bournemouth", "Sunderland": "Sunderland AFC"}

    def team(value):
        value = soccer._team_name(value)
        return aliases.get(value, value)

    year, current_date, weekday_errors = 2025, None, 0
    text_rows = {}
    for line in evidence.read_text().splitlines():
        if date_pattern.match(line):
            if re.search(r"20\d\d", line):
                year = int(line.split()[-1])
                full_date = line
            else:
                full_date = f"{line} {year}"
            current_date = datetime.strptime(full_date, "%a %b %d %Y").date()
            weekday_errors += int(current_date.strftime("%a") != line[:3])
        match = match_pattern.match(line)
        if match:
            a, sa, sb, _ha, _hb, b = match.groups()
            key = team(a), team(b)
            if key in text_rows or current_date is None:
                raise ValueError("Duplicate or undated original TXT fixture")
            text_rows[key] = (str(current_date), (float(sa), float(sb)))
    matches = json.loads(raw.read_text())["matches"]
    missing = date_errors = score_errors = arrays = 0
    for match in matches:
        key = soccer._team_name(match["team1"]), soccer._team_name(match["team2"])
        reference = text_rows.get(key)
        if reference is None:
            missing += 1
            continue
        date_errors += int(match["date"] != reference[0])
        score_errors += int(v2_soccer_score(match) != reference[1])
        arrays += int(isinstance(match.get("score"), list))
    result = {"json_fixtures": len(matches), "text_fixtures": len(text_rows),
              "missing_text_pairs": missing, "date_mismatches": date_errors,
              "full_time_schema_equivalence_mismatches": score_errors,
              "text_weekday_errors": weekday_errors, "bare_full_time_arrays_normalized": arrays}
    if len(matches) != 380 or len(text_rows) != 380 or missing or date_errors or score_errors or weekday_errors:
        raise ValueError(f"EPL source representation audit failed: {result}")
    return result


def baseball_identity_audit(evidence: Path) -> dict:
    with ZipFile(evidence) as archive:
        if archive.namelist() != ["teams.csv"] or archive.getinfo("teams.csv").file_size > 1_000_000:
            raise ValueError("Unexpected Retrosheet team-ID archive structure")
        rows = list(csv.reader(archive.read("teams.csv").decode("utf-8-sig").splitlines()))
    indexed = {row[0]: row for row in rows}
    if indexed.get("OAK") != ["OAK", "AL", "Oakland", "Athletics", "1968", "2024"]:
        raise ValueError("Retrosheet Oakland franchise identity evidence changed")
    if indexed.get("ATH") != ["ATH", "AL", "Sacramento", "Athletics", "2025", "2025"]:
        raise ValueError("Retrosheet Athletics franchise identity evidence changed")
    return {"participant_alias": {"ATH": "OAK"}, "event_ids_preserved": True,
            "source": "https://www.retrosheet.org/teams.zip",
            "pre_event_continuity_reference": "https://www.mlb.com/press-release/press-release-sutter-health-park-in-west-sacramento-to-host-a-s-for-2025-2027-seasons"}


def load_full(sport: str, raw: Path) -> tuple[pd.DataFrame, dict]:
    module = MODULES[sport]
    changes = {"baseball": {"YEARS": tuple(range(2015, 2026))},
               "football": {"END_SEASON": 2025},
               "soccer": {"SEASONS": tuple(f"{y}-{str(y + 1)[2:]}" for y in range(2015, 2026)),
                          "_full_time_score": v2_soccer_score},
               "tennis": {"YEARS": tuple(range(2010, 2026))}}[sport]
    with override(module, **changes):
        frame = module.load(raw)
    attributes = dict(frame.attrs)
    if sport == "baseball":
        # Official team-ID table: OAK/Oakland/Athletics ends in 2024;
        # ATH/Sacramento/Athletics starts in 2025. Preserve franchise history,
        # but never rewrite original Retrosheet event IDs or any v1 records.
        changed = frame.side_a.eq("ATH") | frame.side_b.eq("ATH")
        if (changed & frame.season.ne("2025")).any():
            raise ValueError("ATH franchise alias unexpectedly affects old history")
        frame["side_a"] = frame.side_a.replace({"ATH": "OAK"})
        frame["side_b"] = frame.side_b.replace({"ATH": "OAK"})
        attributes["v2_participant_aliases"] = {"ATH": "OAK"}
        attributes["v2_alias_affected_rows"] = int(changed.sum())
    return validate_events(frame, sport), attributes


def load_frozen_nfl(root: Path) -> tuple[pd.DataFrame, dict, dict, dict]:
    """Read a licensed normalized artifact without claiming it is raw data.

    Excluded rows cannot be re-audited from this filtered artifact. Preserve
    the original structural audit as lineage, and separately audit retained
    identities/dates. Exact CSV hashes enforce equivalence to original staging.
    """
    from experiments.frozen_nfl import load_snapshot

    snapshot = root / "snapshots/nfl_regular_2010_2025.csv.gz"
    provenance = root / "snapshots/nfl_regular_2010_2025.json"
    helper = root / "experiments/frozen_nfl.py"
    metadata = json.loads(provenance.read_text())
    upstream = next(record for record in json.loads((root / "data_manifest.json").read_text())["files"]
                    if record["sport"] == "football" and record["path"].endswith("/games.csv"))
    if metadata["original_source_sha256"] != upstream["sha256"] or metadata["original_source_url"] != upstream["url"]:
        raise ValueError("Frozen NFL lineage differs from the original v1 source lock")
    if metadata["sha256_uncompressed"] != NFL_NORMALIZED_SHA256["all"] or metadata["license"] != "CC-BY-4.0":
        raise ValueError("Frozen NFL normalized snapshot identity/rights mismatch")
    frame = load_snapshot(end_season=2025, root=root)
    frame = validate_events(frame, "football")
    held = frame.loc[frame.season.eq("2025")]
    dates = held.date
    by_day = pd.concat([held[["side_a", "date"]].rename(columns={"side_a": "team"}),
                        held[["side_b", "date"]].rename(columns={"side_b": "team"})])
    counts = pd.concat([held.side_a, held.side_b]).value_counts()
    if (len(held) != 271 or held.event_id.duplicated().any() or by_day.duplicated().any()
            or len(counts) != 32 or not dates.between("2025-09-01", "2026-02-01", inclusive="left").all()):
        raise ValueError("Frozen NFL retained-fixture structure changed")
    original_audit = metadata["audited_source_2025_counts"]
    for key, expected in {"regular_season_rows": 272, "tied_results_excluded": 1,
                          "unfinished_results": 0, "retained_normalized_rows": 271}.items():
        if original_audit[key] != expected:
            raise ValueError("Frozen NFL original source-audit lineage changed")
    audit = {"audit_mode": "retained normalized rows plus recorded original upstream structural audit",
             "retained_holdout_rows": len(held), "duplicate_ids": 0,
             "same_team_same_day_duplicates": 0, "retained_teams": len(counts),
             "retained_games_per_team_min": int(counts.min()), "retained_games_per_team_max": int(counts.max()),
             "recorded_original_upstream_audit": original_audit,
             "schedule_completeness": "Original raw audit established 272 regular-season fixtures and one excluded tie. This normalized snapshot reproduces the same 271 retained fixtures; excluded rows are not present for re-audit."}
    normalized_source = {**file_record(snapshot, root), "kind": "normalized_licensed_snapshot",
                         "representation": metadata["representation"], "license": metadata["license"],
                         "uncompressed_sha256": metadata["sha256_uncompressed"],
                         "provenance_file": file_record(provenance, root), "loader_file": file_record(helper, root),
                         "original_upstream_lineage": {"url": metadata["original_source_url"],
                                                       "sha256": metadata["original_source_sha256"],
                                                       "bytes": upstream["bytes"],
                                                       "retrieved_at_utc": metadata["original_retrieved_at_utc"]}}
    attributes = {"source": "Licensed normalized nflverse regular-season snapshot",
                  "source_representation": "normalized; not original provider download",
                  "license": metadata["license"], "normalized_snapshot_sha256": sha256(snapshot),
                  "original_upstream_sha256": metadata["original_source_sha256"]}
    return frame, attributes, normalized_source, audit


def source_holdout_audit(sport: str, raw: Path) -> dict:
    """Counts/exclusions only; never calculate outcome balance or aggregates."""
    if sport == "football":
        frame = pd.read_csv(raw / "games.csv", usecols=list(football.SOURCE_COLUMNS))
        frame = frame.loc[frame.season.eq(2025) & frame.game_type.eq("REG")].copy()
        scores = frame[["home_score", "away_score"]].apply(pd.to_numeric, errors="raise")
        present = scores.notna().all(axis=1)
        numeric = scores.loc[present].to_numpy()
        invalid = ~np.isfinite(numeric) | (numeric < 0) | (numeric % 1 != 0)
        if invalid.any():
            raise ValueError("Invalid NFL holdout score schema")
        dates = pd.to_datetime(frame.gameday, format="%Y-%m-%d", errors="raise")
        if not dates.between("2025-09-01", "2026-02-01", inclusive="left").all():
            raise ValueError("NFL 2025 dates outside regular-season bounds")
        teams = pd.concat([frame.home_team.replace(football.TEAM_ALIASES), frame.away_team.replace(football.TEAM_ALIASES)])
        counts = teams.value_counts()
        duplicate = int(frame.game_id.duplicated().sum())
        by_day = pd.concat([pd.DataFrame({"team": frame.home_team, "date": dates}),
                            pd.DataFrame({"team": frame.away_team, "date": dates})])
        same_day = int(by_day.duplicated().sum())
        if duplicate or same_day or len(frame) != 272 or len(counts) != 32 or not counts.eq(17).all():
            raise ValueError("NFL full regular-season schedule invariant failed")
        return {"source_rows": len(frame), "uncompleted": int((~present).sum()),
                "ties_excluded": int((present & scores.home_score.eq(scores.away_score)).sum()),
                "duplicate_ids": duplicate, "same_team_same_day_duplicates": same_day,
                "schedule_games": len(frame), "schedule_teams": len(counts),
                "games_per_team_min": int(counts.min()), "games_per_team_max": int(counts.max()),
                "schedule_completeness": "272 distinct regular-season fixtures; 32 teams with 17 games each"}
    if sport == "baseball":
        with override(baseball, YEARS=(2025,)):
            frame = baseball.load(raw)
        counts = pd.concat([frame.side_a, frame.side_b]).value_counts()
        if len(frame) != 2430 or len(counts) != 30 or not counts.eq(162).all():
            raise ValueError("MLB 2025 complete-season schedule invariant failed")
        return {**frame.attrs, "schedule_games": len(frame), "schedule_teams": len(counts),
                "games_per_team_min": int(counts.min()), "games_per_team_max": int(counts.max()),
                "schedule_completeness": "2430 distinct games; 30 teams with 162 games each; doubleheaders retained"}
    if sport == "tennis":
        with override(tennis, YEARS=(2025,)):
            frame = tennis.load(raw)
        # Read only schedule identifiers/date/category beyond adapter fields.
        calendar = pd.read_csv(raw / "atp_matches_2025.csv", usecols=["tourney_id", "tourney_date", "tourney_level"])
        tournaments = calendar[["tourney_id", "tourney_date", "tourney_level"]].drop_duplicates()
        return {**frame.attrs, "source_tournament_ids": int(tournaments.tourney_id.nunique()),
                "source_tournaments_by_level": {str(k): int(v) for k, v in tournaments.groupby("tourney_level").tourney_id.nunique().items()},
                "source_proxy_date_min": str(pd.to_datetime(calendar.tourney_date.astype(str), format="%Y%m%d").min().date()),
                "source_proxy_date_max": str(pd.to_datetime(calendar.tourney_date.astype(str), format="%Y%m%d").max().date()),
                "schedule_completeness": "Full annual source file staged; tournament calendar spans the season. Independent match-by-match completeness is unverified; a knockout/team-event schedule has no fixed regular-season match total."}
    with override(soccer, SEASONS=("2025-26",), _full_time_score=v2_soccer_score):
        frame = soccer.load(raw)
    home, away = frame.side_a.value_counts(), frame.side_b.value_counts()
    same_day = int(pd.concat([frame[["side_a", "date"]].rename(columns={"side_a": "team"}),
                             frame[["side_b", "date"]].rename(columns={"side_b": "team"})]).duplicated().sum())
    duplicate_pairs = int(frame.duplicated(["side_a", "side_b"]).sum())
    if len(frame) != 380 or len(home) != 20 or not home.eq(19).all() or not away.eq(19).all() or same_day or duplicate_pairs:
        raise ValueError("EPL 2025-26 complete-season schedule invariant failed")
    return {**frame.attrs, "source_rows": 380, "schedule_games": len(frame), "schedule_teams": len(home),
            "home_games_per_team": 19, "away_games_per_team": 19,
            "same_team_same_day_duplicates": same_day, "duplicate_ordered_pairs": duplicate_pairs,
            "schedule_completeness": "380 distinct ordered pairs; 20 teams, each 19 home and 19 away games"}


def assert_history_equal(history: pd.DataFrame, v1_path: Path) -> None:
    old = pd.read_csv(v1_path, dtype={"event_id": str, "season": str, "side_a": str, "side_b": str},
                      parse_dates=["date", "available_date"])
    # Do not expose row values if comparison fails: both files contain outcomes.
    try:
        pd.testing.assert_frame_equal(history.reset_index(drop=True)[old.columns], old,
                                      check_dtype=False, check_exact=True)
    except AssertionError:
        raise ValueError(f"Historical normalization changed for {v1_path.stem}") from None


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = frame.to_csv(index=False)
    if path.exists() and path.read_text() != payload:
        raise ValueError(f"Refusing to overwrite a changed staged dataset: {path}")
    if not path.exists():
        path.write_text(payload)


def stage(root: Path, offline: bool = False, frozen_nfl: bool = True,
          output: Path | None = None) -> dict:
    output = (output or root / "data/v2").resolve()
    if not output.is_relative_to(root):
        raise ValueError("Staging output must be inside the requested repository root")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    guard = protected_v1(root)
    def comparable_guard(records):
        return {key: value for key, value in records.items()
                if not (frozen_nfl and key.startswith("data/raw/football/"))}
    if previous and comparable_guard(guard) != comparable_guard(previous["v1_guard"]):
        raise ValueError("v1 protected files differ from the original v2 staging run")
    copy_verified_v1(root, output, frozen_nfl)
    new_sources = {
        "baseball": (baseball.SOURCE_URL.format(year=2025), "gl2025.zip"),
        "soccer": (f"{soccer.SOURCE_BASE}/2025-26/en.1.json", "en.1-2025-26.json"),
        "tennis": (f"{tennis.SOURCE_BASE}/atp_matches_2025.csv", "atp_matches_2025.csv"),
    }
    for sport, (url, filename) in new_sources.items():
        get_file(url, output / "raw" / sport / filename, offline)
    for filename, url in EVIDENCE_URLS.items():
        get_file(url, output / "evidence" / filename, offline)
    soccer_equivalence = soccer_text_audit(output / "raw/soccer/en.1-2025-26.json", output / "evidence/2025-26-source-schema-audit.txt")
    baseball_continuity = baseball_identity_audit(output / "evidence/teams.retrosheet.zip")
    records = {}
    normalized_sources = []
    for sport in SPORTS:
        raw = output / "raw" / sport
        if sport == "football" and frozen_nfl:
            frame, attributes, normalized_source, audit = load_frozen_nfl(root)
            normalized_sources.append(normalized_source)
        else:
            frame, attributes = load_full(sport, raw)
            audit = source_holdout_audit(sport, raw)
        cutoff, end = map(pd.Timestamp, BOUNDARIES[sport])
        target_mask = frame.date.ge(cutoff) & frame.date.lt(end)
        held = frame.loc[target_mask].copy()
        history = frame.loc[frame.date.lt(cutoff)].copy()
        if held.empty or history.empty or set(held.event_id) & set(history.event_id):
            raise ValueError(f"Invalid history/holdout identity split: {sport}")
        v1_history = frame.loc[~frame.season.eq(HOLDOUT[sport])].copy()
        v1_path = root / "data/processed" / f"{sport}.csv"
        if v1_path.exists():
            assert_history_equal(v1_history, v1_path)
        elif not (sport == "football" and frozen_nfl):
            raise FileNotFoundError(f"Original normalized history missing: {sport}")
        safe = history.loc[history.available_date.lt(cutoff)].copy()
        datasets = {"all": (frame, output / "processed" / f"{sport}.csv"),
                    "history": (history, output / "development" / f"{sport}.csv"),
                    "pre_holdout_development": (safe, output / "pre_holdout_development" / f"{sport}.csv"),
                    "sealed_holdout": (held, output / "sealed" / f"{sport}.csv")}
        for label, (data, path) in datasets.items():
            if sport == "football":
                digest = hashlib.sha256(data.to_csv(index=False).encode()).hexdigest()
                if digest != NFL_NORMALIZED_SHA256[label]:
                    raise ValueError(f"NFL normalized {label} bytes differ from the original v2 audit")
            write_csv(data, path)
        coverage = {str(season): {"retained_rows": len(group), "date_min": str(group.date.min().date()),
                                   "date_max": str(group.date.max().date())}
                    for season, group in frame.groupby("season", sort=True)}
        if sport == "soccer":
            audit["independent_text_schema_date_audit"] = soccer_equivalence
        if sport == "baseball":
            audit["franchise_identity_audit"] = baseball_continuity
            audit["franchise_alias_affected_rows"] = attributes["v2_alias_affected_rows"]
        records[sport] = {"holdout_season": HOLDOUT[sport], "holdout_rows": len(held),
                          "history_rows": len(history), "all_rows": len(frame),
                          "holdout_start_inclusive": str(cutoff.date()), "holdout_end_exclusive": str(end.date()),
                          "first_holdout_event_date": str(held.date.min().date()),
                          "new_source_season_retained_rows": int(frame.season.eq(HOLDOUT[sport]).sum()),
                          "new_source_rows_preceding_holdout_start": int((frame.season.eq(HOLDOUT[sport]) & frame.date.lt(cutoff)).sum()),
                          "holdout_available_date_max": str(held.available_date.max().date()),
                          "pre_holdout_development_rows": len(safe),
                          "history_labels_unavailable_at_holdout_start": len(history) - len(safe),
                          "original_source_seasons_match_v1_exactly": True, "duplicate_event_ids": int(frame.event_id.duplicated().sum()),
                          "out_of_order_dates": int(not frame.date.is_monotonic_increasing),
                          "availability_before_event": int(frame.available_date.lt(frame.date).sum()),
                          "holdout_history_event_id_overlap": 0,
                          "coverage_by_season": coverage, "adapter_attributes": attributes,
                          "holdout_audit": audit, "rights": RIGHTS[sport],
                          "official_schedule_reference": SCHEDULE_REFERENCES[sport],
                          "datasets": {label: {**file_record(path, root), "rows": len(data)} for label, (data, path) in datasets.items()}}
    source_files = []
    for directory in (output / "raw", output / "evidence"):
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.name.endswith(".source.json"):
                continue
            if frozen_nfl and path.is_relative_to(output / "raw/football"):
                continue  # A leftover original cache is not an input in this mode.
            sidecar = path.with_suffix(path.suffix + ".source.json")
            metadata = json.loads(sidecar.read_text())
            if metadata["sha256"] != sha256(path):
                raise ValueError(f"Staged source hash mismatch: {path.name}")
            source_files.append({**file_record(path, root), **metadata,
                                 "sidecar_sha256": sha256(sidecar)})
    after_guard = protected_v1(root)
    if after_guard != guard:
        changed = sorted(key for key in guard.keys() | after_guard.keys() if guard.get(key) != after_guard.get(key))
        raise RuntimeError(f"v1 protected files changed during staging: {changed}")
    manifest = {"schema_version": 1, "version": "v2", "audit_type": "outcome-blind-to-performance structural staging",
                "created_at_utc": previous["created_at_utc"] if previous else datetime.now(timezone.utc).isoformat(),
                "staging_script_sha256": sha256(Path(__file__)),
                "nfl_ingestion_mode": "frozen_normalized_snapshot" if frozen_nfl else "original_raw_download",
                "source_pins": {"soccer": soccer.SOURCE_COMMIT, "soccer_original_text": soccer.TEXT_SOURCE_COMMIT,
                                "tennis": tennis.SOURCE_COMMIT,
                                "football": "SHA256-locked normalized CC-BY-4.0 snapshot; original upstream lineage recorded separately" if frozen_nfl else "v1 SHA256-locked mutable release; not refetched",
                                "baseball": "official annual ZIP; SHA256-locked after download"},
                "holdout_policy": {"development_or_evaluation_metrics_computed": False,
                                   "target_rates_computed": False, "per_event_predictions_created": False,
                                   "access_note": "Sealed is a workflow boundary, not encryption. No features/models are imported. Raw NFL 2025 bytes existed in v1 cache but v1 adapter excluded that season.",
                                   "incidental_exposure": "Fixture-calendar/franchise web searches surfaced unsolicited public EPL/MLB result snippets. They were not extracted or used for model development. Perfect analyst outcome blindness is not claimed.",
                                   "timing_rule": "Use pre_holdout_development for fitting before the protocol holdout boundary; history may contain late-available labels. ATP target rows have calendar-2025 tournament-start proxy dates; December-2024 rows from its 2025 file are pre-target history only and are embargoed until available. Preserve strictly earlier available_date for sequential features."},
                "sports": records, "source_files": source_files, "normalized_sources": normalized_sources,
                "v1_guard": guard,
                "v1_guard_verified_unchanged": True}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--offline", action="store_true", help="Require every source/evidence file already cached")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--frozen-nfl", dest="frozen_nfl", action="store_true",
                      help="Use the redistributable normalized NFL snapshot (default)")
    mode.add_argument("--original-nfl", dest="frozen_nfl", action="store_false",
                      help="Require the exact original full NFL raw download and its sidecar")
    parser.set_defaults(frozen_nfl=True)
    parser.add_argument("--output", type=Path, help="Separate staging directory inside --root")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / "data/v2"
    manifest = stage(root, args.offline, args.frozen_nfl, output)
    print(json.dumps({"manifest": str(output / "manifest.json"), "v1_unchanged": True,
                      "coverage": {sport: {key: rec[key] for key in ("holdout_season", "holdout_rows", "history_rows", "pre_holdout_development_rows", "history_labels_unavailable_at_holdout_start")}
                                   for sport, rec in manifest["sports"].items()}}, indent=2))


if __name__ == "__main__":
    main()
