"""Jeff Sackmann / Tennis Abstract ATP singles, preserved immutable snapshot.

Source data: CC BY-NC-SA 4.0, separate from the project's code license.
See docs/sources/tennis.md for attribution, exclusions, and date limitations.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
import re

import pandas as pd

YEARS = tuple(range(2010, 2025))
SOURCE_REPOSITORY = "https://github.com/Kadantte/tennis_atp"
SOURCE_COMMIT = "712be0c5ade693cdab9e69c23a71a0edf5a23c44"
SOURCE_BASE = f"https://raw.githubusercontent.com/Kadantte/tennis_atp/{SOURCE_COMMIT}"
RESULT_DELAY_DAYS = 21
COLUMNS = [
    "event_id", "date", "season", "side_a", "side_b", "score_a", "score_b",
    "neutral", "available_date", "surface", "rank_a", "rank_b",
]
_REQUIRED = {
    "tourney_id", "tourney_date", "match_num", "winner_id", "loser_id",
    "score", "best_of", "surface", "winner_rank", "loser_rank",
    "tourney_name",
}
_NON_COMPLETION = re.compile(
    r"\b(?:RET(?:IRED)?|WALKOVER|DEF(?:AULT)?|ABD|ABANDONED)\b|W\s*/\s*O",
    re.IGNORECASE,
)
_SET = re.compile(r"(\d+)-(\d+)(?:\((\d+)\))?")
_MATCH_TIEBREAK = re.compile(r"\[(\d+)-(\d+)\]")


def download(raw_dir: Path) -> list[Path]:
    """Cache fifteen pinned annual CSVs and their source documentation."""
    from sportslab.data import fetch

    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    # Keeping the original notices beside the data preserves their attribution.
    for filename in ("README.md", "matches_data_dictionary.txt"):
        fetch(f"{SOURCE_BASE}/{filename}", raw_dir / filename)
    return [
        fetch(f"{SOURCE_BASE}/atp_matches_{year}.csv", raw_dir / f"atp_matches_{year}.csv")
        for year in YEARS
    ]


def _completed_score(score: str, best_of: str, tournament: str) -> bool:
    """Require complete sets and a terminal win by the listed winner.

    Bracketed ten-point deciding tiebreaks and Next Gen four-game sets are
    supported. Ambiguous shorthand, unsupported formats, and contradictions
    between the score and listed winner are excluded rather than guessed.
    """
    if best_of not in {"3", "5"}:
        return False
    target = int(best_of) // 2 + 1
    tokens = score.split()
    if not target <= len(tokens) <= int(best_of):
        return False
    short_sets = "nextgen" in re.sub(r"[^a-z]", "", tournament.lower())
    wins = [0, 0]
    for index, token in enumerate(tokens):
        if max(wins) >= target:
            return False  # No sets can follow the match-winning set.
        tiebreak = _MATCH_TIEBREAK.fullmatch(token)
        if tiebreak:
            a, b = map(int, tiebreak.groups())
            high, low = max(a, b), min(a, b)
            complete = (high == 10 and low <= 8) or (high > 10 and high - low == 2)
            if not complete or index != len(tokens) - 1 or wins != [target - 1, target - 1]:
                return False
        else:
            match = _SET.fullmatch(token)
            if not match:
                return False
            a, b = int(match[1]), int(match[2])
            high, low = max(a, b), min(a, b)
            if short_sets:
                complete = high == 4 and low <= 3
                tiebreak_set = high == 4 and low == 3
            else:
                complete = ((high == 6 and low <= 4) or (high == 7 and low in {5, 6})
                            or (high >= 8 and high - low == 2)
                            or (high == 13 and low == 12))
                # Wimbledon used a deciding-set tiebreak at 12-all in 2019–21.
                tiebreak_set = (high, low) in {(7, 6), (13, 12)}
            if not complete or (match[3] is not None and not tiebreak_set):
                return False
        if a == b:
            return False
        wins[int(a < b)] += 1
    return wins[0] == target and wins[1] < target


def _rank(value: str) -> float:
    """Missing or invalid ranks remain missing, never a zero-rank advantage."""
    try:
        value = float(value)
    except (ValueError, TypeError):
        return math.nan
    return value if math.isfinite(value) and value > 0 and value.is_integer() else math.nan


def load(raw_dir: Path) -> pd.DataFrame:
    """Return completed-match outcomes with outcome-independent side assignment.

    ``date`` is the source tournament-start proxy, not an actual match date.
    Results are conservatively unavailable until that proxy plus 21 days.
    The common feature builder must use only strictly earlier availability.
    """
    raw_dir = Path(raw_dir)
    files = [(year, raw_dir / f"atp_matches_{year}.csv") for year in YEARS]
    files = [(year, path) for year, path in files if path.is_file()]
    if not files:
        raise FileNotFoundError(f"No supported ATP annual singles CSVs in {raw_dir}")
    records = []
    seen_ids: set[str] = set()
    exclusions = {"retirement_walkover_default_or_abandoned": 0, "incomplete_or_inconsistent_score": 0}
    source_rows = 0

    for year, path in files:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = _REQUIRED - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Missing ATP columns in {path.name}: {sorted(missing)}")
            for row_number, row in enumerate(reader, start=2):
                context = f"{path.name}:{row_number}"
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"Malformed ATP CSV record in {context}")
                row = {key: value.strip() for key, value in row.items()}
                source_rows += 1
                tournament, match_num = row["tourney_id"], row["match_num"]
                if not tournament.startswith(f"{year}-") or not re.fullmatch(r"\d+", match_num):
                    raise ValueError(f"Invalid ATP event identity in {context}")
                event_id = f"atp:{tournament}:{match_num}"
                if event_id in seen_ids:
                    raise ValueError(f"Duplicate ATP event_id {event_id} in {context}")
                seen_ids.add(event_id)
                winner, loser = row["winner_id"], row["loser_id"]
                if not all(re.fullmatch(r"\d+", player) for player in (winner, loser)) or winner == loser:
                    raise ValueError(f"Invalid ATP player identity in {context}")
                date_text = row["tourney_date"]
                if not re.fullmatch(r"\d{8}", date_text):
                    raise ValueError(f"Invalid ATP tournament date in {context}")
                try:
                    date = pd.to_datetime(date_text, format="%Y%m%d", errors="raise").normalize()
                except (ValueError, OverflowError) as error:
                    raise ValueError(f"Invalid ATP tournament date in {context}") from error
                # The next season can open during the previous December.
                if not pd.Timestamp(year - 1, 12, 1) <= date <= pd.Timestamp(year, 12, 31):
                    raise ValueError(f"ATP tournament date outside season bounds in {context}")
                score = row["score"]
                if _NON_COMPLETION.search(score):
                    exclusions["retirement_walkover_default_or_abandoned"] += 1
                    continue
                if not _completed_score(score, row["best_of"], row["tourney_name"]):
                    exclusions["incomplete_or_inconsistent_score"] += 1
                    continue
                # Sorting immutable IDs, never names/ranks/outcomes, avoids
                # accidentally making side A synonymous with the winner.
                a_is_winner = winner < loser
                rank_winner, rank_loser = _rank(row["winner_rank"]), _rank(row["loser_rank"])
                records.append({
                    "event_id": event_id,
                    "date": date,
                    "season": str(year),
                    "side_a": winner if a_is_winner else loser,
                    "side_b": loser if a_is_winner else winner,
                    "score_a": float(a_is_winner),
                    "score_b": float(not a_is_winner),
                    "neutral": True,
                    "available_date": date + pd.Timedelta(days=RESULT_DELAY_DAYS),
                    "surface": row["surface"] or "unknown",
                    "rank_a": rank_winner if a_is_winner else rank_loser,
                    "rank_b": rank_loser if a_is_winner else rank_winner,
                })
    frame = pd.DataFrame.from_records(records, columns=COLUMNS)
    for column in ("date", "available_date"):
        frame[column] = pd.to_datetime(frame[column])
    for column in ("score_a", "score_b", "rank_a", "rank_b"):
        frame[column] = frame[column].astype(float)
    frame["neutral"] = frame["neutral"].astype(bool)
    frame = frame.sort_values(["date", "event_id"], kind="stable").reset_index(drop=True)
    frame.attrs.update({
        "source": "Jeff Sackmann / Tennis Abstract, preserved by Kadantte/tennis_atp",
        "source_commit": SOURCE_COMMIT,
        "data_license": "CC-BY-NC-SA-4.0",
        "source_rows": source_rows,
        "exclusions": exclusions,
        "years_loaded": [year for year, _ in files],
        "result_delay_days": RESULT_DELAY_DAYS,
    })
    return frame
