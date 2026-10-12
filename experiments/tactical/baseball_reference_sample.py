"""Freeze the prespecified 2023 source-check sample and make local review packets.

This performs deterministic selection and mechanical checks, not human or
independent adjudication. All source excerpts stay in ignored data/tactical.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile

from experiments.tactical import baseball as bb

SEED = 20261011
STRATA = (
    "two_strike_fouls", "bunt_strike_three", "retained_np", "omitted_np",
    "runner_interruption", "midpa_pitcher_change", "pinch_hitter",
    "suspended_date_change", "automatic_count_change", "extra_inning_runner_placement",
)
COUNT_REASONS = frozenset(("source_count_conflict", "invalid_source_count",
    "raw_parsed_count_disagreement", "impossible_pre_pitch_count",
    "terminal_outcome_conflict", "terminal_walk_before_ball_four"))
DEFINITIONS = {
    "count_hand_cells": "One minimum-hash eligible delivery in every supported 12-count by 4-hand-pair cell",
    "pa_anchor": "For a qualifying PA use its minimum hash over all recorded delivered indices; select ten distinct PAs per stratum",
    "zero_delivery_anchor": "Use delivery_index=0 only for a qualifying PA with no recorded delivered pitches",
    "two_strike_fouls": "PA contains F or R at two pre-delivery strikes",
    "bunt_strike_three": "PA contains L, M or O at two pre-delivery strikes",
    "retained_np": "PA contains a raw NP exactly matched to an official parsed NP",
    "omitted_np": "PA contains a raw NP not represented by an official parsed row",
    "runner_interruption": "Non-NP parsed event with pa=0 and a base, out or score transition",
    "midpa_pitcher_change": "At least two raw-active pitchers delivered pitches within the PA",
    "pinch_hitter": "Raw sub with fielding position 11 after a raw NP/play assigned to this PA",
    "suspended_date_change": "First raw-play PA after each raw suspended comment, whether its pitch dates are exact or ambiguous",
    "automatic_count_change": "Raw PA cumulative sequence contains automatic count symbol A or V",
    "extra_inning_runner_placement": "First raw-play PA following a raw radj record",
    "mandatory_exclusions": "Every 2023 PA flagged with a count/adjudication reason, regardless of hash",
    "ordering": "SHA-256 hexadecimal digest ascending, then gid, PA and delivery index; union selected PAs across all reasons",
}


def rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def delivery_hash(gid: str, pa: int, index: int) -> str:
    return hashlib.sha256(f"{SEED}|{gid}|{pa}|{index}".encode()).hexdigest()


def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def context(root: Path):
    report = root / "reports/tactical/baseball/summary.json"
    summary = json.loads(report.read_text())
    if summary["phase"] != "descriptive" or summary["predictive_gate"]["fitting_allowed"]:
        raise ValueError("Reference sampling requires the closed descriptive gate")
    if bb.sha256(Path(bb.__file__)) != summary["parser_sha256"]:
        raise ValueError("Parser and source-derived summary do not match")
    season = next(s for s in summary["seasons"] if s["season"] == 2023)
    for record in season["local_derivatives"].values():
        if bb.sha256(Path(record["path"])) != record["sha256"]:
            raise ValueError("Derivative hash mismatch")
    provenance = {"summary_sha256": bb.sha256(report), "parser_sha256": summary["parser_sha256"],
        "protocol_sha256": bb.sha256(root / "docs/tactical/BASEBALL_PROTOCOL_DRAFT.md"),
        "selection_code_sha256": bb.sha256(Path(__file__)),
        "source_hashes": {s["filename"]: s["sha256"] for s in season["sources"]},
        "derivative_hashes": {k: v["sha256"] for k, v in season["local_derivatives"].items()}}
    return season, provenance


def select(root: Path) -> dict:
    """Only select and freeze. Do not inspect or adjudicate selected windows here."""
    season, provenance = context(root)
    parsed, _ = bb.load_parsed(bb.source_path(root, 2023, "plays"), 2023)
    pas = {}
    cells = {}
    play_pa = {}

    def get(key):
        if key not in pas:
            pas[key] = {"flags": set(), "pitchers": set(), "deliveries": 0, "anchor": None}
        return pas[key]

    for row in rows(Path(season["local_derivatives"]["pitches"]["path"])):
        l, f, target = row["lineage"], row["features"], row["target"]
        key = l["gid"], l["pa"]
        meta = get(key)
        index = f["pa_delivered_pitch_index"]
        anchor = (delivery_hash(*key, index), *key, index)
        meta["anchor"] = min(meta["anchor"], anchor) if meta["anchor"] else anchor
        meta["deliveries"] += 1
        meta["pitchers"].add(f["pitcher"])
        if target["symbol"] in "FR" and f["strikes"] == 2:
            meta["flags"].add("two_strike_fouls")
        if target["symbol"] in "LMO" and f["strikes"] == 2:
            meta["flags"].add("bunt_strike_three")
        if row["eligibility"]["swing"]:
            cell = f"{f['balls']}-{f['strikes']}|{f['batter_hand']}/{f['pitcher_hand']}"
            if cell not in cells or anchor < cells[cell]:
                cells[cell] = anchor

    for event in rows(Path(season["local_derivatives"]["events"]["path"])):
        key = event["gid"], event["pa"]
        meta = get(key)
        play_pa[event["gid"], event["raw_row"]] = key
        if event.get("retained_np"):
            meta["flags"].add("retained_np")
        if event.get("omitted_np"):
            meta["flags"].add("omitted_np")
        if any(s in event.get("raw_sequence", "") for s in "AV"):
            meta["flags"].add("automatic_count_change")
        pn = event.get("parsed_pn")
        if pn:
            p = parsed[key[0]][pn - 1]
            transition = (p["outs_pre"] != p["outs_post"] or p["runs"] != "0" or
                any(p[f"br{i}_pre"] != p[f"br{i}_post"] for i in range(1, 4)))
            if p["pa"] == "0" and p["event"] != "NP" and transition:
                meta["flags"].add("runner_interruption")
    with zipfile.ZipFile(bb.source_path(root, 2023, "eve")) as archive:
        for gid, records in bb.raw_games(archive):
            current = None
            suspended = runner = False
            for record in records:
                r = record.fields
                if r[0] == "com" and r[1].startswith("suspended,"):
                    suspended = True
                elif r[0] == "radj":
                    runner = True
                elif r[0] == "sub" and r[5] == "11":
                    if current is None:
                        raise ValueError("Pinch hitter without preceding raw-play PA")
                    get(current)["flags"].add("pinch_hitter")
                elif r[0] == "play":
                    current = play_pa[gid, record.source_row]
                    if suspended:
                        get(current)["flags"].add("suspended_date_change")
                    if runner:
                        get(current)["flags"].add("extra_inning_runner_placement")
                    suspended = runner = False
    mandatory = set()
    for issue in rows(Path(season["local_derivatives"]["issues"]["path"])):
        if issue["reason"] in COUNT_REASONS:
            mandatory.add((issue["gid"], issue["pa"]))
    for key, meta in pas.items():
        if len(meta["pitchers"]) > 1:
            meta["flags"].add("midpa_pitcher_change")
        if meta["anchor"] is None:
            meta["anchor"] = (delivery_hash(*key, 0), *key, 0)

    selected = defaultdict(list)
    selections = {}
    for cell, anchor in sorted(cells.items()):
        selected[anchor[1:3]].append("count_hand:" + cell)
    for stratum in STRATA:
        candidates = sorted(meta["anchor"] for meta in pas.values() if stratum in meta["flags"])
        selections[stratum] = {"candidate_pas": len(candidates), "selected_pas": min(10, len(candidates)),
            "anchors": [{"gid": a[1], "pa": a[2], "delivery_index": a[3], "sha256": a[0]}
                        for a in candidates[:10]]}
        for anchor in candidates[:10]:
            selected[anchor[1:3]].append(stratum)
    for key in mandatory:
        selected[key].append("mandatory_count_or_adjudication_exclusion")
    membership = {"schema_version": 1, "sport": "baseball", "phase": "descriptive",
        "task": "prespecified_reference_sample", "season": 2023, "seed": SEED,
        "selection_definitions": DEFINITIONS, "provenance": provenance,
        "frozen_before_adjudication": True, "adjudication_status": "not_performed",
        "supported_count_hand_cells": len(cells),
        "cell_selections": {c: {"gid": a[1], "pa": a[2], "delivery_index": a[3], "sha256": a[0]}
                            for c, a in sorted(cells.items())},
        "stratum_selections": selections, "mandatory_exclusion_pas": len(mandatory),
        "entries": [{"gid": key[0], "pa": key[1], "selection_reasons": sorted(reasons),
            "pa_anchor_delivery_index": pas[key]["anchor"][3], "pa_anchor_sha256": pas[key]["anchor"][0],
            "recorded_deliveries": pas[key]["deliveries"]} for key, reasons in sorted(selected.items())]}
    destination = root / "data/tactical/baseball/reference_sample"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "membership.json"
    payload = canonical(membership)
    if path.exists() and path.read_text() != payload:
        raise ValueError("Frozen membership differs; do not overwrite or reselect after inspection")
    if not path.exists():
        path.write_text(payload)
        (destination / "membership.sha256").write_text(bb.sha256(path) + "\n")
    if (destination / "membership.sha256").read_text().strip() != bb.sha256(path):
        raise ValueError("Frozen membership digest mismatch")
    return {"membership_sha256": bb.sha256(path), "selected_pas": len(selected),
        "count_hand_cells": len(cells), "strata": {s: {k: v for k, v in x.items() if k != "anchors"}
            for s, x in selections.items()}, "mandatory_exclusion_pas": len(mandatory)}


def independent_prefix_count(sequence: str, end: int):
    """Direct specification-based count replay, independent of parser count helper."""
    balls = strikes = 0
    prior = []
    for char in sequence[:end]:
        if char in bb.MARKERS:
            continue
        if char not in bb.ADMIN:
            prior.append(char)
        if char == "U":
            balls = strikes = None
        elif balls is not None:
            if char in {"B", "I", "P", "V"}:
                balls += 1
            elif char in {"A", "C", "K", "L", "M", "O", "Q", "S", "T"}:
                strikes += 1
            elif char in {"F", "R"} and strikes < 2:
                strikes += 1
    return balls, strikes, prior


def build_packet(root: Path) -> dict:
    season, provenance = context(root)
    destination = root / "data/tactical/baseball/reference_sample"
    member_path = destination / "membership.json"
    digest = bb.sha256(member_path)
    if digest != (destination / "membership.sha256").read_text().strip():
        raise ValueError("Reference membership has changed")
    membership = json.loads(member_path.read_text())
    if membership["provenance"] != provenance:
        raise ValueError("Sources, parser, protocol or selection implementation changed after freeze")
    selected = {(e["gid"], e["pa"]): e for e in membership["entries"]}
    pitches, events, issues = defaultdict(list), defaultdict(list), defaultdict(list)
    for kind, mapping in (("pitches", pitches), ("events", events), ("issues", issues)):
        for row in rows(Path(season["local_derivatives"][kind]["path"])):
            source = row["lineage"] if kind == "pitches" else row
            key = source["gid"], source["pa"]
            if key in selected:
                mapping[key].append(row)
    parsed, _ = bb.load_parsed(bb.source_path(root, 2023, "plays"), 2023)
    raw_by_game = {}
    with zipfile.ZipFile(bb.source_path(root, 2023, "eve")) as archive:
        rosters = bb.read_rosters(archive)
        wanted_games = {k[0] for k in selected}
        for gid, records in bb.raw_games(archive):
            if gid in wanted_games:
                raw_by_game[gid] = records
    checks, packet_files = [], []
    windows = destination / "windows"
    windows.mkdir(exist_ok=True)
    index = ["# Frozen 2023 baseball reference sample", "", f"Membership SHA-256: {digest}", "",
        "Status: machine packet prepared; independent human/reference adjudication is pending.",
        "Source excerpts are local only. Agreement is representation consistency, not physical ground truth.", "",
        bb.NOTICE, "", "## PA windows", ""]
    totals = Counter()
    for key, entry in sorted(selected.items()):
        gid, pa = key
        raw = raw_by_game[gid]
        lookup = {r.source_row: r for r in raw}
        actor = {}
        active_pitchers = {}
        for r in raw:
            if r.fields[0] in {"start", "sub"} and r.fields[5] == "1":
                active_pitchers[r.fields[3]] = r.fields[1]
            if r.fields[0] == "play":
                actor[r.source_row] = active_pitchers.get(str(1 - int(r.fields[2])))
        raw_rows = [e["raw_row"] for e in events[key]]
        first, last = min(raw_rows), max(raw_rows)
        preceding = [r.source_row for r in raw if r.fields[0] == "play" and r.source_row < first]
        following = [r.source_row for r in raw if r.fields[0] == "play" and r.source_row > last]
        lo = preceding[-1] if preceding else raw[0].source_row
        hi = following[0] if following else raw[-1].source_row
        raw_window = [r for r in raw if lo <= r.source_row <= hi]
        matched_pns = sorted({e["parsed_pn"] for e in events[key] if e.get("parsed_pn")})
        p_lo = max(1, min(matched_pns) - 1) if matched_pns else 1
        p_hi = min(len(parsed[gid]), max(matched_pns) + 1) if matched_pns else 1
        parsed_window = parsed[gid][p_lo - 1:p_hi]
        pa_checks = []
        for row in pitches[key]:
            l, f, t = row["lineage"], row["features"], row["target"]
            r = lookup[l["raw_row"]].fields
            balls, strikes, prior = independent_prefix_count(r[5], l["raw_symbol_offset"])
            checks_for_pitch = {
                "raw_symbol": r[5][l["raw_symbol_offset"]] == t["symbol"],
                "raw_batter": r[3] == f["batter"], "raw_active_pitcher": actor[l["raw_row"]] == f["pitcher"],
                "raw_inning_side": int(r[1]) == f["inning"] and int(r[2]) == f["batting_side"],
                "prefix_count": (balls, strikes) == (f["balls"], f["strikes"]),
                "prefix_delivery_index": len(prior) + 1 == f["pa_delivered_pitch_index"],
                "prefix_history": prior[-3:] == list(f["previous_three_pitch_outcomes"]),
                "eligible_count_bounds": not row["eligibility"]["swing"] or (balls in range(4) and strikes in range(3)),
                "date_ambiguity_gated": l["event_date"] is not None or (
                    "ambiguous_suspension_prefix_timing" in row["qa_exclusions"] and not row["eligibility"]["swing"]),
            }
            if l["parsed_pn"]:
                p = parsed[gid][l["parsed_pn"] - 1]
                checks_for_pitch.update({
                    "official_pre_outs": int(p["outs_pre"]) == f["outs"],
                    "official_pre_runs": (int(p["score_v"]), int(p["score_h"])) == (f["visitor_score"], f["home_score"]),
                    "official_pre_bases": [bool(p[f"br{i}_pre"]) for i in range(1, 4)] ==
                        [f["on_first"], f["on_second"], f["on_third"]],
                    "official_source_record_date": p["date"] == l["source_record_date"],
                })
            pa_checks.append({"delivery_index": f["pa_delivered_pitch_index"], "raw_row": l["raw_row"],
                "raw_symbol_offset": l["raw_symbol_offset"], "matched_fields": checks_for_pitch,
                "reconstructed_prefix_count": [balls, strikes], "qa_exclusions": row["qa_exclusions"]})
            totals.update({"delivery_checks": 1, "field_checks": len(checks_for_pitch),
                           "failed_field_checks": sum(not v for v in checks_for_pitch.values())})
        row_check = {"gid": gid, "pa": pa, "selection_reasons": entry["selection_reasons"],
            "machine_status": "pass" if all(all(c["matched_fields"].values()) for c in pa_checks) else "fail",
            "independent_adjudication_status": "pending", "pitch_checks": pa_checks,
            "source_quality_issues": issues[key]}
        checks.append(row_check)
        artifact = {"membership_sha256": digest, "entry": entry,
            "raw_window": [{"source_file": r.source_file, "source_row": r.source_row, "fields": r.fields} for r in raw_window],
            "official_parsed_window": parsed_window, "reconstructed_pitches": pitches[key],
            "reconstructed_events": events[key], "machine_checks": row_check}
        stem = f"{gid}_pa{pa:03d}"
        json_path = windows / f"{stem}.json"
        json_path.write_text(canonical(artifact))
        text = [f"# {gid} PA {pa}", "", "Selection: " + ", ".join(entry["selection_reasons"]),
            f"Membership SHA-256: {digest}", "", "Independent adjudication: PENDING", "",
            "## Reference checklist", "",
            "- [ ] Raw ordering, active pitcher/batter and substitutions", "- [ ] Roster/adjusted handedness",
            "- [ ] Each pre-pitch count and duplicate-prefix removal", "- [ ] Pre-event bases, outs and runs",
            "- [ ] Source-record date versus physical-date interval", "- [ ] Terminal label, taxonomy and documented exclusions",
            "- [ ] No unexplained discrepancy; record any objection below", "",
            "## Raw EV window (one neighboring play each side)", "", "```csv"]
        for r in raw_window:
            stream = io.StringIO(); csv.writer(stream, lineterminator="").writerow(r.fields)
            text.append(f"{r.source_row}: {stream.getvalue()}")
        text += ["```", "", "## Actors and roster metadata", ""]
        players = sorted({r["features"][k] for r in pitches[key] for k in ("batter", "pitcher")})
        for player in players:
            text.append(f"- {player}: roster bats {rosters[player][0]}, throws {rosters[player][1]}")
        text += ["", "## Official parsed window", "", "```json", json.dumps(parsed_window, indent=2, sort_keys=True), "```",
            "", "## Reconstructed deliveries and mechanical checks", "",
            "|Index|Symbol|Count|Batter / pitcher|Hand/method|Outs; bases; V-H runs|Date / interval|Eligible swing/contact|QA reasons|",
            "|---:|---|---|---|---|---|---|---|---|"]
        for row in pitches[key]:
            l, f, t, e = row["lineage"], row["features"], row["target"], row["eligibility"]
            base = "".join(str(int(f[k])) for k in ("on_first", "on_second", "on_third"))
            date = l["event_date"] or f"UNKNOWN [{l['event_date_min']}, {l['event_date_max']}]"
            text.append(f"|{f['pa_delivered_pitch_index']}|{t['symbol']}|{f['balls']}-{f['strikes']}|{f['batter']} / {f['pitcher']}|"
                f"{f['batter_hand']}/{f['pitcher_hand']} {f['batter_hand_method']}|{f['outs']}; {base}; {f['visitor_score']}-{f['home_score']}|"
                f"{date}|{e['swing']}/{e['contact_given_swing']}|{', '.join(row['qa_exclusions']) or t['taxonomy_exclusion'] or 'none'}|")
        text += ["", "Mechanical status: " + row_check["machine_status"], "",
            "Full matched-field booleans and row-level provenance are in the adjacent JSON file.",
            "This status is not human adjudication or independent physical measurement validation.", "",
            "## Reconstructed event checkpoints / known source issues", "", "```json",
            json.dumps({"events": events[key], "issues": issues[key]}, indent=2, sort_keys=True), "```",
            "", "## Independent reviewer notes", "", "Pending; do not interpret unchecked boxes as acceptance.", "", bb.NOTICE, ""]
        md_path = windows / f"{stem}.md"
        md_path.write_text("\n".join(text))
        packet_files.append({"gid": gid, "pa": pa, "markdown": str(md_path), "markdown_sha256": bb.sha256(md_path),
            "json": str(json_path), "json_sha256": bb.sha256(json_path)})
        index.append(f"- [{gid} PA {pa}](windows/{stem}.md): {', '.join(entry['selection_reasons'])}")
    (destination / "index.md").write_text("\n".join(index) + "\n")
    machine_path = destination / "machine_checks.json"
    machine_path.write_text(canonical({"membership_sha256": digest, "status": "pass" if not totals["failed_field_checks"] else "fail",
        "independent_adjudication_status": "pending", "totals": dict(totals), "entries": checks}))
    (destination / "packet_manifest.json").write_text(canonical({"membership_sha256": digest,
        "machine_checks_sha256": bb.sha256(machine_path), "files": packet_files}))
    aggregate = {"sport": "baseball", "phase": "descriptive", "task": "prespecified_reference_sample",
        "season": 2023, "membership_sha256": digest, "machine_checks_sha256": bb.sha256(machine_path),
        "selected_pas": len(selected), "selected_games": len(raw_by_game), "selected_deliveries": totals["delivery_checks"],
        "supported_count_hand_cells": membership["supported_count_hand_cells"],
        "strata": {s: {k: v for k, v in x.items() if k != "anchors"} for s, x in membership["stratum_selections"].items()},
        "mandatory_exclusion_pas": membership["mandatory_exclusion_pas"], "mechanical_checks": dict(totals),
        "independent_adjudication_status": "pending", "manual_adjudication_claimed": False,
        "fitting_allowed": False, "raw_windows_location": "ignored local data only",
        "provenance": provenance, "notice": bb.NOTICE}
    report = root / "reports/tactical/baseball/reference_sample.json"
    report.write_text(canonical(aggregate))
    if bb.sha256(member_path) != digest:
        raise ValueError("Frozen membership changed during packet generation")
    return aggregate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("select", "packet"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    result = select(args.root.resolve()) if args.stage == "select" else build_packet(args.root.resolve())
    print(canonical(result))


if __name__ == "__main__":
    main()
