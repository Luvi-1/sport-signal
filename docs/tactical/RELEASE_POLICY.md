# Tactical source-release policy

Status: **packaging implementation and draft inventory only**. This document does
not approve a result, distribution, external upload, repository publication or a
replacement Library version. No final tactical archive was built as part of this
implementation. The seven numerical studies and their independent numerical
reviews are now complete. Final privacy, display/distribution and exact release
authority remain externally supplied and separately checked. A synthetic test
fixture is never evidence for a real release.

## Preserved four-sport delivery

The existing delivered archive is the immutable baseline: 114 content files and
its original `PUBLISH_MANIFEST.json`, 115 ZIP entries in total. The new packager
reads its exact bytes instead of reconstructing it from mutable directory trees.
It pins the SHA-256 of the archive, its external manifest and the separate
preservation hash record, and verifies every embedded member against that
manifest. The old manifest is retained unchanged beside a distinctly named new
`TACTICAL_PUBLISH_MANIFEST.json`. Existing source, reports and core results are
never overwritten. The current workspace `.gitignore` already has additional
local-data exclusions; its older delivered version remains the archived baseline.

The old `scripts/package_release.py` is preserved as historical source. **Do not
run it for the tactical extension.** Its recursive Markdown/report inclusion can
pick up restricted research artifacts and its suffix rules omit new web assets,
factor CSVs and source notices. The new script does not import or run it.

Only the original compact, licensed normalized NFL input snapshot may travel as
bundled observations. Its existing CC BY notice and metadata are retained. No
other observation dataset, including an openly licensed one, is granted automatic
redistribution permission by this source release.

## Finite publication catalog

`candidate_spec()` in `scripts/package_tactical_release.py` is an explicit list
of project-relative paths. It includes these classes:

- Tactical parsers, gated numerical runners, reviewed recovery orchestration,
  metrics, presentation code and tests
- The three local web assets, plus an explicitly reviewed pinned provider logo
- The separately added `START_HERE_FIVE_SPORTS.md`, named methodological/research
  documents, factor CSVs, source notices and seven
  separate final model cards
- Exactly seven normalized final aggregates at
  `reports/tactical/model_views/<study>.json`, after independent validation
- A separately reviewed aggregate-snapshot attestation containing public hashes
  and no private source rows, memberships or run metadata
- Optionally, strict textual terminal-status records for genuinely terminal
  blocked studies; these contain no numerical result

There is no recursive inclusion, suffix grant or “include all reports” switch.
An unknown file is excluded even if it looks similar to an allowed file.
Optional candidates receive an explicit include/exclude decision in the exact
review. Required files cannot be silently dropped. Missing required notices,
model cards, code or tests prevent final release. A new explicit catalog path
requires a new full inventory and independent review.

Research JSON is deliberately sparse: only the specifically identified
soccer/basketball factor-source reference and tactical measurement contract are
candidates. Neither is automatically cleared. Other research JSON audit or
acquisition files remain excluded; the narrative and factor inventories can be
reviewed without distributing their raw diagnostics. In particular, StatsBomb
sample/coverage JSON, hoopR source QA, OpenBiomechanics schema/manifests and
source-specific row diagnostics do not enter by a blanket report rule.

## Source-specific obligations

All decisions below are conservative operational release constraints, not legal
advice. Read the actual pinned source terms and the intended distribution scope.
The root code license does not relicense third-party data or derived material.

| Source | Minimum publication conditions |
|---|---|
| StatsBomb | Confirm noncommercial use; publish only independently cleared analysis/aggregates; no raw or row-derived records. Retain visible StatsBomb credit and the verified source-supplied brand logo. A local source QA report is not release clearance |
| SkillCorner basketball and soccer | Keep the appropriate complete MIT notice, source pin, provider credit and modification statement. This project still excludes raw/event/player rows despite more permissive source rights |
| Retrosheet | Retain its requested attribution and identify modifications. The tactical source release does not add new raw/normalized records |
| nflverse PBP | Retain the applicable CC BY 4.0 attribution and release-specific exceptions. The preserved compact NFL snapshot is the only bundled data exception |
| FTN/participation via nflverse | Credit FTN Data and the appropriate provider via nflverse; preserve applicable CC BY-SA 4.0 conditions and review the scope of adaptations |
| Tennis Match Charting Project | Credit Jeff Sackmann/Tennis Abstract/MCP contributors, retain CC BY-NC-SA 4.0, disclose modifications and confirm noncommercial/share-alike scope |
| OpenBiomechanics | Keep CC BY-NC-SA 4.0 and the complete additional professional-sports/financial-firm affiliation exclusion. Only the fixed adult aggregate cohort is eligible. No participant/trial/pseudolabel values, small identifying cells, individual rankings or health profiles |
| BYU serve experiment | Retain the Nate Sandholtz MIT notice. Participant privacy remains separate from that license. All eight individual or pseudonymous player/fold results stay local. Suppress participant/trial labels, small cells and health profiles; retain safeguards for unverified ages |
| MLSE Sport Performance Lab | Keep CC BY-NC-SA 4.0 and its complete additional affiliation restriction. Only separately reviewed bounded aggregate documentation is a candidate; ages remain unverified, and no participant-level or numerical-model export is implied |

