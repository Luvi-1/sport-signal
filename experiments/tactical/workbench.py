"""Read-only, loopback-only workbench for independently staged tactical research.

This module never fetches data, loads executable models, trains or unlocks a test.
Run `python -m experiments.tactical.workbench index` after generating summaries,
then `python -m experiments.tactical.workbench serve`.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from . import model_views

ROOT = Path(__file__).resolve().parents[2]
WEB = Path(__file__).resolve().parent / "web"
REPORTS = {s: f"reports/tactical/{s}/summary.json" for s in
           ("soccer", "basketball", "baseball", "football", "tennis")}
AUX_REPORTS = {"baseball_mechanics": "reports/tactical/mechanics/baseball_summary.json",
               "tennis_execution": "reports/tactical/mechanics/tennis_summary.json"}
REPORT_FILES = {**REPORTS, **AUX_REPORTS}
INDEX = "reports/tactical/workbench_manifest.json"
MAX_BYTES = 2_000_000
STATSBOMB_LOGO = "data/tactical/soccer/source/img/SB - Icon Lockup - Colour positive.png"
PACKAGED_STATSBOMB_LOGO = "experiments/tactical/web/statsbomb-logo.png"
STATSBOMB_LOGO_SHA = "8ba5480785f0dc4be2342ec47c70509483eb79287f85f92be1dfba36fc2872a7"
CATALOG = [
    dict(id="soccer", name="Soccer", question="What shot context can we actually observe?",
         population="FA Women's Super League", unit="Recorded non-penalty shot",
         cutoff="Recorded shot state; partial defender/goalkeeper snapshots",
         measurement="Event-annotated geometry on a standardized 120 × 80 grid",
         unavailable=["Unseen defenders", "Intended target", "Joint mechanics in the event data", "Verified readiness"],
         mechanism="Distance, goal opening and observed defensive geometry change the shooting situation. A shot-only sample does not establish which unchosen action was best.",
         companion="Separate two-match provider-estimated 3-D pose study. Contact timing must be validated before any impact-labelled mechanics analysis.",
         source="https://github.com/statsbomb/open-data", credit="StatsBomb Open Data. Noncommercial research; provider attribution/logo requirements apply.",
         docs="docs/research/SOCCER_BASKETBALL_RESEARCH.md"),
    dict(id="basketball", name="Basketball", question="How does release context differ across recorded shots?",
         population="Ten sampled Liga ACB games", unit="Recorded field-goal release, including fouled misses",
         cutoff="At-release event/tracking representation",
         measurement="Court coordinates and defender distance in feet; provider-estimated tracking",
         unavailable=["General NBA transfer", "All possession choices", "Physical tracking accuracy", "Joint mechanics in this game source"],
         mechanism="Shot location, available shooting angle and opponent proximity describe the recorded release. Immediate field-goal scoring omits free throws and possession continuation.",
         companion="Bounded schema review of a separate nonprofessional free-throw source is complete. Mechanics fitting remains deferred because ages and release/contact alignment are unverified.",
         source="https://github.com/SkillCorner/opendata-basketball", credit="SkillCorner basketball open data, MIT; modifications and source pin documented.",
         docs="docs/research/SOCCER_BASKETBALL_RESEARCH.md"),
    dict(id="baseball", name="Baseball", question="What changes across count and pitch-outcome sequences?",
         population="MLB regular-season Retrosheet records", unit="Validated delivered pitch in reconstructed plate appearance",
         cutoff="State before the selected pitch; prior emitted symbols only",
         measurement="Recorded pitch-outcome codes and count/base/out/score state",
         unavailable=["Pitch type or trajectory", "Batting stance in Retrosheet", "Pitch intention", "Live-game joint mechanics"],
         mechanism="Count and previous observed pitch outcomes constrain the situation. Correct reconstruction must preserve pitcher substitutions and avoid counting cumulative pitch prefixes twice.",
         companion="A separate adult-only laboratory hitting analysis can use actual body-angle and contact measurements; elapsed event timing is unverified. One session per athlete limits the transport question.",
         source="https://www.retrosheet.org/", credit='The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".',
         docs="docs/research/baseball_football/README.md"),
    dict(id="football", name="American football", question="What tendencies accompany the observed at-snap setup?",
         population="NFL competitive regular-season run/pass plays", unit="Eligible play with validated charting join",
         cutoff="Final physical state at the snap, retrospectively charted",
         measurement="Formation, personnel, motion and contextual event annotations",
         unavailable=["The original play call", "Blocking assignments", "Live charting latency", "Body angles and leverage"],
         mechanism="Formation, personnel, motion and game state provide scouting context. Realized dropback includes sacks and scrambles; it does not recover intended play calls.",
         companion="Mechanics literature covers blocking, throwing, receiving and special teams; a rights-cleared large joint-motion source has not been established.",
         source="https://nflverse.nflverse.com/", credit="nflverse and FTN Data; source-specific CC BY / CC BY-SA notices apply.",
         docs="docs/research/baseball_football/README.md"),
    dict(id="tennis", name="Tennis", question="Where does a server direct the next recorded serve?",
         population="Volunteer-charted professional singles matches", unit="Eligible first/second-serve direction with validated pre-point state",
         cutoff="Pre-point score and prior completed points; historical matches use an assumed source-date + 21-day embargo, not verified ingestion. No current rally suffix",
         measurement="Wide/body/T categories; charted direction is not precise ball coordinates",
         unavailable=["Professional intended aim", "Ball spin", "Continuous player positions", "Joint mechanics and verified readiness"],
         mechanism="Score, serve number, handedness and past tendencies describe the situation. Volunteer charting and missing/ambiguous points limit the represented population.",
         companion="A separate eight-player collegiate experiment records stated targets, radar speed and bounce locations, with net censoring and a conditional non-let denominator.",
         source="https://github.com/JeffSackmann/tennis_MatchChartingProject", credit="Jeff Sackmann, Tennis Abstract and Match Charting Project contributors; CC BY-NC-SA 4.0.",
         docs="docs/research/tennis/README.md"),
]
DOCUMENTS = {"research": "docs/research/FIVE_SPORT_RESEARCH_SYNTHESIS.md",
             "method": "docs/tactical/EXECUTION_STAGES.md",
             "learning": "docs/tactical/LEARNING_GUIDE.md",
             "model_views": "docs/tactical/MODEL_VIEWS.md",
             "license_scope": "docs/tactical/notices/DERIVED_MATERIAL_LICENSES.md",
             "statsbomb_notice": "docs/tactical/notices/STATSBOMB_NOTICE.md",
             "skillcorner_notice": "docs/research/notices/SKILLCORNER_BASKETBALL_MIT.txt",
             "retrosheet_notice": "docs/tactical/notices/RETROSHEET_NOTICE.txt",
             "nflverse_ftn_notice": "docs/tactical/notices/NFLVERSE_FTN_NOTICE.md",
             "nflverse_pbp_notice": "docs/tactical/notices/NFLVERSE_PBP_NOTICE.md",
             "mcp_notice": "docs/tactical/notices/MCP_NOTICE.md",
             "openbiomechanics_license": "docs/tactical/notices/OPENBIOMECHANICS_DATA_LICENSE.md",
             "mechanics_attribution": "docs/tactical/notices/MECHANICS_ATTRIBUTION.md",
             "byu_license": "docs/tactical/notices/BYU_MIT.txt"}
DOCUMENTS.update({c["id"]: c["docs"] for c in CATALOG})


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def confined(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path escapes the project")
    return path


def validate_json(value, depth=0):
    if depth > 24:
        raise ValueError("Summary nesting exceeds limit")
    if isinstance(value, dict):
        if len(value) > 2000 or any(not isinstance(k, str) or len(k) > 300 for k in value):
            raise ValueError("Invalid summary object")
        for x in value.values():
            validate_json(x, depth + 1)
    elif isinstance(value, list):
        if len(value) > 10000:
            raise ValueError("Summary array exceeds limit")
        for x in value:
            validate_json(x, depth + 1)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Nonfinite report number")
    elif isinstance(value, str):
        if len(value) > 100_000:
            raise ValueError("Summary text exceeds limit")
    elif value is not None and not isinstance(value, (int, bool)):
        raise ValueError("Unsupported report value")


def read_summary(path: Path) -> tuple[dict, str]:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Summary is too large; aggregate it before indexing")
    raw = path.read_bytes()
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("A summary must be an object")
    validate_json(result)
    return result, sha256(raw)


def validate_report(sport: str, summary: dict):
    expected = {"baseball_mechanics":"baseball", "tennis_execution":"tennis"}.get(sport, sport)
    actual = "football" if summary.get("sport") == "american_football" else summary.get("sport")
    if actual != expected or summary.get("phase") != "descriptive":
        raise ValueError("Summary sport/phase does not match the descriptive contract")
    gate = summary.get("predictive_gate")
    if not isinstance(gate, dict) or gate.get("status") != "closed" or gate.get("fitting_allowed") is not False:
        raise ValueError("An explicit closed predictive gate is required")


def verify_generator(root: Path, sport: str, summary: dict) -> str:
    if any(key in summary and not isinstance(summary[key], dict) for key in ("provenance", "source", "parser_dependencies_sha256")):
        raise ValueError("Generator provenance must contain objects")
    expected = summary.get("parser_sha256") or summary.get("provenance", {}).get("parser_code_sha256") or summary.get("source", {}).get("adapter_sha256")
    module = "mechanics" if sport in AUX_REPORTS else sport
    actual = sha256(confined(root, f"experiments/tactical/{module}.py").read_bytes())
    if expected != actual:
        raise ValueError("Summary generator fingerprint is absent or stale")
    if sport in {"soccer", "basketball"}:
        dependencies = summary.get("parser_dependencies_sha256", {})
        required = {f"experiments/tactical/{sport}.py", "experiments/tactical/shot_sources.py"}
        if set(dependencies) != required:
            raise ValueError("Shot parser dependency manifest is incomplete")
        for path, digest in dependencies.items():
            if sha256(confined(root, path).read_bytes()) != digest:
                raise ValueError("Shot parser dependency changed")
        contract = "docs/research/TACTICAL_MEASUREMENT_CONTRACT.json"
        if sha256(confined(root, contract).read_bytes()) != summary.get("contract_sha256"):
            raise ValueError("Measurement contract changed")
    if sport == "tennis":
        manifest = root / "docs/research/tennis/source_manifest.json"
        if sha256(manifest.read_bytes()) != summary.get("provenance", {}).get("manifest_sha256"):
            raise ValueError("Tennis source manifest changed")
    if sport in AUX_REPORTS:
        relative = "docs/research/baseball_football/openbiomechanics_manifest.json" if sport == "baseball_mechanics" else "docs/research/tennis/source_manifest.json"
        if sha256(confined(root, relative).read_bytes()) != summary.get("source", {}).get("manifest_sha256"):
            raise ValueError("Mechanics source manifest changed")
    return actual


def index_reports(root: Path) -> dict:
    """Explicitly bind existing local summary bytes; never scans raw directories."""
    reports = {}
    for sport, relative in REPORT_FILES.items():
        path = confined(root, relative)
        if path.exists():
            summary, digest = read_summary(path)
            validate_report(sport, summary)
            generator = verify_generator(root, sport, summary)
            reports[sport] = {"path": relative, "sha256": digest, "generator_sha256": generator}
    manifest = {"schema_version": 1, "phase": "descriptive_only", "reports": reports,
                "meaning": "Byte-integrity index of local aggregate summaries; not model validation or a source-license grant."}
    path = confined(root, INDEX)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def report_status(root: Path, sport: str) -> tuple[str, dict | None]:
    if sport not in REPORT_FILES:
        raise KeyError(sport)
    try:
        index = confined(root, INDEX)
        if not index.exists():
            return "not_indexed", None
        manifest, _ = read_summary(index)
        if manifest.get("schema_version") != 1 or manifest.get("phase") != "descriptive_only":
            raise ValueError("Invalid index schema")
        if not isinstance(manifest.get("reports"), dict):
            raise ValueError("Summary index reports must be an object")
        record = manifest["reports"].get(sport)
        if record is None:
            return "not_available", None
        if not isinstance(record, dict) or record.get("path") != REPORT_FILES[sport]:
            raise ValueError("Unexpected summary path")
        summary, digest = read_summary(confined(root, REPORT_FILES[sport]))
        validate_report(sport, summary)
        if verify_generator(root, sport, summary) != record.get("generator_sha256"):
            raise ValueError("Generator changed since indexing")
        if digest != record["sha256"]:
            return "integrity_mismatch", None
        return "descriptive_available", summary
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        return "invalid_artifact", None


def catalog(root: Path) -> dict:
    result = []
    for entry in CATALOG:
        status, _ = report_status(root, entry["id"])
        numerical_status, _ = model_views.load_verified_view(root, entry["id"])
        result.append({**entry, "status": status, "predictive_status": numerical_status})
    return {"schema_version": 1, "mode": "local_descriptive_research", "sports": result,
            "notice": "Descriptive source views remain available. Numerical results appear only after separate independent final-report verification; no pooled cross-sport accuracy."}


def make_server(root: Path, port: int = 8765) -> ThreadingHTTPServer:
    root = root.resolve()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Do not persist URLs, IDs, or local data in access logs.

        def respond(self, code, data: bytes, kind="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(data)

        def json(self, code, value):
            self.respond(code, json.dumps(value, allow_nan=False).encode())

        def do_GET(self):
            host = self.headers.get("Host", "")
            valid = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            origin = self.headers.get("Origin")
            if host not in valid or (origin and origin != f"http://{host}") or self.headers.get("Sec-Fetch-Site") == "cross-site":
                self.json(403, {"error": "Only same-origin local access is allowed"})
                return
            url = urlsplit(self.path)
            if url.query or url.fragment:
                self.json(400, {"error": "Queries are not supported"})
                return
            path = url.path
            assets = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
            if path in assets:
                name, kind = assets[path]
                self.respond(200, (WEB / name).read_bytes(), kind)
            elif path == "/provider/statsbomb-logo.png":
                try:
                    logo = confined(root, STATSBOMB_LOGO)
                    if not logo.exists():
                        logo = confined(root, PACKAGED_STATSBOMB_LOGO)
                    if logo.stat().st_size > MAX_BYTES:
                        raise ValueError("Unexpected logo size")
                    raw = logo.read_bytes()
                    if sha256(raw) != STATSBOMB_LOGO_SHA:
                        raise ValueError("Logo integrity mismatch")
                    self.respond(200, raw, "image/png")
                except (OSError, ValueError):
                    self.json(404, {"error": "Verified provider logo is not installed"})
            elif path == "/api/catalog":
                self.json(200, catalog(root))
            elif path.startswith("/api/model-view/"):
                task = path.removeprefix("/api/model-view/")
                if task not in model_views.TASKS:
                    self.json(404, {"error": "Unknown numerical task"})
                    return
                payload = model_views.response(root, task)
                self.json(200 if payload["view"] is not None else 409, payload)
            elif path.startswith("/api/summary/"):
                sport = path.removeprefix("/api/summary/")
                if sport not in REPORT_FILES:
                    self.json(404, {"error": "Unknown sport"})
                    return
                status, summary = report_status(root, sport)
                self.json(200 if summary is not None else 409, {"status": status, "summary": summary})
            elif path.startswith("/api/document/"):
                key = path.removeprefix("/api/document/")
                if key not in DOCUMENTS:
                    self.json(404, {"error": "Unknown document"})
                    return
                try:
                    doc = confined(root, DOCUMENTS[key])
                    if doc.stat().st_size > MAX_BYTES:
                        raise ValueError("Document too large")
                    self.json(200, {"title": key, "text": doc.read_text()})
                except (OSError, ValueError):
                    self.json(404, {"error": "Document is not available in this installation"})
            else:
                self.json(404, {"error": "Unknown route"})

        def do_POST(self):
            self.json(405, {"error": "Read-only workbench"})
        do_PUT = do_POST
        do_DELETE = do_POST
        do_PATCH = do_POST

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["index", "serve"])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.action == "index":
        print(json.dumps(index_reports(args.root), indent=2))
    else:
        with make_server(args.root, args.port) as server:
            print(f"Local research workbench: http://127.0.0.1:{server.server_port}", flush=True)
            print("Read-only; no download, fitting, holdout unlock or public deployment.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass

if __name__ == "__main__":
    main()
