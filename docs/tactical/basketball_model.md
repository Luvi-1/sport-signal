# Fixed ACB release-context numerical runner

Status: implementation and synthetic/mocked-estimator checks only. No real fit is
permitted until the project lead records approval for the independently reviewed
code, protocol, sources and runtime binding. This document does not authorize a
fit, release data, or report numerical performance.

The sole model specification is
[BASKETBALL_PROTOCOL_DRAFT.md](BASKETBALL_PROTOCOL_DRAFT.md). The source parser and
its measurement limits are documented in [basketball_parser.md](basketball_parser.md).

## Fixed experiment

The estimand is make probability conditional on a recorded field-goal release in
the ten sampled ACB games, including fouled misses. A/B/C/D are mandatory and
fixed. D minus C is the designated comparison, regardless of the result.

- A: Beta(1,1) make rate over every earlier recorded release
- B: three flag × fixed distance cells, shrunk toward A with concentration 20
- C: fixed L2 logistic on log distance, three, hoop bearing, clock and explicit
  clock/bearing-missing indicators
- D: C plus log nearest-defender distance and its unstandardized interaction with
  the three flag; standardization follows the interaction construction

The four expanding development folds use the first 1/2/3/4 development games to
predict the next one. They consume exactly eight C/D fit slots, with no selection
or tuning. The outer procedure consumes exactly ten C/D slots to predict the
five later games in order. A one-class or empty eligible training stream uses
A, reserves its planned slot, and records that no estimator fit was performed.
There are no recalibrators and no additional deployment/refit models.

All logistic settings are explicit: float64, lbfgs, L2, C=1, intercept,
max_iter=2000, tol=1e-8, no class weighting or resampling. Intercept is unpenalized
under lbfgs. Any convergence warning, iteration-cap hit, invalid coefficient or
other numerical failure stops. Failed attempts consume their budget; the runner
never retries an optimizer or restarts an interrupted phase.

C and D train on the same eligible event-geometry rows. A uses all releases;
B uses eligible cells. Every unsupported geometry row receives A in all four
streams. Features never include player IDs, orientation, detection status,
provider shotQuality, assisted/contest/foul outcomes or post-release fields.
The raw tracking masks are only subgroups for the same saved predictions.

## Label and preprocessing boundaries

Preparation hashes source bytes, including future event sources, without parsing
any target file. Contexts come from the reviewed staged parser artifact. Its
parser/contract hashes, source manifest and population are checked. All 30 pinned
source files and the staged context, target, orientation and notice artifacts
are bound to the run.

Development opens only the first five games' event labels and checks them against
the separately staged development targets. Each fold then subsets labels and
contexts to the exact earlier games. No future event source is JSON-parsed and no
future outcome is extracted during preparation or development.

For the outer pass, the complete next game's A/B/C/D predictions are written
exclusively to a new file, fsynced, hashed and recorded before that game's target
source can be parsed. Only then can its labels enter the following game's history.
No outer loss, residual, calibration diagnostic or comparison is computed during
that loop. After all five files are saved and their hashes rechecked, a distinct
scoring stage reads the labels again and joins them to the immutable predictions.

At every authorized label stage, all recorded releases must have explicit binary
targets. Missing, unknown, malformed or nonbinary labels stop with affected IDs,
counts and hashed source lineage in the local journal. This includes geometry-
ineligible rows; there is no target-known subset, implicit row drop or imputed miss.

Each fit learns preprocessing only from eligible earlier training rows. Valid
clock values are in [0,24]; invalid/missing values receive the training median,
or fixed 12 seconds when all training clocks are invalid/missing. An exact-hoop
missing bearing becomes zero with the prespecified indicator. Continuous features
use training population means and standard deviations; a zero deviation uses 1.
Three and missingness indicators are never standardized. There is no clipping or
held-out imputation. Saved preprocessing includes feature order, statistics,
fallback diagnostics and the hash of its training release IDs.

## APIs and execution

The public module is `experiments.tactical.basketball_model`:

- `prepare(root, run_dir=None)`: source/code/runtime freeze only; no target parsing
  or estimation. Returns the artifact identity and immutable run directory
