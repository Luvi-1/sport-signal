"""Pinned laboratory measurements and aggregate descriptions, with no fitting API.

Only the standard library is used. Raw identities stay in memory; only private,
opaque split plans enter ignored data/tactical/mechanics. Public-facing reports
contain aggregate marginal measurements, never trial rows or target correlations.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

VERSION = "measured-mechanics-descriptive-v1"
OBM_COMMIT = "44b98dae05cceb016f080ab39d105c85b8639084"
BYU_COMMIT = "fd435d9158ad5671c819bee3c47a47d7161a42cb"
OBM_REPO = "https://github.com/drivelineresearch/openbiomechanics"
BYU_REPO = "https://github.com/nsandholtz/byu_tennis_serves"
# Reviewed source bytes are pinned independently of the editable acquisition manifest.
OBM_HASHES = {
    "LICENSE-DATA.md": "19b1e9bedd22c36f02cdccd67b7c4dd561e2379f96b540006ad0c6dc9c49cc50",
    "LICENSE-CODE.md": "425055d90434fc55c0a875b11d6ece7e21c7c9beec08b9085fdefb142d28ea37",
    "DATASHEET.md": "5256a2c1665cdc0057f91edeab4156dadbd2e1942205221e91755dee735b015c",
    "baseball_hitting/README.md": "1aed0f97dac90e6d704a1f3c94b107860358cd7056301476c12ba1ac8cf1c0ac",
    "baseball_hitting/data/metadata.csv": "b87567a7dbed13dd438a16512b80b80af81cf909e1203a89f545e6b31a245372",
    "baseball_hitting/data/poi/poi_metrics.csv": "95ab62e2c36e5034435f3edaec2d7d320caf9aa61eac923d907aed6751a2619b",
    "baseball_hitting/data/poi/hittrax.csv": "dc5144bb2817969be2f9b75c62efad42953a492df9e916f46828bcab303c95fb",
}
BYU_HASHES = {
    "README.md": "88ba74f2e5be3a11a9fbf211608607239c561c6cc5a14b67014f05c59e9acede",
    "LICENSE": "cb36b76bc0e409ba6f3388befad7d28cf7998e612d3b4fb4885a37caffb983b0",
    "data/serves.csv": "69942760cbfa80ea30fd70dc125ad89ded989a50b36ff043d40951c0ef635871",
    "data/targets.csv": "30be3fc1882b652402ac22c1439626a97269f29215e4d69c66192fb8a20854e0",
    "R/utils.R": "4adc85471b27101eff090ae978be7ec7be51c71b513c508db1e68c4442a1fd93",
}
META_COLUMNS = tuple("session_swing session_mass_lbs session_height_in athlete_age highest_playing_level hitter_side bat_weight_oz bat_length_in bat_speed_mph_max_x blast_bat_speed_mph_x exit_velo_mph_x user session".split())
HIT_COLUMNS = tuple("session_swing pitch strike_zone la dist res bearing vertical_distance horizontal_distance poi_x poi_y poi_z pitch_angle".split())
SERVE_COLUMNS = tuple("session_id player_id serve_period region index speed_mph clear_net let shot_x shot_y".split())
TARGET_COLUMNS = tuple("player_id dominant_hand region target_x target_y".split())
REGIONS = ("deuce wide", "deuce tee", "ad tee", "ad wide")
# One canonical body-only representative for each explicitly documented construct.
BODY = (
    ("lead_knee_launchpos_x", "Lead knee flexion at foot plant", "deg", "Knee flexion positive; source processed component x; extension is decreasing flexion"),
    ("rear_hip_launchpos_x", "Rear hip flexion at foot plant", "deg", "Hip flexion positive, extension negative; source processed component x"),
    ("rear_elbow_launchpos_x", "Rear elbow flexion at foot plant", "deg", "Elbow flexion positive, extension negative; source processed component x"),
    ("torso_pelvis_launchpos_x", "Torso relative to pelvis at foot plant", "deg", "Relative axial rotation: positive torso toward mound/pelvis toward catcher; source dictionary identifies physical z despite the column's x suffix"),
)
PITCH = (
    ("pitch", "Incoming machine-pitch speed", "mph", "HitTrax incoming pitch speed"),
    ("pitch_angle", "Incoming pitch descent angle", "deg", "HitTrax reported descent angle; additional sign convention is not independently verified"),
    ("horizontal_distance", "Horizontal pitch offset", "in", "Relative to strike-zone center; positive inside to a right-handed batter; not mirrored by hitter side"),
    ("vertical_distance", "Vertical pitch offset", "in", "Relative to strike-zone center; positive above center"),
)
OBSERVED = (
    ("exit_velocity", "Recorded ball exit velocity", "mph", "Ball speed after contact; source recording, not a game outcome", "ball_outcome"),
    ("marker_contact_speed", "Marker-derived bat speed at contact", "mph", "Resultant bat speed at the source contact event; exploratory motion-capture estimate", "marker_bat_outcome"),
    ("blast_contact_speed", "Blast sensor bat speed", "mph", "Separate Blast Motion contact-speed measurement; never substituted for marker speed", "sensor_bat_outcome"),
    ("bat_attack_angle", "Vertical bat attack angle at contact", "deg", "Sweet spot moving upward positive/downward negative; a bat angle, not ball launch angle", "bat_geometry"),
    ("ball_launch_angle", "HitTrax ball launch angle", "deg", "Provider-reported batted-ball launch angle; distinct from bat attack angle", "ball_geometry"),
)
ALIASES = (
    ("bat_torso_angle_connection_x", "bat_torso_angle_ds_y"),
    ("hand_speed_mag_max_x", "hand_speed_mag_seq_max_x"),
    ("pelvis_angle_fm_y", "pelvis_fm_y"),
    ("pelvis_angle_fp_y", "pelvis_launchpos_y"),
    ("torso_angle_fm_y", "torso_fm_y"),
    ("torso_angle_fp_y", "torso_launchpos_y"),
    ("upper_arm_speed_mag_max_x", "upper_arm_speed_mag_seq_max_x"),
    ("upper_arm_speed_mag_max_x", "upper_arm_speed_mag_swing_max_velo_x"),
    ("x_factor_fm_z", "torso_pelvis_fm_x"),
    ("x_factor_fp_z", "torso_pelvis_launchpos_x"),
    ("pelvis_angular_velocity_seq_max_x", "pelvis_angular_velocity_swing_max_x"),
    ("torso_angular_velocity_seq_max_x", "torso_angular_velocity_swing_max_x"),
    ("upper_arm_speed_mag_seq_max_x", "upper_arm_speed_mag_swing_max_velo_x"),
)
MISSING = frozenset(("", "NA", "N/A", "NaN", "nan", "null", "None"))


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def number(value, field="measurement") -> float | None:
    if value is None or str(value).strip() in MISSING:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid numeric {field}") from None
    if not math.isfinite(result):
        raise ValueError(f"Nonfinite {field}")
    return result


def integer(value, field: str, allowed=None) -> int:
    value = number(value, field)
    if value is None or not value.is_integer() or (allowed is not None and value not in allowed):
        raise ValueError(f"Invalid {field}")
    return int(value)


def read_csv(path: Path, columns=None, required=()) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        names = tuple(reader.fieldnames or ())
        if len(set(names)) != len(names) or (columns is not None and names != columns) or not set(required) <= set(names):
            raise ValueError("Unexpected measurement CSV schema")
        rows = []
        for row in reader:
            if None in row or any(x is None for x in row.values()):
                raise ValueError("Ragged measurement CSV row")
            rows.append(row)
        return rows


def unique_index(rows, keys):
    index = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        if any(not str(v).strip() for v in key) or key in index:
            raise ValueError("Missing or duplicate measurement join key")
        index[key] = row
    return index


def verify_files(cache, entries, hashes, repo, commit, key):
    indexed = {e[key]: e for e in entries}
    if len(indexed) != len(entries) or not set(hashes) <= set(indexed):
        raise ValueError("Missing or duplicate pinned file record")
    files, paths = [], {}
    prefix = repo.replace("https://github.com/", "https://raw.githubusercontent.com/") + "/" + commit + "/"
    for name, expected_hash in hashes.items():
        entry = indexed[name]
        path = cache / (Path(name).name if commit == BYU_COMMIT else name)
        if entry["url"] != prefix + name or entry["sha256"] != expected_hash:
            raise ValueError("Unreviewed source URL/hash; reacquisition review required")
        if path.stat().st_size != entry["bytes"] or digest(path) != expected_hash:
            raise ValueError("Pinned source byte-integrity mismatch")
        paths[name] = path
        files.append({"role": name, "url": entry["url"], "sha256": expected_hash, "bytes": entry["bytes"]})
    return paths, files


def validate_sources(root: Path, sport: str):
    if sport == "baseball":
        manifest_path = root / "docs/research/baseball_football/openbiomechanics_manifest.json"
        source = json.loads(manifest_path.read_text())
        if source["repository_commit"] != OBM_COMMIT or source["license"] != "CC BY-NC-SA 4.0 plus professional-organization exclusion; code separately MIT":
            raise ValueError("OpenBiomechanics pin/license mismatch")
        paths, files = verify_files(root / "data/raw/tactical_research/openbiomechanics", source["files"], OBM_HASHES, OBM_REPO, OBM_COMMIT, "path")
        notice = {
            "repository": OBM_REPO, "commit": OBM_COMMIT,
            "license": "CC BY-NC-SA 4.0 plus professional-sports/financial-analysis affiliation exclusion; data/documentation distinct from MIT software",
            "license_url": f"{OBM_REPO}/blob/{OBM_COMMIT}/LICENSE-DATA.md",
            "attribution": "OpenBiomechanics Project, Driveline Baseball Research & Development",
            "eligibility": "Confirmed independent noncommercial local research without excluded affiliations; not a commercial or redistribution grant",
            "consent": "Source datasheet reports human-subject consent, de-identification and Western IRB/WCG WB-DLR-115; no re-identification or individual health/selection inference",
        }
    elif sport == "tennis":
        manifest_path = root / "docs/research/tennis/source_manifest.json"
        candidates = [s for s in json.loads(manifest_path.read_text())["sources"] if s["id"] == "byu_serves"]
        if len(candidates) != 1:
            raise ValueError("BYU source manifest ambiguity")
        source = candidates[0]
        if source["commit"] != BYU_COMMIT or source["repository"] != BYU_REPO or source["license"] != "MIT stated in repository README and LICENSE":
            raise ValueError("BYU pin/license mismatch")
        if len(source["files"]) != len(BYU_HASHES):
            raise ValueError("Unexpected BYU acquisition file set")
        paths, files = verify_files(root / "data/research/tennis/byu-inspection", source["files"], BYU_HASHES, BYU_REPO, BYU_COMMIT, "file")
        notice = {
            "repository": BYU_REPO, "commit": BYU_COMMIT,
            "license": "MIT stated in repository README and LICENSE",
            "license_url": f"{BYU_REPO}/blob/{BYU_COMMIT}/LICENSE",
            "attribution": "Copyright (c) 2026 Nate Sandholtz; Nathan Sandholtz, Ryan Hanson, Ron Hager, Stephanie Kovalchik and Gilbert Fellingham",
            "eligibility": "Local descriptive educational research; retain copyright and license notice; no supplied compiled binary or fitted output executed",
            "consent": "Source uses coded participants. Primary paper Section 3 footnote 2 reports BYU IRB #2025-487 determined the study fell outside the regulatory definition of human-subjects research and therefore outside IRB oversight; this is not an IRB approval claim. Participant ages and individual consent details remain unverified",
            "ethics_documentation": {"url": "https://arxiv.org/html/2607.28500v2", "location": "Section 3, footnote 2", "checked_date_utc": "2026-10-11", "scope": "Direct primary-paper statement verification, separate from pinned CSV byte validation"},
        }
    else:
        raise ValueError("Unsupported mechanics sport")
    notice.update(files=files, manifest_sha256=digest(manifest_path), adapter_sha256=digest(Path(__file__)),
                  transformation=VERSION, modification="Validated joins, separated measurement roles, adult-filtered baseball, and aggregated marginal distributions; no fitted outputs",
                  publication="Local aggregate view only; separate source-specific review required before public reports, rows, figures or weights; no endorsement implied")
    return paths, notice


@dataclass(frozen=True)
class Swing:
    group: str
    session: str
    body: dict[str, float | None]
    pitch: dict[str, float | None]
    observed: dict[str, float | None]


@dataclass(frozen=True)
class Serve:
    group: str
    session: str
    period: int
    region: str
    speed: float | None
    clear_net: bool
    target_x: float
    target_y: float
    x: float | None
    y: float | None

    @property
    def dx(self):
        return None if self.x is None else self.x - self.target_x

    @property
    def dy(self):
        return None if self.y is None else self.y - self.target_y

    @property
    def radial_error(self):
        return None if self.x is None else math.hypot(self.dx, self.dy)


def adapt_baseball(metadata, poi, hittrax):
    meta = unique_index(metadata, ("session_swing",))
    kin = unique_index(poi, ("session_swing",))
    hit = unique_index(hittrax, ("session_swing",))
    if set(meta) != set(kin) or not set(hit) <= set(meta):
        raise ValueError("Incomplete or orphaned baseball join")
    groups, session_owners, adult_groups = defaultdict(set), defaultdict(set), set()
    adults, minor_groups = [], set()
    missing_age = 0
    for key, row in meta.items():
        k = kin[key]
        if not row["user"] or not row["session"] or integer(row["session"], "session") != integer(k["session"], "session"):
            raise ValueError("Invalid baseball participant/session join")
        groups[row["user"]].add(row["session"])
        session_owners[row["session"]].add(row["user"])
        for field in ("exit_velo_mph_x", "blast_bat_speed_mph_x", "bat_speed_mph_max_x"):
            if number(row[field]) != number(k[field]):
                raise ValueError("Duplicated metadata/POI measurement disagrees")
        age = number(row["athlete_age"], "age eligibility")
        if age is None:
            missing_age += 1
        elif age < 18:
            minor_groups.add(row["user"])
        else:
            adults.append(key)
            adult_groups.add(row["user"])
    if any(len(v) != 1 for v in groups.values()) or any(len(v) != 1 for v in session_owners.values()):
        raise ValueError("Reviewed one-session-per-athlete contract changed")
    if adult_groups & minor_groups:
        raise ValueError("Inconsistent age eligibility within athlete")
    for row in poi:
        for first, second in ALIASES:
            if number(row[first]) != number(row[second]):
                raise ValueError("Reviewed equivalent measurement columns disagree")
    outcome_keys = [k for k in adults if number(kin[k]["exit_velo_mph_x"]) is not None]
    selected_keys = [k for k in outcome_keys if k in hit]
    swings = []
    for key in selected_keys:
        m, p, h = meta[key], kin[key], hit[key]
        swings.append(Swing(m["user"], m["session"],
            {f: number(p[f], f) for f, *_ in BODY},
            {f: number(h[f], f) for f, *_ in PITCH},
            {"exit_velocity": number(p["exit_velo_mph_x"]),
             "marker_contact_speed": number(p["bat_speed_mph_contact_x"]),
             "blast_contact_speed": number(p["blast_bat_speed_mph_x"]),
             "bat_attack_angle": number(p["attack_angle_contact_x"]),
             "ball_launch_angle": number(h["la"])}))
    counts = {
        "source_swings": len(meta), "source_athletes": len(groups), "source_sessions": len(session_owners),
        "under_18_swings_excluded": sum(1 for k in meta if meta[k]["user"] in minor_groups),
        "under_18_athletes_excluded": len(minor_groups), "unknown_age_swings_excluded": missing_age,
        "adult_swings": len(adults), "adult_athletes": len(adult_groups),
        "adult_recorded_exit_velocity_swings": len(outcome_keys),
        "adult_recorded_exit_velocity_athletes": len({meta[k]["user"] for k in outcome_keys}),
        "adult_missing_exit_velocity": len(adults) - len(outcome_keys),
        "adult_observed_exit_without_paired_context": len(outcome_keys) - len(selected_keys),
        "primary_swings": len(swings), "primary_athletes": len({r.group for r in swings}),
        "source_paired_context_swings": len(hit),
        "primary_strike_zone_category_missing_not_used": sum(hit[k]["strike_zone"] in MISSING for k in selected_keys),
    }
    return swings, counts


def adapt_tennis(serves, targets):
    target_index = unique_index(targets, ("player_id", "region"))
    unique_index(serves, ("session_id", "player_id", "serve_period", "region", "index"))
    short_keys = Counter((r["session_id"], r["player_id"], r["index"]) for r in serves)
    for row in targets:
        if row["region"] not in REGIONS or row["dominant_hand"] not in {"L", "R"}:
            raise ValueError("Invalid target region/hand convention")
        if any(number(row[f], f) is None for f in ("target_x", "target_y")):
            raise ValueError("Unobserved stated target")
    records, lets, let_missing = [], 0, 0
    raw_bounces, raw_speed_missing = 0, 0
    for row in serves:
        period = integer(row["serve_period"], "serve period", {1, 2})
        clear = integer(row["clear_net"], "net-clear flag", {0, 1})
        is_let = integer(row["let"], "let flag", {0, 1})
        if row["region"] not in REGIONS or any(integer(row[f], "coded session/attempt") < 1 for f in ("session_id", "player_id", "index")):
            raise ValueError("Invalid experimental condition")
        target = target_index.get((row["player_id"], row["region"]))
        if target is None:
            raise ValueError("Unmatched stated target")
        x, y = number(row["shot_x"], "bounce depth"), number(row["shot_y"], "bounce lateral position")
        speed = number(row["speed_mph"], "radar speed")
        if (x is None) != (y is None):
            raise ValueError("Partial bounce coordinate pair")
        if speed is not None and speed <= 0:
            raise ValueError("Nonpositive measured radar speed")
        raw_bounces += x is not None
        raw_speed_missing += speed is None
        if is_let:
            if clear != 1:
                raise ValueError("Let flag conflicts with net-crossing convention")
            lets += 1
            let_missing += x is None
            continue
        if (clear == 0 and x is not None) or (clear == 1 and x is None):
            raise ValueError("Non-let net censoring disagrees with bounce observability")
        records.append(Serve(row["player_id"], row["session_id"], period, row["region"], speed, bool(clear),
                             number(target["target_x"]), number(target["target_y"]), x, y))
    counts = {
        "source_attempts": len(serves), "source_players": len({r["player_id"] for r in serves}),
        "source_sessions": len({r["session_id"] for r in serves}), "stated_targets": len(targets),
        "source_first_period_attempts": sum(r["serve_period"] == "1" for r in serves),
        "source_second_period_attempts": sum(r["serve_period"] == "2" for r in serves),
        "lets_excluded": lets, "lets_with_missing_bounce": let_missing,
        "source_observed_bounce_pairs": raw_bounces, "source_missing_speeds": raw_speed_missing,
        "nonlet_attempts": len(records), "nonlet_observed_bounce_pairs": sum(r.x is not None for r in records),
        "nonlet_net_censored": sum(not r.clear_net for r in records),
        "repeated_short_key_extra_rows_retained": sum(n - 1 for n in short_keys.values()),
        "nonlet_player_session_cells": len({(r.group, r.session) for r in records}),
        "nonlet_player_period_region_cells": len({(r.group, r.period, r.region) for r in records}),
    }
    return records, counts


def quantile(values, q):
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] * (hi - position) + ordered[hi] * (position - lo) if lo != hi else ordered[lo]


def distribution(values):
    values = list(values)
    finite = [v for v in values if v is not None]
    if any(not math.isfinite(v) for v in finite):
        raise ValueError("Nonfinite aggregate measurement")
    result = {"denominator": len(values), "observed": len(finite), "missing": len(values) - len(finite)}
    if len(finite) >= 10:
        result.update(mean=round(mean(finite), 4), q10=round(quantile(finite, .1), 4),
                      median=round(quantile(finite, .5), 4), q90=round(quantile(finite, .9), 4))
    else:
        result["values_suppressed"] = True
    return result


def histogram(values_and_groups, cutpoints, key, unit, definition):
    """Fixed marginal bins; suppress sparse and one complementary occupied cell.

    This is a modest disclosure precaution, not a formal anonymization guarantee.
    No bins condition on any target outcome or identify a participant.
    """
    if tuple(sorted(set(cutpoints))) != tuple(cutpoints) or any(not math.isfinite(v) for v in cutpoints):
        raise ValueError("Invalid fixed histogram boundaries")
    counts, groups, total, missing = [0] * (len(cutpoints) + 1), [set() for _ in range(len(cutpoints) + 1)], 0, 0
    for value, group in values_and_groups:
        total += 1
        if value is None:
            missing += 1
            continue
        if not math.isfinite(value):
            raise ValueError("Nonfinite geometry measurement")
        index = sum(value >= c for c in cutpoints)
        counts[index] += 1
        groups[index].add(group)
    suppressed = {i for i, n in enumerate(counts) if n and (n < 10 or len(groups[i]) < 3)}
    if len(suppressed) == 1:
        candidates = [i for i, n in enumerate(counts) if n and i not in suppressed]
        if candidates:
            suppressed.add(min(candidates, key=lambda i: (counts[i], i)))
    bounds = (None, *cutpoints, None)
    return {"key": key, "unit": unit, "definition": definition, "denominator": total,
            "observed": total - missing, "missing": missing, "closure": "lower-inclusive upper-exclusive",
            "suppression": "Occupied cells below 10 observations or 3 participants, plus a complementary occupied cell when needed; not a formal privacy guarantee",
            "bins": [{"lower": bounds[i], "upper": bounds[i + 1], "count": None if i in suppressed else counts[i],
                      "suppressed": i in suppressed} for i in range(len(counts))]}


def opaque_group(source, group):
    return hashlib.sha256((VERSION + "|" + source + "|" + group).encode()).hexdigest()


def split_plan(rows, sport):
    """Outcome-independent, private group memberships, frozen before any fit."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[opaque_group(sport, row.group)].append(row)
    keys = sorted(grouped)
    if sport == "baseball":
        if len(keys) < 5:
            raise ValueError("Insufficient groups for fixed five-fold baseball plan")
        assignments = {group: i % 5 for i, group in enumerate(keys)}
        outer = []
        for fold in range(5):
            test = [k for k in keys if assignments[k] == fold]
            train = [k for k in keys if assignments[k] != fold]
            # Training-only salted ordering for each outer fold, independent of outcomes.
            inner_order = sorted(train, key=lambda k: hashlib.sha256((f"inner-{fold}|" + k).encode()).hexdigest())
            outer.append({"fold": fold, "test_groups": test, "training_groups": train,
                          "inner_assignment": {g: i % 4 for i, g in enumerate(inner_order)}})
    elif sport == "tennis":
        outer = [{"fold": i, "test_groups": [k], "training_groups": [g for g in keys if g != k]} for i, k in enumerate(keys)]
    else:
        raise ValueError("Unsupported split sport")
    return {"version": VERSION, "sport": sport, "status": "draft_memberships_fixed_no_fit",
            "grouping": "athlete" if sport == "baseball" else "player",
            "method": "five outer/four inner group folds" if sport == "baseball" else "fixed leave-one-player-out; no inner selection",
            "groups": len(keys), "observations": len(rows), "outcome_independent": True,
            "membership_privacy": "Private ignored artifact; do not serve or publish group hashes/membership",
            "folds": outer}


