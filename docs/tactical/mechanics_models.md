# Grouped laboratory numerical runners

Implementation: `experiments/tactical/mechanics_model.py`.

**Implementation and synthetic/mock verification only.** This document does not
approve a real fit, create a stage approval, or replace the exact laboratory
protocols. At implementation handoff no real target loading, run preparation,
estimation, model selection, outer prediction, or outer score was performed.
The protocols and existing descriptive parser are unchanged.

## Separate experiments and denominators

- `baseball_mechanics`: the exact paired adult OpenBiomechanics cohort, 571 swings
  from 82 athletes. Five outer athlete folds, four inner folds, two ridge feature
  blocks, four fixed alphas, 170 ridge fits and five analytic training means
- `tennis_execution`: the exact BYU cohort of 548 recorded non-let attempts from
  eight players. All 111 net-censored attempts remain; 437 have observed bounce
  pairs. Nineteen lets are excluded by the existing reviewed parser. Eight
  leave-player-out folds and the two fixed B0/B1 hurdle forms give 16 fits

These are grouped experiments. Each participant supplies training data for other
participants' outer folds. There is no untouched final chronological lockbox,
human-blind experiment, or verified future-session forecast. Source eligibility
QA necessarily uses recorded outcomes and, for BYU, let/net status. That parser
runs only after numerical-stage authorization; all actual fitting/inner selection
receives explicitly indexed training/validation labels. Prediction functions
receive feature contexts only. The held-out label mutation tests establish
within-fold invariance, not global source-label blindness.

## Immutable lifecycle

The CLI exposes three separate phases:

```sh
python -m experiments.tactical.mechanics_model prepare --task baseball_mechanics
python -m experiments.tactical.mechanics_model develop --task baseball_mechanics
python -m experiments.tactical.mechanics_model evaluate --task baseball_mechanics
```

Use `tennis_execution` for the other experiment. These commands are instructions
for an independently cleared run, not commands already executed during this
implementation. No CLI flag bypasses approval or supplies a replacement dataset.

1. `prepare` validates pinned source bytes and reads the existing aggregate summary
   and private split manifest. It never calls the CSV reader, loads targets,
   regenerates membership, fits, or creates approval. `prepare_binding` binds the
   exact protocol, parser, runner, gates, scoring helper, package configuration,
   acquisition manifest, source bytes, descriptive summary, private memberships,
   measurement contract, and previous independent reviews. The numerical review
   clearing that exact binding is supplied separately by the lead
2. `develop` calls `require_stage(..., "development")` before any target CSV read.
   The existing parser reproduces the fixed cohort and an exact comparison to the
   frozen deterministic group plan. One durable stage-start marker, a process
   lock, exact named operation slots, and the shared hash-chained operation ledger
   prevent retries and concurrent/repeated stages. Failed attempts remain consumed
3. Each outer fold saves its model parameters and all paired held-out predictions.
   Baseball also retains every inner fitted parameter set, inner validation row
   membership/prediction, selected alpha, and inner score in the private development
   details. No outer performance function is called during development
4. After **every** fold finishes, `SELECTION_FREEZE.json` binds all outer models,
   outer predictions, all inner models/predictions and selection details, the
   complete operation ledger, feature-context hash, cohort and fit counts
5. `evaluate` requires a separate exact binding approval and the shared complete
   cross-task global freeze. It checks every frozen artifact before its target
   reader runs, reconstructs predictions from saved JSON parameters, verifies
   exact row pairing and serialization parity, then reserves the one scoring
   operation. All outer predictions must be present before any loss is computed

Run artifacts live under ignored `artifacts/tactical/<task>/`. Writes are exclusive,
fsynced and mode 0600; there is no overwrite/restart option. The shared local gates
are auditable workflow controls, not a security boundary against a person who can
edit arbitrary local files or code. A failed run needs a separately reviewed
revision; it is never automatically resumed, retried or replaced.

## Numerical formulas

### Baseball

Only the four exact incoming-pitch fields and four canonical body angles from the
protocol enter the two matrices. Identity, session, age, handedness, current or
aliased outcomes, bat speed, target components, and filenames never enter either
matrix. Age is only source eligibility. There is no automatic numeric-column
selection, mirroring, imputation, interactions or target standardization.

