# Independently verified aggregate model views

## Scope and current state

This is presentation code for the local read-only analyst workbench, not a model
runner, evaluation command, approval generator, or deployment. Its implementation
was tested with invented aggregate values only. Neither passing those tests nor
creating a normalized JSON object establishes that a real study was fitted,
scored, useful, calibrated, or approved for release.

The five event-sport views and two separate laboratory companions preserve their
own units, targets, populations and denominators. Descriptive source/parser
views remain available while numerical evidence is missing or invalid. Numerical
absence says nothing about whether development fitting has occurred. Only
completed, independently checked final reports can supply a numerical view.

The interface offers:

- Target/cohort and metric selectors, without pooling unlike targets on one scale
- Same-case model and feature-block results, including unavailable procedures
- Model-minus-reference loss gaps, paired uncertainty, ties and worse outcomes
- Fixed-bin reliability with case/cluster support and visible empty/sparse bins
- Measured feature blocks, unmeasured factors, physical units and research limits
- A separate laboratory section; no individual athlete/player/fold records

The adapter never imports numerical runners, changes shared gates, reads target
caches, reconstructs individual probabilities, fits a model or estimates a metric.
It does not offer a scenario-prediction endpoint. No weights, pickle/joblib files,
raw rows, per-case probability tables or private group plans are served.

## Two distinct evidence paths

`GET /api/model-view/{task}` accepts only the fixed seven task names in
`experiments/tactical/model_views.py`. It returns HTTP 409 with a null view until
verification succeeds. Unknown tasks and raw/model paths return 404. Both
verification paths require the exact all-seven completion attestation; a subset,
ongoing development, or a terminally blocked study cannot unlock numerical views.

### 1. Full local research installation

The externally authored review is:

`docs/tactical/INDEPENDENT_FINAL_MODEL_VIEW_REVIEW.json`

Its exact top-level fields are:

- `schema_version`: integer 1
- `review_type`: `independent_final_model_view_review`
- `status`: `cleared`
- `reviewer`: nonempty reviewer identity, at most 200 characters
- `independent`: true
- `implementation_sha256`: exact mapping for every `IMPLEMENTATION` path
- `seven_task_completion`: exact seven-task mapping defined below
- `tasks`: mapping of tasks whose normalized projections were independently checked

Each `seven_task_completion` entry contains exactly `status` (`verified_final`),
`binding_sha256`, `final_report_sha256`, and `independent_result_review_sha256`.
All seven audit hashes identify the same independently authored numerical audit:

`docs/tactical/INDEPENDENT_FINAL_NUMERICAL_REVIEW.json`

The full-local loader verifies that audit's actual bytes and required semantics:
`schema_version: 1`, `review_type: tactical_final_numerical_review`,
`status: verified_final`, `independent: true`, a nonblank `reviewer`, a valid
`evaluation_freeze_sha256`, and exactly all seven `tasks`. Each task must contain
`status: verified_final`, `binding_sha256`, `selection_sha256`,
`final_report_sha256`, and `checks`. Binding/report hashes must match the
seven-study completion entries. The exact required checks are
`saved_prediction_metrics_recomputed`, `frozen_selection_verified`,
`same_case_comparisons_verified`, `uncertainty_method_verified`,
`no_test_reselection`, and `runtime_attempts_disclosed`, all true.
Extra audit narrative/limitations are ignored as authority and never served.
Empty, pending or wrong-kind audits fail even when their bytes are hash-bound.
The audit's global-freeze digest must match the actual
`artifacts/tactical/EVALUATION_FREEZE.json`. That file must identify exactly all
seven tasks and their audited binding hash, fixed selection path and selection
hash. Every `artifacts/tactical/{task}/SELECTION_FREEZE.json` is byte-hashed and
matched to the audit. Selection contents, models and targets are not parsed.
Its review must cover
all seven exact bindings, completed final reports, saved-prediction metric
recomputation and study limitations. A hash alone is not a substitute for that
review. This implementation must not author, sign, fabricate or repair either
review, and does not create a placeholder at either real path.

Each `tasks` entry contains exactly:

