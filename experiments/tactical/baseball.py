"""Retrosheet hybrid pitch/state reconstruction, local descriptive research only.

The information used here was obtained free of charge from and is copyrighted by
Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".

No training, scoring, extrapolated probabilities or physical pitch measurements.
Run ``python -m experiments.tactical.baseball --help`` from the repository root.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Iterable
import urllib.request
import zipfile

VERSION = "retrosheet-hybrid-v1"
SOURCE_PINS = {
    "2023eve.zip": "301e6d36afd58f3c2f9b3dfa546cb7953b24c90a4de57a69565ccc2f2a5eb8d1",
    "2024eve.zip": "5dfd9ed678c9c619f6a216322922c99234c067d0ec15b12790546f620ced2fa4",
    "2025eve.zip": "5ece2be6c8ec5b47b9d8d90f2ca533ceca7eee915c7e0997f9bd6d64b879303c",
    "2023plays.zip": "0129befd7944f60a858e5fdc265a44ed20afaa568679b37fca1083e3c083b20e",
    "2024plays.zip": "a3e8c08876ddf70e1ffb0b20486c2873cf4aae19e0acc8002096e9056107615b",
    "2025plays.zip": "ea7f4be3464825b332ed6f8c19e15310858458ea9eddf3e91a954e5b47f69d73",
}
NOTICE = ('The information used here was obtained free of charge from and is copyrighted by '
          'Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".')
SPEC_URL = "https://www.retrosheet.org/eventfile.htm"
PITCH_CODES = frozenset("ABCFHIKLMNOPQRSTUVXY")
MARKERS = frozenset("123+*.>")
ADMIN = frozenset("AVN")
CONVENTIONAL = frozenset("BCFSTX")
SWINGS = frozenset("FSTX")
CONTACT = frozenset("FTX")
REQUIRED_PARSED = frozenset(("gid pn event inning top_bot vis_home batter pitcher bathand pithand "
    "balls strikes count pitches pa k walk hbp bip bunt hr xi outs_pre outs_post br1_pre br2_pre br3_pre "
    "br1_post br2_post br3_post score_v score_h runs date gametype").split())
KNOWN_ANOMALIES = {("SEA202503280", 42): "known_source_count_anomaly_SEA202503280_pn42"}
FEATURE_FIELDS = ("inning", "batting_side", "top_bottom", "outs", "on_first", "on_second",
    "on_third", "visitor_score", "home_score", "batting_score_difference", "balls", "strikes",
    "batter", "pitcher", "batter_hand", "pitcher_hand", "batter_hand_method",
    "pa_delivered_pitch_index", "previous_pitch_outcome", "previous_three_pitch_outcomes")


class AlignmentError(ValueError):
    """A structural ambiguity: do not silently drop rows or create an eligible file."""


@dataclass(frozen=True)
class RawRecord:
    source_file: str
    source_row: int
    fields: tuple[str, ...]


@dataclass
class GameResult:
    gid: str
    pitches: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    stats: Counter = field(default_factory=Counter)
    issues: list[dict] = field(default_factory=list)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_source(path: Path, year: int, kind: str) -> dict:
    meta = json.loads(path.with_suffix(path.suffix + ".source.json").read_text())
    route = "events" if kind == "eve" else "downloads/plays"
    url = f"https://www.retrosheet.org/{route}/{year}{kind}.zip"
    if meta.get("url") != url or meta.get("filename") != path.name:
        raise AlignmentError(f"Unexpected source URL/name: {path}")
    if (path.stat().st_size != meta.get("bytes") or sha256(path) != meta.get("sha256") or
            meta.get("sha256") != SOURCE_PINS.get(path.name)):
        raise AlignmentError(f"Source hash/size mismatch: {path}")
    if not meta.get("retrieved_utc"):
        raise AlignmentError(f"Missing retrieval provenance: {path}")
    return dict(meta, local_path=str(path), role="raw_events_and_rosters" if kind == "eve" else "official_parsed_states")


def source_path(root: Path, year: int, kind: str) -> Path:
    cached = root / "data/raw/tactical_research" / f"{year}{kind}.zip"
    return cached if cached.exists() else root / "data/tactical/baseball/sources" / cached.name


def fetch_missing_sources(root: Path, years: tuple[int, ...]):
    """Explicit opt-in official pinned downloads. Never overwrite source versions."""
    for year in years:
        for kind in ("eve", "plays"):
            path = source_path(root, year, kind)
            if path.exists():
                validate_source(path, year, kind)
                continue
            route = "events" if kind == "eve" else "downloads/plays"
            url = f"https://www.retrosheet.org/{route}/{path.name}"
            with urllib.request.urlopen(url, timeout=180) as response:
                payload = response.read()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != SOURCE_PINS.get(path.name):
                raise AlignmentError(f"Official source changed; review required before replacing pin: {url}")
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".zip.partial")
            temporary.write_bytes(payload)
            temporary.replace(path)
            metadata = {"filename": path.name, "url": url, "bytes": len(payload),
                "sha256": digest, "retrieved_utc": datetime.now(timezone.utc).isoformat()}
            path.with_suffix(".zip.source.json").write_text(json.dumps(metadata, indent=2) + "\n")
            validate_source(path, year, kind)


def read_rosters(archive: zipfile.ZipFile) -> dict[str, tuple[str, str]]:
    players = {}
    for name in sorted(archive.namelist()):
        if not name.upper().endswith(".ROS"):
            continue
        for row in csv.reader(io.StringIO(archive.read(name).decode("utf-8-sig"))):
            if len(row) < 5:
                raise AlignmentError(f"Malformed roster: {name}")
            hands = (row[3], row[4])
            if row[0] in players and players[row[0]] != hands:
                raise AlignmentError(f"Conflicting roster handedness: {row[0]}")
            players[row[0]] = hands
    if not players:
        raise AlignmentError("No roster handedness found")
    return players


def raw_games(archive: zipfile.ZipFile) -> Iterable[tuple[str, list[RawRecord]]]:
    seen = set()
    for name in sorted(archive.namelist()):
        if not re.search(r"\.EV[ANFR]$", name.upper()):
            continue
        gid, records = None, []
        for number, row in enumerate(csv.reader(io.StringIO(archive.read(name).decode("utf-8-sig"))), 1):
            if not row:
                continue
            if row[0] == "id":
                if gid is not None:
                    yield gid, records
                gid, records = row[1], []
                if gid in seen:
                    raise AlignmentError(f"Duplicate raw game: {gid}")
                seen.add(gid)
            elif gid is None:
                raise AlignmentError(f"Record before game id: {name}:{number}")
            records.append(RawRecord(name, number, tuple(row)))
        if gid is not None:
            yield gid, records


def load_parsed(path: Path, year: int) -> tuple[dict[str, list[dict]], dict]:
    games = defaultdict(list)
    excluded = Counter()
    with zipfile.ZipFile(path) as archive:
        name = f"{year}plays.csv"
        with archive.open(name) as stream:
            reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""))
            if not REQUIRED_PARSED.issubset(reader.fieldnames or ()):
                raise AlignmentError(f"Missing parsed fields: {REQUIRED_PARSED - set(reader.fieldnames or ())}")
            for number, row in enumerate(reader, 2):
                if row["gametype"] != "regular":
                    excluded["nonregular_parsed_rows"] += 1
                    continue
                if None in row or any(v is None for v in row.values()):
                    raise AlignmentError(f"Malformed parsed CSV row {number}")
                row = {key: row[key] for key in REQUIRED_PARSED}
                row["source_row"] = number
                row["source_file"] = name
                games[row["gid"]].append(row)
    for gid, rows in games.items():
        if [int(r["pn"]) for r in rows] != list(range(1, len(rows) + 1)):
            raise AlignmentError(f"Noncontiguous or duplicated parsed key: {gid}")
    return dict(games), dict(excluded)


def pitch_letters(sequence: str) -> list[tuple[int, str]]:
    """Keep source offsets while excluding pickoff/modifier punctuation."""
    invalid = set(sequence) - PITCH_CODES - MARKERS
    if invalid:
        raise AlignmentError(f"Unsupported pitch-string characters: {sorted(invalid)}")
    return [(i, char) for i, char in enumerate(sequence) if char in PITCH_CODES]


def advance_count(balls: int | None, strikes: int | None, symbol: str) -> tuple[int | None, int | None]:
    if balls is None or strikes is None or symbol == "U":
        return None, None
    if symbol in "BIPV":
        return balls + 1, strikes
    if symbol in "ACKLMOQST":
        return balls, strikes + 1
    if symbol in "FR":
        return balls, strikes + (strikes < 2)
    return balls, strikes


def classify_target(symbol: str, terminal_bunt: bool = False, terminal_interference: bool = False) -> dict:
    """Eligibility is current-pitch-specific, never a future whole-PA bunt filter."""
    if symbol in ADMIN:
        raise ValueError("Administrative symbol is not a delivered pitch")
    reason = None
    if terminal_interference:
        reason = "interference_delivery"
    elif symbol in "LMO" or (symbol == "X" and terminal_bunt):
        reason = "bunt_delivery"
    elif symbol in "PQRY":
        reason = "pitchout_delivery"
    elif symbol == "H":
        reason = "hit_by_pitch"
    elif symbol == "I":
        reason = "intentional_delivered_ball"
    elif symbol in "KU":
        reason = "unknown_pitch_or_strike_type"
    elif symbol not in CONVENTIONAL:
        reason = "unsupported_target_symbol"
    swing = int(symbol in SWINGS) if reason is None else None
    contact = int(symbol in CONTACT) if swing == 1 else None
    return {"symbol": symbol, "swing": swing, "contact_given_swing": contact,
            "taxonomy_exclusion": reason, "terminal_bunt_annotation": bool(terminal_bunt),
            "terminal_interference_annotation": bool(terminal_interference)}


def _integer(row: dict, key: str, low: int = 0, high: int | None = None) -> int:
    value = row[key]
    if not re.fullmatch(r"\d+", str(value)):
        raise AlignmentError(f"Invalid integer {key}={value!r}")
    number = int(value)
    if number < low or (high is not None and number > high):
        raise AlignmentError(f"Out-of-range {key}={value!r}")
    return number


def parse_game(gid: str, records: Iterable[RawRecord], parsed: list[dict],
               rosters: dict[str, tuple[str, str]]) -> GameResult:
    """Consume raw records once; parsed terminal outcomes never construct features.

    Official pre/post states validate the raw-timestamped context and supply only
    *completed* event transitions. Any structural mismatch aborts the season.
    Count-quality failures quarantine their PA; unknown U poisons its suffix.
    """
    result = GameResult(gid)
    pitchers, lineups, bat_adj, pit_adj = {}, {}, {}, {}
    pn = pa_no = 0
    half = None
    completed = True
    prefix = ""
    balls = strikes = 0
    outs, bases, score = 0, ["", "", ""], [0, 0]
    pending_runners = {}
    previous, pa_indices, pa_pitchers, pa_reasons = [], [], set(), set()
    pa_raw_prefixes, pa_pitcher_prefixes, batter_replacements = set(), set(), set()
    date, htbf = gid[3:11], False
    pending_suspension = None

    def issue(reason: str, rec: RawRecord, details=None, whole_pa=True):
        result.stats[reason] += 1
        result.issues.append({"gid": gid, "pa": pa_no, "parsed_pn": pn,
            "raw_file": rec.source_file, "raw_row": rec.source_row,
            "reason": reason, "details": details})
        if whole_pa:
            pa_reasons.add(reason)

    def close_pa():
        if pa_reasons:
            result.stats["quarantined_pas"] += 1
            for index in pa_indices:
                result.pitches[index]["qa_exclusions"] = sorted(set(result.pitches[index]["qa_exclusions"]) | pa_reasons)
        if len(pa_pitchers) > 1:
            result.stats["pa_with_multiple_pitchers"] += 1

    for rec in records:
        r = rec.fields
        kind = r[0]
        if kind == "info":
            if r[1] == "date":
                date = r[2].replace("/", "")
            elif r[1] == "htbf":
                htbf = r[2] == "true"
            continue
        if kind == "com":
            if len(r) > 1 and r[1].startswith("suspended,"):
                resumed = r[1].split(",")[1]
                if not re.fullmatch(r"\d{8}", resumed):
                    raise AlignmentError(f"Invalid resumed date in {gid}")
                pending_suspension = (date, resumed)
                date = resumed
                result.stats["suspended_resume_boundaries"] += 1
            continue
        if kind in {"start", "sub"}:
            if len(r) != 6:
                raise AlignmentError(f"Malformed {kind}: {gid}")
            player, side, slot, position = r[1], r[3], r[4], r[5]
            old = lineups.get((side, slot))
            lineups[side, slot] = player
            if kind == "sub" and old:
                bases = [player if runner == old else runner for runner in bases]
                if position == "11" and strikes == 2:
                    batter_replacements.add((old, player))
            if position == "1":
                pitchers[side] = player
            continue
        if kind in {"badj", "padj"}:
            if len(r) != 3 or r[2] not in {"L", "R"}:
                raise AlignmentError(f"Unsupported hand adjustment in {gid}: {r}")
            (bat_adj if kind == "badj" else pit_adj)[r[1]] = r[2]
            result.stats[kind + "_records"] += 1
            continue
        if kind == "radj":
            if len(r) != 3 or r[2] not in {"1", "2", "3"}:
                raise AlignmentError(f"Unsupported runner adjustment: {r}")
            pending_runners[int(r[2]) - 1] = r[1]
            continue
        if kind != "play":
            continue
        if len(r) != 7:
            raise AlignmentError(f"Malformed play record: {gid}:{rec.source_row}")
        _, inning_s, side, batter, source_count, sequence, event = r
        if side not in {"0", "1"} or not inning_s.isdigit() or int(inning_s) < 1:
            raise AlignmentError(f"Invalid raw half-inning: {gid}")
        inning = int(inning_s)
        new_half = (inning, side) != half
        if completed or new_half:
            if pa_no:
                close_pa()
            if new_half:
                outs, bases = 0, ["", "", ""]
            pa_no += 1
            prefix, balls, strikes = "", 0, 0
            previous, pa_indices, pa_pitchers, pa_reasons = [], [], set(), set()
            pa_raw_prefixes, pa_pitcher_prefixes, batter_replacements = set(), set(), set()
            completed = False
            result.stats["pa_started"] += 1
        half = (inning, side)
        for base, runner in pending_runners.items():
            bases[base] = runner
        pending_runners.clear()
        candidate = parsed[pn] if pn < len(parsed) else None
        is_np = event == "NP"
        retained_np = is_np and candidate is not None and all(
            str(candidate[k]) == value for k, value in
            (("event", event), ("batter", batter), ("pitches", sequence)))
        p = None
        if not is_np or retained_np:
            if candidate is None:
                raise AlignmentError(f"Missing parsed record: {gid}:{pn + 1}")
            p = candidate
            pn += 1
            credited_batter = (p["batter"] != batter and p["k"] == "1" and
                (p["batter"], batter) in batter_replacements and
                (p["pitches"] == sequence or (p["batter"], p["pitches"]) in pa_raw_prefixes))
            credited_pitcher = (p["pitcher"] != pitchers.get(str(1 - int(side))) and
                p["walk"] == "1" and p["batter"] == batter and
                (batter, p["pitches"], p["pitcher"]) in pa_pitcher_prefixes)
            if p["pitcher"] != pitchers.get(str(1 - int(side))) and not credited_pitcher:
                raise AlignmentError(f"Unproved parsed pitcher attribution mismatch: {gid}:{pn}")
            expected = {"gid": gid, "pn": str(pn), "event": event,
                        "inning": inning_s, "vis_home": side}
            if credited_batter:
                result.stats["parsed_strikeout_attribution_retains_replaced_batter"] += 1
            elif credited_pitcher:
                result.stats["parsed_walk_attribution_retains_replaced_pitcher_prefix"] += 1
                expected.update(batter=batter)
            else:
                expected.update(batter=batter, pitches=sequence)
            if any(str(p[k]) != value for k, value in expected.items()):
                diff = {k: [value, p[k]] for k, value in expected.items() if str(p[k]) != value}
                raise AlignmentError(f"Raw/parsed alignment mismatch {gid}:{pn}: {diff}")
            result.stats["aligned_parsed_rows"] += 1
            if retained_np:
                result.stats["retained_np_rows"] += 1
            pre = (_integer(p, "outs_pre", high=2), [p[f"br{i}_pre"] for i in range(1, 4)],
                   [_integer(p, "score_v"), _integer(p, "score_h")])
            if (outs, bases, score) != pre:
                raise AlignmentError(f"Pre-state mismatch {gid}:{pn}: raw={(outs, bases, score)}, parsed={pre}")
            if p["date"] != date:
                raise AlignmentError(f"Event-date mismatch {gid}:{pn}: raw={date}, parsed={p['date']}")
            parsed_count = (_integer(p, "balls", high=3), _integer(p, "strikes", high=2))
            if source_count not in {"", "??"} and source_count != f"{parsed_count[0]}{parsed_count[1]}":
                if credited_batter or credited_pitcher:
                    result.stats["attribution_record_count_differs_from_actual_raw_count"] += 1
                else:
                    issue("raw_parsed_count_disagreement", rec, [source_count, parsed_count])
        else:
            result.stats["omitted_np_rows"] += 1
        result.stats["raw_play_rows"] += 1
        pa_raw_prefixes.add((batter, sequence))
        pa_pitcher_prefixes.add((batter, sequence, pitchers.get(str(1 - int(side)))))
        if not sequence:
            result.stats["empty_pitch_string_raw_rows"] += 1
            if p is not None:
                result.stats["empty_pitch_string_parsed_rows"] += 1

        coded = pitch_letters(sequence)
        letters = "".join(symbol for _, symbol in coded)
        if not letters.startswith(prefix):
            # Retrosheet occasionally replaces/removes an N annotation when a
            # no-delivery runner event is rewritten as a pickoff marker. N has
            # no count or target effect; never normalize A/V or delivered codes.
            if letters.replace("N", "").startswith(prefix.replace("N", "")):
                prefix = prefix.replace("N", "")
                coded = [(offset, symbol) for offset, symbol in coded if symbol != "N"]
                letters = letters.replace("N", "")
                result.stats["no_pitch_prefix_normalizations"] += 1
            else:
                raise AlignmentError(f"Noncumulative pitch prefix: {gid}:{pn}: {prefix!r} -> {letters!r}")
        result.stats["duplicate_prefix_symbols_removed"] += len(prefix)
        new_coded = coded[len(prefix):]
        prefix = letters
        ambiguous_date = pending_suspension if any(symbol not in ADMIN for _, symbol in new_coded) else None
        if ambiguous_date:
            issue("ambiguous_suspension_prefix_timing", rec,
                {"date_min": ambiguous_date[0], "date_max": ambiguous_date[1],
                 "source_record_date": date}, whole_pa=False)
        # Only this first post-boundary raw record can materialize an unseen
        # prior-day prefix. Already emitted pitches retain their prior dates;
        # subsequent record order resumes a dated, known cumulative prefix.
        pending_suspension = None
        pitcher = pitchers.get(str(1 - int(side)))
        if pitcher not in rosters or batter not in rosters:
            raise AlignmentError(f"Missing active pitcher/batter roster: {gid}: {pitcher}/{batter}")
        pitch_hand = pit_adj.get(pitcher, rosters[pitcher][1])
        roster_bat_hand = rosters[batter][0]
        bat_hand = bat_adj.get(batter, roster_bat_hand)
        hand_method = "raw_adjustment" if batter in bat_adj else "roster"
        if bat_hand == "B":
            bat_hand = {"L": "R", "R": "L"}.get(pitch_hand)
            hand_method = "switch_hitter_opposite_pitcher_inference"
        hand_problem = pitch_hand not in {"L", "R"} or bat_hand not in {"L", "R"}
        if p is not None:
            if p["pitcher"] != pitcher:
                result.stats["parsed_pitcher_differs_from_active_raw_pitcher"] += 1
            # Parsed bathand can retain B: it is not always an actual-side measure.
            if p["pitcher"] == pitcher and p["pithand"] != pitch_hand:
                issue("pitcher_hand_conflict", rec, [pitch_hand, p["pithand"]])
            if p["batter"] == batter and p["bathand"] in {"L", "R"} and p["bathand"] != bat_hand:
                issue("batter_hand_conflict", rec, [bat_hand, p["bathand"]])
        before_last = (balls, strikes)
        for delta_index, (offset, symbol) in enumerate(new_coded):
            before_last = (balls, strikes)
            result.stats["incremental_symbols"] += 1
            if symbol in ADMIN:
                result.stats["administrative_" + symbol] += 1
            else:
                result.stats["delivered_pitch_symbols"] += 1
                pa_pitchers.add(pitcher)
                if len(pa_pitchers) > 1:
                    result.stats["pitches_after_midpa_pitcher_change"] += 1
                quality = []
                if balls is None or strikes is None:
                    quality.append("count_unknown_after_U")
                elif not (0 <= balls <= 3 and 0 <= strikes <= 2):
                    quality.append("impossible_pre_pitch_count")
                    pa_reasons.add("impossible_pre_pitch_count")
                if hand_problem:
                    quality.append("unresolved_handedness")
                if ambiguous_date:
                    quality.append("ambiguous_suspension_prefix_timing")
                    result.stats["ambiguous_suspension_deliveries"] += 1
                features = dict(zip(FEATURE_FIELDS, (
                    inning, int(side), int(side) ^ int(htbf), outs,
                    bool(bases[0]), bool(bases[1]), bool(bases[2]), score[0], score[1],
                    score[int(side)] - score[1 - int(side)], balls, strikes, batter,
                    pitcher, bat_hand, pitch_hand, hand_method, len(previous) + 1,
                    previous[-1] if previous else "START", tuple(previous[-3:]))))
                terminal_symbol = delta_index == len(new_coded) - 1
                bunt = bool(symbol == "X" and terminal_symbol and p is not None and p["bunt"] == "1")
                interference = bool(terminal_symbol and p is not None and
                    (p.get("xi") == "1" or "/BINT" in event))
                target = classify_target(symbol, bunt, interference)
                lineage = {"gid": gid, "pa": pa_no,
                    "event_date": None if ambiguous_date else date,
                    "event_date_min": ambiguous_date[0] if ambiguous_date else date,
                    "event_date_max": ambiguous_date[1] if ambiguous_date else date,
                    "event_date_status": "ambiguous_suspension_prefix" if ambiguous_date else "raw_record_date",
                    "source_record_date": date,
                    "raw_file": rec.source_file, "raw_row": rec.source_row,
                    "raw_symbol_offset": offset, "cumulative_symbol_index": len(coded) - len(new_coded) + delta_index,
                    "parsed_pn": pn if p is not None else None,
                    "parsed_file": p.get("source_file") if p else None,
                    "parsed_source_row": p.get("source_row") if p else None}
                result.pitches.append({"lineage": lineage, "features": features,
                    "target": target, "qa_exclusions": quality})
                pa_indices.append(len(result.pitches) - 1)
                previous.append("BUNT_IN_PLAY" if bunt else symbol)
            balls, strikes = advance_count(balls, strikes, symbol)
        expected_count = (balls, strikes) if (is_np or not new_coded or
            (sequence and sequence[-1] not in PITCH_CODES and p is not None and p["pa"] != "1")) else before_last
        if source_count not in {"", "??"}:
            if not re.fullmatch(r"[0-3][0-2]", source_count):
                issue("invalid_source_count", rec, source_count)
            elif None not in expected_count and tuple(map(int, source_count)) != expected_count:
                reason = KNOWN_ANOMALIES.get((gid, pn), "source_count_conflict")
                issue(reason, rec, {"source_count": source_count, "reconstructed": expected_count})
        else:
            result.stats["source_count_not_available"] += 1
        # Terminal checks are QA/target annotations, never part of features.
        terminal_check = "not_pa_terminal"
        if p is not None and p["pa"] == "1":
            terminal_check = "consistent"
            last = letters[-1:] if letters else ""
            administrative_other_out = (not pa_indices and last == "V" and balls == 4 and p["walk"] != "1")
            early_walk = p["walk"] == "1" and letters and balls is not None and balls < 4
            inconsistent = ((last in {"X", "Y"} and p["bip"] != "1" and p.get("hr") != "1" and p.get("xi") != "1") or
                (last == "H" and p["hbp"] != "1") or
                (last in {"B", "I", "V"} and balls == 4 and p["walk"] != "1" and not administrative_other_out) or
                (strikes == 3 and p["k"] != "1") or
                (p["k"] == "1" and letters and strikes is not None and strikes != 3) or
                (p["walk"] == "1" and letters and balls is not None and balls > 4) or
                ((p["bip"] == "1" or p.get("hr") == "1") and last and last not in {"X", "Y", "U"}
                 and "/BINT" not in event and not administrative_other_out))
            if early_walk:
                terminal_check = "exceptional_adjudication"
                issue("terminal_walk_before_ball_four", rec, {"balls": balls, "event": event})
            if administrative_other_out:
                # E.g. four automatic intentional balls followed by an appeal
                # for failing to touch first. There is no pitch response label.
                terminal_check = "administrative_no_delivery_nonwalk_outcome"
                result.stats["administrative_no_delivery_nonwalk_outcomes"] += 1
            if inconsistent:
                terminal_check = "conflict"
                issue("terminal_outcome_conflict", rec, {"last_symbol": last, "event": event})
        result.events.append({"gid": gid, "pa": pa_no, "raw_file": rec.source_file,
            "raw_row": rec.source_row, "parsed_pn": pn if p else None,
            "parsed_source_row": p.get("source_row") if p else None,
            "source_count": source_count, "reconstructed_source_count": expected_count,
            "raw_sequence": sequence, "terminal_event": event,
            "terminal_target_check": terminal_check,
            "retained_np": bool(retained_np), "omitted_np": bool(is_np and not retained_np)})
        if p is not None:
            outs = _integer(p, "outs_post", high=3)
            bases = [p[f"br{i}_post"] for i in range(1, 4)]
            score[int(side)] += _integer(p, "runs")
            completed = p["pa"] == "1" or outs == 3
            if completed:
                bat_adj.clear()
                pit_adj.clear()
                result.stats["pa_completed_or_inning_ended"] += 1
            # Some 2023 parsed files split inherited-strikeout attribution into
            # a credited K row and a generated NP row for the actual hitter.
            # The latter has no raw event. Consume it only under this exact
            # identity/prefix/substitution/no-state-change proof.
            adjunct = parsed[pn] if pn < len(parsed) else None
            if credited_batter and adjunct is not None and adjunct["event"] == "NP":
                identity_ok = all(str(adjunct[k]) == value for k, value in (
                    ("batter", batter), ("pitches", sequence), ("inning", inning_s),
                    ("vis_home", side), ("date", date), ("pa", "0"), ("runs", "0")))
                state_ok = (str(adjunct["outs_pre"]) == str(outs) == str(adjunct["outs_post"]) and
                    [adjunct[f"br{i}_pre"] for i in range(1, 4)] == bases ==
                    [adjunct[f"br{i}_post"] for i in range(1, 4)] and
                    [int(adjunct["score_v"]), int(adjunct["score_h"])] == score)
                if identity_ok and state_ok:
                    pn += 1
                    result.stats["aligned_parsed_rows"] += 1
                    result.stats["generated_attribution_np_rows"] += 1
                    result.events.append({"gid": gid, "pa": pa_no,
                        "raw_file": rec.source_file, "raw_row": rec.source_row,
                        "parsed_pn": pn, "parsed_source_row": adjunct.get("source_row"),
                        "origin": "official_attribution_bookkeeping_no_raw_event",
                        "terminal_event": "NP", "raw_sequence": sequence})
    if pa_no:
        close_pa()
        if not completed:
            result.stats["right_censored_pa_at_game_end"] += 1
    if pn != len(parsed):
        raise AlignmentError(f"Unconsumed parsed records: {gid}: {pn}/{len(parsed)}")
    for pitch in result.pitches:
        good = not pitch["qa_exclusions"] and pitch["target"]["taxonomy_exclusion"] is None
        pitch["eligibility"] = {"swing": good,
            "contact_given_swing": good and pitch["target"]["swing"] == 1}
    return result


def _distribution_rows(counters: dict) -> list[dict]:
    output = []
    for (context, value, target), counts in sorted(counters.items()):
        n = sum(counts.values())
        output.append({"context": context, "value": value, "target": target,
            "denominator": n, "positive_count": counts[1], "negative_count": counts[0],
            "observed_fraction": counts[1] / n if n else None,
            "kind": "development_observed_frequency", "unit": "delivered_pitch",
            "season": 2023})
    return output


def run_season(raw_path: Path, parsed_path: Path, year: int, output: Path) -> dict:
    """Write rows under ignored data only. Later years expose QA counts, not patterns."""
    source_meta = [validate_source(raw_path, year, "eve"), validate_source(parsed_path, year, "plays")]
    games, excluded = load_parsed(parsed_path, year)
    stats, qa_exclusions, taxonomy_exclusions = Counter(), Counter(), Counter()
    distribution = defaultdict(Counter)
    date_min, date_max = "99999999", "00000000"
    output.mkdir(parents=True, exist_ok=True)
    paths = {kind: output / f"{year}_{kind}.jsonl.gz" for kind in ("pitches", "events", "issues")}
    temporary = {kind: p.with_suffix(p.suffix + ".partial") for kind, p in paths.items()}
    streams = {kind: io.TextIOWrapper(gzip.GzipFile(filename=p, mode="wb", compresslevel=6, mtime=0),
                                     encoding="utf-8") for kind, p in temporary.items()}
    seen = set()
    try:
        with zipfile.ZipFile(raw_path) as archive:
            rosters = read_rosters(archive)
            for gid, records in raw_games(archive):
                if gid not in games:
                    raise AlignmentError(f"Raw game absent from regular parsed archive: {gid}")
                result = parse_game(gid, records, games[gid], rosters)
                seen.add(gid)
                stats.update(result.stats)
                stats["games"] += 1
                for kind in streams:
                    rows = getattr(result, kind)
                    for row in rows:
                        streams[kind].write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
                for row in result.pitches:
                    date_min = min(date_min, row["lineage"]["event_date_min"])
                    date_max = max(date_max, row["lineage"]["event_date_max"])
                    qa_exclusions.update(row["qa_exclusions"])
                    reason = row["target"]["taxonomy_exclusion"]
                    if reason:
                        taxonomy_exclusions[reason] += 1
                    if row["qa_exclusions"]:
                        stats["qa_quarantined_deliveries"] += 1
                    for target in ("swing", "contact_given_swing"):
                        if not row["eligibility"][target]:
                            continue
                        stats["eligible_" + target] += 1
                        if year == 2023:
                            f = row["features"]
                            contexts = {"all": "all", "count": f"{f['balls']}-{f['strikes']}",
                                "handedness": f"{f['batter_hand']}/{f['pitcher_hand']}",
                                "outs": str(f["outs"]), "previous_pitch_outcome": f["previous_pitch_outcome"],
                                "base_occupancy": "".join(str(int(f[k])) for k in ("on_first", "on_second", "on_third"))}
                            for name, value in contexts.items():
                                distribution[name, value, target][row["target"][target]] += 1
        if seen != set(games):
            raise AlignmentError(f"Parsed games missing raw source: {sorted(set(games) - seen)}")
        expected_games = {2023: 2430, 2024: 2429, 2025: 2430}[year]
        if stats["games"] != expected_games:
            raise AlignmentError(f"Pinned season game coverage changed: {year}")
        if year == 2025:
            reference = {"aligned_parsed_rows": 189939, "delivered_pitch_symbols": 710079,
                "omitted_np_rows": 26906, "retained_np_rows": 628,
                "duplicate_prefix_symbols_removed": 15251,
                "pitches_after_midpa_pitcher_change": 171, "pa_with_multiple_pitchers": 64}
            if any(stats[key] != value for key, value in reference.items()):
                raise AlignmentError("Production 2025 expansion differs from independently recorded source QA")
    finally:
        for stream in streams.values():
            stream.close()
    for kind, path in temporary.items():
        path.replace(paths[kind])
    return {"season": year, "role": "development_descriptive" if year == 2023 else "QA_only",
        "sources": source_meta, "event_date_min": date_min, "event_date_max": date_max,
        "denominators": dict(sorted(stats.items())), "source_exclusions": excluded,
        "qa_exclusion_delivery_counts_nonexclusive": dict(sorted(qa_exclusions.items())),
        "taxonomy_exclusion_delivery_counts": dict(sorted(taxonomy_exclusions.items())),
        "development_distributions": _distribution_rows(distribution) if year == 2023 else [],
        "local_derivatives": {k: {"path": str(p), "sha256": sha256(p)} for k, p in paths.items()}}


def run(root: Path, years: tuple[int, ...] = (2023, 2024, 2025)) -> dict:
    if not years or any(y not in (2023, 2024, 2025) for y in years) or len(set(years)) != len(years):
        raise ValueError("Supported unique seasons are 2023, 2024 and 2025")
    local = root / "data/tactical/baseball"
    seasons = []
    for year in years:
        seasons.append(run_season(source_path(root, year, "eve"), source_path(root, year, "plays"), year, local))
    summary = {"schema_version": 1, "parser_version": VERSION, "sport": "baseball",
        "parser_sha256": sha256(Path(__file__)),
        "task": "pitch_outcome_count_sequence_tendency", "phase": "descriptive",
        "population": "MLB regular-season Retrosheet records; current-pitch conventional swing/take eligibility",
        "time": {"seasons": list(years), "development_season": 2023,
            "feature_cutoff": "before each delivered pitch", "publication_time": "retrospective official archives",
            "later_years": "eligibility and measurement QA only; no context target patterns or predictive scores"},
        "units": {"observation": "delivered_pitch", "count": "balls/strikes", "score": "runs",
            "context": "categorical occupancy, outs, inning, identity, handedness and prior pitch outcomes"},
        "targets": {"swing": "swing indicator among conventional identified BC FSTX pitches, excluding in-play bunts",
            "contact_given_swing": "bat-ball contact among eligible FSTX swings; foul tips count as contact"},
        "feature_allowlist": list(FEATURE_FIELDS), "seasons": seasons,
        "development_distributions": next((s["development_distributions"] for s in seasons if s["season"] == 2023), []),
        "measurement_caveats": [
            "Pitch outcomes/count context only: no pitch type, velocity, location, stance, bat path or body mechanics",
            "Annual retrospective annotations do not establish a historical live feed or causal coaching effect",
            "Switch-hitter batting side uses roster-opposite-pitcher inference unless raw badj overrides; method is retained",
            "Raw substitutions identify the active pitcher; parsed pitcher may instead be a responsibility assignment",
            "Eligibility uses the current realized pitch category and is a conditional retrospective denominator",
            "Unknown U poisons count downstream within its PA; count contradictions quarantine the PA without clipping",
            "Raw/parsed agreement establishes same-provider representation consistency, not independent physical measurement accuracy",
            "First post-suspension records may materialize earlier pitches: newly emitted deliveries retain a date interval and are excluded if timing is ambiguous",
            "Whole-game dependence and sparse context cells preclude treating observed fractions as calibrated predictions",
            "2024/2025 source QA was inspected; no predictive fit, score, candidate selection or performance-blind claim is made"],
        "source_notice": NOTICE, "source_specification": SPEC_URL,
        "release_scope": "local-only raw/row derivatives; source-specific aggregate release review required",
        "predictive_gate": {"status": "closed", "fitting_allowed": False,
            "reason": "Exact numerical protocol requires independent review and project-owner approval before fitting"}}
    report = root / "reports/tactical/baseball/summary.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    tmp = report.with_suffix(".json.partial")
    tmp.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    tmp.replace(report)
    (local / "RETROSHEET_NOTICE.txt").write_text(NOTICE + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--years", type=int, nargs="+", default=[2023, 2024, 2025])
    parser.add_argument("--fetch-missing", action="store_true",
        help="Explicitly fetch missing official archives only if their bytes match the pinned hashes")
    args = parser.parse_args()
    if args.fetch_missing:
        if any(y not in (2023, 2024, 2025) for y in args.years):
            parser.error("Only pinned 2023–2025 archives may be fetched")
        fetch_missing_sources(args.root.resolve(), tuple(args.years))
    summary = run(args.root.resolve(), tuple(args.years))
    print(json.dumps({"phase": summary["phase"], "sport": summary["sport"],
        "seasons": [{"season": s["season"], "denominators": s["denominators"]} for s in summary["seasons"]]}, indent=2))


if __name__ == "__main__":
    main()