def base_report(sport, source, population, plan):
    return {"schema_version": 1, "adapter_version": VERSION, "sport": sport, "phase": "descriptive",
            "predictive_gate": {"status": "closed", "fitting_allowed": False},
            "fit_status": "No fitting, target-feature correlations, model selection, calibration or prediction scoring performed",
            "source": source, "population": population,
            "split_description": {k: plan[k] for k in ("status", "grouping", "method", "groups", "observations", "outcome_independent")},
            "privacy": "Aggregate-only local reports; no source athlete identifiers, participant profiles, trial rows, health or selection rankings; no professional-event row pooling"}


def baseball_summary(rows, counts, source, plan):
    report = base_report("baseball", source, {"label": "Adult paired-context machine-hitting cohort", "unit": "recorded swing",
        "primary_denominator": "Age at least 18, observed recorded exit velocity and matched HitTrax incoming-pitch context",
        "counts": counts, "task": "Pitching machine approximately 65 mph from approximately 40 ft; predominantly collegiate source",
        "future_fit_estimand": "Execution-conditioned recorded-exit-velocity association in the adult paired cohort; new-athlete laboratory transport"}, plan)
    report["measurement_frame"] = {
        "method": "Source-processed marker body kinematics; HitTrax pitch and ball outputs; separate Blast bat sensor",
        "global_axes": "+x toward mound, +y toward right-handed batter box, +z upward; source performs selected handedness/sign adjustments",
        "body_angle_convention": "Use documented processed joint convention once; never infer physical axis from column suffix or mirror a second time",
        "event": "Foot plant at lead force 100% body weight; foot contact uses 10% and is a different event",
        "sampling": "Marker-derived 360 Hz; force plates 1080 Hz; source filters marker signals at 20 Hz and force signals at 40 Hz",
        "timing": "Offline whole-trial processing. No verified elapsed hitting event times or online detector latency in these summary CSVs",
        "accuracy": "Documentation/schema/consistency checks are not independent physical sensor or anatomical validation"}
    report["measurements"] = [dict(key=f, label=label, unit=unit, definition=definition, role="body_angle",
        observation_time="source-extracted foot plant, retrospectively processed", **distribution(r.body[f] for r in rows)) for f, label, unit, definition in BODY]
    report["measurements"] += [dict(key=f, label=label, unit=unit, definition=definition, role="incoming_pitch_context",
        observation_time="recorded incoming machine-pitch state; availability latency unverified", **distribution(r.pitch[f] for r in rows)) for f, label, unit, definition in PITCH]
    report["observed_outcomes"] = [dict(key=f, label=label, unit=unit, definition=definition, role=role,
        observation_time="at/after contact, retrospective descriptive display only", future_predictor=False,
        **distribution(r.observed[f] for r in rows)) for f, label, unit, definition, role in OBSERVED]
    cuts = ((0, 30, 60, 90, 120), (0, 30, 60, 90, 120), (60, 90, 120, 150), (-45, -30, -15, 0, 15))
    report["geometry"] = [histogram(((r.body[f], r.group) for r in rows), edges, f, unit, label)
                          for (f, label, unit, _), edges in zip(BODY, cuts)]
    report["geometry"] += [histogram(((r.pitch[f], r.group) for r in rows), (-12, -6, 0, 6, 12), f, "in", label)
                           for f, label in (("horizontal_distance", "Horizontal pitch-location coverage"), ("vertical_distance", "Vertical pitch-location coverage"))]
    report["validation"] = {"source_hashes_verified": True, "one_to_one_metadata_poi": True,
        "hittrax_subset_join": True, "duplicate_measurement_pairs_checked": len(ALIASES),
        "metadata_target_copies_agree": True, "one_session_per_athlete": True,
        "features_semantically_allowlisted": True, "all_primary_body_and_pitch_measurements_observed": all(v is not None for r in rows for v in (*r.body.values(), *r.pitch.values())),
        "independent_sensor_accuracy_verified": False, "live_feature_availability_verified": False}
    report["limitations"] = [
        "The 638-adult exit-velocity cohort and 571-adult paired-context cohort answer different selection-conditioned questions; this view uses only the latter",
        "One session per athlete; session and athlete effects cannot be separated, and no future-session claim is supported",
        "Body angles are distinct from bat attack and ball launch angles; these marginal summaries contain no association or technique-effect estimate",
        "Marker and Blast bat speeds are different measurements; bat-derived velocities and aliases are excluded from body feature candidates",
        "Missing contact/context rows cannot be assumed to be misses; no all-pitch decision or live MLB transfer claim",
        "No raw event times, pre-pitch stance width, foot orientation, live causal filtering audit or independently validated sensor error are available here",
        "Outcome-bearing identifiers, unverified point-of-impact units, predicted ball-in-play result and target-derived variables never enter candidate metadata or this report",
        "No minor observations, body-health assessments, athlete rankings or individual display are included in the primary view"]
    return report


