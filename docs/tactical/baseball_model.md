# Gated baseball pitch-sequence runner

Status: implemented for independent runner review. Tests use invented rows and
mocked logistic/calibration estimators only. This document does not authorize a
real binding, new target inspection, fitting, calibration, prediction or scoring.
The parser's descriptive outputs and the closed protocol are unchanged.

## Entry points and stage order

The local module is `experiments.tactical.baseball_model`. Its five commands are:

```sh
python -m experiments.tactical.baseball_model prepare
python -m experiments.tactical.baseball_model develop
python -m experiments.tactical.baseball_model calibrate
python -m experiments.tactical.baseball_model predict
python -m experiments.tactical.baseball_model evaluate
```

These are operational documentation, not instructions to run unapproved stages.
Only an explicit lead clearance permits real preparation. Development and
calibration additionally require independently reviewed, owner-approved shared
gate records for the exact immutable binding. Both prediction and evaluation
require the separately approved global evaluation freeze across the exact cohort
of tasks recorded by the shared gates. No command writes an approval.

1. Preparation verifies the accepted adjudication, parser, protocol, validation,
   frozen reference sample, all six source archives and source sidecars, all nine
   parser derivatives, and the frozen reference packet/windows. It prepares
   label-free contexts and a game/PA/pitch membership manifest, then binds their
   exact hashes together with this runner and the shared gate/metric code
2. Development reads only the 2023 initial and early-2024 selection target rows.
   It reserves and estimates all 18 candidates, chooses the two logistic C
   values separately within each target, writes the immutable selection, and
   refits exactly ten designated procedures on initial plus selection rows
3. Calibration requires the complete ten-model refit manifest before reading
   calibration targets. It reserves ten calibrators, persists every success or
   failure, and writes `artifacts/tactical/baseball/SELECTION_FREEZE.json`
4. Prediction reads 2025 prefix contexts and eligibility only. Both target
   arrays, and every available raw/calibrated procedure, are persisted before
   `PREDICTIONS_SEALED.json` can exist. Unavailable model/calibrator results are
   explicit statuses, not invented replacement probabilities
5. Evaluation verifies the global freeze, all model/calibration hashes and both
   complete prediction sets before the private reader may decode a 2025 label.
   It creates local aggregate reports; it does not publish them

Each public numerical entry and each private label/fit operation rechecks the
exact shared stage approval and full bound inputs. The private reader rejects
unauthorized roles before decoding target JSON. The private fit additionally
checks the exact configuration, ordered cohort feature/identity hash, and the
labels' binding/target/role provenance. A durable operation is reserved before
any train-only encoder, table estimator, classifier or calibrator is fitted.

## Frozen source prerequisites

The accepted reference adjudication is
`reports/tactical/baseball/reference_adjudication.json`, SHA-256
`9854b5876623fe45f183b2ebf4402092b711d234162873e43b22bdf7bba6f3a1`.
It covers 133 PAs and 641 deliveries with zero unexplained discrepancies. The
frozen sample membership SHA-256 is
`3d5b30035926ad1c9c94e319de1dfdd9f120a270c76a65b38f5bddf4f7b421c9`.
These are source-representation prerequisites, not numerical approval or
independent physical contact observations.

Preparation uses projected parsed columns `gid`, `date`, `gametype`; raw game
IDs, initial dates and suspension comments; and every delivery date interval.
It never substitutes the game ID's date. Reversed or out-of-season intervals
fail closed before any fold is assigned. The whole-game span union assigns the
protocol's 2,430 initial, 1,261 selection, 1,167 calibration, one boundary-excluded,
and 2,430 evaluation games. `BOS202406260` must be the sole boundary exclusion.
All delivery memberships, including ambiguous/excluded prefixes, remain in the
manifest. The three annual eligible swing/contact denominators must match the
approved parser QA exactly.

The mixed parser JSONL contains targets, but the runner does not deserialize an
entire row during preparation or label-free inference. A top-level structural
scanner locates field spans; only explicitly requested namespaces reach the JSON
decoder. The target reader first projects identity and rejects unwanted rows,
then decodes the target namespace only for the authorized exact cohort. Hashing
source bytes is permitted integrity work, not predictive target inspection.

## Exact estimators and budget