- `develop(root, run_dir=...)`: separately authorized eight-slot development pass;
  persists all four diagnostics and the fixed-design selection freeze
- `evaluate(root, run_dir=...)`: separately authorized ten-slot sequential outer
  procedure, then final scoring; requires completed development and the global
  cross-task evaluation freeze
- `predict(model_artifact, contexts)`: pure label-free inference from saved JSON
  model parameters. It never fits or recalibrates

Set thread settings consistently before preparation and every subsequent phase:

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python -m experiments.tactical.basketball_model prepare
# The lead must review and approve the exact binding before this command:
python -m experiments.tactical.basketball_model develop --run-dir artifacts/tactical/basketball/ARTIFACT_ID
# Separate lead evaluation approval and the global freeze are mandatory:
python -m experiments.tactical.basketball_model evaluate --run-dir artifacts/tactical/basketball/ARTIFACT_ID
```

The module never creates approval records. The shared `gates.py` verifies the
fixed lead-managed approval location, code/protocol/source/runtime hashes and
cross-task selection freezes. Every C/D slot is also reserved in the shared
stage-specific operation ledger before estimator invocation. The runner adds
its own hash-chained phase, fit, target-read, prediction and scoring journal.
These are local operational safeguards, not an adversarial authentication system.

Repeated phases, overwritten artifacts, exhausted/out-of-order slots, changed
source bytes, altered preprocessing dependencies or corrupted journals stop.
The original failed manifest and journal remain available. A correction needs a
reviewed revision that preserves the original run and labels a corrected outer
rerun exploratory. This runner supplies no convenient reset or retry flag.

Synthetic checks (no real estimator fit):

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python -m unittest discover -s tests -p 'test_tactical_basketball_model*.py' -v
```

## Local artifacts

Everything source-derived stays in ignored locations:

- `artifacts/tactical/basketball/run_binding.json`: common approval binding
- `artifacts/tactical/basketball/SELECTION_FREEZE.json`: completed development and
  immutable D/C design, not an outcome-selected winner
- `artifacts/tactical/basketball/ARTIFACT_ID/manifest.json` and `journal.jsonl`
- `models/`: JSON parameters, training ID/target hashes and preprocessing
- `development_predictions/` and `evaluation_predictions/`: label-free immutable
  prediction files, quality masks, fallback flags and model/preprocessing hashes
- `development_report.json` and `evaluation_report.json`; copies in
  `reports/tactical/basketball/model/ARTIFACT_ID/`

The artifacts use JSON rather than executable pickle objects. Immediate points
are (2 or 3) × make probability when shot value is known. They exclude free throws,
rebounds, turnovers and continuation; no earlier decision to shoot is modeled.

## Reporting

Primary results use the same event-geometry cohort for A/B/C/D. All-release
fallback and the fixed 0.1-ft, 1-ft and direct-detection masks are mandatory
sensitivities of identical predictions. Reports include per-game support, makes,
fallbacks, quality exclusions, D-minus-C losses, shot/equal-game aggregates, and
exactly five leave-one-evaluation-game-out summaries without refitting.

Log loss uses epsilon 1e-6 and natural logs. Binary Brier uses saved unclipped
probabilities. A second direct implementation checks both score arrays against
the shared scoring helper. Reliability has exactly five fixed make-probability
bins and marks n<30 as low support. Single-class AUROC is explicitly null; undefined
game results are never silently averaged. There are no headline confidence
intervals or p-values.

The exploratory yardstick is D log loss at least 0.005 nats/release lower than C,
no aggregate Brier worsening, and negative log-loss differences in at least four
of five games. Failing it never selects another model or triggers another search.
Five games cannot establish a population effect. Some later aggregate outcomes
were inspected during source QA, so this is not human-blind/prospective evidence.
Provider consistency is not physical measurement accuracy, and there is no claim
of NBA transfer, stable defender skill or causal coaching benefit. External
publication remains a separate, source-specific authorization decision.

Secondary accuracy retains the shared argmax class-order convention: exact p=0.5 ties choose class 0. This is explicitly labeled and does not affect log loss, Brier or the designated D-minus-C comparison.
