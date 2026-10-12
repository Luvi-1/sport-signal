"""Retrosheet regular-season game logs, 2015–2024.

The information used here was obtained free of charge from and is copyrighted
by Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".
Dataset terms: https://www.retrosheet.org/notice.txt (separate from code license).
"""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path
import re
from zipfile import ZipFile

import pandas as pd

YEARS = tuple(range(2015, 2025))
SOURCE_URL = "https://www.retrosheet.org/gamelogs/gl{year}.zip"
COLUMNS = [
    "event_id", "date", "season", "side_a", "side_b", "score_a", "score_b",
    "neutral", "available_date",
]
_MAX_MEMBER_BYTES = 20_000_000


def download(raw_dir: Path) -> list[Path]:
    """Fetch the ten official annual archives using the shared provenance helper."""
    from sportslab.data import fetch

    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    return [
        fetch(SOURCE_URL.format(year=year), raw_dir / f"gl{year}.zip")
        for year in YEARS
    ]


def _date(value: str, context: str) -> pd.Timestamp:
    if not re.fullmatch(r"\d{8}", value):
        raise ValueError(f"Invalid Retrosheet date {value!r} in {context}")
    try:
        return pd.to_datetime(value, format="%Y%m%d", errors="raise").normalize()
    except (ValueError, OverflowError) as error:
        raise ValueError(f"Invalid Retrosheet date {value!r} in {context}") from error


def _score(value: str) -> float | None:
    try:
        score = float(value)
    except ValueError:
        return None
    if not math.isfinite(score) or score < 0 or not score.is_integer():
        return None
    return score


def load(raw_dir: Path) -> pd.DataFrame:
    """Load existing annual archives into one row per decided regular-season game.

    Only exact gl2015.zip ... gl2024.zip names are considered. Each archive must
    contain one correspondingly named GLYYYY.TXT member. Members are streamed,
    never extracted. Missing/invalid scores, tied scores, and forfeits/no-decisions
    are excluded. Suspended games become available on their completion date.
    The returned frame's ``attrs['exclusions']`` records exclusion counts.
    """
    raw_dir = Path(raw_dir)
    archives = [(year, raw_dir / f"gl{year}.zip") for year in YEARS]
    archives = [(year, path) for year, path in archives if path.is_file()]
    if not archives:
        raise FileNotFoundError(f"No supported Retrosheet annual archives in {raw_dir}")

    records: list[dict] = []
    exclusions = {"missing_or_invalid_scores": 0, "ties": 0, "forfeits_or_no_decisions": 0}
    source_rows = 0
    seen_ids: set[str] = set()
    delayed_results = 0

    for year, path in archives:
        with ZipFile(path) as archive:
            expected = f"gl{year}.txt"
            members = [item for item in archive.infolist() if item.filename.lower() == expected]
            if len(members) != 1:
                raise ValueError(f"Expected exactly one {expected} member in {path.name}")
            member = members[0]
            if member.file_size > _MAX_MEMBER_BYTES:
                raise ValueError(f"Oversized Retrosheet data member in {path.name}")
            with archive.open(member) as stream:
                reader = csv.reader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""))
                for row_number, row in enumerate(reader, start=1):
                    if not row or all(not value.strip() for value in row):
                        continue
                    context = f"{path.name}:{row_number}"
                    if len(row) != 161:
                        raise ValueError(f"Expected 161 Retrosheet fields in {context}, got {len(row)}")
                    source_rows += 1
                    date = _date(row[0], context)
                    if date.year != year:
                        raise ValueError(f"Game date does not match archive year in {context}")
                    game_number = row[1].strip()
                    if game_number not in {"0", "1", "2", "3", "A", "B"}:
                        raise ValueError(f"Invalid game number in {context}: {game_number!r}")
                    away, home = row[3].strip(), row[6].strip()
                    if not re.fullmatch(r"[A-Z0-9]{2,3}", away) or not re.fullmatch(r"[A-Z0-9]{2,3}", home) or home == away:
                        raise ValueError(f"Invalid home/away team identifiers in {context}")
                    event_id = f"retrosheet:{home}{row[0]}{game_number}"
                    if event_id in seen_ids:
                        raise ValueError(f"Duplicate Retrosheet event_id {event_id} in {context}")
                    seen_ids.add(event_id)

                    # The score alone can misrepresent a forfeited game's winner.
                    if row[14].strip():
                        exclusions["forfeits_or_no_decisions"] += 1
                        continue
                    away_score, home_score = _score(row[9]), _score(row[10])
                    if away_score is None or home_score is None:
                        exclusions["missing_or_invalid_scores"] += 1
                        continue
                    if away_score == home_score:
                        exclusions["ties"] += 1
                        continue

                    available_date = date
                    if row[13].strip():
                        available_date = _date(row[13].split(",", 1)[0], context)
                        if available_date < date:
                            raise ValueError(f"Completion date precedes start date in {context}")
                    delayed_results += int(available_date > date)
                    records.append({
                        "event_id": event_id,
                        "date": date,
                        "season": str(year),
                        "side_a": home,
                        "side_b": away,
                        "score_a": home_score,
                        "score_b": away_score,
                        # Retrosheet records designated home/away, not a neutral flag.
                        "neutral": False,
                        "available_date": available_date,
                    })

    frame = pd.DataFrame.from_records(records, columns=COLUMNS)
    frame["date"] = pd.to_datetime(frame["date"])
    frame["available_date"] = pd.to_datetime(frame["available_date"])
    frame["score_a"] = frame["score_a"].astype(float)
    frame["score_b"] = frame["score_b"].astype(float)
    frame["neutral"] = frame["neutral"].astype(bool)
    frame = frame.sort_values(["date", "event_id"], kind="stable").reset_index(drop=True)
    frame.attrs.update({
        "source": "Retrosheet annual regular-season game logs",
        "source_rows": source_rows,
        "exclusions": exclusions,
        "delayed_results": delayed_results,
        "years_loaded": [year for year, _ in archives],
    })
    return frame
