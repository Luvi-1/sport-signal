"""Explicit, fail-closed SOURCE packaging. Default: inventory only; never publish.

The old package_release.py is deliberately not imported or executed. An external
exact review is required even to validate a final package. See RELEASE_POLICY.md.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TASKS = ("soccer", "basketball", "baseball", "football", "tennis", "baseball_mechanics", "tennis_execution")
ARCHIVE = "artifacts/basketball_preservation/four-sport-delivered.zip"
BASE_MANIFEST = "artifacts/basketball_preservation/four-sport-publish-manifest.json"
BASE_HASHES = "artifacts/basketball_preservation/four_sport_hashes.json"
# Trust anchors recorded from the delivered files, not learned from an editable draft.
PRESERVED_SHA256 = {
    ARCHIVE: "03e1cc9ae25598d249669a251f527db5e177d1b5b88f48879e60e029ea5016c3",
    BASE_MANIFEST: "5a609522a8bb912eccce5bad61f2ef021a2dceae1b6b68fe9be3e6b02f869b60",
    BASE_HASHES: "70e8228ebbbe4e17480bb0ee495a3c95948f59d218296c911b3e5b51a1758978",
}
PREFIX = "sports-analytics/"
MAX_FILE = 2_000_000
DRAFT_DIR = "artifacts/tactical/release_draft"
VIEW_REVIEW = "docs/tactical/INDEPENDENT_FINAL_MODEL_VIEW_REVIEW.json"
SNAPSHOT_REVIEW = "docs/tactical/INDEPENDENT_AGGREGATE_SNAPSHOT_REVIEW.json"
RESULT_REVIEW = "docs/tactical/INDEPENDENT_FINAL_NUMERICAL_REVIEW.json"
GLOBAL_FREEZE = "artifacts/tactical/EVALUATION_FREEZE.json"
STATSBOMB_LOGO_SHA256 = "8ba5480785f0dc4be2342ec47c70509483eb79287f85f92be1dfba36fc2872a7"
FINAL_MANIFEST = "TACTICAL_PUBLISH_MANIFEST.json"
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
NFL_SNAPSHOT = "snapshots/nfl_regular_2010_2025.csv.gz"

PRIVACY_COPIES = ({'original_path': 'experiments/tactical/mechanics.py',
  'archive_path': 'experiments/tactical/mechanics.py',
  'staged_path': 'artifacts/tactical/release_public_copies/experiments/tactical/mechanics.py',
  'original_sha256': 'd6a9a82170b6cbf5cb1aaa2b454896058317652e52802cb276a52927e9133a36',
  'public_sha256': 'f4a5694ad668f5301fb8fd16d89bec3646f1ff0c71d27c0f90711bffaf35663d',
  'operation': 'remove_source_speed_extremum_from_explanatory_text',
  'edits': [{'start': 35913,
             'end': 36060,
             'replacement': 'Radar speed is post-impact and some readings are missing; source extrema remain '
                            'local-only, with no silent clipping or pre-motion speed input'}]},
 {'original_path': 'tests/test_tactical_mechanics.py',
  'archive_path': 'tests/test_tactical_mechanics.py',
  'staged_path': 'artifacts/tactical/release_public_copies/tests/test_tactical_mechanics.py',
  'original_sha256': 'b6c0c969c08da29953e9837be1e8f4d84f7dd1d9109e5c6906b379c60cf7ef49',
  'public_sha256': 'b9b229e4f875a1c5494635df19f2a743d0fae50e638c7d6d6008544b791850d4',
  'operation': 'replace_observed_extremum_with_fabricated_test_fixture',
  'edits': [{'start': 10852,
             'end': 10930,
             'replacement': '        # Deliberately fabricated, nonphysical speed fixture; never a source '
                            'observation.\n'
                            '        serves[0].update(speed_mph="1000.25", '
                            'simulated_win_probability="0.999")'},
            {'start': 10981,
             'end': 11027,
             'replacement': '        self.assertEqual(rows[0].speed, 1000.25)'}]},
 {'original_path': 'docs/tactical/TENNIS_EXECUTION_PROTOCOL_DRAFT.md',
  'archive_path': 'docs/tactical/TENNIS_EXECUTION_PROTOCOL_PUBLIC.md',
  'staged_path': 'artifacts/tactical/release_public_copies/docs/tactical/TENNIS_EXECUTION_PROTOCOL_PUBLIC.md',
  'original_sha256': '654ea8bc951026ced3e57bb57fac2558feb6d9b0df9eeaeff5616beab66ce072',
  'public_sha256': '9738e25edbf62c881229de0904f0083323f187e4b5b48b5fceac73d0fb6d8746',
  'operation': 'remove_source_speed_extrema_and_make_individual_diagnostics_local_only',
  'edits': [{'start': 4295,
             'end': 4464,
             'replacement': 'are missing across all source attempts; observed speed extrema remain '
                            'local-only.\n'
                            'No silent clipping is applied. No joint angles, racket pose, spin or response '
                            'latency\n'
                            'are measured.'},
            {'start': 10318,
             'end': 10694,
             'replacement': 'Privately retain the eight held-out-player paired losses, fixed pseudonymous\n'
                            'labels and support counts for numerical auditing only. These individual and\n'
                            'small-cell participant diagnostics, trial records and rankings remain '
                            'local-only\n'
                            'and are not part of this public protocol or aggregate release. Public displays\n'
                            'contain no player-level results. The numerical comparison and uncertainty\n'
                            'specification below are unchanged.'}]})

PRIVACY_COPIES = (*PRIVACY_COPIES, {'original_path': 'experiments/tactical/mechanics_model.py',
 'archive_path': 'experiments/tactical/mechanics_model.py',
 'staged_path': 'artifacts/tactical/release_public_copies/experiments/tactical/mechanics_model.py',
 'original_sha256': '5aaecaceec5b654649bfcec94e5bbafa0b4a42529bf6b7f0c23f44aa0114e91a',
 'public_sha256': '0f2ccbab35a901386375a884bd1a2181856cf778fda5d0db87efd998c75eba74',
 'operation': 'repair_public_protocol_path_only',
 'edits': [{'start': 2044, 'end': 2078, 'replacement': 'TENNIS_EXECUTION_PROTOCOL_PUBLIC.md'}]})

PRIVACY_STAGE = "artifacts/tactical/release_public_copies"
PRIVACY_PROVENANCE = PRIVACY_STAGE + "/PRIVACY_COPY_PROVENANCE.json"
PUBLIC_COPY_NOTE = "docs/tactical/PUBLIC_SOURCE_RELEASE_NOTES.md"
DERIVED_LICENSE_NOTICE = "docs/tactical/notices/DERIVED_MATERIAL_LICENSES.md"
REQUIRED_EXCLUSIONS = (
    "docs/research/INDEPENDENT_METHOD_REVIEW.md",
    "docs/research/SPL_BOUNDED_SCHEMA_ADDENDUM.md",
    "docs/research/baseball_football/OPENBIOMECHANICS_AUDIT.md",
    "docs/research/baseball_football/RESEARCH_BRIEF.md",
    "docs/research/baseball_football/football_other_roles_review.md",
    "docs/research/tennis/data_contract.md",
    "docs/research/tennis/tactical_model_design.md",
)

SOURCE_RULES = {
    "original_code": {"license": "Original project code: MIT", "checks": ["original_code_only"]},
    "original_research": {"license": "Original writing; cited works retain their rights", "checks": ["no_copied_source_documents"]},
    "statsbomb": {"license": "StatsBomb custom noncommercial agreement", "checks": ["noncommercial_use_confirmed", "no_raw_or_row_derived_data", "credit_visible", "official_logo_present", "logo_use_reviewed"]},
    "skillcorner_basketball": {"license": "MIT; SkillCorner basketball notice", "checks": ["copyright_notice_retained", "source_pin_and_modifications_disclosed"]},
    "skillcorner_soccer": {"license": "MIT; SkillCorner soccer notice", "checks": ["copyright_notice_retained", "source_pin_and_modifications_disclosed"]},
    "retrosheet": {"license": "Retrosheet attribution notice", "checks": ["required_credit_retained", "modifications_disclosed"]},
    "nflverse_pbp": {"license": "CC BY 4.0 (release-specific exceptions still apply)", "checks": ["attribution_and_license_retained", "modifications_disclosed"]},
    "nflverse_ftn": {"license": "CC BY-SA 4.0; FTN Data via nflverse", "checks": ["attribution_and_license_retained", "sharealike_scope_reviewed", "modifications_disclosed"]},
    "mcp": {"license": "CC BY-NC-SA 4.0", "checks": ["noncommercial_use_confirmed", "attribution_and_license_retained", "sharealike_scope_reviewed", "modifications_disclosed"]},
    "openbiomechanics": {"license": "CC BY-NC-SA 4.0 plus affiliation exclusion", "checks": ["noncommercial_use_confirmed", "attribution_and_license_retained", "sharealike_scope_reviewed", "affiliation_exclusion_confirmed", "adult_only_aggregate", "participant_trial_and_pseudolabel_values_absent", "small_cells_suppressed", "health_profiles_absent", "modifications_disclosed"]},
    "byu": {"license": "MIT; participant privacy is a separate restriction", "checks": ["copyright_notice_retained", "all_eight_individual_results_suppressed", "participant_trial_and_pseudolabel_values_absent", "small_cells_suppressed", "health_profiles_absent", "ages_unverified_safeguards", "modifications_disclosed"]},
    "spl": {"license": "CC BY-NC-SA 4.0 plus affiliation exclusion", "checks": ["noncommercial_use_confirmed", "attribution_and_license_retained", "sharealike_scope_reviewed", "affiliation_exclusion_confirmed", "participant_trial_and_pseudolabel_values_absent", "small_cells_suppressed", "health_profiles_absent", "ages_unverified_safeguards", "modifications_disclosed"]},
}
STUDY_SOURCES = {
    "soccer": ("statsbomb",), "basketball": ("skillcorner_basketball",), "baseball": ("retrosheet",),
    "football": ("nflverse_pbp", "nflverse_ftn"), "tennis": ("mcp",),
    "baseball_mechanics": ("openbiomechanics",), "tennis_execution": ("byu",),
}
MIXED_RESEARCH_SOURCES = tuple(sorted({source for sources in STUDY_SOURCES.values() for source in sources} | {"skillcorner_soccer", "spl"}))
NOTICES = {
    "statsbomb": ("docs/tactical/notices/STATSBOMB_NOTICE.md", "experiments/tactical/web/statsbomb-logo.png"),
    "skillcorner_basketball": ("docs/research/notices/SKILLCORNER_BASKETBALL_MIT.txt",),
    "skillcorner_soccer": ("docs/research/notices/SKILLCORNER_SOCCER_MIT.txt",),
    "retrosheet": ("docs/tactical/notices/RETROSHEET_NOTICE.txt",),
    "nflverse_pbp": ("docs/tactical/notices/NFLVERSE_PBP_NOTICE.md",),
    "nflverse_ftn": ("docs/tactical/notices/NFLVERSE_FTN_NOTICE.md",),
    "mcp": ("docs/tactical/notices/MCP_NOTICE.md",),
    "openbiomechanics": ("docs/tactical/notices/OPENBIOMECHANICS_DATA_LICENSE.md", "docs/tactical/notices/MECHANICS_ATTRIBUTION.md"),
    "byu": ("docs/tactical/notices/BYU_MIT.txt", "docs/tactical/notices/MECHANICS_ATTRIBUTION.md"),
    "spl": ("docs/research/notices/SPL_LICENSE.txt",),
}
for _source in NOTICES:
    NOTICES[_source] = (*NOTICES[_source], DERIVED_LICENSE_NOTICE)

CONTENT_CHECKS = ("full_file_content_reviewed", "no_secrets_or_credentials", "no_raw_or_row_derived_observations",
                  "no_models_or_weights", "no_private_memberships_or_identifiers", "no_sensitive_individual_profiles",
                  "no_source_documents_or_papers", "no_unreviewed_small_cells",
                  "automated_test_results_reviewed", "browser_validation_status_disclosed", "model_cards_match_final_status", "privacy_copy_provenance_verified")
EXCLUSIONS = [
    "Every raw/private/cache data file, except the preserved licensed normalized NFL snapshot",
    "Every unlisted path; no recursive directory or suffix allowlisting",
    "Unreviewed research JSON, including StatsBomb per-match/coverage and hoopR audits",
    "Source-case predictions, feature matrices, model parameters/weights/pickles, SQLite databases",
    "Participant/trial/pseudolabel values, eight BYU individual results, small cells and health profiles",
    "Private group plans, run bindings, stage approvals, source acquisition manifests and final runner reports",
    "Downloaded source PDFs/documents, environments, caches, Laya weights, secrets and logs",
]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode()


def parse(raw: bytes):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("Duplicate JSON key")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def exact(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise ValueError("Unexpected or missing review/schema fields")


def relative(name: str) -> str:
    if (not isinstance(name, str) or not name or any(c in name for c in "\\:*?<>|\"") or any(ord(c) < 32 for c in name)
            or name != PurePosixPath(name).as_posix() or PurePosixPath(name).is_absolute()
            or any(p in (".", "..", "") for p in name.split("/"))):
        raise ValueError("Unsafe relative path")
    return name


def path_for(root: Path, name: str) -> Path:
    name = relative(name)
    root = root.resolve()
    path = root
    for part in name.split("/"):
        path = path / part
        if path.is_symlink():
            raise ValueError("Symlink path forbidden")
    if not path.resolve().is_relative_to(root):
        raise ValueError("Path escaped project")
    return path


def read_bytes(root: Path, name: str, limit=MAX_FILE) -> bytes:
    """Bounded descriptor reads reject aliases and file changes, including parents."""
    path_for(root, name)
    root_fd = os.open(root.resolve(), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptor = root_fd
    opened = [root_fd]
    try:
        for part in relative(name).split("/")[:-1]:
            descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            opened.append(descriptor)
        fd = os.open(name.split("/")[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        opened.append(fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError("Missing, aliased, nonregular or oversized file: " + name)
        chunks, remaining = [], limit + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk); remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_nlink)
        if len(raw) > limit or len(raw) != before.st_size or identity(before) != identity(after):
            raise ValueError("File changed during bounded read: " + name)
        return raw
    finally:
        for fd in reversed(opened):
            os.close(fd)


def _privacy_copy(raw: bytes, mapping: dict) -> bytes:
    if digest(raw) != mapping["original_sha256"]:
        raise ValueError("Frozen privacy-copy original changed")
    edits = sorted(mapping["edits"], key=lambda edit: edit["start"])
    last = 0
    for edit in edits:
        if not (type(edit["start"]) is int and type(edit["end"]) is int
                and last <= edit["start"] < edit["end"] <= len(raw)):
            raise ValueError("Invalid fixed privacy span")
        last = edit["end"]
    result = raw
    for edit in reversed(edits):
        result = result[:edit["start"]] + edit["replacement"].encode() + result[edit["end"]:]
    if digest(result) != mapping["public_sha256"] or len(result) > MAX_FILE:
        raise ValueError("Fixed privacy transformation differs from reviewed public bytes")
    return result


def copy_provenance(mapping: dict) -> dict:
    return {key: mapping[key] for key in ("original_path", "archive_path", "original_sha256", "public_sha256", "operation")} | {
        "scope": "privacy_only_copy_not_executed_source",
        "edits": [{"start": edit["start"], "end": edit["end"],
                   "replacement_sha256": digest(edit["replacement"].encode())} for edit in mapping["edits"]]}


def stage_privacy_copies(root: Path) -> dict:
    """Write only the fixed public-copy paths; never modify executed originals."""
    pending = {}
    for mapping in PRIVACY_COPIES:
        raw = read_bytes(root, mapping["original_path"])
        pending[mapping["staged_path"]] = _privacy_copy(raw, mapping)
    provenance = {"schema_version": 1, "status": "privacy_copies_prepared_not_approved",
                  "copies": [copy_provenance(mapping) for mapping in PRIVACY_COPIES]}
    pending[PRIVACY_PROVENANCE] = canonical(provenance)
    # Validate every existing destination before making any change. No alternate
    # filenames, user-supplied mappings, overwrites or fallback-to-original exist.
    for name, raw in pending.items():
        path = path_for(root, name)
        if path.exists() and read_bytes(root, name) != raw:
            raise ValueError("Existing privacy staging bytes differ; refusing overwrite")
    for name, raw in pending.items():
        path = path_for(root, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(raw)
                output.flush(); os.fsync(output.fileno())
        if read_bytes(root, name) != raw:
            raise ValueError("Privacy staging verification failed")
    return provenance


def candidate_spec() -> list[dict]:
    """Finite path catalog. Discovery of a new file never grants it eligibility."""
    entries = {}
    def add(paths, kind, sources=("original_code",), required=False):
        for name in paths:
            relative(name)
            if name in entries:
                raise ValueError("Duplicate catalog path: " + name)
            entries[name] = dict(path=name, kind=kind, sources=sorted(sources), required=required,
                                 risk="source_terms_and_privacy_review" if set(sources) - {"original_code", "original_research"} else "content_review")
    add(["experiments/tactical/" + n + ".py" for n in (
        "__init__", "_soccer_football_common", "baseball", "baseball_model", "baseball_reference_sample", "basketball", "basketball_model",
        "football", "football_model", "gates", "mechanics", "mechanics_model", "metrics", "model_views", "model_view_projection", "shot_sources", "soccer", "soccer_model", "tennis", "tennis_model", "tennis_recovery", "workbench")], "code", required=True)
    add(["experiments/tactical/web/" + n for n in ("app.js", "index.html", "style.css")], "web_asset", required=True)
    add(["scripts/package_tactical_release.py", "scripts/qa_tactical_workbench.py", "scripts/test_tactical_dom.cjs", "scripts/test_tactical_model_views_dom.cjs"], "code", required=True)
    add(["scripts/research/" + n + ".py" for n in ("audit_skillcorner_all_tracking", "audit_skillcorner_basketball", "audit_soccer_pose", "audit_spl_sample_quality", "audit_statsbomb_coverage", "audit_statsbomb_samples", "check_tennis_cache_lineage")], "code")
    add(["tests/test_tactical_" + n + ".py" for n in ("baseball_model", "baseball_parser", "baseball_reference", "basketball", "basketball_model", "cache_lineage", "development_freeze", "football", "football_model", "gates", "mechanics", "mechanics_model", "mechanics_sources", "metrics", "model_views", "model_view_projection", "nfl_independent_flow", "release", "soccer", "soccer_model", "tennis", "tennis_model", "tennis_model_pipeline", "tennis_recovery", "workbench")], "test", required=True)
    add(["docs/tactical/" + n + ".md" for n in ("EXECUTION_STAGES", "LEARNING_GUIDE", "MODEL_VIEWS", "MODEL_VIEW_PROJECTION", "RELEASE_POLICY", "RELIABILITY_BIN_CONVENTIONS", "WORKBENCH")], "documentation", ("original_research",), True)
    add([SNAPSHOT_REVIEW], "public_provenance", ("original_research",))
    add([PUBLIC_COPY_NOTE], "documentation", ("original_research", "byu", "openbiomechanics"), True)
    add(["START_HERE_FIVE_SPORTS.md"], "documentation", MIXED_RESEARCH_SOURCES, True)
    add(["docs/tactical/BENCHMARK_RESULTS.md"], "research_synthesis",
        tuple(sorted({source for sources in STUDY_SOURCES.values() for source in sources})), True)
    add(["docs/tactical/TENNIS_RECOVERY.md"], "documentation", ("mcp",), True)
    for task in TASKS:
        sources = STUDY_SOURCES[task]
        protocol = "TENNIS_EXECUTION" if task == "tennis_execution" else task.upper()
        protocol_path = ("docs/tactical/TENNIS_EXECUTION_PROTOCOL_PUBLIC.md" if task == "tennis_execution"
                         else f"docs/tactical/{protocol}_PROTOCOL_DRAFT.md")
        add([protocol_path], "documentation", sources, True)
        add([f"docs/tactical/model_cards/{task}.md"], "model_card", sources, True)
        add([f"reports/tactical/model_views/{task}.json"], "sanitized_final_aggregate", sources)
        add([f"reports/tactical/release_status/{task}.json"], "terminal_status", sources)
    for task in TASKS[:5]:
        add([f"docs/tactical/{task}_model.md", f"docs/tactical/{task}_parser.md"], "documentation", STUDY_SOURCES[task], True)
    add(["docs/tactical/mechanics_measurements.md", "docs/tactical/mechanics_models.md"], "documentation", ("openbiomechanics", "byu"), True)
    add(["docs/research/" + n + ".md" for n in ("FIVE_SPORT_GAPS_AND_PRIORITIES", "FIVE_SPORT_RESEARCH_SYNTHESIS", "INDEPENDENT_METHOD_REVIEW", "INTEGRATION_PLAN", "MEASUREMENT_AND_EVALUATION", "RESEARCH_PUBLICATION_POLICY", "SOURCE_CONTRACT_TEMPLATE", "WORKBENCH_DESIGN")], "documentation", MIXED_RESEARCH_SOURCES)
    add(["docs/research/SOCCER_BASKETBALL_RESEARCH.md", "docs/research/SOCCER_BASKETBALL_FACTOR_INVENTORY.csv", "docs/research/SOCCER_BASKETBALL_FACTOR_SOURCES.json", "docs/research/TACTICAL_MEASUREMENT_CONTRACT.json"], "research_synthesis", ("statsbomb", "skillcorner_basketball", "skillcorner_soccer", "spl"))
    add(["docs/research/SPL_BOUNDED_SCHEMA_ADDENDUM.md"], "research_synthesis", ("spl",))
    add(["docs/research/baseball_football/" + n + ".md" for n in ("README", "RESEARCH_BRIEF", "RIGHTS_AND_DATA", "LITERATURE_REVIEW", "LAB_MECHANICS_CANDIDATE", "OPENBIOMECHANICS_AUDIT", "baseball_biomechanics_review", "baseball_other_roles_review", "football_mechanics_review", "football_other_roles_review")]
        + ["docs/research/baseball_football/factor_inventory.csv"], "research_synthesis", ("retrosheet", "nflverse_pbp", "nflverse_ftn", "openbiomechanics"))
    add(["docs/research/tennis/" + n + ".md" for n in ("README", "biomechanics_factor_review", "data_contract", "tactical_literature_review", "tactical_model_design")], "research_synthesis", ("mcp", "byu"))
    add(["scripts/research/README.md"], "documentation", ("original_research",))
    notice_sources = {}
    for source, names in NOTICES.items():
        for name in names:
            notice_sources.setdefault(name, []).append(source)
    for name, sources in notice_sources.items():
        add([name], "attribution_asset" if name.endswith(".png") else "license_notice", sources, name == DERIVED_LICENSE_NOTICE)
    for mapping in PRIVACY_COPIES:
        if mapping["archive_path"] in entries:
            entry = entries[mapping["archive_path"]]
            entry["sources"] = sorted(set(entry["sources"]) | {"byu"})
            entry["risk"] = "fixed_privacy_copy_and_source_review"
    for name in REQUIRED_EXCLUSIONS:
        entries[name]["required_decision"] = "exclude"
    return [entries[name] for name in sorted(entries)]


def preserved(root: Path) -> tuple[dict[str, bytes], dict]:
    blobs = {name: read_bytes(root, name, 20_000_000) for name in PRESERVED_SHA256}
    for name, raw in blobs.items():
        if digest(raw) != PRESERVED_SHA256[name]:
            raise ValueError("Preserved four-sport trust anchor changed: " + name)
    manifest = parse(blobs[BASE_MANIFEST])
    files = manifest.get("files", [])
    if not files or manifest.get("file_count") != len(files):
        raise ValueError("Invalid preserved file count")
    expected = {}
    for entry in files:
        name = relative(entry["path"])
        if name in expected or name in (FINAL_MANIFEST, "PUBLISH_MANIFEST.json"):
            raise ValueError("Duplicate or reserved preserved path")
        expected[name] = entry
    content = {}
    with zipfile.ZipFile(io.BytesIO(blobs[ARCHIVE])) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != {PREFIX + n for n in expected} | {PREFIX + "PUBLISH_MANIFEST.json"}:
            raise ValueError("Preserved ZIP membership differs from manifest")
        if archive.read(PREFIX + "PUBLISH_MANIFEST.json") != blobs[BASE_MANIFEST]:
            raise ValueError("Preserved embedded manifest changed")
        for name, entry in expected.items():
            info = archive.getinfo(PREFIX + name)
            if info.file_size > MAX_FILE or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Unsafe preserved ZIP entry")
            raw = archive.read(info)
            if len(raw) != entry["bytes"] or digest(raw) != entry["sha256"]:
                raise ValueError("Preserved content does not match manifest")
            content[name] = raw
    content["PUBLISH_MANIFEST.json"] = blobs[BASE_MANIFEST]
    return content, manifest


def inventory(root: Path) -> tuple[dict, dict[str, bytes]]:
    original, _ = preserved(root)
    payloads = dict(original)
    records = [dict(path=name, kind="preserved_four_sport", sources=["preserved_four_sport"], required=True,
                    risk="previously_authorized_immutable", origin="delivered_archive", exists=True,
                    bytes=len(raw), sha256=digest(raw)) for name, raw in original.items()]
    for spec in candidate_spec():
        name = spec["path"]
        if name in original:
            raise ValueError("Candidate would replace a preserved file")
        mapping = next((item for item in PRIVACY_COPIES if item["archive_path"] == name), None)
        provenance = {}
        if mapping:
            original_raw = read_bytes(root, mapping["original_path"])
            expected_public = _privacy_copy(original_raw, mapping)
            candidate = path_for(root, mapping["staged_path"])
            raw = read_bytes(root, mapping["staged_path"]) if candidate.exists() else None
            if raw is not None and raw != expected_public:
                raise ValueError("Staged privacy copy differs from exact fixed transformation")
            provenance = {"privacy_copy": copy_provenance(mapping)}
        else:
            candidate = path_for(root, name)
            raw = read_bytes(root, name) if candidate.exists() else None
        if raw is not None:
            payloads[name] = raw
        records.append({**spec, **provenance, "origin": "privacy_sanitized_copy" if mapping else "workspace", "exists": raw is not None,
                        "bytes": len(raw) if raw is not None else None, "sha256": digest(raw) if raw is not None else None})
    document = {"schema_version": 1, "status": "draft_not_approved", "requested_studies": list(TASKS),
                "preserved_sha256": PRESERVED_SHA256, "source_rules": SOURCE_RULES, "exclusions": EXCLUSIONS,
                "candidates": sorted(records, key=lambda r: r["path"])}
    return document, payloads


def hash_string(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Exact SHA-256 required")


def all_true(obj, keys):
    exact(obj, keys)
    if any(value is not True for value in obj.values()):
        raise ValueError("Required independent check not cleared")


def forbidden_addition(name):
    parts = PurePosixPath(name).parts
    private_originals = {item["original_path"] for item in PRIVACY_COPIES if item["original_path"] != item["archive_path"]}
    return (name in private_originals or parts[0] in {"data", "artifacts", "snapshots"} or any(p.startswith(".") for p in parts)
            or any(p in {"__pycache__", "node_modules", "cache", "models", "predictions"} for p in parts)
            or PurePosixPath(name).suffix.lower() in {".pkl", ".pickle", ".joblib", ".pt", ".pth", ".npz", ".npy", ".sqlite", ".sqlite3", ".db", ".pdf", ".log", ".jsonl", ".zip", ".gz"})


def verify_studies(root: Path, review: dict, selected: set[str]):
    exact(review, TASKS)
    for task, item in review.items():
        exact(item, ("state", "evidence_path", "evidence_sha256", "checks"))
        all_true(item["checks"], ("independently_audited", "honest_status", "privacy_reviewed"))
        hash_string(item["evidence_sha256"])
        evidence = read_bytes(root, item["evidence_path"])
        if digest(evidence) != item["evidence_sha256"]:
            raise ValueError("Study evidence changed")
        view = f"reports/tactical/model_views/{task}.json"
        blocked = f"reports/tactical/release_status/{task}.json"
        if item["state"] == "completed_audited":
            if item["evidence_path"] != VIEW_REVIEW or view not in selected or blocked in selected:
                raise ValueError("Completed study needs its exact reviewed aggregate")
            # This validator only reads metadata/reports. It never loads source rows,
            # model weights, performs a fit, or unlocks an evaluation stage.
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from experiments.tactical.model_views import load_verified_view
            status, _ = load_verified_view(root, task)
            if status != "verified_final_available":
                raise ValueError("Study final evaluation or independent audit is incomplete: " + task)
        elif item["state"] == "terminal_blocked":
            if item["evidence_path"] != blocked or blocked not in selected or view in selected:
                raise ValueError("Blocked study needs its exact public terminal status")
            doc = parse(evidence)
            exact(doc, ("schema_version", "task", "status", "terminal", "reason_code"))
            if (type(doc["schema_version"]) is not int or doc["schema_version"] != 1 or doc["task"] != task
                    or doc["status"] != "terminal_blocked" or doc["terminal"] is not True
                    or doc["reason_code"] not in {"rights_or_access_blocked", "protocol_budget_exhausted", "source_integrity_failure", "nonrecoverable_execution_failure", "cancelled_by_owner"}):
                raise ValueError("Pending/developing is not a terminal blocked result")
        else:
            raise ValueError("Every requested study needs a final audited or reviewed terminal status")


NUMERICAL_CHECKS = ("saved_prediction_metrics_recomputed", "frozen_selection_verified", "same_case_comparisons_verified",
                    "uncertainty_method_verified", "no_test_reselection", "runtime_attempts_disclosed")


def validate_numerical_review(raw: bytes, completion: dict) -> dict:
    """Numerical clearance is semantic evidence, not merely a hash-shaped value."""
    review = parse(raw)
    required = {"schema_version", "review_type", "status", "independent", "reviewer", "evaluation_freeze_sha256", "tasks"}
    if not isinstance(review, dict) or not required.issubset(review):
        raise ValueError("Final numerical review schema is incomplete")
    if (type(review["schema_version"]) is not int or review["schema_version"] != 1
            or review["review_type"] != "tactical_final_numerical_review" or review["status"] != "verified_final"
            or review["independent"] is not True or not isinstance(review["reviewer"], str)
            or not 1 <= len(review["reviewer"].strip()) <= 200):
        raise ValueError("Final numerical review is not independently verified")
    hash_string(review["evaluation_freeze_sha256"])
    exact(review["tasks"], TASKS)
    exact(completion, TASKS)
    for task, record in review["tasks"].items():
        fields = {"status", "binding_sha256", "selection_sha256", "final_report_sha256", "checks"}
        if not isinstance(record, dict) or not fields.issubset(record) or record["status"] != "verified_final":
            raise ValueError("All seven numerical tasks must be verified final")
        for field in ("binding_sha256", "selection_sha256", "final_report_sha256"):
            hash_string(record[field])
        all_true(record["checks"], NUMERICAL_CHECKS)
        if any(record[field] != completion[task][field] for field in ("binding_sha256", "final_report_sha256")):
            raise ValueError("Numerical review differs from seven-study completion provenance")
    # Extra narrative/limitations may be present but confer no authority and are
    # not copied to the public archive by this validator.
    return review


def verify_numerical_freeze(root: Path, numerical: dict):
    raw = read_bytes(root, GLOBAL_FREEZE)
    if digest(raw) != numerical["evaluation_freeze_sha256"]:
        raise ValueError("Actual global evaluation freeze differs from numerical audit")
    freeze = parse(raw)
    if not isinstance(freeze, dict) or type(freeze.get("schema_version")) is not int or freeze["schema_version"] != 1:
        raise ValueError("Global evaluation freeze schema invalid")
    exact(freeze.get("tasks"), TASKS)
    for task in TASKS:
        item = freeze["tasks"][task]
        expected_path = f"artifacts/tactical/{task}/SELECTION_FREEZE.json"
        audit = numerical["tasks"][task]
        if (not isinstance(item, dict) or item.get("selection_path") != expected_path
                or item.get("binding_sha256") != audit["binding_sha256"]
                or item.get("selection_sha256") != audit["selection_sha256"]
                or digest(read_bytes(root, expected_path)) != audit["selection_sha256"]):
            raise ValueError("Actual task selection freeze differs from numerical audit: " + task)


def verify_detached_snapshot(root: Path, payloads: dict[str, bytes], selected: set[str], studies: dict):
    completed = {task for task, item in studies.items() if item["state"] == "completed_audited"}
    if not completed:
        if SNAPSHOT_REVIEW in selected:
            raise ValueError("Terminal notes cannot claim a completed numerical snapshot")
        return
    if completed != set(TASKS):
        raise ValueError("Numerical snapshot requires all seven completed studies; blocked notes cannot supply results")
    if SNAPSHOT_REVIEW not in selected:
        raise ValueError("Completed numerical release requires its independent sanitized snapshot review")
    snapshot = parse(payloads[SNAPSHOT_REVIEW])
    local_raw = read_bytes(root, VIEW_REVIEW)
    local = parse(local_raw)
    numerical_raw = read_bytes(root, RESULT_REVIEW)
    result_review_sha256 = digest(numerical_raw)
    numerical = validate_numerical_review(numerical_raw, snapshot.get("seven_task_completion"))
    verify_numerical_freeze(root, numerical)
    if (snapshot.get("local_final_review_sha256") != digest(local_raw)
            or snapshot.get("seven_task_completion") != local.get("seven_task_completion")):
        raise ValueError("Detached snapshot provenance differs from the actual local review")
    exact(snapshot.get("tasks"), TASKS)
    exact(snapshot.get("seven_task_completion"), TASKS)
    for task in TASKS:
        proof = snapshot["seven_task_completion"][task]
        entry = local["tasks"][task]
        if (proof["binding_sha256"] != entry["binding_sha256"]
                or proof["final_report_sha256"] != entry["final_report_sha256"]
                or proof["independent_result_review_sha256"] != result_review_sha256):
            raise ValueError("Snapshot evidence does not match the actual completed numerical audit")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from experiments.tactical.model_views import IMPLEMENTATION, load_verified_view
    minimal = {SNAPSHOT_REVIEW, *IMPLEMENTATION, *(f"reports/tactical/model_views/{task}.json" for task in TASKS)}
    if not minimal.issubset(selected):
        raise ValueError("Detached presentation dependencies missing from selected release")
    # Copy only public selected bytes. The local review, private bindings, original
    # runner reports and source inputs must not be available to this check.
    with tempfile.TemporaryDirectory(prefix="tactical-sanitized-validation-") as temp:
        detached = Path(temp)
        for name in minimal:
            path = path_for(detached, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payloads[name])
        for task in TASKS:
            status, view = load_verified_view(detached, task)
            if status != "verified_final_available" or not view or view.get("delivery_mode") != "audited_aggregate_snapshot":
                raise ValueError("Sanitized extraction cannot display its reviewed aggregate: " + task)


def validate_review(root: Path, document: dict, payloads: dict[str, bytes], raw: bytes, expected_sha256: str) -> dict:
    hash_string(expected_sha256)
    if digest(raw) != expected_sha256:
        raise ValueError("External review hash changed")
    review = parse(raw)
    exact(review, ("schema_version", "review_type", "status", "reviewer", "independent", "inventory_sha256",
                   "intended_use", "decisions", "files", "content_checks", "source_scopes", "studies"))
    if (type(review["schema_version"]) is not int or review["schema_version"] != 1
            or review["review_type"] != "independent_final_tactical_source_release_review"
            or review["status"] != "cleared" or review["independent"] is not True
            or not isinstance(review["reviewer"], str) or not 1 <= len(review["reviewer"].strip()) <= 200
            or review["intended_use"] != "independent_noncommercial_research"):
        raise ValueError("External independent final source-release review required")
    if review["inventory_sha256"] != digest(canonical(document)):
        raise ValueError("Full inventory changed since independent review")
    all_true(review["content_checks"], CONTENT_CHECKS)
    records = {r["path"]: r for r in document["candidates"]}
    exact(review["decisions"], records)
    selected = set()
    for name, disposition in review["decisions"].items():
        if disposition not in {"include", "exclude"}:
            raise ValueError("Every exact candidate needs include/exclude disposition")
        record = records[name]
        if name in REQUIRED_EXCLUSIONS and disposition != "exclude":
            raise ValueError("Audited local-only document must be excluded")
        if record["required"] and disposition != "include":
            raise ValueError("Required source, test, model-card or preserved file excluded")
        if disposition == "include":
            if not record["exists"] or name not in payloads:
                raise ValueError("Selected file is missing")
            if record["origin"] != "delivered_archive" and forbidden_addition(name):
                raise ValueError("Forbidden data/weight/cache/source-document addition")
            selected.add(name)
    exact(review["files"], selected)
    for name in selected:
        exact(review["files"][name], ("sha256", "bytes"))
        expected = review["files"][name]
        hash_string(expected["sha256"])
        if type(expected["bytes"]) is not int:
            raise ValueError("Exact integer byte count required")
        if expected != {"sha256": digest(payloads[name]), "bytes": len(payloads[name])}:
            raise ValueError("Full selected allowlist hash/size mismatch")
    sources = {s for name in selected for s in records[name]["sources"] if s != "preserved_four_sport"}
    exact(review["source_scopes"], sources)
    for source in sources:
        scope = review["source_scopes"][source]
        exact(scope, ("paths", "checks"))
        expected_paths = sorted(name for name in selected if source in records[name]["sources"])
        if scope["paths"] != expected_paths:
            raise ValueError("Source-specific publication scope must match exact paths")
        all_true(scope["checks"], SOURCE_RULES[source]["checks"])
        if not set(NOTICES.get(source, ())).issubset(selected):
            raise ValueError("Required source notice or logo missing: " + source)
    # Verify the source-supplied logo rather than substituting a look-alike asset.
    logo = "experiments/tactical/web/statsbomb-logo.png"
    if "statsbomb" in sources and digest(payloads[logo]) != STATSBOMB_LOGO_SHA256:
        raise ValueError("StatsBomb logo differs from pinned source asset")
    verify_studies(root, review["studies"], selected)
    verify_detached_snapshot(root, payloads, selected, review["studies"])
    return {"schema_version": 1, "status": "independently_reviewed_source_release", "intended_use": review["intended_use"],
            "review_sha256": digest(raw), "inventory_sha256": digest(canonical(document)),
            "preserved_sha256": PRESERVED_SHA256, "source_rules": SOURCE_RULES,
            "studies": {task: review["studies"][task]["state"] for task in TASKS},
            "file_count": len(selected), "files": [records[name] for name in sorted(selected)],
            "scope": "Source, notices and independently cleared aggregates only. Original four-sport contents preserved. No rights are expanded by packaging."}


def reproducible_zip(payloads: dict[str, bytes], manifest: dict) -> bytes:
    """Pure serializer; callers must first obtain validate_review's result."""
    names = [record["path"] for record in manifest["files"]]
    if len(names) != len(set(names)) or FINAL_MANIFEST in names:
        raise ValueError("Duplicate/reserved archive name")
    entries = {}
    for record in manifest["files"]:
        name = relative(record["path"])
        raw = payloads[name]
        if digest(raw) != record["sha256"] or len(raw) != record["bytes"]:
            raise ValueError("Content changed between review and serialization")
        entries[name] = raw
    entries[FINAL_MANIFEST] = canonical(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(PREFIX + name, date_time=FIXED_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | (0o755 if name.endswith(".sh") else 0o644)) << 16
            info.flag_bits = 0
            info.extra = b""
            info.comment = b""
            archive.writestr(info, entries[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def write_draft(root: Path, document: dict):
    directory = path_for(root, DRAFT_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    path_for(root, DRAFT_DIR + "/inventory.json").write_bytes(canonical(document))
    path_for(root, DRAFT_DIR + "/inventory.sha256").write_text(digest(canonical(document)) + "  inventory.json\n")
    lines = ["# Draft publication inventory", "", "NOT APPROVED. This is not a release archive or permission to publish.", "",
             "| Path | Present | Origin | Kind | Sources | Risk | Required |", "|---|---|---|---|---|---|---|"]
    for r in document["candidates"]:
        lines.append(f"| {r['path']} | {r['exists']} | {r['origin']} | {r['kind']} | {', '.join(r['sources'])} | {r['risk']} | {r['required']} |")
    lines.extend(["", "## Excluded", *["- " + item for item in EXCLUSIONS], ""])
    path_for(root, DRAFT_DIR + "/INVENTORY.md").write_text("\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--review", help="Externally supplied exact independent final review, project-relative")
    parser.add_argument("--review-sha256", help="Independently supplied exact review fingerprint")
    parser.add_argument("--stage-public-copies", action="store_true", help="Prepare only the fixed privacy copies; no archive or approval")
    parser.add_argument("--write-zip", action="store_true", help="Write a local final ZIP only after every independent review gate passes; never publish")
    args = parser.parse_args(argv)
    if bool(args.review) != bool(args.review_sha256) or (args.write_zip and not args.review):
        parser.error("Final validation/ZIP requires both external --review and --review-sha256")
    if args.stage_public_copies and (args.review or args.review_sha256 or args.write_zip):
        parser.error("Privacy staging cannot be combined with review or archive writing")
    try:
        root = args.root.resolve()
        if args.stage_public_copies:
            prepared = stage_privacy_copies(root)
            print(json.dumps({"status": prepared["status"], "copies": len(prepared["copies"]), "zip_written": False}))
            return 0
        document, payloads = inventory(root)
        if not args.review:
            write_draft(root, document)
            print(json.dumps({"status": "draft_not_approved", "candidate_count": len(document["candidates"]),
                              "missing_candidates": sum(not r["exists"] for r in document["candidates"]), "zip_written": False}))
            return 0
        raw = read_bytes(root, args.review)
        manifest = validate_review(root, document, payloads, raw, args.review_sha256)
        if args.write_zip:
            # Snapshot payloads are the exact bytes reviewed above; do not reopen
            # source files while archiving. Exclusive writes never overwrite a release.
            archive = reproducible_zip(payloads, manifest)
            folder = path_for(root, "artifacts/tactical/release")
            folder.mkdir(parents=True, exist_ok=True)
            outputs = {"sports-analytics-tactical-source.zip": archive,
                       "publish-manifest.json": canonical(manifest),
                       "SHA256SUMS": (digest(archive) + "  sports-analytics-tactical-source.zip\n" + digest(canonical(manifest)) + "  publish-manifest.json\n").encode()}
            if any(path_for(root, "artifacts/tactical/release/" + name).exists() for name in outputs):
                raise ValueError("Release destination already exists; refusing overwrite")
            for name, body in outputs.items():
                with path_for(root, "artifacts/tactical/release/" + name).open("xb") as output:
                    output.write(body)
        print(json.dumps({"status": manifest["status"], "file_count": manifest["file_count"], "zip_written": args.write_zip}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
