# Deterministic aggregate model-view projection

## What this code does

`experiments/tactical/model_view_projection.py` maps the seven completed runner
report schemas to the strict presentation schema in `model_views.py`. It copies
reported aggregate values and uncertainty, preserving their target, unit and
weighting. It does not fit, calibrate, predict, join labels, compute a score,
construct a case set, or infer a missing result.

Implementation tests use invented source-shaped reports in temporary directories.
No real final reports have been used to develop or test this builder. This code
and a passing test suite do not authorize final evaluation or constitute a result
review. Numerical execution and publication remain separate gates.

The builder has no route in the HTTP server. Existing served files remain
unchanged. It never imports the numerical runners or shared execution gates.

## Independent support is required

A final numerical auditor may add an optional `aggregate_view_support` list to
each task in `docs/tactical/INDEPENDENT_FINAL_NUMERICAL_REVIEW.json`. Every support
entry has exactly:

- `id`: the allowlisted target code
- `cohort`: the allowlisted cohort code
- `cases`: positive integer eligible-case count
- `clusters`: positive integer count using that task's declared grouping
- `case_set_sha256`: the standardized eligible-case identity fingerprint

The auditor derives this support only during authorized final verification of
actual saved prediction identities. The builder never opens those identities.
The fingerprint is SHA-256 of the UTF-8 bytes of canonical JSON for the object
below. Both each row identity's JSON string and the enclosing object use Python
`json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True,
allow_nan=False)`. There is no byte-order mark or trailing newline. Non-ASCII
characters are escaped by that exact serialization convention; nonfinite values
are rejected, never serialized as NaN/Infinity. The enclosing object is:

- `task`: exact seven-study task code
- `target`: the target `id`
- `cohort`: the cohort code
- `case_ids`: lexicographically sorted, unique canonical-JSON string encodings of
  each source row identity

Identity count must equal `cases`; duplicate identities must be rejected by the
independent verification. Strings inside `case_ids` are the encoded identities,
not parsed/restructured copies. This definition is recorded for the auditor;
there is deliberately no builder utility that reads prediction rows or computes
this hash. It must not be replaced with a prediction-file hash, arbitrary feature
hash, parser row-stream hash, source eligibility hash or model hash. Those hashes
have different meanings even when their counts match.

If a cohort cannot be independently reconciled, omit its support. The builder
returns `aggregate_projection_unavailable` and no view if none of the task's
cohorts have support. Partially available tasks explicitly list omitted cohorts
and retain only independently supported projections. No support or case-set
fingerprint is manufactured from the runner's marginal metrics.

## Source-to-view mapping

Only known report-construction keys are read:

- Soccer: `streams`; matched R-minus-G `primary` contrasts. Full and matched
  case sets stay separate
- ACB: `diagnostics.cohorts[*].candidates` and
  `D_minus_C_shot_weighted`; all declared sensitivity-cohort codes remain distinct
- Baseball: `targets[*].procedures` raw/calibrated aggregates, the precomputed
  calibrated sequence-minus-context comparison and secondary history contrasts
- NFL: `procedures`, `primary_game_bootstrap` and
  `week_dependence_sensitivity`
- MCP tennis: evaluated `cells`, their `methods`, and saved `contrasts.intervals`;
  point-weighted versus match-macro loss gaps stay on different metric selectors
- Baseball mechanics: `models` scalar error summaries and the precomputed
  augmented-minus-context equal-athlete MAE interval
- BYU: `models` nested attempt/equal-player summaries, the precomputed equal-player
  joint NLL interval, and the reported attempt-weighted contrast

A scalar metric is never a source for a newly calculated pairwise gap. Only an
existing precomputed difference is projected. The presentation validator checks
that a supplied difference agrees with the same-case marginal losses; that is
integrity arithmetic, not a new performance estimate. Unknown source sections,
weights, model parameters and prose are not copied.

Declared counts and existing class-order, log-clipping, Brier, units and
accuracy-tie metadata are cross-checked against the task conventions; contradictory
metadata is rejected rather than silently relabeled. Present contrast-weighting
metadata must match the case-weighted, match-macro or equal-participant estimand;
missing optional weighting fields are not invented. Contrast support is checked
under its actual estimand: match/game/athlete/player groups are exact, week/event
clusters retain their different group meanings, tournament-cluster match-macro
contrasts count matches, and four-week blocks retain the declared calendar.
Missing uncertainty support withholds the interval rather than inventing it.
Its declared method label is retained, so unavailable game/week or match/event
intervals remain distinct without implying precision. Optional tennis accuracy
tie metadata must declare three-class argmax with first [wide, body, T] ties;
a binary threshold convention is rejected.
Declared counts are cross-checked against audited support. BYU bounce-only
metrics require their own reported `attempts` and `players` counts; they retain
437 bounces rather than silently receiving the 548-non-let denominator. When
that metric support is absent, its value is unavailable and its support is
unreported (zero counts); no denominator is inferred. Positive/negative density
NLL values remain valid on their density scale.

