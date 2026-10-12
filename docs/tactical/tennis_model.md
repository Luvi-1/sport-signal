# Tennis numerical runner

Status: implementation for independent review. No real numerical fits, source
feature extraction, resource probe, selection, calibration or predictive
performance were run during implementation. Passing synthetic tests is not
approval to fit. The exact authority is the local reviewed binding and the
project lead's separate development/evaluation approvals.

## Scope and commands

`experiments.tactical.tennis_model` implements the four fixed A1/A2 × men's/women's
MCP corpus cells in `TENNIS_PROTOCOL_DRAFT.md`. It uses the frozen parser without
altering its eligibility, including the contradicted 2021 Hurkacz–Federer source
date quarantine. The source remains local noncommercial research under its
CC BY-NC-SA terms. Nothing here authorizes model-weight distribution, raw data
sharing, deployment, biomechanical inference or causal coaching recommendations.

Use the pinned `.venv-laya/bin/python` runtime:

```sh
python -m experiments.tactical.tennis_model prepare --root .
python -m experiments.tactical.tennis_model develop --root .
python -m experiments.tactical.tennis_model evaluate --root . --as-of 20260122
python -m unittest discover -s tests -p 'test_tactical_tennis_model*.py' -v
```

`prepare` only verifies/hashes source bytes and binds protocol, parser, runner,
shared metrics, gates, the SQLite index, match QA and runtime. Preparation also
requires an independently created local SOURCE_CACHE_REVIEW.json anchor that
binds expected index/QA/summary bytes to the exact raw-source and parser hashes
and the stage-one review. The runner never creates or refreshes that anchor.
It also checks the current source summary, parser and raw manifest against the
existing independent stage-one review, rejecting stale lineage before binding.
Hashing future
source bytes does not parse their targets. Do not run this until implementation
review is settled: changed bindings cannot silently replace an existing one.

`develop` requires the exact development approval before source target access.
It constructs development rows, fits the fixed candidates, freezes all four
selection decisions, then constructs and calibrates 2024. `--no-probe` declines
the optional nonlinear family altogether; it does not select a smaller grid.
A final `SELECTION_FREEZE.json` includes preprocessing, model/code/source/protocol
identities, selection, temperatures, history settings, dependencies and attempts.
It does not unlock evaluation. `evaluate` additionally requires the lead's global
cross-task freeze and a separate matching evaluation approval. The sole evaluation
availability cutoff is fixed at 20260122, admitting every eligible 2025 source-date
match including 31 December under the strict +21-day rule. An earlier/later
caller-supplied cutoff or a cache with another cutoff fails closed; partial-year
evaluation is not allowed.

The Python `predict(root, cell, prepoint_features, history)` API consumes an
explicit parser pre-point feature mapping and already-available history. It
returns the frozen designated model's calibrated three-class probabilities,
support and interpretation limits. It loads no current target row or future
source frame and is a local research API rather than a production service.

## Label firewall and chronological histories

- Whole source matches are date-keyed and accepted only by the reviewed parser
  and date QA. Every point travels with its match and both actors
- Parameter labels must have source Date + 21 calendar days strictly before the
  end-of-stage cutoff; late-December labels do not move into the next fit stage
- The index is opened read-only. Each target `SELECT payload` first checks its
  role: authorized parameter label or past history available strictly before
  the analysis date. The reader handles one accepted match at a time
- Future feature construction does not preload a full target-bearing future
  dataframe. Separate role guards cover raw source and cached-label access
- At each analysis day the chronological history cursor admits all eligible
  older complete matches before the first feature snapshot. It then freezes for
  the day. No within-match or same-day directional update is allowed
- Current score replay still uses earlier completed points in the current match
  and A2 sees the completed first fault. Current target outcomes and unparsed
  rally suffixes are excluded from the feature API
- Empty 2010 histories are persisted across development/calibration/evaluation
  checkpoints. Late-December labels are admitted later only when needed by the
  approved past-history policy. 2024/2025 histories can update, while trained
  weights, scales and hyperparameters remain fixed
- Stage reports count unavailable matches and candidate point rows without
  extracting their unavailable target labels. Directional counts for those
  omitted populations are deliberately not manufactured from early reads

The +21-day date is assumed availability, not verified completion, publication
or historical ingestion. Whole-match QA is retrospective cohort selection,
not a prediction input. Prior source QA already inspected 2025 score/eligibility
information; this is performance-blind after that QA, not an untouched lockbox.

## Feature and candidate contract

B0 uses exactly the global +1, surface +100 and surface×side +30 smoothing.
B1 uses the four half-life 365/infinity × alpha 50/200 settings, side then
surface×side shrinkage toward B0. Numeric features additionally use fixed 730-day,
alpha-100 server and returner histories. Their support features are explicitly
actor-total effective eligible observations and distinct prior eligible matches,
across sides/surfaces. Support tiers use ordinary actor-total eligible counts,
not decayed effective sample sizes. Baseline fallback means no server-side
eligible history; a player with a different-surface history can retain side-level
information through the prescribed hierarchy.

Only fixed categorical vocabularies and 21 numeric fields are model columns.
Player names are history keys and private audit/grouping fields. Blank hand is
U, A2 omitted/unknown direction stays explicit, and tie-break scores use separate
numeric fields with structural zero outside tie-breaks. Missing/nonfinite numeric
inputs fail rather than being imputed. No event date, identity one-hot,
player-pair, rank, suffix, current outcome, Notes prose or free-text field enters
the matrices.