The explicit future notice paths are in `NOTICES`. The script does not create or
copy missing notices, infer eligibility, fetch source materials or accept terms.
Source-supplied logo bytes must match the pinned SHA-256; an arbitrary picture or
link is insufficient. Every source scope identifies **exact selected file paths**
and all mandatory assertions. Combined-source files require each applicable
source review. Required attribution files are themselves explicit catalog entries.

## Files that stay local

- Raw downloads, private/cached datasets, source case tables, feature matrices and
  row-level predictions, apart from the preserved NFL snapshot exception
- Pickles, joblib/NumPy model bundles, numerical parameters/weights, SQLite stores,
  trained Laya weights, environments, node modules and caches
- Private group plans, participant/trial/individual pseudolabel records,
  per-player/fold statistics, small identifying cells and sensitive health profiles
- Run bindings, numerical stage approvals, source acquisition manifests, original
  final runner reports and independent private evidence not explicitly designated
  as a sanitized public attestation
- Source PDFs/papers/document downloads, copied documentation, secrets,
  authentication data, logs and temporary files; explicitly listed license
  notices and the attributed logo are the intentional notices/assets exception

The script does not sanitize arbitrary documents. It refuses to infer that a file
is safe because its name contains “aggregate.” All selected additions need an
independent full-content check, including code fixtures and documentation. Content
checks apply to additions; immutable baseline data retain the explicit original
NFL snapshot exception. Source notices may reproduce the required notice text.

## Independent review contract

Default invocation is safe inventory-only:

```sh
python scripts/package_tactical_release.py
```

It writes only the ignored draft inventory, its SHA-256 and a readable path/risk
listing. It writes no approval, model, final ZIP, Library object or remote content.
Missing final materials are listed as missing rather than fabricated.

Final **validation without ZIP creation** requires both an externally provided
review path and its independently supplied SHA-256:

```sh
python scripts/package_tactical_release.py \
  --review docs/tactical/INDEPENDENT_FINAL_RELEASE_REVIEW.json \
  --review-sha256 <exact independently supplied digest>
```

Draft model cards and the new entrypoint must be updated to match the final
reviewed status; their presence is not completion. `model_cards_match_final_status`
is a separate required content-review check.

The named review is not generated by this script and is not auto-included in the
archive. Its exact JSON fields are:

- `schema_version`: integer 1
- `review_type`: `independent_final_tactical_source_release_review`
- `status`: `cleared`; `independent`: true; nonempty `reviewer`
- `inventory_sha256`: hash of the entire canonical current draft inventory
- `intended_use`: `independent_noncommercial_research`
- `decisions`: every candidate path mapped to `include` or `exclude`, without extras
- `files`: every included path mapped to exactly `sha256` and `bytes`, without extras
- `content_checks`: every key in `CONTENT_CHECKS` explicitly true
- `source_scopes`: every included source mapped to exact sorted `paths` and its
  exact source-specific `checks`, all true
- `studies`: exactly the seven study identifiers in `TASKS`, with no omissions

Each study has exactly `state`, `evidence_path`, `evidence_sha256` and `checks`.
The checks are `independently_audited`, `honest_status` and `privacy_reviewed`, all
true. A completed study uses `state=completed_audited`, its public normalized
aggregate, and the exact local final-view review as evidence. The full-local
validator must verify its actual completed report, seven-study run binding,
implementation hashes, normalized projection and independent checks. Development
progress, a successful fit, a model file or a source-only review cannot substitute.

The numerical audit itself must use `schema_version=1`,
`review_type=tactical_final_numerical_review`, `status=verified_final`,
`independent=true`, a nonempty reviewer, an `evaluation_freeze_sha256` and exactly
seven `tasks`. Each task has verified-final status and exact binding, selection
and final-report hashes. Its six required checks must all be true: saved prediction
metrics recomputed, frozen selection verified, same-case comparisons verified,
uncertainty method verified, no test reselection and runtime attempts disclosed.
The script's `NUMERICAL_CHECKS` supplies their exact JSON names. Extra narrative
never overrides these fields. Source rights/privacy remain separate decisions.

The audit's global-freeze digest must match the actual ignored
`EVALUATION_FREEZE.json`; its seven task entries must match the same binding,
exact selection path and selection digest. Each actual selection file is hashed.
Only bookkeeping metadata is read here, never targets or model weights, and none
of these private artifacts is copied into the sanitized distribution.

A terminal blocked record has exactly `schema_version=1`, the study `task`,
`status=terminal_blocked`, `terminal=true` and one enumerated `reason_code`.
The allowed codes are rights/access blocked, exhausted protocol budget, source
integrity failure, nonrecoverable execution failure, or owner cancellation, using
the script's exact snake-case names. Its independent review must explicitly clear
that status. Ongoing work, a recoverable failure, pending computation or missing
review is not terminal. A terminal note contains no numerical result and cannot
be used to pass the completed numerical-snapshot contract. The current supported
deliveries are an all-seven completed numerical snapshot or source plus reviewed
terminal notes without numerical views. Mixed completed/blocked numerical
snapshots require a separately reviewed presentation contract and remain closed.

