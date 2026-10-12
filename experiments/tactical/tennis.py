"""Pinned MCP A1/A2 serve parsing and descriptive QA. No fitted models.

Only the standard library is imported. Raw strings, source rows and row-level
outputs remain under ignored data/tactical/tennis. See docs/tactical/tennis_parser.md.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote
from typing import Iterable

MCP_REPOSITORY = "https://github.com/JeffSackmann/tennis_MatchChartingProject"
MCP_COMMIT = "1813a1309b7ed7ebf1c7e884b32bf675d00e4edf"
PARSER_VERSION = "mcp-serve-prefix-v1"
POINT_COLUMNS = ("match_id", "Pt", "Set1", "Set2", "Gm1", "Gm2", "Pts", "Gm#", "TbSet", "Svr", "1st", "2nd", "Notes", "PtWinner")
MATCH_COLUMNS = ("match_id", "Player 1", "Player 2", "Pl 1 hand", "Pl 2 hand", "Date", "Tournament", "Round", "Time", "Court", "Surface", "Umpire", "Best of", "Final TB?", "Charted by")
POINT_FILES = tuple(f"charting-{sex}-points-{era}.csv" for sex in "mw" for era in ("to-2009", "2010s", "2020s"))
REQUIRED_FILES = set(POINT_FILES) | {"charting-m-matches.csv", "charting-w-matches.csv", "README.md", "data_dictionary.txt", "MatchChart 0.3.2.xlsm"}
DIRECTIONS = {"4": "wide", "5": "body", "6": "T", "0": None}
FAULTS = dict(zip("nwdxge!", ("net", "wide", "deep", "wide_and_deep", "foot_fault", "unknown", "shank")))
SHOT_CODES = frozenset("fbrsvzopuy lmhijktq".replace(" ", ""))
SUPPORTED_RULES = frozenset(("0", "1", "A", "T", "V", "W"))
DEV_YEARS = (2010, 2022)
HISTORY_EMBARGO_DAYS = 21
KNOWN_DATE_QUARANTINES = {
    "20210701-M-Wimbledon-QF-Hubert_Hurkacz-Roger_Federer": {
        "source_date": "20210701", "verified_event_date": "20210707",
        "evidence": "https://www.wimbledon.com/en_GB/scores/2021/schedule/pdf/schedulePDF17.pdf",
        "action": "quarantine; no silent source-date correction"}}


def assumed_available_date(source_date: str):
    """Conservative research embargo, NOT verified completion/publication time."""
    if not re.fullmatch(r"\d{8}", source_date):
        raise ValueError("Expected source date YYYYMMDD")
    return datetime.strptime(source_date, "%Y%m%d").date() + timedelta(days=HISTORY_EMBARGO_DAYS)


def history_available_before(source_date: str, analysis_date: str) -> bool:
    return assumed_available_date(source_date) < datetime.strptime(analysis_date, "%Y%m%d").date()



def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_sources(root: Path) -> dict:
    """Fail closed on pin, file-set, byte-size, URL or SHA-256 disagreement."""
    manifest_path = root / "docs/research/tennis/source_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    source = next(item for item in manifest["sources"] if item["id"] == "mcp")
    if source["repository"] != MCP_REPOSITORY or source["commit"] != MCP_COMMIT or source["license"] != "CC-BY-NC-SA-4.0":
        raise ValueError("MCP pin/license does not match the reviewed contract")
    if {entry["file"] for entry in source["files"]} != REQUIRED_FILES or len(source["files"]) != len(REQUIRED_FILES):
        raise ValueError("Unexpected MCP source file set")
    cache = root / "data/research/tennis/source-samples"
    files = []
    for entry in source["files"]:
        path = cache / entry["file"]
        expected_url = f"https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/{MCP_COMMIT}/{quote(entry["file"])}"
        if entry.get("source_commit") != MCP_COMMIT or entry["url"] != expected_url:
            raise ValueError(f"Unpinned source: {entry['file']}")
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError(f"Source hash/size mismatch: {entry['file']}")
        files.append({key: entry[key] for key in ("file", "url", "sha256", "bytes")})
    return {"repository": source["repository"], "commit": MCP_COMMIT,
            "commit_utc": source["commit_utc"], "license": source["license"],
            "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "attribution": "Jeff Sackmann / Tennis Abstract and Match Charting Project contributors",
            "manifest_sha256": digest(manifest_path), "parser_code_sha256": digest(Path(__file__)), "files": files,
            "transformation": PARSER_VERSION,
            "use_scope": "Local noncommercial research/descriptive QA only; no raw redistribution, hosted service or fitted artifact authorization implied"}


def read_csv(path: Path, columns: tuple[str, ...]):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        if tuple(next(reader)) != columns:
            raise ValueError(f"Unexpected CSV schema: {path.name}")
        for number, values in enumerate(reader, 2):
            yield number, values


def metadata_errors(row: dict) -> tuple[str, ...]:
    errors = []
    date = row["Date"]
    if row["match_id"] in KNOWN_DATE_QUARANTINES:
        errors.append("verified_source_date_contradiction")
    try:
        if not re.fullmatch(r"\d{8}", date):
            raise ValueError()
        datetime.strptime(date, "%Y%m%d")
    except ValueError:
        errors.append("metadata_invalid_date")
    if not row["match_id"].startswith(date + "-"):
        errors.append("metadata_date_id_mismatch")
    if row["Surface"] not in {"Hard", "Clay", "Grass"}:
        errors.append("metadata_invalid_surface")
    if row["Best of"] not in {"3", "5"}:
        errors.append("metadata_invalid_best_of")
    if any(row[k] not in {"R", "L", "U", ""} for k in ("Pl 1 hand", "Pl 2 hand")):
        errors.append("metadata_invalid_hand")
    if not row["Player 1"] or not row["Player 2"] or row["Player 1"] == row["Player 2"]:
        errors.append("metadata_invalid_players")
    if row["Final TB?"] not in SUPPORTED_RULES:
        errors.append("unsupported_or_missing_scoring_rules")
    return tuple(errors)


def load_metadata(cache: Path):
    matches, invalid = {}, defaultdict(set)
    stats = Counter()
    seen = defaultdict(set)
    for corpus in "mw":
        for _, values in read_csv(cache / f"charting-{corpus}-matches.csv", MATCH_COLUMNS):
            stats[f"{corpus}_raw_rows"] += 1
            key = (corpus, values[0] if values else "")
            if len(values) != len(MATCH_COLUMNS):
                invalid[key].add("metadata_malformed_csv")
                stats["malformed_csv_rows"] += 1
                continue
            raw = tuple(values)
            if raw in seen[key]:
                stats["exact_duplicate_extra_rows"] += 1
                continue
            seen[key].add(raw)
            row = dict(zip(MATCH_COLUMNS, (v.strip() for v in values)))
            errors = metadata_errors(row)
            invalid[key].update(errors)
            if key in matches and matches[key] != row:
                invalid[key].add("metadata_conflict")
            else:
                matches[key] = row
    return matches, invalid, dict(stats)


def ingest_points(cache: Path, db: sqlite3.Connection, duplicate_stream=None):
    """Disk-backed deterministic deduplication; never select a conflicting match."""
    db.executescript("""
        DROP TABLE IF EXISTS points;
        CREATE TABLE points(corpus TEXT, match_id TEXT, pt INTEGER, payload TEXT,
                            source_file TEXT, source_row INTEGER,
                            PRIMARY KEY(corpus, match_id, pt)) WITHOUT ROWID;
    """)
    stats, invalid = Counter(), defaultdict(set)
    variants = {}
    conflicting_keys = set()
    previous = {}
    decreasing = set()
    for filename in POINT_FILES:
        corpus = filename.split("-")[1]
        for number, values in read_csv(cache / filename, POINT_COLUMNS):
            stats["raw_rows"] += 1
            stats[f"{corpus}_raw_rows"] += 1
            match_id = values[0] if values else ""
            key = (corpus, match_id)
            if len(values) != len(POINT_COLUMNS):
                invalid[key].add("point_malformed_csv")
                stats["malformed_csv_rows"] += 1
                continue
            if not re.fullmatch(r"[1-9]\d*", values[1]):
                invalid[key].add("invalid_point_ordinal")
                stats["invalid_point_ordinal_rows"] += 1
                continue
            pt = int(values[1])
            if pt < previous.get(key, 0):
                decreasing.add(key)
            previous[key] = pt
            point_key = (*key, pt)
            payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
            cur = db.execute("INSERT OR IGNORE INTO points VALUES(?,?,?,?,?,?)", (*point_key, payload, filename, number))
            if not cur.rowcount:
                stats["duplicate_extra_rows"] += 1
                if point_key not in variants:
                    prior = db.execute("SELECT payload FROM points WHERE corpus=? AND match_id=? AND pt=?", point_key).fetchone()[0]
                    variants[point_key] = {prior}
                exact = payload in variants[point_key]
                if exact:
                    stats["exact_duplicate_extra_rows"] += 1
                else:
                    variants[point_key].add(payload)
                    conflicting_keys.add(point_key)
                    invalid[key].add("conflicting_point_key")
                if duplicate_stream is not None:
                    duplicate_stream.write(json.dumps({"corpus": corpus, "match_id": match_id, "pt": pt,
                        "source_file": filename, "source_row": number, "kind": "exact" if exact else "conflicting",
                        "row_sha256": hashlib.sha256(payload.encode()).hexdigest()}, sort_keys=True) + "\n")
        db.commit()
    stats["conflicting_point_keys"] = len(conflicting_keys)
    stats["conflicting_matches"] = sum("conflicting_point_key" in v for v in invalid.values())
    stats["source_matches_with_decreasing_point_order"] = len(decreasing)
    stats["unique_point_keys"] = db.execute("SELECT COUNT(*) FROM points").fetchone()[0]
    return dict(stats), invalid


@dataclass(frozen=True)
class ServePrefix:
    raw_prefix: str
    start: int
    end: int
    direction: str | None
    direction_status: str
    outcome: str
    fault: str | None = None
    lets: int = 0
    modifiers: str = ""
    flags: tuple[str, ...] = ()
    suffix_start: int | None = None


def parse_serve(value: str) -> ServePrefix:
    """Parse the serve prefix only. Deliberately never interprets a rally suffix.

    Offsets refer to the original cell, including any whitespace. Unknown/missing
    direction, unobserved point, penalty, time violation and lets remain distinct.
    """
    raw = value
    start = len(raw) - len(raw.lstrip())
    text = raw.strip()
    flags = ["trimmed_whitespace"] if text != raw else []
    lets = len(text) - len(text.lstrip("c"))
    pos = lets
    if lets:
        flags.append("let_directions_unrecorded")
    base = text[pos:]
    specials = {"S": "unobserved_server", "R": "unobserved_receiver", "P": "penalty_server", "Q": "penalty_receiver", "V": "first_serve_time_violation"}
    if base in specials:
        return ServePrefix(raw[start:start + len(text)], start, start + len(text), None, "unobserved" if base in "SR" else "not_applicable", specials[base], lets=lets, flags=tuple(flags))
    if not base:
        return ServePrefix(text, start, start + len(text), None, "missing", "missing", lets=lets, flags=tuple(flags))
    # Bare documented error symbols occur in the corpus, but omit the required
    # direction token. Preserve their meaning as an extension, never coerce to 0.
    if base in FAULTS:
        return ServePrefix(text, start, start + len(text), None, "omitted", "fault", FAULTS[base], lets, flags=tuple(flags + ["omitted_direction_extension"]))
    if base[0] not in DIRECTIONS:
        return ServePrefix(text[:pos + 1], start, start + pos + 1, None, "invalid", "unsupported", lets=lets, flags=tuple(flags + ["unsupported_serve_start"]))
    direction = DIRECTIONS[base[0]]
    pos += 1
    modifiers = ""
    while pos < len(text) and text[pos] in "+;":
        modifiers += text[pos]
        pos += 1
    if len(set(modifiers)) != len(modifiers):
        flags.append("repeated_serve_modifier")
    outcome, fault, suffix = "in_play_or_unspecified", None, None
    if pos < len(text):
        char = text[pos]
        if char in FAULTS:
            outcome, fault = "fault", FAULTS[char]
            pos += 1
            if pos != len(text):
                outcome = "unsupported"
                flags.append("unexpected_fault_suffix")
        elif char in "*#":
            outcome = "ace" if char == "*" else "unreturned"
            pos += 1
            if pos != len(text):
                outcome = "unsupported"
                flags.append("unexpected_terminal_suffix")
        elif char in SHOT_CODES or char == "C":
            suffix = start + pos
            flags.append("rally_suffix_not_parsed")
            if "C" in text[pos:]:
                flags.append("wrong_challenge_in_unparsed_suffix")
        else:
            outcome = "unsupported"
            flags.append("unsupported_serve_modifier_or_suffix")
    else:
        flags.append("point_completion_not_encoded")
    return ServePrefix(raw[start:start + pos], start, start + pos, direction,
        "known" if direction is not None else "explicit_unknown", outcome, fault, lets,
        modifiers, tuple(flags), suffix)


def serve_events(row: dict) -> list[dict]:
    """Source-preserving serve/let events only; never invent rally contacts.

    A c token records an observed let occurrence with unrecorded direction.
    Penalties, unobserved point awards and time violations are non-contact events.
    Event numbers are local to this partial serve stream, not rally stroke counts.
    """
    events = []
    for period, field in ((1, "1st"), (2, "2nd")):
        raw = row[field]
        parsed = parse_serve(raw)
        if parsed.outcome == "missing" and not parsed.lets:
            continue
        for index in range(parsed.lets):
            offset = parsed.start + index
            events.append({"event_ordinal": len(events) + 1, "serve_period": period,
                "striker": row["Svr"], "event_kind": "let", "physical_contact": True,
                "raw_token": raw[offset:offset + 1], "source_field": field,
                "source_start": offset, "source_end": offset + 1,
                "direction": None, "direction_status": "unrecorded_for_let", "terminal_status": "replay_service"})
        if parsed.outcome == "missing":
            continue
        physical = parsed.outcome in {"fault", "ace", "unreturned", "in_play_or_unspecified"}
        offset = parsed.start + parsed.lets
        events.append({"event_ordinal": len(events) + 1, "serve_period": period,
            "striker": row["Svr"] if physical else None, "source_server": row["Svr"],
            "event_kind": "serve" if physical else parsed.outcome,
            "physical_contact": physical if parsed.outcome != "unsupported" else None,
            "raw_token": raw[offset:parsed.end], "source_field": field,
            "source_start": offset, "source_end": parsed.end,
            "direction": parsed.direction, "direction_status": parsed.direction_status,
            "modifiers": parsed.modifiers, "fault_type": parsed.fault,
            "terminal_status": parsed.outcome, "quality_flags": list(parsed.flags)})
    return events


@dataclass(frozen=True)
class ScoreState:
    sets: tuple[int, int] = (0, 0)
    games: tuple[int, int] = (0, 0)
    points: tuple[int, int] = (0, 0)
    server: int = 1
    game_number: int = 1
    point_number: int = 1
    game_point_number: int = 0
    tiebreak_first_server: int | None = None
    complete: bool = False


def tiebreak_rule(meta: dict, state: ScoreState):
    code = meta["Final TB?"]
    if code not in SUPPORTED_RULES:
        raise ValueError("Unsupported scoring rules")
    final = sum(state.sets) == int(meta["Best of"]) - 1
    if code == "V" or (code == "0" and final):
        return None
    if code == "W":
        return (8, 7)
    if code == "T" and final:
        return (12, 7)
    return (6, 10 if code == "A" and final else 7)


def in_tiebreak(meta: dict, state: ScoreState) -> bool:
    rule = tiebreak_rule(meta, state)
    return rule is not None and state.games == (rule[0], rule[0])


def point_score(meta: dict, state: ScoreState) -> tuple[str, str]:
    p = state.points
    if in_tiebreak(meta, state):
        absolute = tuple(str(v) for v in p)
    elif min(p) >= 3:
        absolute = ("40", "40") if p[0] == p[1] else (("AD", "40") if p[0] > p[1] else ("40", "AD"))
    else:
        absolute = tuple(("0", "15", "30", "40")[min(v, 3)] for v in p)
    return absolute if state.server == 1 else absolute[::-1]


def advance_score(meta: dict, state: ScoreState, winner: int) -> ScoreState:
    if winner not in (1, 2) or state.complete:
        raise ValueError("Invalid winner or point after match completion")
    pts = list(state.points)
    pts[winner - 1] += 1
    tb = in_tiebreak(meta, state)
    threshold = tiebreak_rule(meta, state)[1] if tb else 4
    won_game = pts[winner - 1] >= threshold and pts[winner - 1] - pts[2 - winner] >= 2
    following = replace(state, points=tuple(pts), point_number=state.point_number + 1,
                        game_point_number=state.game_point_number + 1)
    if not won_game:
        if tb:
            first = state.tiebreak_first_server or state.server
            total = sum(pts)
            server = first if ((total + 1) // 2) % 2 == 0 else 3 - first
            following = replace(following, server=server, tiebreak_first_server=first)
        return following
    games = list(state.games)
    games[winner - 1] += 1
    sets = list(state.sets)
    if tb or (games[winner - 1] >= 6 and games[winner - 1] - games[2 - winner] >= 2):
        sets[winner - 1] += 1
        games = [0, 0]
    next_server = 3 - (state.tiebreak_first_server or state.server) if tb else 3 - state.server
    return replace(following, games=tuple(games), sets=tuple(sets), points=(0, 0),
                   server=next_server, game_number=state.game_number + 1,
                   game_point_number=0, tiebreak_first_server=None,
                   complete=max(sets) == (int(meta["Best of"]) // 2 + 1))


def expected_source_score(meta: dict, state: ScoreState) -> dict:
    return {"Pt": str(state.point_number), "Set1": str(state.sets[0]), "Set2": str(state.sets[1]),
            "Gm1": str(state.games[0]), "Gm2": str(state.games[1]), "Pts": "-".join(point_score(meta, state)),
            "Gm#": str(state.game_number), "Svr": str(state.server),
            "TbSet": "True" if tiebreak_rule(meta, state) is not None else "False"}


def terminal_winner(row: dict, first: ServePrefix, second: ServePrefix) -> int | None:
    """Only direct serve/special outcomes, never inferred full-rally parity."""
    try:
        server = int(row["Svr"])
    except ValueError:
        return None
    if first.outcome in {"unobserved_server", "penalty_receiver"}:
        return server
    if first.outcome in {"unobserved_receiver", "penalty_server"}:
        return 3 - server
    attempt = second if first.outcome in {"fault", "first_serve_time_violation"} else first
    if attempt.outcome in {"ace", "unreturned"}:
        return server
    if attempt is second and second.outcome == "fault":
        return 3 - server
    return None


def audit_match(meta: dict, rows: list[dict]):
    """Replay only prior outcomes. Any disagreement quarantines the whole match.

    The last row need not finish a match (retirements/partial charts); this is
    reported separately and never fabricates a completed match outcome.
    """
    reasons, checks, states = set(), Counter(), []
    if meta["Final TB?"] not in SUPPORTED_RULES:
        return [], {"unsupported_or_missing_scoring_rules"}, checks, False
    state = ScoreState()
    for row in rows:
        states.append(state)
        expected = expected_source_score(meta, state)
        for name, value in expected.items():
            checks[f"{name}_tested"] += 1
            if row[name] != value:
                reasons.add("score_or_server_transition_mismatch")
                checks[f"{name}_mismatch"] += 1
        if state.complete:
            reasons.add("points_after_match_completion")
            break
        if row["PtWinner"] not in {"1", "2"}:
            reasons.add("invalid_point_winner")
            break
        first, second = parse_serve(row["1st"]), parse_serve(row["2nd"])
        known = terminal_winner(row, first, second)
        if known is not None:
            checks["direct_terminal_winner_tested"] += 1
            if known != int(row["PtWinner"]):
                reasons.add("direct_terminal_winner_mismatch")
                checks["direct_terminal_winner_mismatch"] += 1
        state = advance_score(meta, state, int(row["PtWinner"]))
    return states, reasons, checks, state.complete


def prediction_features(meta: dict, state: ScoreState, corpus: str, task: str,
                        first_fault: ServePrefix | None = None) -> dict:
    """Structural feature allowlist. No current point row or future string input."""
    if task not in {"A1", "A2"}:
        raise ValueError("Only A1/A2 are implemented")
    server, receiver = state.server, 3 - state.server
    sp, rp = point_score(meta, state)
    features = {"corpus": corpus, "match_date": meta["Date"], "surface": meta["Surface"],
        "server": meta[f"Player {server}"], "returner": meta[f"Player {receiver}"],
        "server_hand": meta[f"Pl {server} hand"] or "U", "returner_hand": meta[f"Pl {receiver} hand"] or "U",
        "serve_period": 1 if task == "A1" else 2,
        "serve_side": "deuce" if state.game_point_number % 2 == 0 else "ad",
        "server_sets": state.sets[server - 1], "returner_sets": state.sets[receiver - 1],
        "server_games": state.games[server - 1], "returner_games": state.games[receiver - 1],
        "server_points": sp, "returner_points": rp, "point_ordinal": state.point_number,
        "game_number": state.game_number, "current_tiebreak": in_tiebreak(meta, state),
        "set_tiebreak_rule": tiebreak_rule(meta, state) is not None}
    if task == "A2":
        if first_fault is None or first_fault.outcome != "fault":
            raise ValueError("A2 requires a known completed first fault")
        features.update(first_fault_direction=first_fault.direction,
                        first_fault_direction_status=first_fault.direction_status,
                        first_fault_type=first_fault.fault)
    return features


def target_record(meta: dict, row: dict, state: ScoreState | None, corpus: str,
                  task: str, match_reasons: Iterable[str] = (), *,
                  parsed_attempts: tuple[ServePrefix, ServePrefix] | None = None,
                  include_quality: bool = True) -> dict:
    """Separate retrospective eligibility/quality from prefix-only features."""
    if task not in {"A1", "A2"}:
        raise ValueError("Only A1/A2 are implemented")
    first, second = parsed_attempts or (parse_serve(row["1st"]), parse_serve(row["2nd"]))
    attempt = first if task == "A1" else second
    reasons = set(match_reasons)
    if task == "A2" and first.outcome != "fault":
        reasons.add("first_serve_time_violation_not_first_fault" if first.outcome == "first_serve_time_violation" else "did_not_reach_verified_second_serve")
    if first.outcome not in {"fault", "first_serve_time_violation"} and row["2nd"].strip():
        reasons.add("second_field_without_verified_first_fault_or_violation")
    if first.outcome == "fault" and not row["2nd"].strip():
        reasons.add("first_fault_missing_second_field")
    if attempt.outcome in {"unobserved_server", "unobserved_receiver"}:
        reasons.add("unobserved_point")
    elif attempt.outcome.startswith("penalty_"):
        reasons.add("penalty_no_observed_serve")
    elif attempt.outcome == "first_serve_time_violation":
        reasons.add("first_serve_lost_time_violation")
    elif attempt.outcome == "unsupported":
        reasons.add("unsupported_serve_prefix")
    elif attempt.outcome == "missing":
        reasons.add("missing_attempt")
    if attempt.direction_status != "known":
        reasons.add("direction_" + attempt.direction_status)
    if attempt.lets:
        reasons.add("let_prefixed_attempt_target_ambiguous")
    if "trimmed_whitespace" in attempt.flags or "repeated_serve_modifier" in attempt.flags:
        reasons.add("noncanonical_serve_prefix")
    features = None
    if state is not None and (task == "A1" or first.outcome == "fault"):
        features = prediction_features(meta, state, corpus, task, first if task == "A2" else None)
    if state is None:
        reasons.add("validated_prepoint_state_unavailable")
    return {"task": task, "eligible": not reasons, "exclusions": sorted(reasons), "features": features,
            "target": attempt.direction, "quality": {"notes_present": bool(row["Notes"].strip()),
            "first": asdict(first), "second": asdict(second)} if include_quality else None,
            "cutoff": "before_first_serve_motion" if task == "A1" else "after_first_fault_before_second_serve_motion"}


def support_summary(counts: Counter) -> dict:
    values = sorted(counts.values())
    return {"players": len(values), "server_appearances": sum(values),
            "players_at_least": {str(n): sum(v >= n for v in values) for n in (1, 10, 30, 100, 1000)},
            "top10_share": sum(values[-10:]) / sum(values) if values else None,
            "minimum": min(values) if values else None, "maximum": max(values) if values else None}


def run(root: Path, write_rows: bool = False) -> dict:
    root = root.resolve()
    provenance = validate_sources(root)
    cache = root / "data/research/tennis/source-samples"
    local = root / "data/tactical/tennis"
    report_dir = root / "reports/tactical/tennis"
    local.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    matches, invalid_meta, meta_stats = load_metadata(cache)
    db = sqlite3.connect(local / "source_index.sqlite3")
    db.execute("PRAGMA journal_mode=OFF")
    db.execute("PRAGMA temp_store=FILE")
    db.execute("PRAGMA cache_size=-16384")
    with (local / "duplicate_provenance.jsonl").open("w") as duplicate_stream:
        source_stats, invalid_points = ingest_points(cache, db, duplicate_stream)
    audit_counts, quality_counts, quarantine = Counter(), Counter(), Counter()
    totals = {task: Counter() for task in ("A1", "A2")}
    primary_exclusions = {task: Counter() for task in totals}
    exclusions = {task: Counter() for task in totals}
    strata, patterns = defaultdict(Counter), defaultdict(Counter)
    player_points, player_matches = defaultdict(Counter), defaultdict(Counter)
    source_matches, valid_matches, complete_matches = 0, 0, 0
    emitted = 0
    # Reproducible gzip header: no time or filename embedded.
    row_raw = (local / "development_prediction_rows.jsonl.gz").open("wb") if write_rows else None
    row_stream = gzip.GzipFile(fileobj=row_raw, mode="wb", mtime=0, filename="") if write_rows else None
    with (local / "match_quality.jsonl").open("w") as audit_stream:
        keys = db.execute("SELECT DISTINCT corpus,match_id FROM points ORDER BY corpus,match_id").fetchall()
        for corpus, match_id in keys:
            source_matches += 1
            records = db.execute("SELECT payload,source_file,source_row FROM points WHERE corpus=? AND match_id=? ORDER BY pt", (corpus, match_id)).fetchall()
            rows = [dict(zip(POINT_COLUMNS, json.loads(record[0]))) for record in records]
            meta = matches.get((corpus, match_id))
            reasons = set(invalid_points.get((corpus, match_id), ())) | set(invalid_meta.get((corpus, match_id), ()))
            if meta is None:
                reasons.add("metadata_missing")
            if [int(row["Pt"]) for row in rows] != list(range(1, len(rows) + 1)):
                reasons.add("point_ordinal_not_consecutive_from_one")
            states, checks, complete = [], Counter(), False
            if not reasons:
                states, score_reasons, checks, complete = audit_match(meta, rows)
                reasons.update(score_reasons)
                audit_counts.update(checks)
            if reasons:
                quarantine.update(reasons)
            else:
                valid_matches += 1
                complete_matches += int(complete)
            audit_stream.write(json.dumps({"corpus": corpus, "match_id": match_id, "point_count": len(rows),
                "quarantined": bool(reasons), "reasons": sorted(reasons), "score_checks": dict(checks),
                "complete_match_by_score": complete}, sort_keys=True) + "\n")
            year = meta["Date"][:4] if meta and re.fullmatch(r"\d{8}", meta["Date"]) else "unavailable"
            surface = meta["Surface"] if meta else "unavailable"
            development = year.isdigit() and DEV_YEARS[0] <= int(year) <= DEV_YEARS[1]
            supported_players_in_match = defaultdict(set)
            for index, row in enumerate(rows):
                first, second = parse_serve(row["1st"]), parse_serve(row["2nd"])
                for period, attempt in ((1, first), (2, second)):
                    quality_counts[f"period{period}_outcome:{attempt.outcome}"] += 1
                    quality_counts[f"period{period}_direction_status:{attempt.direction_status}"] += 1
                    for flag in attempt.flags:
                        quality_counts[f"period{period}_flag:{flag}"] += 1
                    quality_counts[f"period{period}_recorded_lets"] += attempt.lets
                quality_counts["notes_present"] += int(bool(row["Notes"].strip()))
                for task in totals:
                    state = states[index] if not reasons and index < len(states) else None
                    record = target_record(meta, row, state, corpus, task, reasons,
                                           parsed_attempts=(first, second), include_quality=write_rows)
                    bucket = strata[(task, corpus, surface, year)]
                    totals[task]["candidate_point_rows"] += 1
                    bucket["candidate_point_rows"] += 1
                    entered = task == "A1" or first.outcome == "fault"
                    if entered:
                        totals[task]["target_opportunities_before_quality_exclusions"] += 1
                        bucket["target_opportunities_before_quality_exclusions"] += 1
                        if not reasons:
                            totals[task]["entry_opportunities_after_match_qa"] += 1
                            bucket["entry_opportunities_after_match_qa"] += 1
                    if record["eligible"]:
                        totals[task]["eligible_rows"] += 1
                        bucket["eligible_rows"] += 1
                        totals[task]["eligible_rows_with_notes"] += int(bool(row["Notes"].strip()))
                        bucket["eligible_rows_with_notes"] += int(bool(row["Notes"].strip()))
                        features = record["features"]
                        player_points[(task, corpus, "all_years_coverage")][features["server"]] += 1
                        supported_players_in_match[(task, "all_years_coverage")].add(features["server"])
                        if development:
                            totals[task]["development_eligible_rows"] += 1
                            patterns[(task, corpus, surface, features["serve_side"])][record["target"]] += 1
                            player_points[(task, corpus, "development")][features["server"]] += 1
                            supported_players_in_match[(task, "development")].add(features["server"])
                    else:
                        totals[task]["excluded_rows"] += 1
                        bucket["excluded_rows"] += 1
                        totals[task]["excluded_after_entry" if entered else "structural_nonentry_rows"] += 1
                        if reasons:
                            primary_exclusions[task]["match_quarantined"] += 1
                        elif not entered:
                            primary_exclusions[task]["not_verified_first_fault_entry"] += 1
                        else:
                            primary_exclusions[task][record["exclusions"][0]] += 1
                        exclusions[task].update(record["exclusions"])
                        bucket.update({"excluded:" + reason: 1 for reason in record["exclusions"]})
                    if write_rows and development:
                        record.update(corpus=corpus, match_id=match_id, point_ordinal=int(row["Pt"]),
                                      serve_events=serve_events(row),
                                      source_file=records[index][1], source_row=records[index][2], source_commit=MCP_COMMIT)
                        row_stream.write((json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())
                        emitted += 1
            for (task, period), players in supported_players_in_match.items():
                player_matches[(task, corpus, period)].update(players)
    if row_stream is not None:
        row_stream.close()
        row_raw.close()
    db.close()
    report = {"schema_version": 1, "parser_version": PARSER_VERSION, "sport": "tennis", "stage": "source_parser_descriptive_only", "phase": "descriptive",
        "predictive_gate": {"status": "closed", "fitting_allowed": False},
        "fit_status": "No model fitting, calibration, prediction scoring or model selection performed",
        "provenance": provenance,
        "scope": {"targets": ["A1 first-serve direction", "A2 second-serve direction after verified first fault"],
            "direction_categories": ["wide", "body", "T"], "direction_is": "observer-coded direction, not intended target",
            "development_pattern_years_inclusive": list(DEV_YEARS),
            "other_years": "Schema/parser/quality and eligibility/support counts only; no target-by-context distributions or predictive evaluation",
            "strict_let_policy": "Let-prefixed selected deliveries excluded; their let directions and first physical-attempt target are unobserved",
            "supported_rules": sorted(SUPPORTED_RULES), "unsupported_rules": "N no-ad, S replacement match tiebreak, blank/other are quarantined",
            "feature_timing": "Replayed pre-point state; A2 additionally receives only completed first-fault direction/status/type",
            "availability_limit": "Retrospective annotated data; historical publication/ingestion times and a live-feed availability window are unverified",
            "sampling_limit": "Voluntary charted matches, not a tour census; player popularity, eras and surfaces are uneven",
            "annotation_limit": "Notes presence is flagged; unmarked reconstructed/guessed annotations cannot be identified and notes are not interpreted as verified health or pre-point facts",
            "denominators": {"A1": "One potential first-service target per deduplicated point, then explicit observation/rule/quality exclusions", "A2": "Candidate entry requires a parsed completed first fault; excluded_after_entry plus eligible_rows equals candidate entry opportunities. Entry opportunities after match QA is the validated-match denominator. Conflicting representatives can affect candidate counts, never eligible rows. Structural nonentry is separate"},
            "eligibility_limit": "Whole-match retrospective QA is not a prospective feature; notes are QA-only and never an input"},
        "source_counts": source_stats, "metadata_counts": meta_stats,
        "match_quality": {"point_bearing_matches": source_matches, "validated_matches": valid_matches,
            "quarantined_matches": source_matches - valid_matches,
            "validated_complete_matches": complete_matches, "validated_incomplete_or_retired_matches": valid_matches - complete_matches,
            "quarantine_reasons_nonexclusive": dict(sorted(quarantine.items()))},
        "score_checks": dict(sorted(audit_counts.items())), "source_quality_counts": dict(sorted(quality_counts.items())),
        "targets": {task: {"counts": dict(totals[task]), "primary_exclusions_mutually_exclusive": dict(sorted(primary_exclusions[task].items())), "exclusion_reasons_nonexclusive": dict(sorted(exclusions[task].items()))} for task in totals},
        "coverage_by_target_corpus_surface_year": [dict(task=k[0], corpus=k[1], surface=k[2], year=k[3], **v) for k, v in sorted(strata.items())],
        "development_direction_counts": [dict(task=k[0], corpus=k[1], surface=k[2], serve_side=k[3], counts=dict(v), eligible_rows=sum(v.values())) for k, v in sorted(patterns.items())],
        "player_support": [dict(task=k[0], corpus=k[1], period=k[2], eligible_serves=support_summary(player_points[k]),
            eligible_server_match_appearances=support_summary(player_matches[k])) for k in sorted(player_points)],
        "row_output": {"enabled": write_rows, "development_rows_written": emitted, "storage": "Ignored local data/tactical/tennis only"},
        "absent_measurements": ["Measured coordinates", "Physical angles", "Ball or racket speed", "Spin rate", "Player tracking", "Pose or stance", "Biomechanics", "Intended target", "Reliable shot timestamps", "Verified chart publication timestamps"],
        "unimplemented_and_unapproved": ["Full rally grammar and terminal parity", "B/C/D prefix response targets", "BYU execution companion", "Manual stratified parser adjudication", "Exact fit/evaluation protocol and independent gate approval", "All numerical fitting and predictive scoring"]}
    output = report_dir / "quality_report.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    summary = dict(report)
    summary["coverage_by_target_corpus_surface_year"] = [{k: v for k, v in cell.items() if not k.startswith("excluded:")} for cell in report["coverage_by_target_corpus_surface_year"]]
    summary["detailed_quality_report"] = "quality_report.json"
    summary_path = report_dir / "summary.json"
    temporary = summary_path.with_suffix(".json.partial")
    temporary.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n")
    temporary.replace(summary_path)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--write-development-rows", action="store_true", help="Write development-only row derivatives to ignored local storage")
    args = parser.parse_args(argv)
    report = run(args.root, args.write_development_rows)
    print(json.dumps({"report": str(args.root / "reports/tactical/tennis/summary.json"),
        "match_quality": report["match_quality"], "targets": {k: v["counts"] for k, v in report["targets"].items()},
        "fit_status": report["fit_status"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
