"""Pinned nflverse/FTN source QA and descriptive, retrospective at-snap scouting.

No estimator, scoring function, or predictive execution path is implemented.
Only the 2023 development population can produce target-conditioned distributions.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.request import urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEVELOPMENT_SEASON = 2023
KEYS = ["game_id", "play_id"]
PINNED_HASHES = {
    "play_by_play_2023.csv.gz": "4649804ee0f0a40b41e51ec75a1ce921949d7fab5459213488656b92f78560e8",
    "play_by_play_2025.csv.gz": "2f135887790a013fd004e609e37096bb4816d5cc80b9f19122e1bad478961978",
    "pbp_participation_2022.csv": "37eae0a8c388d0974c6df9a1f9a1d01f09f63a21440d3b03d7f208c1438c51e4",
    "pbp_participation_2023.csv": "ad01aeb4045ee19a4f086ff38b52b14c8f427d3401e529c3078a4545921650a9",
    "pbp_participation_2024.csv": "b1f436a98b2a7759eb4ed1181e072a35c2666f9aeb356a49c943d28d6be6b0b9",
    "pbp_participation_2025.csv": "59069adfee7b0f464befba8a5e8be331e523633cc6a7ab403d37bcbcdfbe66ac",
    "ftn_charting_2022.csv": "80e13831525f726cb3befb7eb62aa6ea8bf55d36080fcf09fdddd7c578f3b200",
    "ftn_charting_2023.csv": "6045bbca32c1f61d32d9cf66e7cf6355f583b90c8ac2f5ed155d733ec335e8d7",
    "ftn_charting_2024.csv": "6faae8118cc13ce62589210d553733128ed35e558671009b4a7a8fc5c674c2cb",
    "ftn_charting_2025.csv": "62a66416043ff08d43303bf5f3af5390e3fe0f29461a1fc6e295a15cac6ea994",
}
PBP_CONTEXT = (
    "down", "ydstogo", "yardline_100", "qtr", "quarter_seconds_remaining",
    "half_seconds_remaining", "game_seconds_remaining", "score_differential",
    "posteam_timeouts_remaining", "defteam_timeouts_remaining", "no_huddle",
    "posteam_type",
)
PBP_METADATA = ("season", "season_type", "week", "posteam", "defteam", "game_date")
PBP_ELIGIBILITY = ("play_type", "qb_kneel", "qb_spike", "play_deleted")
PBP_TARGETS = ("qb_dropback", "sack", "qb_scramble")
PART_PRESNAP = ("offense_formation", "offense_personnel", "defense_personnel", "defenders_in_box")
FTN_PRESNAP = ("qb_location", "starting_hash", "n_offense_backfield", "n_defense_box", "is_motion")
FEATURE_COLUMNS = (
    *PBP_CONTEXT[:-1], "offense_is_home", "formation", "formation_era", "motion",
    "defenders_in_box", "offense_backfield", "starting_hash",
    "offense_rb", "offense_te", "offense_wr", "offense_ol", "offense_qb", "offense_other",
    "defense_dl", "defense_lb", "defense_db", "defense_other",
)
# Semantic allowlist: none of these columns is admitted by substring matching.
FORBIDDEN_EXAMPLES = (
    "defense_man_zone_type", "defense_coverage_type", "was_pressure",
    "number_of_pass_rushers", "n_pass_rushers", "n_blitzers", "time_to_throw",
    "passer_player_id", "receiver_player_id", "route", "read_thrown",
    "is_play_action", "is_rpo", "air_yards", "yards_gained", "epa", "xpass",
    "score_differential_post", "home_score", "away_score", "drive_end_yard_line",
)
PREDICTIVE_GATE = {
    "status": "closed", "fitting_allowed": False, "predictive_scoring_allowed": False,
    "reason": "Exact numerical protocol and independent review plus project-owner approval are required.",
}
CLOCKS = {
    "physical_event": "Final observable physical state at the ball snap; current play's later outcomes are excluded from inputs.",
    "observation_publication": "Retrospective charting after games; 2023+ participation is published after the postseason. Fetch time is not historical availability time.",
    "actionable_decision": "The offense chose its play earlier. These records support later film review/scouting, not a demonstrated live feed or live play-call recommendation.",
}
CAVEATS = [
    "Realized dropback includes sacks and quarterback scrambles; it is not the intended play call or original RPO decision.",
    "Descriptive rates are unsmoothed empirical fractions on the 2023 development sample, not fitted or calibrated forecasts and not causal effects.",
    "Personnel is roster-position composition, not alignment geometry, blocking role, route assignment, leverage, or joint mechanics.",
    "The 2022 NGS formation taxonomy differs from the 2023+ FTN quarterback-alignment taxonomy; EMPTY is not recoded as shotgun or treated as absent later.",
    "Motion records occurrence, not trajectory, direction, speed, timing, or defensive response.",
    "Zero QB-location/hash values are missing sentinels; zero backfield count is valid. Zero box count is conservatively quarantined as ambiguous missingness while its raw value is preserved.",
    "Canonical 2023+ formation and box count come from FTN charting; participation disagreements are audited, never averaged or used for fallback imputation.",
    "Charting inter-rater reliability and independent physical validation are unavailable here; schema checks are representation QA, not measurement-accuracy validation.",
    "Rows called competitive are REG down 1–4 recorded run/pass plays excluding kneels and spikes; this includes late-game plays and does not remove blowouts.",
    "Recorded run/pass eligibility is retrospective; nullified no_play rows are excluded. This is not an all-called-plays prospective population.",
    "2025 was previously inspected for source QA; it can later be performance-blind after QA, not wholly human-blind. This module emits no 2025 target summaries.",
    "No pressure target analysis, two-stage forecast, model fitting, validation performance, player ranking, or individual sensitive claims are supplied.",
]


@dataclass
class FootballPanel:
    season: int
    metadata: pd.DataFrame
    features: pd.DataFrame
    raw_presnap: pd.DataFrame
    target: pd.Series | None
    qa: dict[str, Any]


def _require_columns(frame: pd.DataFrame, columns: tuple | list, name: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{name}: missing required columns {missing}")


def _text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    result = re.sub(r"\s+", " ", str(value)).strip().upper()
    return None if result in {"", "NAN", "NONE", "NULL", "NA", "N/A"} else result


def _canonical_keys(frame: pd.DataFrame, source: str, season: int) -> pd.DataFrame:
    rename = {"nflverse_game_id": "game_id", "nflverse_play_id": "play_id"}
    out = frame.rename(columns={k: v for k, v in rename.items() if k in frame}).copy()
    if out.columns.duplicated().any():
        raise ValueError(f"{source}: ambiguous duplicate column names")
    _require_columns(out, KEYS, source)
    out["game_id"] = out.game_id.map(_text)
    numbers = pd.to_numeric(out.play_id, errors="coerce")
    bad = out.game_id.isna() | numbers.isna() | (numbers % 1 != 0) | (numbers < 0)
    if bad.any():
        raise ValueError(f"{source}: invalid/null join keys on {int(bad.sum())} rows")
    out["play_id"] = numbers.astype("int64")
    if not out.game_id.str.startswith(f"{season}_").all():
        raise ValueError(f"{source}: mixed or unexpected game-id season")
    if out.duplicated(KEYS).any():
        raise ValueError(f"{source}: duplicate game_id/play_id keys")
    return out


def _boolean(series: pd.Series) -> pd.Series:
    table = {"0": 0, "0.0": 0, "FALSE": 0, "1": 1, "1.0": 1, "TRUE": 1}
    return series.map(_text).map(table).astype("Int64")


def _bounded(series: pd.Series, low: float, high: float, *, integer: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    valid = values.between(low, high)
    if integer:
        valid &= values.mod(1).eq(0)
    return values.where(valid).astype("Float64")


def normalize_formation(value: Any, season: int) -> str | None:
    """Preserve taxonomy; do not infer alignment from an NGS formation name."""
    value = _text(value)
    if value:
        value = value.replace(" ", "_").replace("-", "_")
    permitted = {"SHOTGUN", "UNDER_CENTER", "PISTOL"}
    if season <= 2022:
        permitted |= {"SINGLEBACK", "I_FORM", "EMPTY", "JUMBO", "WILDCAT"}
    return value if value in permitted else None


def normalize_personnel(value: Any, side: str, season: int) -> dict[str, Any]:
    """Aggregate stated positions; never invent omitted legacy OL/QB counts."""
    if side not in {"offense", "defense"}:
        raise ValueError("side must be offense or defense")
    groups = ({"rb": {"RB", "FB"}, "te": {"TE"}, "wr": {"WR"},
               "ol": {"OL", "C", "G", "T"}, "qb": {"QB"}} if side == "offense" else
              {"dl": {"DL", "DE", "DT", "NT"}, "lb": {"LB", "ILB", "MLB", "OLB"},
               "db": {"DB", "CB", "FS", "SS", "S"}})
    empty = {f"{side}_{name}": None for name in [*groups, "other"]}
    raw = _text(value)
    result = {**empty, "valid": False, "status": "missing", "stated_total": None}
    if raw in {None, "0"}:
        return result
    positions = {}
    known = {"RB", "FB", "TE", "WR", "OL", "C", "G", "T", "QB", "DL", "DE", "DT", "NT",
             "LB", "ILB", "MLB", "OLB", "DB", "CB", "FS", "SS", "S", "K", "P", "LS"}
    for item in raw.split(","):
        match = re.fullmatch(r"\s*(\d+)\s+([A-Z]+)\s*", item)
        if not match or match[2] not in known or match[2] in positions or int(match[1]) > 11:
            return {**result, "status": "invalid_syntax_or_position"}
        positions[match[2]] = int(match[1])
    total = sum(positions.values())
    if total > 11 or total == 0:
        return {**result, "status": "invalid_total", "stated_total": total}
    # FTN enumerates all positions. NGS offense deliberately often only lists RB/TE/WR.
    if season >= 2023 and total != 11:
        return {**result, "status": "incomplete_ftn_total", "stated_total": total}
    for name, aliases in groups.items():
        empty[f"{side}_{name}"] = sum(positions.get(p, 0) for p in aliases)
    if season <= 2022 and side == "offense":
        for name in ["ol", "qb"]:
            if not set(positions).intersection(groups[name]):
                empty[f"{side}_{name}"] = None
    grouped = set().union(*groups.values())
    empty[f"{side}_other"] = sum(n for p, n in positions.items() if p not in grouped)
    return {**empty, "valid": True, "status": "parsed", "stated_total": total}


def _count_records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    work = frame[columns].astype("string").fillna("missing")
    return work.groupby(columns, dropna=False, sort=True).size().rename("n").reset_index().to_dict("records")


def _cohort(pbp: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Sequential exclusions partition input records; uncertain eligibility is excluded."""
    mask = pd.Series(True, index=pbp.index)
    exclusions = {}
    conditions = [
        ("not_regular_season", pbp.season_type.eq("REG")),
        ("deleted_or_unknown_flag", _boolean(pbp.play_deleted).eq(0).fillna(False)),
        ("not_recorded_run_or_pass", pbp.play_type.isin(["run", "pass"])),
        ("not_valid_down_1_to_4", pd.to_numeric(pbp.down, errors="coerce").isin([1, 2, 3, 4])),
        ("kneel_or_unknown_flag", _boolean(pbp.qb_kneel).eq(0).fillna(False)),
        ("spike_or_unknown_flag", _boolean(pbp.qb_spike).eq(0).fillna(False)),
    ]
    for reason, permitted in conditions:
        exclusions[reason] = int((mask & ~permitted).sum())
        mask &= permitted
    selected = pbp.loc[mask].copy().reset_index(drop=True)
    return selected, {"input_rows": len(pbp), "eligible_rows": len(selected),
                      "games": int(selected.game_id.nunique()), "sequential_exclusions": exclusions,
                      "exclusions_partition_input": sum(exclusions.values()) + len(selected) == len(pbp)}


