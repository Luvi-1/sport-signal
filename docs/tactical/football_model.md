# Gated NFL realized-dropback numerical runner

Implementation status: code and synthetic/mocked tests only. The exact statistical
contract is `FOOTBALL_PROTOCOL_DRAFT.md`. No model result or numerical clearance
is implied here, and the protected descriptive parser is unchanged.

## Stage API and target firewall

`experiments.tactical.football_model` exposes `prepare(root)`, `develop(root)`,
`calibrate(root)`, `predict(root)` and `evaluate(root)`. No `--unlock` option exists.
Shared `gates.py` binds exact source bytes, code, protocol, runtime and metadata.
Only the lead-controlled binding-specific approval can authorize development.
Final prediction and scoring require a separate global selection freeze and
evaluation approval. A caller cannot substitute an approval file.

Preparation loads only PBP keys, eligibility, metadata and admitted pre-snap
columns, plus the explicit participation/FTN allowlists. Source basename, season,
SHA256 and provenance are validated before dataframe body reads. Every raw PBP
row ordinal is retained internally for role-restricted target reads. The frozen
membership is sorted season/week/game/play/role; its support must exactly match
the protocol and no game can cross roles. 2022 is never a training season.

Development targets are read only for 2023 initial training and 2024 weeks 1–9
selection. The CSV reader skips non-role source row ordinals before producing a
target dataframe; calibration/final targets never enter a development dataframe.
Calibration has a separate fixed-role reader. The protocol phrase “both classes
in each development role” is implemented phase-specifically: initial/selection
labels are validated immediately before candidate fitting; calibration labels
stay unread until the separately authorized calibration stage, where both classes
are checked before its first fit. A calibration failure stops and reports without
reopening candidate selection. Unknown target flags stop the
stage and preserve local lineage; no complete-case target subset is invented.
Every reader checks its role and metadata before source body access and emits a
column/role audit. Supplemental join audits are target-blind, and the parser's
later-play-category diagnostic remains inaccessible.

A final reader additionally demands immutable prediction bytes and matching
frozen model evidence before opening final target columns. The whole 2025
population remains in every model comparison regardless of feature missingness.

## Exact procedure and accounting

The twelve context fields form A, the eleven formation/personnel fields extend
B and the four motion/box/backfield/hash fields extend C. `formation_era` and all
identity, later-play and outcome fields remain outside the learned matrix. Four
fixed deterministic context terms are applied equally to logistic and trees.
Categorical levels, MISSING, UNKNOWN and column order are fixed. Every numeric
field receives a missingness indicator, training-only median imputation and
population-mean/std scaling; all-missing columns impute zero and zero variance
uses scale one. No dummy or missingness indicator is standardized.

Nine initial logistic and 24 initial tree candidates use exactly the approved
grids. Selection is unrounded 2024 weeks-1–9 log loss with 1e-6 ties and the
specified regularization/complexity order. All six winners are committed before
six declared union refits. Both count references are built initially and rebuilt
on that same union. Seven sigmoid calibrators are fitted only on 2024 weeks
10–18; nonconvergence or nonpositive slope stops before holdout. Constant remains
uncalibrated. Logistic C versus logistic A remains the designated comparison.

The persistent ledger contains 50 planned operations: 46 optimizer fits and four
count builds. Each operation reserves an attempt before execution and saves its
result, exact configuration/input signature and hash. A successful operation is
loaded rather than refitted. A failed operation is not silently retried. Only an
explicitly reviewed infrastructure interruption permits an identical-operation
retry, with at most three such individual retries and 53 total attempts. Semantic
changes require a new review/freeze, never a reduced grid or pipeline restart.
All numeric work is single-process/single-thread and uses seed 20261011.

## Artifacts, frozen inference and scoring

All artifacts remain ignored/local under `artifacts/tactical/football/model/`.
Every candidate and its selection score, model/transform, calibrator, column and
class order, source/code/environment/split fingerprint, rare-personnel vocabulary,
refit context support and target-read audit is preserved. Joblib files are accepted
only with the exact locally generated manifest hash and environment; never load
untrusted pickle files.

After authorized calibration, batch versus single-row parity is verified on the
first 32 canonical calibration keys, chosen independently of outcomes. The
selection artifact `artifacts/tactical/football/SELECTION_FREEZE.json` binds the
frozen model manifest. Predictions contain all eight procedures, with raw and
calibrated versions except the uncalibrated constant. Predict/evaluate reject
changed model or prediction bytes and never overwrite an existing final file.

Binary Brier uses raw saved probabilities. Only log loss clips at 1e-6. Scores
include AUROC, accuracy using p>=.5 and ten fixed equal-width reliability bins
with play/game support. Paired 2,000-replicate game and week percentile intervals
use seeds 20261011 and 20261012, sorted clusters and linear quantiles; both are
reported regardless of their direction. The prespecified one-dimensional slices
retain small-cell counts and suppress comparative metrics below 100 plays or
five games. Personnel grouping comes only from initial-training support. Refit
context support is stored for a future thin-support UI without removing any
final evaluation rows.

Final reports are local under `reports/tactical/football/model/`. Missingness
transport, retrospective intent limits and few-week/repeated-team dependence are
explicit caveats. Independent recomputation and source-specific publication and
attribution review remain separate release requirements.

## Synthetic-only verification

```sh
.venv-laya/bin/python -m unittest tests.test_tactical_football_model -v
```

Tests cover budgets and grids, fixed transforms and vocabularies, training-only
imputation, UNKNOWN/MISSING distinction, strict source-role readers, closed gates,
prohibited/current/future feature mutation, row/join permutation, tie behavior,
reference shrinkage, serialization, batch/single transform parity, support and
score conventions. Estimators are mocked; no actual estimator fit is invoked.

Before calibration labels are opened, DEVELOPMENT_FREEZE.json verifies the complete fixed candidate/refit grid, candidate scores, selected configurations, prepared population, operation artifacts and developed model. The dependency fingerprint includes shot_sources.py. Exact p=0.5 ties choose class 1, as fixed in the protocol.