def tennis_summary(rows, targets, counts, source, plan):
    report = base_report("tennis", source, {"label": "Eight-player collegiate practice serve experiment", "unit": "recorded non-let serve attempt",
        "primary_denominator": "All 548 recorded non-let attempts; 437 observed bounces and 111 net-censored attempts retained",
        "counts": counts, "task": "Assigned court-side/target region and supplied first/second serve-period labels; no verified point-pair identifiers",
        "future_fit_estimand": "Net/bounce execution distribution conditional on a recorded non-let attempt and the player's stated target"}, plan)
    report["measurement_frame"] = {
        "coordinates": "Meters in returner's half: origin net/center-service-line intersection, x depth away from net, y lateral positive toward deuce court",
        "method": "Stated marked targets; bounce water marks measured by tape distance/digital angle finder then converted to Cartesian coordinates; radar speed in mph",
        "error": "dx=observed bounce x minus that player's exact stated target x; dy analogously; radial error=sqrt(dx^2+dy^2), meters",
        "censoring": "Net-hit non-lets have no observed bounce; coordinates and errors remain absent, never zero-filled or assigned synthetic bounces",
        "timing": "Stated targets precede attempts; bounce and current-serve radar speed are post-impact; session IDs order sessions, not verified dates",
        "serve_period": "Supplied experimental period, not an independently reconstructed first-fault/second-serve point chain",
        "accuracy": "Primary paper Section 3 footnote 4 reports a nominal radar accuracy specification of +/-3% of the reading; no independent per-attempt radar/coordinate validation or body/joint angles are supplied"}
    specs = (
        ("bounce_depth", "Observed bounce depth", "m", "x in source court frame", lambda r: r.x),
        ("bounce_lateral", "Observed bounce lateral position", "m", "y in source frame, positive deuce", lambda r: r.y),
        ("depth_error", "Signed depth error from stated target", "m", "Exact row target joined by player and region, bounce x minus target x", lambda r: r.dx),
        ("lateral_error", "Signed lateral error from stated target", "m", "Exact row target joined by player and region, bounce y minus target y; no handedness reflection", lambda r: r.dy),
        ("radial_error", "Radial execution error", "m", "Euclidean displacement from stated target, observed bounces only", lambda r: r.radial_error),
        ("radar_speed", "Recorded radar speed", "mph", "Current serve post-impact radar measurement; not a pre-motion predictor; extreme readings retained for QA", lambda r: r.speed),
    )
    report["measurements"] = [dict(key=f, label=label, unit=unit, definition=definition,
        role="post_impact_execution_measurement", **distribution(fn(r) for r in rows)) for f, label, unit, definition, fn in specs]
    report["measurements"] += [dict(key=f, label=label, unit="m", definition="Exact marked locations, one target per player/region shared by both periods; these summaries weight each target once",
        role="stated_target", **distribution(number(r[f]) for r in targets)) for f, label in (("target_x", "Stated target depth"), ("target_y", "Stated target lateral position"))]
    report["geometry"] = [histogram(((fn(r), r.group) for r in rows), edges, key, "m", label) for key, label, fn, edges in (
        ("bounce_depth", "Marginal observed depth coverage", lambda r: r.x, (0, 2, 4, 6.4, 8, 10)),
        ("bounce_lateral", "Marginal observed lateral coverage", lambda r: r.y, (-6, -4.115, -2, 0, 2, 4.115, 6)),
        ("depth_error", "Marginal signed depth error", lambda r: r.dx, (-3, -2, -1, 0, 1, 2, 3)),
        ("lateral_error", "Marginal signed lateral error", lambda r: r.dy, (-3, -2, -1, 0, 1, 2, 3)),
        ("radial_error", "Marginal radial error; bounces only", lambda r: r.radial_error, (.5, 1, 1.5, 2, 3, 4)),
    )]
    # Counts describe experimental support only; no target-error conditional mining.
    condition_counts = Counter((r.period, r.region) for r in rows)
    condition_groups = defaultdict(set)
    for r in rows:
        condition_groups[r.period, r.region].add(r.group)
    report["condition_support"] = [{"serve_period": period, "region": region,
        "attempts": count if count >= 10 and len(condition_groups[period, region]) >= 3 else None}
        for (period, region), count in sorted(condition_counts.items())]
    report["validation"] = {"source_hashes_verified": True, "all_targets_joined": True,
        "extended_source_key_unique": True, "short_key_not_treated_as_unique": True,
        "net_censoring_preserved": True, "partial_coordinate_pairs": 0,
        "borrowed_simulated_win_labels": False, "individual_profiles_exported": False,
        "measurement_accuracy_independently_verified": False, "ethics_statement_verified_from_primary_paper": True, "age_and_individual_consent_details_independently_verified": False}
    report["limitations"] = [
        "Conditional non-let description, not an all-attempt pre-serve forecast; all 19 lets excluded and separately counted, including five without coordinates",
        "The 437 observed-bounce error measurements omit 111 net-censored bounces; this selection must not become a claim of high overall accuracy",
        "Eight collegiate practice players and shared sessions do not establish professional-match, future-session or broad-population calibration",
        "Exact stated target coordinates are used internally, but no per-player target/bounce display or individual ranks are exposed",
        "Repeated short indices are retained; no invented first/second point pairs or completed-point outcomes",
        "The source's simulated win-probability surfaces are neither imported nor treated as observed labels; no optimal aim recommendation",
        "Radar speed is post-impact and some readings are missing; source extrema remain local-only, with no silent clipping or pre-motion speed input",
        "No joint/body angle, spin, verified readiness, injury or selection measurement is available in this source"]
    return report


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def run(root: Path, sport="all"):
    root = root.resolve()
    result = {}
    for selected in (("baseball", "tennis") if sport == "all" else (sport,)):
        paths, source = validate_sources(root, selected)
        if selected == "baseball":
            metadata = read_csv(paths["baseball_hitting/data/metadata.csv"], META_COLUMNS)
            poi = read_csv(paths["baseball_hitting/data/poi/poi_metrics.csv"], required=("session_swing", "session", *(f for f, *_ in BODY)))
            hit = read_csv(paths["baseball_hitting/data/poi/hittrax.csv"], HIT_COLUMNS)
            rows, counts = adapt_baseball(metadata, poi, hit)
            expected = {"source_swings": 677, "source_athletes": 98, "adult_swings": 643, "adult_athletes": 93,
                        "adult_recorded_exit_velocity_swings": 638, "adult_recorded_exit_velocity_athletes": 92,
                        "primary_swings": 571, "primary_athletes": 82}
            protocol = "BASEBALL_MECHANICS_PROTOCOL_DRAFT.md"
        else:
            serves = read_csv(paths["data/serves.csv"], SERVE_COLUMNS)
            targets = read_csv(paths["data/targets.csv"], TARGET_COLUMNS)
            rows, counts = adapt_tennis(serves, targets)
            expected = {"source_attempts": 567, "source_players": 8, "source_sessions": 8, "stated_targets": 32,
                        "lets_excluded": 19, "nonlet_attempts": 548, "nonlet_observed_bounce_pairs": 437,
                        "nonlet_net_censored": 111, "repeated_short_key_extra_rows_retained": 21}
            protocol = "TENNIS_EXECUTION_PROTOCOL_DRAFT.md"
        if any(counts[k] != value for k, value in expected.items()):
            raise ValueError("Reviewed mechanics denominator changed")
        plan = split_plan(rows, selected)
        plan_path = root / f"data/tactical/mechanics/{selected}_split_manifest.json"
        write_json(plan_path, plan)
        summary = baseball_summary(rows, counts, source, plan) if selected == "baseball" else tennis_summary(rows, targets, counts, source, plan)
        summary["split_description"]["private_membership_sha256"] = digest(plan_path)
        protocol_path = root / "docs/tactical" / protocol
        summary["protocol"] = {"status": "NO-FIT draft pending independent review and explicit approval",
                               "document": f"docs/tactical/{protocol}", "sha256": digest(protocol_path)}
        report_path = root / f"reports/tactical/mechanics/{selected}_summary.json"
        write_json(report_path, summary)
        result[selected] = summary
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--sport", choices=("all", "baseball", "tennis"), default="all")
    args = parser.parse_args(argv)
    summaries = run(args.root, args.sport)
    print(json.dumps({sport: {"phase": s["phase"], "predictive_gate": s["predictive_gate"],
          "counts": s["population"]["counts"], "summary": f"reports/tactical/mechanics/{sport}_summary.json"}
          for sport, s in summaries.items()}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