Training weights are `N / (G * n_g)`, giving each training athlete the same total
weight. Means and population variances use those training weights only. Constant
training columns are dropped from the coefficient vector, which excludes them
from penalization; their count is saved. An all-constant fit stops for review.
Float64 `Ridge(solver="svd", fit_intercept=True)` minimizes weighted summed SSE
plus alpha times standardized coefficient squared norm. The intercept is not
penalized. Every estimator prediction is checked against its saved numeric model.

Each block independently selects from `{0.1, 1, 10, 100}` by equal-athlete MAE over
all four pooled inner held-out folds. Thus athletes, rather than unequal-size
inner folds, are weighted equally. A tie within `1e-12` mph chooses the larger
alpha. The selected block is refitted once on the complete outer training set.
Exactly 160 inner fits, ten outer refits and five analytic means are allowed. All
175 operations are durably reserved, with the fit kinds separately identified.

Primary scoring is macro-athlete MAE. Macro RMSE first square-roots each athlete's
MSE and then averages those RMSEs. Row MAE/RMSE, all five aggregate outer contrasts,
and the mean-reference results are retained. The designated candidate remains
augmented ridge even after an unfavorable result. The project threshold requires
at least 0.5 mph lower macro MAE and the paired interval's upper limit below zero.
There is no recalibrator, prediction interval, or residual-scale fit.

### BYU execution

B0 uses fixed Beta(1,1) net smoothing. Clearance-bounce means and raw second moments
use their observed-bounce counts as the denominator, followed by `Q - mu mu^T +
0.0025 I`. B1 uses exactly 20 pooled pseudo-observations for each of the fixed
period-by-region cells, independently respecting total-attempt and bounce counts.
It shrinks raw second moments, not already-centered covariances. Empty cells fall
back algebraically and support failures are recorded privately. The minimum
training counts remain 100 attempts, 50 observed bounces and three players with
observed bounces; failure stops rather than changes the model.

Inputs are supplied period, assigned region and that row's exact marked target.
Current speed, current let/net flags, bounce/error, player identity and source
filenames are absent. No point pairs or bounces are invented. Equal-attempt
training differs explicitly from primary equal-player evaluation.

Net NLL is only `-log(p_net)`. An observed bounce receives `-log(1-p_net)` plus a
Cholesky-based bivariate Gaussian NLL for target-relative error. A net record never
calls the Gaussian density or reads coordinates. Nonfinite/nonpositive-definite
results fail rather than clip. Continuous NLL may be negative. Location NLL,
Euclidean error and the fixed 90% ellipse cutoff apply only to the 437 observed
bounces; net Brier and joint NLL use all 548 attempts. Both equal-player and
attempt-weighted summaries are shown. The fixed practical threshold is a 0.02
nats/attempt equal-player reduction; its uncertainty interval is also disclosed.
There is no outer winner selection, tuning, recalibration or refit.

## Uncertainty, independent checks and privacy

Both experiments use exactly 2,000 paired whole-participant resamples from
`Generator(PCG64(20261011))`, with draw arrays `(2000, 82)` and `(2000, 8)` and
linear percentile endpoints. Scores and intervals are conditional on saved
out-of-group predictions. They do not quantify full training/selection, shared
session, sensor or population uncertainty. An independent scalar macro-metric
calculation, determinant-based Gaussian calculation, shared Brier check and shared
cluster-bootstrap recomputation challenge the primary formulas.

BYU session-exclusion sensitivity keeps predictions unchanged, averages within
remaining players and then equally across supported players. The aggregate report
shows the contrast range and remaining-player counts. The eight pseudonymous
player-fold differences and session-specific details stay in a separate private
artifact; even those small participant aggregates require separate privacy review.
No participant identifiers, per-trial results, physiological profiles or player
rankings are exported. There is no workbench integration or public report/weight
publication in this runner. Source-specific release rights remain a separate gate.

## Verification command

```sh
python -m unittest tests.test_tactical_mechanics_model -v
```

The suite uses pure synthetic formulas, mocked estimators and fabricated temporary
source/approval fixtures. It never fits a real estimator, parses provider rows or
approves a real task. Coverage includes weighted fold preprocessing, exact objective
configuration, alpha ties, macro-RMSE reduction order, raw-moment shrinkage, censored
net NLL, negative continuous density loss, bootstrap units, read-before-approval
spies, immutable starts, exact caps, outer-label mutation, saved JSON parity,
complete freeze coverage and altered source/model/prediction rejection.