def _join(left: pd.DataFrame, right: pd.DataFrame, columns: tuple, name: str, *, development_targets: bool = False) -> tuple[pd.DataFrame, dict]:
    _require_columns(right, columns, name)
    selected = right[KEYS + list(columns)].rename(columns={c: f"{name}__{c}" for c in columns})
    joined = left.merge(selected, on=KEYS, how="left", validate="one_to_one", indicator=f"{name}__join", sort=False)
    missing = joined[f"{name}__join"].eq("left_only")
    counts = {"eligible_denominator": len(left), "matched": int((~missing).sum()), "unmatched": int(missing.sum()),
              "match_fraction": float((~missing).mean()) if len(left) else None,
              "unmatched_by_team": _count_records(joined.loc[missing], ["posteam"])}
    if development_targets:
        counts["unmatched_by_team_and_play_category"] = _count_records(joined.loc[missing], ["posteam", "play_type"])
    return joined, counts


def build_panel(pbp: pd.DataFrame, participation: pd.DataFrame, ftn: pd.DataFrame,
                season: int, *, include_targets: bool | None = None) -> FootballPanel:
    if include_targets is None:
        include_targets = season == DEVELOPMENT_SEASON
    if include_targets and season != DEVELOPMENT_SEASON:
        raise ValueError("Target access is limited to the 2023 development population")
    _require_columns(pbp, [*PBP_CONTEXT, *PBP_METADATA, *PBP_ELIGIBILITY], "PBP")
    pbp = _canonical_keys(pbp, "PBP", season)
    part = _canonical_keys(participation, "participation", season)
    chart = _canonical_keys(ftn, "FTN", season)
    if not pd.to_numeric(pbp.season, errors="coerce").eq(season).all():
        raise ValueError("PBP: season field disagrees with requested season")
    pbp["season"] = season
    selected, cohort_qa = _cohort(pbp)
    joined, part_qa = _join(selected, part, PART_PRESNAP, "participation", development_targets=include_targets)
    joined, ftn_qa = _join(joined, chart, FTN_PRESNAP, "ftn", development_targets=include_targets)
    features = pd.DataFrame(index=joined.index)
    bounds = {"down": (1, 4), "ydstogo": (0, 100), "yardline_100": (0, 100), "qtr": (1, 10),
              "quarter_seconds_remaining": (0, 900), "half_seconds_remaining": (0, 1800),
              "game_seconds_remaining": (0, 3600), "score_differential": (-100, 100),
              "posteam_timeouts_remaining": (0, 3), "defteam_timeouts_remaining": (0, 3)}
    for col, (low, high) in bounds.items():
        features[col] = _bounded(joined[col], low, high, integer=True)
    features["no_huddle"] = _boolean(joined.no_huddle)
    features["offense_is_home"] = joined.posteam_type.map(_text).map({"HOME": 1, "AWAY": 0}).astype("Int64")
    part_form = joined["participation__offense_formation"].map(lambda x: normalize_formation(x, season))
    ftn_form = joined["ftn__qb_location"].map(_text).map({"S": "SHOTGUN", "U": "UNDER_CENTER", "P": "PISTOL"})
    features["formation"] = ftn_form if season >= 2023 else part_form
    features["formation_era"] = "FTN_QB_ALIGNMENT_2023_PLUS" if season >= 2023 else "NGS_FORMATION_2016_2022"
    features["motion"] = _boolean(joined["ftn__is_motion"])
    raw_ftn_box = _bounded(joined["ftn__n_defense_box"], 0, 11, integer=True)
    features["defenders_in_box"] = raw_ftn_box.mask(raw_ftn_box.eq(0))
    features["offense_backfield"] = _bounded(joined["ftn__n_offense_backfield"], 0, 10, integer=True)
    features["starting_hash"] = joined["ftn__starting_hash"].map(_text).map({"L": "left", "M": "middle", "R": "right"})
    personnel_qa = {}
    for side in ["offense", "defense"]:
        # Preserve complete original source files unchanged.
        raw = joined[f"participation__{side}_personnel"]
        parsed = raw.map(lambda v: normalize_personnel(v, side, season))
        counts = pd.DataFrame(parsed.tolist(), index=joined.index, columns=normalize_personnel(None, side, season))
        for col in [c for c in FEATURE_COLUMNS if c.startswith(f"{side}_") and c in counts]:
            features[col] = pd.to_numeric(counts[col], errors="coerce").astype("Float64")
        personnel_qa[side] = {"status_counts": counts.status.value_counts(dropna=False).to_dict(),
                              "stated_totals": _count_records(counts, ["stated_total"])}
    features = features.reindex(columns=FEATURE_COLUMNS)
    part_box = _bounded(joined["participation__defenders_in_box"], 0, 11, integer=True)
    both_box = part_box.notna() & raw_ftn_box.notna()
    both_form = part_form.notna() & ftn_form.notna()
    coverage = {c: {"denominator": len(features), "observed": int(features[c].notna().sum()),
                   "missing": int(features[c].isna().sum())} for c in FEATURE_COLUMNS}
    raw_presnap = joined[[*KEYS, *[f"participation__{c}" for c in PART_PRESNAP], *[f"ftn__{c}" for c in FTN_PRESNAP]]].copy()
    target = None
    target_qa = None
    if include_targets:
        _require_columns(joined, PBP_TARGETS, "development PBP")
        flags = {name: _boolean(joined[name]) for name in PBP_TARGETS}
        if any(s.isna().any() for s in flags.values()):
            raise ValueError("Development target flags must be fully observed binary fields")
        target = (flags["qb_dropback"].eq(1) | flags["sack"].eq(1) | flags["qb_scramble"].eq(1)).astype("Int64")
        target.name = "realized_dropback"
        target_qa = {"denominator": len(target), "dropbacks": int(target.sum()),
                     "recorded_rushes_without_dropback": int((target == 0).sum()),
                     "sacks_included": int(flags["sack"].sum()), "scrambles_included": int(flags["qb_scramble"].sum()),
                     "qb_dropback_flag_disagreements_with_union": int(target.ne(flags["qb_dropback"]).sum())}
    qa = {"season": season, "target_access": "development_only" if include_targets else "disabled_source_qa_only",
          "cohort": cohort_qa, "join_key_uniqueness": {"pbp": True, "participation": True, "ftn": True},
          "joins": {"participation": part_qa, "ftn": ftn_qa}, "feature_coverage": coverage,
          "personnel_parser": personnel_qa,
          "source_disagreements": {
              "box_count": {"paired_observations": int(both_box.sum()), "different": int((both_box & part_box.ne(raw_ftn_box)).sum())},
              "formation": {"paired_observations": int(both_form.sum()), "different": int((both_form & part_form.ne(ftn_form)).sum()),
                            "comparable_taxonomy": season >= 2023}},
          "sentinels_and_caveats": {"qb_location_zero": int(joined["ftn__qb_location"].map(_text).eq("0").sum()),
                                    "starting_hash_zero": int(joined["ftn__starting_hash"].map(_text).eq("0").sum()),
                                    "box_zero_ambiguous_quarantined": int(raw_ftn_box.eq(0).sum()),
                                    "backfield_zero_valid": int(features.offense_backfield.eq(0).sum())}}
    if target_qa is not None:
        qa["development_target_definition_checks"] = target_qa
    metadata = joined[[*KEYS, *PBP_METADATA]].copy()
    return FootballPanel(season, metadata, features, raw_presnap, target, qa)