There are nine candidates per target: beta(1,1) constant, count × hand table,
count × hand × immediately previous delivered-category table, three context
logistics and three context-plus-sequence logistics. C is exactly 0.03, 0.3, 3.0.
Tables shrink with strength 100 to their declared parent. Unknown context/history
cells return that parent. Selection uses uncalibrated mean natural-log loss;
within 1e-6 nats, smaller C wins. A whole failed logistic block uses its fixed
context-table fallback and marks that logistic comparison unavailable.

There are exactly 38 reserved development attempts: 18 initial candidates,
10 designated refits, 10 calibrators. Failed attempts remain consumed. No extra
candidate, retry, class balancing, feature selection or alternative calibration
method is available. Partial phases retain their evidence and cannot silently
restart. Existing equal or differing artifacts are never overwritten.

Logistics use sparse float64 one-hot encoding fitted only on their fit roles,
unknown levels ignored, no dropped level or frequency merging, and precisely the
protocol's L2/lbfgs/intercept/no-class-weight/1,000-iteration/1e-8 settings. The
prefix-only feature allowlist is eight context fields plus four separate
sequence fields. Hand-method values use fixed one-to-one short labels solely
for storage. Player IDs, dates, current symbols and final outcomes never become
predictors. Saved categories and coefficients reproduce estimator inference at
absolute tolerance 1e-12 before the model is accepted.

Each calibrator minimizes the exact penalized Bernoulli objective using
L-BFGS-B, (a,b)=(1,0), the fixed bounds and optimization limits. Calibration
input clips to [1e-6,1−1e-6], distinct from metric clipping. Nonconvergence or a
parameter within 1e-8 of a declared bound is unavailable, with raw results
retained. The boundary tolerance only detects the optimizer's reported bound;
it does not trigger another calibration method.

## Metrics, uncertainty and resource limits

Every designated procedure uses identical target-specific rows. Binary Brier is
mean((original p−y)²). Natural-log loss clips p to [1e-12,1−1e-12]. Units are nats
per eligible delivered pitch for swing and per eligible swing for contact.
Accuracy predicts class 1 at p≥0.5. AUROC is secondary and unavailable for a
single-class subset. Reliability uses ten fixed equal-width bins with the final
bin including 1; empty bins remain visible. The baseball-local bin edges are
`np.arange(11, dtype=float)/10`, so literal decimal endpoints such as 0.3, 0.6
and 0.7 belong to the bin starting at that endpoint.

The primary calibrated sequence-minus-context swing comparison requires at
least 0.001 nats/pitch reduction and a paired 95% interval entirely below zero.
Contact and history-table comparisons are explicitly secondary. The runner
initializes one RNG per target, sorts game IDs lexicographically and makes
2,000 shared whole-game draws. Every draw recomputes pitch-weighted differences
from game loss sums and denominators. Quantiles use the linear method. Fixed
count, hand, inning, base and score slices include support and are exploratory.
No slice can replace the all-eligible primary denominator or create a new claim.

Training count × hand support is saved per model for display. A cell requires
200 opportunities and 20 distinct training games for display, without removing
any benchmark row. Logistic unseen-level counts and rates are reported.

The runner limits numerical libraries to two threads and address space to
8 GiB, and records peak resident bytes. The selection/refit/calibration phases
share six hours of active wall-clock allowance; evaluation has a 30-minute
allowance. Per-phase reports retain CPU/wall time, peak RSS, package/runtime
fingerprint and seed. A resource failure stops the phase without sample or grid
reduction. The predictive outputs are retrospective conditional associations;
there is no claim about unthrown pitches, mechanics, strategy effects or
prospective online availability.

## Local artifacts and tests

All new artifacts are under ignored `artifacts/tactical/baseball/`. JSON model
states are reviewable; prediction NPZ files contain local row IDs and never
leave the local research tree automatically. Both carry source-hash provenance
through their accompanying manifests. Publication still requires independent
metric recomputation, pinned-data reproduction, protected-baseline verification
and source-specific release review.

```sh
python -m unittest discover -s tests -p 'test_tactical_baseball_model.py' -v
```

The synthetic suite covers source integrity, role/read timing, train-only
encoding, current/future outcome invariance, exact grids and attempt accounting,
private fit rejection, source-date unions, immutable persistence, inference
parity, calibration boundaries, common-case denominators and paired uncertainty.
It does not inspect new real targets or fit a real model.

The information used here was obtained free of charge from and is copyrighted by
Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".