- `status`: `verified_final`
- `binding_sha256`: canonical run identity
- `binding_file_sha256`: exact bytes of the original run-binding file
- `final_report_sha256`: exact original completed final-report bytes
- `view_sha256`: exact normalized aggregate projection bytes
- `checks`: every check below explicitly true

Required checks are `final_evaluation_complete`,
`independent_metric_recomputation`, `same_case_comparisons_verified`,
`normalized_projection_verified`, `aggregate_only_privacy_review`, and
`source_terms_checked`. The task's binding/report identities must equal its
seven-study completion entry. The original binding must name the exact seven-task
evaluation cohort and its canonical content must reproduce its identity hash.

The loader reads only the fixed review/audit/global-freeze records, seven
selection-commitment byte streams, five presentation implementation files, and
the requested task's binding, completed report and normalized projection.
It checks task-specific completion markers and all byte hashes. Reviewed copies
under an alternate `--root` must also match the live server assets and the Python
source identities captured when this process imported the presentation modules.
Restart the workbench after source edits; copying differently reviewed files into
an alternate root cannot authorize a stale/different running implementation. It does not open
source rows, target caches, group plans, executable model artifacts or private
individual result files. The original binding/report/audit contents are never
returned to the browser.

The original final-report paths are fixed in `_final_path`: soccer, football and
MCP tennis use their `reports/tactical/{task}/model/evaluation.json`; baseball
uses `artifacts/tactical/baseball/EVALUATION.json`; the two mechanics studies use
`artifacts/tactical/{task}/evaluation_report.json`; ACB uses the report path for
its exact bound artifact ID. Paths cannot be supplied by a URL or normalized view.

### 2. Separately reviewed sanitized aggregate snapshot

A clean source/aggregate distribution cannot contain private run inputs and
artifacts. It therefore has a distinct external distribution review:

`docs/tactical/INDEPENDENT_AGGREGATE_SNAPSHOT_REVIEW.json`

This path is considered only when the full-local model-view review is absent.
An existing invalid full-local review never falls back to snapshot mode.

Its exact fields are `schema_version` (integer 1), `review_type`
(`independent_aggregate_snapshot_review`), `status` (`cleared`), `reviewer`,
`independent` (true), `distribution_scope`
(`local_noncommercial_aggregate_snapshot`), `local_final_review_sha256`,
`implementation_sha256`, `seven_task_completion`, and `tasks`.

Implementation hashes and the seven-study completion schema are identical to
full-local mode. Each snapshot task entry contains exactly `status`
(`verified_final`), `view_sha256`, and `checks`. The checks are all six local
checks plus `sanitized_snapshot_verified` and
`aggregate_distribution_authorized`, all true.

Before distribution, the independent release review/packager must check these
provenance hashes against the actual completed local review, final numerical
audit, bindings and original reports. The detached reader verifies the exact
shipped implementation and normalized aggregate bytes. Original report/binding/
audit hashes are provenance attestations in this mode: the clean bundle cannot
reproduce source-to-report verification without the excluded private artifacts.
The UI explicitly labels this an **audited aggregate-only snapshot**, with no
trained weights or current live model. It does not claim runnable fitted models,
a fresh evaluation or a public-release license. Source-specific distribution
clearance remains separate and necessary.

Neither evidence path is a cryptographic authentication system against an owner
who can replace code and reviews. They are conservative local integrity and
review-provenance checks. Files are byte-hashed on each request; there is no
unverified JSON fallback or automatic approval creation.

## Strict normalized aggregate schema

The only numerical payload file is:

`reports/tactical/model_views/{task}.json`

It contains exactly `schema_version` (integer 1), `task`, `phase`
(`independently_verified_final_aggregate`), and `targets`.

Each target contains exactly:

- `id`, `cohort`: task-specific fixed allowlisted codes
- `cases`, `clusters`: supported cohort counts; positive integers
- `case_set_sha256`: aggregate fingerprint of the fixed eligible case set
- `models`, `comparisons`, `reliability`: bounded aggregate lists