L uses fixed vocabulary sparse one-hot plus training-only StandardScaler
`with_mean=False` (saved mean/scale; no centering of the sparse matrix), the exact
saga/L2 C grid and only the 300→1000-iteration convergence retry. N uses the same
semantic fields, float64 numeric matrix and saved int32 categorical codes, native
categorical indicators, and the exact 15/31-leaf grid. No validation-led early
stopping or alternate model search occurs. All transformations and selected
models remain frozen after selection, without a 2023 weight refit.

Within-family tie bands are measured against the true minimum loss rather than
chained pairwise ties. The family simplicity rule is B0/B1/L/N within 0.002 nats
of the best selected family. Calibration is a bounded scalar log-temperature
optimization with the exact support gates, tolerance and iteration limit.
Failure/insufficient support retains identity T=1; it never changes the main
family. Empty/unsupported cells stay descriptive without pooling.

## Resource and reproducibility safeguards

Compact float64/int32 memory-mapped arrays, int8 labels and deterministic gzip
metadata keep all source rows out of Python dictionaries at once. Feature and
row IDs have ordered hashes; every materialized dataset file is hashed. Before opening cached labels, its
manifest must equal the complete stage-parent row manifest; applicable candidate
or final freezes protect those parent artifacts. The
history checkpoint holds small aggregate counters, not full source rows. Data
rows and private actor identities remain under ignored local artifacts.

The one optional resource probe is the earliest 100,000 eligible training A1-men
rows (or all if fewer), source-date/match/point ordered, 15 leaves and 20
iterations. It produces no predictive score. Its model is discarded. The exact
factor-of-two safety extrapolation uses all four training row counts. N is
admitted only under the declared CPU, peak-RSS and full-matrix memory estimates.
The probe never substitutes smaller real candidate training populations.

All optimizer attempts are write-ahead reserved in the shared approval journal
and the tennis ledger. Interrupted/failed attempts still consume their slot.
The ledger prevents extra probe, grid or convergence-retry attempts. At most
49 optimizations can occur (24 L including prescribed retries, eight N, one
probe, sixteen temperatures); unavailable cells/families reduce actual work.
There are no infrastructure retries or transferable extra candidates.

There is one process with four BLAS/OpenMP threads. Runtime includes the full
CPython patch/platform and exact pinned NumPy/pandas/SciPy/scikit-learn versions.
An explicit full-cell matrix/estimator envelope is checked before fitting.
The optimizer resource context additionally applies a 4-GiB address-space limit,
which is conservatively stricter than the 4-GiB resident-memory limit, and an OS
CPU soft limit using the remaining 90-minute budget. CPU limit rounding is under
one second. Peak RSS, wall/CPU duration, cumulative candidate-stage CPU, status,
seed and threads are saved for each attempt. The complete stage CPU/RSS totals
are additionally checked and saved immediately before candidate and final
freezes, including transformations/predictions after the last optimizer.
A resource failure is disclosed;
it does not authorize a new model or reduced cohort.

Partial construction or interrupted fitting fails closed. The runner does not
automatically erase partial outputs and rerun attempts. A reviewed resumption
must use unchanged completed checkpoints, or report the operation incomplete.

## Locked comparisons

Evaluation saves prediction arrays and their ordered-row/freeze digests before
scoring. All frozen families use identical rows. Metrics use natural log loss
with epsilon 1e-12 and renormalization, multiclass Brier sum (no division by
three), fixed ten-bin per-class reliability, accuracy, recalls, match/server
macro log loss and support/fallback coverage.

The planned main-minus-B1 contrast is reported calibrated and uncalibrated.
Whole-match paired bootstrap, normalized-tournament/year bootstrap and four-week
moving-calendar-block sensitivity each use 2,000 replicates and seed 20261011,
with point-weighted and match-macro versions. The moving bootstrap includes all
53 bins anchored on 1 January 2025, including empty weeks and a shortened final
bin. Each sample draws fourteen non-circular four-week windows and retains the
first 53 whole bins. Complete matches remain intact. Small group support returns
an explicit unavailable interval, not a spurious precise estimate.

All four primary contrast intervals use 98.75% confidence. A claim requires at
least a 0.005-nat reduction and an adjusted interval entirely below zero; when
B1 was designated main, no improvement is claimed. The test ranking cannot
nominate a different model. Predeclared slices suppress direction/performance
output below 200 points or twenty matches while retaining coverage counts.

## Tests and remaining review

The synthetic suite covers strict embargo/year-end boundaries; the three-day
match example and known quarantine; no future parameter/history/cache reads;
day-start freezing and both actor roles; feature immunity to current/future
outcome/suffix/QA fields; unknown actor/context backoff; exact B0/B1 math; decay
age; first-fault semantics; tie-break structural values; training-only scaling;
fixed vocabularies; candidate/tie/support contracts; probability clipping;
deterministic arrays/gzip; the 49-attempt ceiling; and before-fit gate failures.
The full four-cell orchestration is also exercised with fixed-distribution
estimator stubs and a mocked temperature optimizer, including a future-label
mutation and candidate-freeze-before-calibration assertion. No unit test trains
a logistic/nonlinear estimator on source data.

Independent implementation review and exact development approval remain required.
The test suite and source/code/protocol bindings must be refreshed after any
accepted implementation correction, before any real fit or resource probe.
