"""Historical NFL regular-season results from the nflverse schedules release.

Only the explicit result/schedule allowlist below is parsed. The upstream raw
file contains additional fields, including market data, which are never loaded
into the modeling table. See docs/sources/football.md for dataset rights.
"""

from pathlib import Path

import numpy as np
import pandas as pd


SOURCE_URL = "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
RAW_FILENAME = "games.csv"
START_SEASON = 2010
END_SEASON = 2024
SOURCE_COLUMNS = (
    "game_id", "season", "game_type", "gameday", "home_team", "away_team",
    "home_score", "away_score", "location",
)
OUTPUT_COLUMNS = (
    "event_id", "date", "season", "side_a", "side_b", "score_a", "score_b",
    "neutral", "available_date",
)

# Keep a relocated franchise's rating/history continuous across code changes.
TEAM_ALIASES = {"STL": "LAR", "LA": "LAR", "OAK": "LV", "SD": "LAC"}


def download(raw_dir: Path) -> list[Path]:
    """Cache the release through the shared SHA256 provenance helper.

    The remote release is mutable; preserve the local snapshot and its sidecar
    to reproduce a run. See the repository snapshot lock for expected bytes.
    """
    from sportslab.data import fetch

    return [fetch(SOURCE_URL, Path(raw_dir) / RAW_FILENAME)]


def load(raw_dir: Path) -> pd.DataFrame:
    """Return completed, non-tied NFL regular-season games from 2010–2024.

    ``side_a`` is the designated home franchise, even at neutral venues.
    Dates are date-granularity schedule dates, not exact publication times.
    Feature builders must use only results with ``available_date < date``.
    """
    frame = pd.read_csv(
        Path(raw_dir) / RAW_FILENAME,
        usecols=list(SOURCE_COLUMNS),
        dtype={name: "string" for name in (
            "game_id", "game_type", "gameday", "home_team", "away_team",
            "location",
        )},
    )
    season = pd.to_numeric(frame["season"], errors="raise")
    in_scope = season.between(START_SEASON, END_SEASON) & frame["game_type"].eq("REG")
    frame = frame.loc[in_scope].copy()
    season = season.loc[in_scope]
    if not season.mod(1).eq(0).all():
        raise ValueError("Football seasons must be integer season years")
    frame["season"] = season.astype(int).astype(str)

    for column in ("home_score", "away_score"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    frame = frame.dropna(subset=["home_score", "away_score"]).copy()
    scores = frame[["home_score", "away_score"]].to_numpy(dtype=float)
    if not np.isfinite(scores).all() or (scores < 0).any() or (scores % 1 != 0).any():
        raise ValueError("Football scores must be finite, nonnegative integers")
    # Binary home-win research conditions on games with a decisive result.
    frame = frame.loc[frame["home_score"].ne(frame["away_score"])].copy()

    for column in ("game_id", "gameday", "home_team", "away_team", "location"):
        if frame[column].isna().any() or frame[column].str.strip().eq("").any():
            raise ValueError(f"Football {column} is missing for a completed game")
    if frame["game_id"].duplicated().any():
        raise ValueError("Football game_id must be unique")
    if not frame["location"].isin(["Home", "Neutral"]).all():
        raise ValueError("Football location must be Home or Neutral")

    dates = pd.to_datetime(frame["gameday"], format="%Y-%m-%d", errors="raise").dt.normalize()
    side_a = frame["home_team"].replace(TEAM_ALIASES).astype(str)
    side_b = frame["away_team"].replace(TEAM_ALIASES).astype(str)
    if side_a.eq(side_b).any():
        raise ValueError("A football game must contain two different franchises")
    result = pd.DataFrame({
        "event_id": frame["game_id"].astype(str),
        "date": dates,
        "season": frame["season"],
        "side_a": side_a,
        "side_b": side_b,
        "score_a": frame["home_score"].astype(float),
        "score_b": frame["away_score"].astype(float),
        "neutral": frame["location"].eq("Neutral").astype(bool),
        "available_date": dates.copy(),
    })
    return result.sort_values(["date", "event_id"], kind="stable").reset_index(drop=True)