def development_distributions(panel: FootballPanel) -> dict[str, Any]:
    if panel.season != DEVELOPMENT_SEASON or panel.target is None:
        raise ValueError("Target-by-context descriptions are locked outside 2023 development")
    if not panel.metadata.season.eq(DEVELOPMENT_SEASON).all():
        raise ValueError("Mixed-season metadata cannot enter development distributions")
    rows = panel.features.copy()
    rows["distance_band"] = pd.cut(rows.ydstogo.astype(float), [-1, 2, 5, 10, 100],
                                   labels=["0-2", "3-5", "6-10", "11+"]).astype("string")
    rows["realized_dropback"] = panel.target
    specs = [["down"], ["formation"], ["motion"], ["down", "distance_band"],
             ["down", "distance_band", "formation"], ["formation", "motion"]]
    tables = []
    for fields in specs:
        grouped = rows[fields].astype("string").fillna("missing")
        grouped["realized_dropback"] = rows.realized_dropback
        cells = grouped.groupby(fields, dropna=False, sort=True).realized_dropback.agg(["count", "sum"]).reset_index()
        entries = []
        for cell in cells.to_dict("records"):
            n, successes = int(cell.pop("count")), int(cell.pop("sum"))
            entries.append({**cell, "n": n, "dropbacks": successes, "rushes_without_dropback": n - successes,
                            "observed_dropback_fraction": successes / n if n else None})
        tables.append({"group_by": fields, "denominator": len(rows), "cells": entries})
    return {"season": DEVELOPMENT_SEASON, "phase": "descriptive", "unit": "recorded play",
            "denominator": len(rows), "rate_unit": "fraction, not percentage",
            "method": "unsmoothed empirical counts; no fitted predictions or causal interpretation",
            "tables": tables}