Prespecified logistic fallback output in baseball is marked as an unavailable
logistic procedure, rather than presented as independently fitted logistic
performance. Missing optional tennis families similarly remain unavailable.
A missing/undefined metric does not receive a numeric replacement.

Classification reliability copies exact fixed edges, bucket counts, mean
probability and observed fraction. Reported bin-level game support is copied;
when it is absent it remains null. Missing bins cause that entire reliability
series to remain unavailable; the builder does not invent zero-count bins, merge
bins, count games or rebuild bins from individual probabilities.

No per-game, per-session, per-player, per-fold or per-trial record list is
traversed or exported. In particular:

- ACB's source has individual leave-one-game-out records but no already reported
  aggregate omission range. This builder does not calculate a new range, and
  reports the absence explicitly. The interface can show such a range only if a
  separately verified normalized projection supplies it
- Soccer's equal-game sensitivity lacks corresponding equal-game marginal
  metrics in this normalized schema. It is not relabeled as shot-weighted loss
- All eight BYU individual/pseudonymous player/fold records, its session-removal
  details, and baseball outer-fold records remain outside the projection

The normalized view currently cannot substantiate every supporting condition
behind a successful practical/statistical criterion. Therefore successful source
Booleans become null, not false. Independently reported negative criteria may
remain false. Favorable estimates remain visible without unsupported criterion-
success claims. See `MODEL_VIEWS.md` for the exact schema and display policy.

## Guarded file driver and candidate output

The pure `project_report(task, report, aggregate_view_support)` function is used
for synthetic testing and assumes its real inputs have already been independently
cleared. The file driver `prepare_candidates(root)` performs these checks before
opening any final aggregate report:

1. Parse and semantically validate the exact seven-task final numerical audit
2. Verify its global evaluation-freeze hash and all seven fixed selection hashes
3. Reconcile all seven current canonical run-binding identities with that audit
4. Only then open the fixed final-report paths, check all reported byte hashes
   and completion markers, and perform the deterministic projections

Only audit/freeze/binding metadata and completed aggregate reports are opened.
Directory-relative no-follow reads reject symlinks in every evidence-path
component, including aliases to other files inside the project. Only bounded
regular files are accepted; a fixed report filename cannot redirect this driver
to a private prediction/target file before its hash is checked.
The seven fixed original final-report path families have an 8 MiB
(8,388,608-byte) ceiling, accommodating verbose completed aggregate reports.
Every other evidence file retains the 2,000,000-byte ceiling, including audit,
selection, binding and normalized-view files. The larger allowance applies only
to exact source-report names; it does not bypass hash checks or permit truncation.
No target cache, source dataset, model serialization, saved probability array,
raw row or private group plan is in the read allowlist. This driver does not use
an unchecked snapshot review to obtain access to original local research files.

These commands are documented for a future independently cleared installation,
not instructions to run before that clearance:

```sh
python -m experiments.tactical.model_view_projection --root .
python -m experiments.tactical.model_view_projection --root . --write-candidates
```

The first command is read-only and prints availability/count summaries without
printing all metric values. The second also writes only:

`artifacts/tactical/model_view_candidates/{task}.json`

The writer rejects symlinks in every candidate-directory component and candidate
filename. Directory-relative no-follow/exclusive opens prevent a path alias or
check/write race from redirecting candidates into served reports.
The writer rechecks the complete driver and requires the supplied candidate
contents to equal the current verified projection. It refuses existing candidate
files rather than silently overwriting them. No candidate file is written for a
task without supported target/cohort evidence. Ordinary candidate output is
ignored by source control and is not a served workbench artifact.

The candidate uses the strict normalized final-aggregate schema but is still a
**candidate projection**, not an independently approved display. A separate
review must verify source-to-projection fidelity/privacy and explicitly install
reviewed normalized files plus their exact-hash model-view review. This builder
never writes under `reports/tactical/model_views`, creates a final numerical/
model-view/snapshot review, opens a numerical execution gate, edits selections,
changes source reports, publishes a bundle or grants source rights.

## Tests

```sh
python -m unittest discover -s tests -p 'test_tactical_model_view_projection.py' -v
```

Synthetic tests mirror source construction keys for all seven report families,
check deterministic non-mutating projections, support/count/hash mismatches,
unavailable metrics/cells/fallbacks, exact reliability bins, distinct weighted
estimands, negative density losses, suppression of group records and all-success
claim removal. File-driver tests prove that missing/pending audit or a changed
binding prevents any final-report access, and that output is candidate-only,
non-overwriting and authority-rechecked. No test imports a runner, performs a fit,
creates a real review, reads an actual final report or runs a browser/socket.
