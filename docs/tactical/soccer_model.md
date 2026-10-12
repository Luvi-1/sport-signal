# Gated WSL numerical runner

Implementation status: code and synthetic/mocked tests only. No numerical result
is implied by this document. The exact statistical contract is
`SOCCER_PROTOCOL_DRAFT.md`; its independent review and binding-specific owner
approval remain prerequisites for fitting.

## Entry points and boundary

`experiments.tactical.soccer_model` exposes `prepare(root)`, `develop(root)`,
`calibrate(root)`, `predict(root)` and `evaluate(root)`. There is no generic unlock
flag and a caller-supplied approval path is rejected. Shared `gates.py` controls
approval. Preparation is target-blind. Development and calibration require the
approved development binding. Prediction and final-label access require the
separate evaluation approval and the global selection freeze.

Preparation checks reviewed source/derivative byte hashes, the pinned StatsBomb
commit, the exact 462-file source set, and each context's unique match-index
season/date/cohort lineage. This also prevents a development match from crossing
inner season folds. Parser/dependency/measurement-contract hashes and all three
cohort denominators must agree with the reviewed build. It hashes raw bytes without interpreting source event outcomes. It binds
code, protocol, runtime, measurement contract, source files, target-blind context
cache and the existing development-target file by bytes. Hashing a target file
is not target loading. The default descriptive parser is untouched.

Development reads only development targets. Calibration opens only the declared
60 calibration matches. Final targets are inaccessible unless the global gate is
open and immutable predictions have been written and hashed; the reader itself
checks that evidence. Null/unknown/nonbinary eligible targets stop the stage and
save affected event/match lineage locally. No unknown label is discarded or
recoded as a miss.

## Procedure

Seven reporting streams implement the protocol exactly: full and matched A/B
references, full and matched G logistic geometry models, and matched R with the
four recorded-defense terms. Matched comparisons retain exactly the same rows.
Coverage includes full geometry and separate failed matched requirements.

The fixed C grid has 18 inner logistic fits across two expanding-season folds,
three final development fits and at most three specified recalibration fits.
Pooled validation log loss selects C within each learned stream; ties within
1e-6 prefer smaller C. The designated final comparison remains calibrated
matched R minus calibrated matched G, regardless of results. Single-class
training uses the specified smoothed-rate fallback. Calibration uses the exact
bounded, identity-centered intercept/slope objective and fixed support/failure
identity rules. No fallback consults final outcomes.

Training-only means, population standard deviations, one-hot vocabularies,
column order and class order are serialized. Bearing missingness is a separate
binary input; no actual missing keeper is placed on the goal line. L2 logistic
uses lbfgs, max_iter 2000 and tolerance 1e-8. Every real fit is guarded, runs under
a single-thread limit and treats convergence warnings as stopping errors.

## Local artifacts and scoring

Ignored artifacts live under `artifacts/tactical/soccer/model/`. They include the
membership/preparation manifest, every candidate operation and score, selection,
base models, preprocessing, calibrators, target-read audits, ID fingerprints,
serialization hashes, inference parity, raw/calibrated probabilities and the
prediction manifest. `artifacts/tactical/soccer/SELECTION_FREEZE.json` binds the
completed model manifest for the global gate. These files are immutable within a
run; changed code or inputs need reviewed re-freezing, never silent overwrite.

The operation ledger saves each success and refuses to refit it. The bound is
24 planned learned-estimation slots; a single-class or calibration identity
fallback can consume a planned slot without running an optimizer. There are no
extra retry fits in the soccer protocol. A failed operation remains failed until
review; successful results are preserved.

Scoring uses saved un-clipped probabilities for binary Brier and clips only
log-loss probabilities to [1e-6,1-1e-6]. Reliability uses the exact six protocol
bins, retaining empty bins and marking n<50. The primary paired match bootstrap
uses 2,000 samples, sorted IDs, seed 20261011 and NumPy linear percentiles. The
same fixed loss arrays produce the equal-game-weighted sensitivity. All mandatory
raw streams, coverage, AUROC and body/distance descriptive slices are retained.
Scores remain local under `reports/tactical/soccer/model/`; independent saved-score
recomputation and StatsBomb publication/attribution review remain separate gates.

## Verification

Run only the synthetic/mocked suite before numerical clearance:

```sh
.venv-laya/bin/python -m unittest tests.test_tactical_soccer_model -v
```

The suite checks closed gates, strict target validation, exact budgets, geometry
and cohort conditions, one-hot unknowns, training-only preprocessing, fixed cells,
ties, permitted degeneracy fallback, future-field mutation, row permutation,
serialization and the exact scoring convention. It never calls an actual
estimator fit, even on synthetic data. Real fitted inference parity is checked
and frozen after authorized calibration.

Before calibration labels are opened, DEVELOPMENT_FREEZE.json must verify the complete fixed candidate/refit grid, candidate scores, selection bytes, prepared population, operation artifacts and developed model. Exact p=0.5 ties in secondary accuracy choose class 1 and are labeled explicitly. Saved-probability log loss/Brier also pass a separate direct-formula check.