A model contains `id`, the identical `case_set_sha256`, and `metrics`.
Every metric contains `value`, `cases`, `clusters`, and `status`. Supported
statuses are `reported`, `not_reported`, `insufficient_support`,
`undefined_single_class`, and `procedure_unavailable`. Unavailable values must
be null. Reported metrics retain the fixed eligible denominator, except BYU
bounce-only metrics, which explicitly use 437 observed bounces. No metric may
silently drop difficult cases. Missing model or target/cohort projections are
listed as unavailable in the interface, not replaced with invented estimates.

A comparison contains exactly `model`, `reference`, `metric`, `delta`,
`interval`, `confidence`, `uncertainty`, `sensitivity_range`, `criterion_met`.
Both models must use the same cases and cluster counts. A finite delta must
match model loss minus reference loss. Negative is favorable; zero is a tie;
positive is worse. Only declared lower-is-better losses have contrast plots.
Unavailable contrasts have no delta, interval, sensitivity, or criterion result.
Only each task's supported uncertainty methods are accepted. Basketball omission
ranges cannot be represented as confidence intervals. A practical threshold is
not automatically a statistically demonstrated improvement; the task-specific
criterion and limits appear beside the definitions. This minimal schema does not
include every supporting cross-metric, per-game and dependence condition needed
to verify a successful criterion. Therefore `criterion_met: true` is rejected.
A successful criterion in the original source report must be projected as null
here, not as false. The interface labels a negative gap a favorable estimate
without claiming that a practical/statistical criterion was met. An independently
verified negative criterion may remain false and is displayed explicitly.

A reliability series contains exactly `model`, `class`, and `bins`. Each bin
contains `n`, `clusters` (count or null when not reported), `mean_probability`,
and `observed_fraction`. The fixed bin count/order and total eligible support
must match the task contract. Empty bins have null rates. Sparse occupied bins
remain visible as hollow amber markers; accessible tables retain every bin.
Marker size represents support, not certainty. These are aggregate bin means,
never per-case probability tables. A close diagonal does not establish calibration.

All display prose, targets, metric names, model IDs, units, cohort labels and
feature descriptions are controlled by code. Extra keys are rejected at every
schema level, rather than silently redacted. JSON duplicate keys, nonfinite
numbers, malformed hashes, path escape, oversized evidence and unexpected
models/targets fail closed. Reviews, normalized views, metadata and implementation
files are limited to 2,000,000 bytes each. Only the fixed original final-report
paths returned by `_final_path` have an 8 MiB (8,388,608-byte) limit; basketball's
path includes the reviewed binding's 64-lowercase-hex artifact ID. Similar names,
development reports and arbitrary paths do not receive that larger limit.
Both readers use bounded regular-file reads and no-follow directory components,
so aliases cannot transfer a final report's allowance to another file. Exact
hashes and independent review requirements are unchanged.

## Numerical and measurement distinctions

- Soccer: non-penalty WSL shots; full versus matched defensive-geometry cases
  remain separate; coordinates are a native 120 × 80 grid, not metres
- ACB: release-level target includes fouled misses; five-game prequential
  evaluation, no headline confidence interval or population-superiority claim;
  coordinates/defender distance are feet and representation agreement is not
  physical accuracy
- Baseball: swing per eligible delivered pitch and contact per eligible swing
  have different denominators; previous outcome symbols are not pitch types
- NFL: realized dropback from retrospective at-snap charting, including sacks and
  scrambles; not original play-call intent or verified live annotation latency
- MCP tennis: four serve/corpus cells; assumed source date plus 21-day availability
  is not verified ingestion; 2025 evaluation cutoff is 22 January 2026; wide/body/T
  class order and 98.75% intervals remain explicit
- OpenBiomechanics: fixed adult-only 571 swings/82 athletes; foot plant means the
  100% bodyweight lead-force threshold; four body angles retain source anatomical
  definitions; macro RMSE is the mean of athlete-specific RMSEs, in mph; no
  verified elapsed event timing or untouched chronological final lockbox
- BYU: 548 non-lets, 437 observed bounces and 111 net-censored attempts; 19 lets
  excluded; no imputation of net bounces; density NLL uses square metres and may
  be negative; bounce error uses metres; all eight individual/pseudonymous
  player, fold and session records remain suppressed