def predict(*args: Any, **kwargs: Any) -> None:
    raise PermissionError(PREDICTIVE_GATE["reason"])


def source_url(filename: str) -> str:
    if filename not in PINNED_HASHES:
        raise ValueError("Unreviewed source file")
    release = ("pbp" if filename.startswith("play_by_play") else
               "pbp_participation" if filename.startswith("pbp_participation") else "ftn_charting")
    return f"https://github.com/nflverse/nflverse-data/releases/download/{release}/{filename}"


def verify_source(path: Path, expected_sha256: str, expected_url: str | None = None) -> dict[str, Any]:
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != expected_sha256:
        raise ValueError(f"Source hash mismatch: {path.name}; refusing changed or unpinned input")
    sidecar = Path(str(path) + ".source.json")
    if not sidecar.is_file():
        raise ValueError(f"Missing provenance sidecar: {path.name}")
    record = json.loads(sidecar.read_text())
    if record.get("sha256") != sha or record.get("bytes") != path.stat().st_size:
        raise ValueError(f"Invalid provenance size/hash: {path.name}")
    try:
        fetched = datetime.fromisoformat(record.get("retrieved_utc", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid provenance time: {path.name}") from exc
    if fetched.tzinfo is None or not record.get("url") or (expected_url and record.get("url") != expected_url):
        raise ValueError(f"Invalid provenance source/time: {path.name}")
    return {"filename": path.name, "url": record["url"], "retrieved_utc": record["retrieved_utc"],
            "bytes": path.stat().st_size, "sha256": sha,
            "attribution": "nflverse" if path.name.startswith("play_by_play") else
                           "Next Gen Stats via nflverse" if "participation_2022" in path.name else "FTN Data via nflverse",
            "license": "CC BY 4.0" if path.name.startswith("play_by_play") else "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/" if path.name.startswith("play_by_play") else "https://creativecommons.org/licenses/by-sa/4.0/"}


def acquire_source(filename: str, raw_dir: Path, cache_dir: Path, *, download_missing: bool = False) -> tuple[Path, dict]:
    url = source_url(filename)
    candidates = [raw_dir / filename, cache_dir / filename]
    existing = next((p for p in candidates if p.is_file()), None)
    if existing is None:
        if not download_missing:
            raise FileNotFoundError(f"Missing pinned {filename}; pass --download-missing for its official release")
        cache_dir.mkdir(parents=True, exist_ok=True)
        with urlopen(url, timeout=90) as response:
            payload = response.read()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != PINNED_HASHES[filename]:
            raise ValueError(f"Official release changed for {filename}; review and repin before use")
        existing = cache_dir / filename
        existing.write_bytes(payload)
        record = {"url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                  "bytes": len(payload), "sha256": actual}
        Path(str(existing) + ".source.json").write_text(json.dumps(record, indent=2) + "\n")
    return existing, verify_source(existing, PINNED_HASHES[filename], url)


def _read_source(path: Path, season: int) -> tuple[pd.DataFrame, dict]:
    # Bind source identity and permitted role before even a header/body dataframe read.
    read_hashes = {**PINNED_HASHES, "play_by_play_2024.csv.gz": "23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06"}
    match = re.fullmatch(r"(play_by_play|pbp_participation|ftn_charting)_(20\d{2})\.csv(?:\.gz)?", path.name)
    if path.name not in read_hashes or match is None:
        raise ValueError("Unpinned source cannot be read")
    if int(match.group(2)) != season:
        raise ValueError("Source basename season disagrees with requested role")
    release = "pbp" if match.group(1) == "play_by_play" else match.group(1)
    expected_url = f"https://github.com/nflverse/nflverse-data/releases/download/{release}/{path.name}"
    verify_source(path, read_hashes[path.name], expected_url)
    columns = pd.read_csv(path, nrows=0).columns.tolist()
    if path.name.startswith("play_by_play"):
        wanted = [*KEYS, *PBP_CONTEXT, *PBP_METADATA, *PBP_ELIGIBILITY]
        if season == DEVELOPMENT_SEASON:
            wanted += list(PBP_TARGETS)
    elif path.name.startswith("pbp_participation"):
        wanted = ["nflverse_game_id", "play_id", *PART_PRESNAP]
    else:
        wanted = ["nflverse_game_id", "nflverse_play_id", *FTN_PRESNAP]
    if not set(wanted).issubset(columns):
        raise ValueError(f"{path.name}: required source schema changed")
    frame = pd.read_csv(path, usecols=wanted, low_memory=False)
    source = "pbp" if path.name.startswith("play_by_play") else "participation" if path.name.startswith("pbp_participation") else "ftn"
    _canonical_keys(frame, source, season)
    qa = {"filename": path.name, "season": season, "rows": len(frame), "schema_columns": columns,
          "loaded_columns": wanted, "duplicate_keys": 0, "null_or_invalid_keys": 0,
          "target_columns_loaded": season == DEVELOPMENT_SEASON and source == "pbp"}
    return frame, qa


def build_summary(raw_dir: Path | str | None = None, cache_dir: Path | str | None = None,
                  *, download_missing: bool = False) -> dict[str, Any]:
    raw_dir = Path(raw_dir) if raw_dir is not None else ROOT / "data/raw/tactical_research"
    cache_dir = Path(cache_dir) if cache_dir is not None else ROOT / "data/tactical/football"
    frames, sources, schemas = {}, [], []
    for filename in sorted(PINNED_HASHES):
        season = int(re.search(r"_(20\d\d)\.csv", filename)[1])
        path, provenance = acquire_source(filename, raw_dir, cache_dir, download_missing=download_missing)
        frame, schema = _read_source(path, season)
        frames[filename] = frame
        sources.append(provenance)
        schemas.append(schema)
    panels = {}
    for season in [2023, 2025]:
        panels[season] = build_panel(frames[f"play_by_play_{season}.csv.gz"], frames[f"pbp_participation_{season}.csv"],
                                    frames[f"ftn_charting_{season}.csv"], season)
    era_audits = []
    for season in [2022, 2023, 2024, 2025]:
        source = frames[f"pbp_participation_{season}.csv"]
        normalized = source.offense_formation.map(lambda v: normalize_formation(v, season))
        era_audits.append({"season": season, "denominator": len(source), "population": "all source participation records, all season types",
                           "formation_taxonomy": "NGS detailed formation" if season == 2022 else "FTN QB alignment",
                           "formation_missing_or_unrecognized": int(normalized.isna().sum()),
                           "personnel_style": "grouped positions; OL/QB may be omitted" if season == 2022 else "enumerated player positions"})
    return {
        "schema_version": "football-descriptive-v1", "sport": "american_football", "task": "retrospective_final_at_snap_scouting",
        "title": "NFL formation, personnel and motion source explorer", "phase": "descriptive",
        "generated_utc": datetime.now(timezone.utc).isoformat(), "predictive_gate": PREDICTIVE_GATE,
        "parser_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sources": sources, "source_schema_qa": schemas, "population": "NFL regular-season recorded run/pass plays, down 1–4, excluding kneels and spikes",
        "time_scope": {"development_descriptions": [2023], "source_schema_only": [2022, 2024], "source_eligibility_qa_only": [2025],
                       "proposed_future_protocol": "2023 training; 2024 weeks 1–9 selection, weeks 10–18 calibration; 2025 performance-blind test after QA. Not frozen or executed."},
        "clocks": CLOCKS, "units": {"record": "play", "distance": "yards", "clock": "seconds remaining", "score": "points, offense minus defense before play", "personnel_and_box": "stated player counts", "rate": "fraction"},
        "feature_allowlist": list(FEATURE_COLUMNS), "excluded_later_stage_examples": list(FORBIDDEN_EXAMPLES),
        "denominators": [{"season": y, "eligible_plays": p.qa["cohort"]["eligible_rows"], "games": p.qa["cohort"]["games"]} for y, p in panels.items()],
        "cohort_quality": [p.qa for p in panels.values()], "era_schema_audit": era_audits,
        "development_distributions": development_distributions(panels[2023]),
        "measurement_caveats": CAVEATS,
        "publication": {"raw_rows": "local_only", "row_derivatives": "local_only", "workbench": "read_only_local_aggregate_summary",
                        "external_release": "requires source-specific publication review; code license does not relicense source data",
                        "transformations": "strict keyed joins, declared cohort filtering, sentinel handling, personnel grouping and development aggregate counts"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw/tactical_research")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data/tactical/football")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/tactical/football/summary.json")
    parser.add_argument("--download-missing", action="store_true", help="Fetch only official, already hash-pinned releases")
    args = parser.parse_args(argv)
    report = build_summary(args.raw_dir, args.cache_dir, download_missing=args.download_missing)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "phase": report["phase"], "denominators": report["denominators"], "predictive_gate": "closed"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