The local checks are auditable workflow safeguards, not an authentication or
security boundary against someone who can edit code and review files. A hash
identifies bytes; it is not proof of reviewer independence, legal permission or
consent. Those decisions remain externally supplied and are never self-created
by packaging. Publishing still requires the project owner's authorization.

## Sanitized aggregate workbench

The source distribution excludes all raw/private dependencies. Numerical views
therefore need their own independently supplied
`INDEPENDENT_AGGREGATE_SNAPSHOT_REVIEW.json`. It binds exact implementation and
aggregate hashes and the seven genuinely completed final-study provenances.
Public provenance hashes do not claim that an extracted source-only bundle can
reproduce private source/model computations. The display must identify itself as
an audited aggregate snapshot, with no trained weights or live inference.

The snapshot route is final-completed-only. A blocked note does not grant a
numerical display, and no empty placeholder can be presented as a finished model.
A release with missing real final numerical/privacy evidence remains blocked.
The detached validation checks use only files selected for the source release;
private local files cannot accidentally make an incomplete source bundle pass.
The snapshot completion hashes must match the actual local final-view review and
the actual `INDEPENDENT_FINAL_NUMERICAL_REVIEW.json`; neither can be fabricated.

Automated test evidence must be reviewed and the actual browser-validation status
disclosed. Browser-rendered visual QA was blocked in the current environment and
has not been claimed as passed. Static, DOM and offline route tests do not verify
rendered layout, screen-reader behavior or browser compatibility. A release
review must preserve that limitation unless a later real browser pass supersedes
it with its own evidence.

## Determinism and verification

Only a separately authorized final invocation adds `--write-zip`. It uses an
exclusive new destination; it will not overwrite any existing release. Every
archive path is sorted, every timestamp is fixed to 1 January 2026, file modes
are fixed, and compression parameters are fixed. Repeated runs with the same
Python/zlib implementation and input bytes produce identical ZIP bytes. The
archive includes a canonical SHA-256 manifest, and local `SHA256SUMS` binds both
the ZIP and the external manifest. Selected bytes are snapshotted before review
and reused for serialization rather than reopening changing source files.

The packager rejects path traversal, symlinked parents/files, duplicate JSON keys,
nonfinite JSON, unexpected fields, oversized inputs, changed preservation anchors,
stale inventory hashes, missing mandatory notices and mismatched selected bytes.

Focused test command:

```sh
python -m unittest discover -s tests -p test_tactical_release.py -v
```

All test review/status/archive contents are fabricated in temporary directories.
ZIP determinism tests use in-memory synthetic archives. The complete synthetic
seven-study integration fixture simulates live implementation identity in its
temporary root while exercising the real review and detached-view validators. No real numerical stage,
final approval or distribution is run by these tests.

## Presentation and preservation

The original root README, project metadata, original core and original results
remain untouched. The new START_HERE_FIVE_SPORTS.md, BENCHMARK_RESULTS.md and seven
model cards describe the completed numerical studies without claiming a single
cross-sport accuracy or hiding unfavorable results. Their exact final contents
remain subject to privacy and source-specific release review. The parent retains
control of the existing delivery identity and any authorized new version.

## Fixed privacy-only source copies

Four exact, hash-pinned transformations are the sole staging substitutions. The
fixed mapping in the packager names original, staged and archive destinations,
original/public SHA-256 identities and exact byte spans. It contains no removed
observations, wildcard mapping, caller-supplied replacement or fallback to an
unsanitized original. Descriptive parser text omits an observed source extremum;
a test uses a clearly fabricated nonphysical fixture; the public tennis-execution
protocol omits extrema and restricts participant diagnostics to local auditing;
and a public runner changes only its protocol-path literal to the PUBLIC name.
The executed original files are never written or replaced.

The originals and staged copies are read through bounded regular-file descriptor
reads that reject symlinked parents/files, hardlinks and changes during the read.
The original pin must match, the exact span transform must match its public pin,
and a staged candidate must equal those transformed bytes. Staging is explicit:

```sh
python scripts/package_tactical_release.py --stage-public-copies
```

This writes only fixed ignored source copies and preparation provenance. It cannot
be combined with a release review or archive-write flag and creates no approval.
A changed staging destination is refused, never overwritten. The final inventory
and manifest label these bytes privacy_sanitized_copy and bind their provenance;
the independent release review also must clear privacy_copy_provenance_verified.

The executed tennis-execution DRAFT protocol is not a candidate. Its distinct
PUBLIC destination is required. The seven specifically audited local-only
research notes remain named optional candidates, but their final decisions must
be exclude. Required DERIVED_MATERIAL_LICENSES.md applies to every relevant
source scope, and PUBLIC_SOURCE_RELEASE_NOTES.md explains changed identities,
omitted QA links, and why this distribution makes no fresh tactical-refit claim.