Binary Brier is mean positive-class squared error on original probabilities;
MCP tennis Brier sums all three class errors without dividing by three.
Log loss uses natural logarithms. Soccer/ACB/NFL binary clipping epsilon is
1e-6; baseball and MCP tennis use 1e-12, with tennis class flooring followed by
renormalization. Accuracy ties choose class 0 for ACB, class 1 at p≥0.5 for the
other binary studies, and first argmax in [wide, body, T] for MCP tennis.

NFL and MCP tennis retain their exact frozen serialized floating-point linspace
edges. Display labels are rounded, but nominal decimal boundary values can land
in the preceding bin; see `RELIABILITY_BIN_CONVENTIONS.md`. Baseball uses its
separate explicit decimal edge convention. No score changes with plot binning.

Every numerical panel discloses performance-blind-after-source-QA exposure and
that intervals omit model-selection, measurement and transport uncertainty.
Nothing here authorizes causal coaching, medical/readiness claims or individual
rankings. Lab companions are never pooled with professional event tasks.

## Fixed presentation defaults and source attribution

The initial selectors follow prespecified targets, never JSON key/array order or
final-score ranking: soccer goal/matched/log loss; ACB make/event geometry/log
loss; baseball swing/eligible/log loss; NFL dropback/eligible/log loss; MCP
A1_m/eligible/log loss, with all four cells retained; baseball laboratory
exit velocity/adult paired/equal-athlete MAE; BYU joint execution/non-let/
equal-player joint NLL. Missing primary target/cohort evidence is labelled
unavailable; any displayed alternative is label-ordered and is not a replacement
primary result. Missing primary metrics remain selectable and unavailable.

Every numerical panel independently renders code-controlled provider credit and
fixed notice links, including in a detached snapshot without descriptive
summaries. The document modal serves only allowlisted local notice paths. It
includes the exact scope in `notices/DERIVED_MATERIAL_LICENSES.md`, source-specific
share-alike conditions, OpenBiomechanics' additional affiliation exclusion and
Nate Sandholtz/BYU's MIT notice. The pinned StatsBomb logo remains visible for
soccer. The historical independent method review is not an exposed document;
the method route uses `EXECUTION_STAGES.md`.

## Local operation, verification and remaining visual QA

The workbench remains at `127.0.0.1` only. It rejects foreign Host/Origin and
cross-site requests, accepts no query-controlled paths, has read-only routes and
no CDN, telemetry, upload, publication, inference or background refresh.
The StatsBomb attribution route accepts the exact supplied-logo SHA from its
original source location, or `experiments/tactical/web/statsbomb-logo.png` when
the original is absent. An altered present original never falls back silently.
No logo is redrawn or fetched remotely.

Focused offline checks:

```sh
python -m unittest discover -s tests -p 'test_tactical_model_views.py' -v
node --check experiments/tactical/web/app.js
node scripts/test_tactical_model_views_dom.cjs
node scripts/test_tactical_dom.cjs
```

The numerical DOM test generates invented JSON in process only, directly from
synthetic test helpers. It never writes a project report or real review. Unit
review/report fixtures live exclusively in temporary directories. The existing
optional jsdom dependency is used from `artifacts/tactical/domqa`; it is not
required to run the Python workbench. The descriptive fixture file is unchanged.

Coverage includes every study, shape/privacy/path/hash failures, all-seven
completion requirements, detached provenance, fixed cohort and censoring rules,
metric/class selectors, empty/sparse reliability, ties and worse outcomes,
closed/invalid states, and stale navigation/document responses. The actual HTTP
handler and headers are tested without constructing an OS socket.

These checks are **not browser-rendered visual QA**. The existing verified OS
process/socket restriction blocked Chromium, and the cloud browser could not
reach this executor's loopback. No bypass, public tunnel or retry is attempted.
A capable local installation must still inspect desktop/narrow layouts, scrolling,
keyboard interaction, actual screen-reader behavior and attribution before a
fully rendered-browser validation claim.
