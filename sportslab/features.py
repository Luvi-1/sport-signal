"""One-pass availability-aware features. Outcomes never enter their own row."""
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass, field
import heapq
import math
import numpy as np
import pandas as pd

FEATURES = ["elo_diff", "surface_elo_diff", "form_diff", "margin_diff", "scoring_diff",
            "conceding_diff", "experience_diff", "rest_diff", "neutral",
            "cold_a", "cold_b", "log_rank_diff", "rank_missing_a", "rank_missing_b"]

@dataclass
class Participant:
    elo: float = 1500.0
    games: int = 0
    last_date: pd.Timestamp | None = None
    results: deque = field(default_factory=lambda: deque(maxlen=10))
    margins: deque = field(default_factory=lambda: deque(maxlen=10))
    scored: deque = field(default_factory=lambda: deque(maxlen=10))
    conceded: deque = field(default_factory=lambda: deque(maxlen=10))

def _mean(values, default=0.0):
    return float(np.mean(values)) if values else default

class FeatureState:
    def __init__(self, sport: str):
        self.sport = sport
        self.players = defaultdict(Participant)
        self.surface_elo = defaultdict(lambda: 1500.0)
        self.last_available = None

    def features(self, row) -> dict:
        a, b = self.players[row.side_a], self.players[row.side_b]
        # A newcomer has no invented rest history; cap known rest at 30 days.
        rest = lambda p: min(max((row.date - p.last_date).days, 0), 30) if p.last_date is not None else 30
        ra, rb = getattr(row, "rank_a", np.nan), getattr(row, "rank_b", np.nan)
        ma, mb = not np.isfinite(ra) or ra <= 0, not np.isfinite(rb) or rb <= 0
        return dict(zip(FEATURES, [
            (a.elo-b.elo)/400,
            (self.surface_elo[(row.side_a,row.surface)]-self.surface_elo[(row.side_b,row.surface)])/400,
            _mean(a.results,.5)-_mean(b.results,.5),
            _mean(a.margins)-_mean(b.margins), _mean(a.scored)-_mean(b.scored),
            _mean(a.conceded)-_mean(b.conceded), math.log1p(a.games)-math.log1p(b.games),
            (rest(a)-rest(b))/30, float(row.neutral), float(a.games==0), float(b.games==0),
            math.log((rb if not mb else 1000)/(ra if not ma else 1000)), float(ma), float(mb)
        ]))

    def update(self, row):
        a, b = self.players[row.side_a], self.players[row.side_b]
        result = float(row.score_a > row.score_b) + .5 * float(row.score_a == row.score_b)
        home = 0 if row.neutral or self.sport == "tennis" else 55
        expected = 1/(1+10**((b.elo-a.elo-home)/400))
        change = 20*(result-expected)
        a.elo += change
        b.elo -= change
        ka, kb = (row.side_a,row.surface), (row.side_b,row.surface)
        se = 1/(1+10**((self.surface_elo[kb]-self.surface_elo[ka]-home)/400))
        self.surface_elo[ka] += 20*(result-se)
        self.surface_elo[kb] -= 20*(result-se)
        for p, value, score, other in ((a,result,row.score_a,row.score_b),(b,1-result,row.score_b,row.score_a)):
            p.games += 1
            p.last_date = max(p.last_date, row.date) if p.last_date is not None else row.date
            p.results.append(value)
            p.margins.append(float(score-other))
            p.scored.append(float(score))
            p.conceded.append(float(other))
        self.last_available = max(self.last_available,row.available_date) if self.last_available is not None else row.available_date

def build_features(events: pd.DataFrame, sport: str) -> pd.DataFrame:
    """Every row uses only results with available_date STRICTLY before its date.

    Match-day rows are computed in one batch; pending results are then queued.
    Tennis uses a deliberately delayed availability date because its source dates
    tournaments rather than matches. Feature history can roll forward within the
    holdout, but classifier parameters remain frozen.
    """
    events = events.sort_values(["date","event_id"],kind="stable")
    state, pending, serial, rows = FeatureState(sport), [], 0, []
    for date, group in events.groupby("date",sort=True):
        while pending and pending[0][0] < date:
            _, _, prior = heapq.heappop(pending)
            state.update(prior)
        for row in group.itertuples(index=False):
            record = state.features(row)
            record.update(event_id=row.event_id, date=row.date, available_date=row.available_date,
                          side_a=row.side_a, side_b=row.side_b,
                          max_source_available_date=state.last_available)
            record["target"] = (int(row.score_a>row.score_b)*2 + int(row.score_a==row.score_b)) if sport=="soccer" else int(row.score_a>row.score_b)
            rows.append(record)
        for row in group.itertuples(index=False):
            heapq.heappush(pending,(row.available_date,serial,row))
            serial += 1
    out = pd.DataFrame(rows)
    assert np.isfinite(out[FEATURES].values).all()
    assert (out.max_source_available_date.isna() | (out.max_source_available_date < out.date)).all()
    return out
