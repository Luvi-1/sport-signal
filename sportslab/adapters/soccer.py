"""Pinned OpenFootball English Premier League results, with audited normalization.

The JSON data and source license are CC0-1.0; see ``docs/sources/soccer.md``.
This module supplies results only, never model features or synthetic matches.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

import pandas as pd


SOURCE_COMMIT = "e6744429ee395bc86f247348c6184bb08d4eb361"
TEXT_SOURCE_COMMIT = "b17e8f01707d83d2ce1790c14d4a5eeb35987825"
SOURCE_BASE = f"https://raw.githubusercontent.com/openfootball/football.json/{SOURCE_COMMIT}"
TEXT_SOURCE_BASE = f"https://raw.githubusercontent.com/openfootball/england/{TEXT_SOURCE_COMMIT}"
SEASONS = tuple(f"{year}-{str(year + 1)[2:]}" for year in range(2015, 2025))
COLUMNS = [
    "event_id", "date", "season", "side_a", "side_b", "score_a", "score_b",
    "neutral", "available_date",
]


def download(raw_dir: Path) -> list[Path]:
    """Fetch ten immutable season files plus source/license audit evidence.

    ``raw_dir`` is the soccer-specific raw-data directory. The shared fetcher
    preserves downloaded bytes and records SHA256 provenance alongside files.
    """
    from sportslab.data import fetch

    raw_dir = Path(raw_dir)
    paths = [
        fetch(f"{SOURCE_BASE}/{season}/en.1.json", raw_dir / f"en.1-{season}.json")
        for season in SEASONS
    ]
    paths.append(fetch(f"{SOURCE_BASE}/LICENSE.md", raw_dir / "LICENSE.openfootball-json.md"))
    paths.append(fetch(
        f"{TEXT_SOURCE_BASE}/2019-20/1-premierleague.txt",
        raw_dir / "2019-20-source-date-audit.txt",
    ))
    paths.append(fetch(f"{TEXT_SOURCE_BASE}/LICENSE.md", raw_dir / "LICENSE.openfootball-england.md"))
    return paths


def _team_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected a nonempty team name, got {value!r}")
    # The source adds " FC" to many existing club names from 2020-21 onward.
    # Preserve AFC Bournemouth and Sunderland AFC; do not fuzzy-match identities.
    name = value.strip().removesuffix(" FC")
    if not name:
        raise ValueError("Team name is empty after normalization")
    return name


def _match_date(value: object, season: str, round_name: object) -> tuple[pd.Timestamp, bool]:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"Expected an ISO match date, got {value!r}")
    date = pd.Timestamp(value).normalize()
    corrected = False
    # The pinned JSON incorrectly assigns July 2020 to July 2019. These 66
    # matches are confirmed against the original TXT and its weekday labels.
    # Never generalize this correction to other seasons or arbitrary rounds.
    if (season == "2019-20" and "2019-07-01" <= value <= "2019-07-26"
            and round_name in {f"Matchday {n}" for n in range(32, 39)}):
        date = date.replace(year=2020)
        corrected = True
    start_year = int(season[:4])
    if not pd.Timestamp(start_year, 8, 1) <= date <= pd.Timestamp(start_year + 1, 7, 31):
        raise ValueError(f"Date {value!r} falls outside the supported {season} season window")
    return date, corrected


def _full_time_score(match: dict) -> tuple[float, float] | None:
    score = match.get("score")
    if score is None:
        return None
    if not isinstance(score, dict):
        raise ValueError("Expected a score object")
    full_time = score.get("ft")
    if full_time is None:
        return None
    if not isinstance(full_time, list) or len(full_time) != 2:
        raise ValueError(f"Expected two full-time scores, got {full_time!r}")
    if any(value is None for value in full_time):
        return None
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        or not math.isfinite(value) or value < 0 or value != int(value)
        for value in full_time
    ):
        raise ValueError(f"Invalid full-time score: {full_time!r}")
    return float(full_time[0]), float(full_time[1])


def load(raw_dir: Path) -> pd.DataFrame:
    """Normalize completed fixtures found in the configured ten season files.

    Home team is side A; away team is side B. Results become available on the
    recorded match date, at day precision. Consumers must freeze all features
    before a date's results, because intraday result availability is unknown.
    Invalid scored records and repeated season/home/away pairs fail loudly.
    Unplayed fixtures and incomplete scores are omitted, never imputed.
    """
    raw_dir = Path(raw_dir)
    records: list[dict] = []
    loaded_files: list[str] = []
    skipped = 0
    date_corrections = 0
    for season in SEASONS:
        path = raw_dir / f"en.1-{season}.json"
        if not path.is_file():
            continue
        loaded_files.append(path.name)
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not isinstance(data.get("matches"), list):
            raise ValueError(f"{path.name}: expected a top-level matches list")
        for index, match in enumerate(data["matches"]):
            try:
                if not isinstance(match, dict):
                    raise ValueError("Expected a match object")
                scores = _full_time_score(match)
                if scores is None:
                    skipped += 1
                    continue
                side_a = _team_name(match.get("team1"))
                side_b = _team_name(match.get("team2"))
                if side_a == side_b:
                    raise ValueError("A team cannot play itself")
                date, corrected = _match_date(match.get("date"), season, match.get("round"))
                date_corrections += int(corrected)
                # EPL has one home fixture per ordered pair per season. Keeping
                # scores and date out of the identity makes it stable on a
                # result correction or rescheduling without merging reverse legs.
                identity = json.dumps([side_a, side_b], ensure_ascii=False, separators=(",", ":"))
                digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
                records.append({
                    "event_id": f"soccer:en.1:{season}:{digest}",
                    "date": date,
                    "season": season,
                    "side_a": side_a,
                    "side_b": side_b,
                    "score_a": scores[0],
                    "score_b": scores[1],
                    "neutral": False,
                    "available_date": date,
                })
            except (ValueError, TypeError, OverflowError) as exc:
                raise ValueError(f"{path.name}, match {index}: {exc}") from exc
    if not loaded_files:
        raise FileNotFoundError(f"No supported OpenFootball season files in {raw_dir}; run download first")
    if not records:
        raise ValueError("No completed matches with full-time scores were found")
    frame = pd.DataFrame.from_records(records, columns=COLUMNS)
    if frame["event_id"].duplicated().any():
        duplicates = frame.loc[frame["event_id"].duplicated(), "event_id"].tolist()
        raise ValueError(f"Duplicate soccer fixture identities: {duplicates[:3]}")
    frame = frame.sort_values(["date", "event_id"]).reset_index(drop=True)
    frame.attrs.update({
        "source": "OpenFootball football.json",
        "source_commit": SOURCE_COMMIT,
        "license": "CC0-1.0",
        "loaded_files": loaded_files,
        "skipped_incomplete_matches": skipped,
        "corrected_july_2020_dates": date_corrections,
    })
    return frame
