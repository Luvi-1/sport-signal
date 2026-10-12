# NFL realized-dropback benchmark: exact batch protocol draft

**DRAFT FOR INDEPENDENT REVIEW. NO FIT AUTHORIZATION.** Prepared 11 October 2026.
No predictive model, calibration model, model-selection run or holdout performance
calculation has been executed. The implemented parser's predictive gate stays
closed. Acceptance of this draft, an immutable freeze and project-owner approval
are all required before a numerical runner can be enabled.

## 1. Estimand, population and main comparison

Estimate the probability of a **recorded realized dropback** among NFL REG,
down-1–4, undeleted recorded run/pass plays with observed false kneel/spike flags,
conditional on the final observable physical state at the snap, represented by
retrospectively published charting. Unit: play. Horizon: that recorded play.
Target: `qb_dropback OR sack OR qb_scramble`, requiring observed binary flags.
Denominator: the full declared cohort, including missing charting fields.

This does not recover the original play call, an RPO's intent, an unchosen action,
or the effect of changing formation/motion. The retrospective run/pass eligibility
condition is not known for every called play before action. No pressure model,
player assessment, live recommendation, betting task, online learning or treatment
effect is part of this contract.

**One primary comparison:** calibrated full-feature regularized logistic model C
versus calibrated context-only logistic model A, on identical 2025 rows. Primary
contrast is C minus A mean log loss in natural-log units per play. Brier change is
a prespecified proper-score guardrail. Logistic is designated before evaluation;
a boosted-tree result cannot replace it after holdout inspection.

All other contrasts, including B versus A, C versus B, tree-versus-logistic and
subgroups, are labelled secondary/exploratory. They cannot change the designated
procedure or resurrect a failed primary improvement claim.

Three clocks:

- Physical event: final observable state at the snap
- Observation/publication: FTN charting after games; 2023+ participation after the
  postseason. Recorded download times do not establish historical live delivery
- Decision: play selection occurred earlier. The output may support subsequent
  scouting/film review, not that earlier decision or a demonstrated live-feed test

## 2. Sources, actual support and frozen membership

Use the same source-specific hashes, strict keys, normalizations and exclusions
as `football_parser.md` and `experiments/tactical/football.py`. The existing ten
pins cover participation/FTN 2022–2025 and PBP 2023/2025; 2022 is schema reference
only, never a training season. The newly acquired 2024 PBP is separately pinned:

- Official URL: https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2024.csv.gz
- Bytes: 19,362,351
- Retrieved: 2026-10-11T09:17:56.794114+00:00
- SHA-256: `23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06`
- Source/rights: nflverse, CC BY 4.0; source-specific notices and local-only raw data
  remain applicable

2024 PBP was acquired solely to resolve split support. Its target columns were
not loaded. Reproducible local QA is in
`reports/tactical/football/protocol_2024_source_qa.json`; this is not a fitted result.

| Role | Exact games by PBP season/week | Eligible plays | Games |
|---|---|---:|---:|
| Initial training | 2023 REG weeks 1–18 | 33,836 | 272 |
| Candidate selection | 2024 REG weeks 1–9 | 16,824 | 138 |
| Calibration only | 2024 REG weeks 10–18 | 16,511 | 134 |
| Declared post-selection refit | union of initial training and selection | 50,660 | 410 |
| Locked final evaluation | 2025 REG weeks 1–18 | 32,813 | 272 |

All three seasons join participation and FTN at 100% for these eligible cohorts.
Every row belongs to one game and one role; no game, drive or play is split across
roles. Chronology is season/week, not calendar-year text (January games retain
their NFL season). Freeze a sorted `(season, week, game_id, play_id, role)` manifest
and its hash, with no target values in the public membership artifact. The counts
above are assertions, not targets to force through alternative exclusions.

Known measurement support is part of the freeze:

- 2023: 88 missing normalized formations; 75 ambiguous zero boxes quarantined;
  4 offensive and 21 defensive non-11 personnel strings quarantined
- 2024 selection: 255 missing formations, 253 missing box/hash values, and 15
  missing defensive-personnel blocks. Of the 255 missing formations, 241 occur in
  three week-7 games (97 BAL–TB, 72 LAC–ARI, 72 SEA–ATL). These are counts of
  missing records, not a claim that all records in each game are missing
- 2024 calibration: 10 missing formations, 9 missing box/hash values and 9 missing
  defensive-personnel blocks; offensive personnel is complete in both 2024 parts
- 2025: 56 missing normalized formations, 52 quarantined zero boxes, 9 offensive
  and 28 defensive non-11 personnel strings; **no outcomes inspected by this task**

Retain every eligible row across all model blocks. Do not repair the 2024 source
pattern by borrowing participation formation, complete-case filtering or moving
weeks. This observed selection/calibration missingness shift is a transport limit
and must be disclosed. Missingness flags may use only declared pre-snap fields.

Source QA previously examined some 2025 labels in the research stage. Therefore
2025 is **performance-blind after source QA**, not fully human-blind or prospective.
No more target-by-context profiling or model performance is permitted before freeze.

## 3. Inputs and deterministic feature ladder

The parser currently exposes 28 named features. All 2023+ rows have the same
`formation_era`; retain it as audit metadata, not a learned input. The following
27 actual fields constitute the raw predictive ladder. No feature search is allowed.

**A: context (12 raw fields)**

`down`, `ydstogo`, `yardline_100`, `qtr`, `quarter_seconds_remaining`,
`half_seconds_remaining`, `game_seconds_remaining`, `score_differential`,
`posteam_timeouts_remaining`, `defteam_timeouts_remaining`, `no_huddle`,
`offense_is_home`.

**B: A plus formation/personnel (11 additional raw fields)**

`formation`, `offense_rb`, `offense_te`, `offense_wr`, `offense_ol`, `offense_qb`,
`offense_other`, `defense_dl`, `defense_lb`, `defense_db`, `defense_other`.

**C: B plus motion/box/backfield/hash (4 additional raw fields)**

`motion`, `defenders_in_box`, `offense_backfield`, `starting_hash`.

No team/player identity, extracted passer identity, player-name missingness,
current coverage, pressure/rushers/blitzers, time-to-throw, play action/RPO,
receiver/route, passing depth, yards, EPA, provider probability, final score,
future drive fields or temporal team/QB histories enter this first experiment.
Season/week/game keys are split/audit metadata only. There are no historical
rolling features and thus no online history or weight updates.

### Fixed deterministic context basis

Apply these additions equally to logistic and trees in every block, before
fitted preprocessing, using only the named source values:

- `log_distance = log1p(ydstogo)`
- `goal_distance_squared = (yardline_100 / 100)^2`
- `two_minute_half = 1` iff qtr is 1–4 and half_seconds_remaining <= 120, otherwise
  0; missing if either required input is missing
- `late_game_score = score_differential` iff qtr=4 and game_seconds_remaining <=
  300, otherwise 0; missing if any required input is missing

These are fixed representations of admitted pre-snap information, not extra
source measurements. No further interactions, knots or data-chosen bins.

### Categorical vocabulary and numeric processing

Categorical inputs are down (1,2,3,4), qtr (1,2,3,4,OT with qtr>=5 mapped to OT),
no_huddle (0,1), offense_is_home (0,1), plus formation
(SHOTGUN,UNDER_CENTER,PISTOL), motion (0,1) and starting_hash (left,middle,right)
when present in the block. Each gets explicit MISSING and UNKNOWN levels.
Source parser-invalid categories remain MISSING; a newly legal but unseen input
at inference maps UNKNOWN. Do not infer category order from observed labels.

Use dense float64 one-hot encoding with all listed levels retained, no dropped
reference category, and no target/frequency encoding. Numeric features are the
remaining admitted fields plus log_distance, goal_distance_squared and
late_game_score; two_minute_half is categorical (0,1,MISSING,UNKNOWN).
For every numeric field, add a missingness indicator whether or not training has
missing values; median-impute on the fitting population only. If the fitting
population is entirely missing, impute zero and keep its indicator. Standardize
numeric values using fitting-population mean and population standard deviation;
a zero standard deviation is replaced by one. Do not standardize dummy variables
or missingness indicators. No clipping other than the parser's predeclared
physical/range validity rules; no outcome-based imputation or feature selection.

Initial candidate transforms fit 2023 only. After selection, refit all transforms
from scratch on the declared 50,660-row refit union. Calibration and 2025 fit no
transform and cannot expand vocabularies. Freeze column order in each artifact.

## 4. Exact procedures and selection grid

All procedures use unweighted natural-prevalence observations; no oversampling,
class weights or synthetic examples. All numerical random seeds are **20261011**.
Target class 1 always means realized dropback. The environment must record Python,
NumPy, pandas, SciPy and scikit-learn versions; the current project pins are
Python >=3.11, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0 and scikit-learn 1.8.0.
Freeze the actual Python patch version before execution. Run single-process, with
BLAS/OpenMP thread counts one, for deterministic execution.

### Two fixed reference procedures

1. **Training-only constant:** `(N_dropback + 0.5)/(N + 1)` from its fitting
   population. It is never calibrated or tuned. The Jeffreys correction avoids
   exact zero/one while being fully specified
2. **Smoothed context counts:** fixed distance bands 0–2, 3–5, 6–10, 11+ yards;
   missing distance is a distinct category. Start with the same global constant
   m. For each down d, `p_d = (s_d + 50*m)/(n_d + 50)`. For each down×distance cell,
   `p_cell = (s_cell + 50*p_d)/(n_cell + 50)`. Unseen down backs off to m; unseen
   cell backs off to p_d. This baseline uses context only and has no tuned
   smoothing strength, formation extension or adaptive rare-cell threshold

Both count procedures are constructed on initial training for a development
comparison, then rebuilt once on the declared refit union. They are references;
only logistic and trees traverse the full A/B/C ladder.

### Regularized logistic: 9 initial fits

Fit each A/B/C block with C in **[0.1, 1.0, 10.0]**: 3 blocks × 3 candidates = 9.
Use L2 regularization, intercept, lbfgs solver, max_iter=2000, tol=1e-6,
class_weight=None and no warm starts. Each candidate fits exactly the same 2023
rows and its own training-only transform. A convergence failure fails that
candidate's execution check; do not silently increase max_iter, choose a new
solver or narrow the grid after viewing outcomes.

### Histogram gradient boosting: 24 initial fits

Fit each A/B/C block over this Cartesian grid:

- learning_rate in **[0.05, 0.10]**
- max_leaf_nodes in **[7, 15]**
- l2_regularization in **[0.0, 10.0]**

That is 8 candidates × 3 blocks = 24 fits. Fixed parameters:
loss=log_loss; max_iter=150; min_samples_leaf=200; max_depth=None; max_bins=255;
max_features=1.0; early_stopping=False; warm_start=False; class_weight=None;
no monotonic constraints, no interaction constraints and no native categorical
inputs (the fixed encoded matrix is used). There is no internal validation split
and no early-stopping use of selection or calibration records.

### Candidate selection and ties

Within each of the six family×block groups, choose the candidate with lowest
unrounded mean 2024 weeks-1–9 log loss. Scores within **1e-6 nats/play** of the
lowest are tied. Tie-break using the following ascending order, without consulting
Brier/AUC/calibration/test results:

- Logistic: C=0.1, then 1, then 10
- Trees: fewer leaves, then larger L2, then lower learning rate

Do not select the feature block or model family on 2025. A/B/C and both families
all retain their selected candidate for the fixed comparative report. The main
procedure remains logistic C and its comparator logistic A regardless of the
selection ranking of trees. Preserve every candidate's parameters and selection
score, including failures. A failed candidate must be repaired only as an
implementation/infrastructure defect and rerun under the identical contract;
otherwise pause the protocol for review rather than execute a reduced grid.

## 5. Refit, calibration and fixed inference

After the six winners are committed to the selection manifest, refit each once
on 2023 plus 2024 weeks 1–9 (50,660 plays/410 games), rebuilding its transforms
only on that union. Rebuild both count procedures on that same union. No 2024
weeks-10–18 observations enter these base fits.

Fit one prespecified sigmoid recalibrator for each of the six selected learned
procedures and the smoothed context baseline, using only 2024 weeks 10–18.
For base probability p, compute `z=log(p_clipped/(1-p_clipped))` with clipping to
[1e-6,1-1e-6]. Fit binary logistic y on this single z with intercept,
L2/C=1.0, lbfgs, max_iter=2000, tol=1e-6, no class weights and no preprocessing of
z. This is seven one-dimensional calibration fits. Do not try isotonic,
calibration-family choices, alternate penalties or subgroup recalibrators.
If a calibration fit fails convergence or has a nonpositive fitted slope, pause
for review before holdout opening; do not select a replacement using 2025.

The constant reference remains uncalibrated and training-only. Save both raw and
calibrated probabilities for the other seven procedures. Primary comparisons
always use the declared calibrated versions; raw versions are diagnostic and
cannot become the winner after test inspection. Calibration scores are fitting
diagnostics, not an independent performance estimate.

At final freeze, save exact transforms, model parameters, calibrators, class order,
versions, hashes and a parity test of batch and single-row inference. All remain
fixed throughout 2025; no weekly, game, team or row-level updates.

## 6. Fit budget, execution stages and target firewall

| Estimation stage | Learned optimizer fits | Deterministic count builds |
|---|---:|---:|
| 2023 candidates | 9 logistic + 24 trees = 33 | 2 |
| Declared refits | 3 logistic + 3 trees = 6 | 2 |
| Calibration | 7 | 0 |
| Total | **46** | **4** |

Thus **50 estimation/build operations**, producing eight frozen final procedures
(two references plus six family×block models). Bootstrap computation resamples
saved losses; it never refits. No seed search, feature search, additional seasons,
ensembles, pressure task, HMM or neural architecture is in this budget.
Allow at most three individual exact-configuration interrupted-operation retries
in total, never whole-pipeline restarts, so at most 53 attempts; an interruption is not
permission for a new statistical candidate. Fixing a semantic/data contract bug
requires a documented review and a new freeze before holdout use.

Execution order after approval:

1. Reproduce source and parser hashes and the whole-game membership manifest;
   validate support, duplicates and parser/mutation tests. Before any fitting,
   confirm target flags are observed binary and both classes occur in each
   development role. Do not change cohort to solve a target problem
2. Enable a separate approved development-label reader for 2023/2024. Preserve the
   default descriptive parser's 2023-only gate. The numerical runner must verify an
   explicit approved protocol hash rather than accepting a generic `--unlock`
3. Fit/select on the fixed development roles; persist every candidate score and
   the selected configuration manifest; then refit and calibrate as above
4. Freeze all artifacts, source pins (including the new 2024 pin), exact code and
   environment, split membership, prediction column order, evaluator code and
   reporting/slice specification. Independently verify the manifest and inference
   parity before requesting holdout release
5. Construct 2025 features without loading qb_dropback/sack/qb_scramble, save all
   eight frozen procedures' predictions and row keys, and hash that file
6. Only after those hashes exist and the authorized evaluation gate is opened,
   load 2025 target flags through a separate evaluator and compute the fixed
   report once. No hyperparameter/model/block/calibration or display selection
   changes are allowed in response

A target-read audit must show which columns/roles each process read. Prohibited
feature mutation, future-row mutation, row permutation, supplemental join reorder,
serialization parity and identical-row comparisons are mandatory tests. A
baseline evaluation code path cannot bypass the gate. Any unrecoverable source,
label, calibration or implementation problem pauses dependent work; it does not
justify covert exploratory 2025 analysis.

## 7. Scores, uncertainty and interpretation criteria

Evaluate on all 32,813 locked eligible rows, equally weighted per play, using
probabilities clipped to [1e-6,1-1e-6] for log loss only:

- Main proper metric: mean binary log loss, natural logs, nats/play
- Proper-score guardrail: mean Brier score on un-clipped probabilities
- Secondary discrimination: ROC AUC; accuracy at fixed p>=0.5 threshold
- Calibration description: observed rate, mean prediction, their difference, and
  ten fixed equal-width bins [0,.1), …, [.9,1]. Each bin reports play/game support,
  mean probability and observed fraction. No test-fitted recalibrator or
  calibration-slope regression is included in the fit budget

Primary uncertainty is a **paired whole-game bootstrap**, 2,000 replicates with
seed 20261011: draw 272 games with replacement, retain all plays of each draw,
recompute each procedure's sum of play losses divided by the total sampled plays,
and report percentile 2.5/97.5 intervals for C-minus-A differences. Resample the
same games for both models. Games of different lengths keep their actual play
weights; this is not a game-balanced estimand.

Prespecified dependence sensitivity: repeat 2,000 paired replicates by drawing
18 season-week clusters with replacement (seed 20261012), retaining every game
and play from each sampled week. Report both intervals, with the warning that
18 week clusters are few and repeated teams can create dependence beyond either
cluster scheme. Do not choose whichever interval is favorable. These intervals
are conditional on this fitted/selected procedure and snapshot; they do not
capture source bias, model-selection uncertainty or league-wide causal effects.

Proposed minimum worthwhile benchmark gain, subject to review before freeze:
main C-minus-A log-loss point difference <= **-0.005 nats/play**, both paired
interval upper bounds <0, and C-minus-A Brier point difference <= **+0.001**.
This is an explicit portfolio usefulness threshold, not a published coaching or
financial utility conversion. Always publish absolute scores and differences.
If the criterion fails, report failure/uncertainty and withhold an improvement
claim; do not swap in the tree winner or retune on test. The observed conditional
association cannot support technique prescriptions even if this criterion passes.

## 8. Fixed secondary slices, support and release limits

Only after the authorized holdout evaluation, report support, log loss, Brier and
calibration tables for these prespecified one-dimensional slices:

- Down 1–4; distance 0–2/3–5/6–10/11+/missing
- Formation SHOTGUN/UNDER_CENTER/PISTOL/missing; motion 0/1/missing
- Offensive team, as evaluation grouping only
- Score state trailing/tied/leading; time state qtr1–3, qtr4 with >300 seconds,
  qtr4 with <=300 seconds, OT, missing
- Offensive personnel RB×TE×WR tuple, with rare tuples pooled into OTHER if their
  **initial 2023** support is <200 plays or <10 games; freeze that vocabulary from
  2023 and never use test frequencies to define rare groups

No cross-product slice search and no subgroup superiority claim. Display raw
counts even for small cells; suppress a cell's comparative metric/interval when
it has fewer than 100 plays or 5 games in the evaluated population and label
insufficient support. This is a reporting rule, not a selection/exclusion rule:
all those plays remain in overall scores. No multiple-testing-adjusted discovery
claim is attempted for exploratory slices.

For a future scouting UI, define a comparable-context cell as
(down, distance band, formation, motion). Its support comes from the **base-refit
population only**. Flag thin support below 200 plays or 10 games; hide a numeric
scouting estimate for that UI query and show support/caveat text instead. Missing
and UNKNOWN are explicit cell levels. This never removes rows from evaluation.
No recommendation or value-ranking language is allowed, and arbitrary later
user-selected slices remain exploratory descriptions.

Raw records, row-level predictions and player identifiers stay local. Before
releasing aggregates or artifacts, perform the source-specific publication review,
retain nflverse/FTN/NGS attribution and applicable CC BY/CC BY-SA conditions,
verify protected-core hashes and independently recompute saved evaluation scores.

## 9. Decisions still required before any fitting

- Independent reviewer acceptance or concrete amendments to this exact contract,
  particularly the practical-gain threshold, calibration slope gate, missingness
  transport caveat and fixed reporting support limits
- Project-owner approval for this bounded realized-dropback experiment only
- Implementation and review of the gated numerical runner; the current parser
  remains descriptive and cannot execute this draft
- Exact Python/environment lock, source and fold hashes, and a reviewed immutable
  reporting/evaluation manifest

No additional source acquisition is presently needed to establish the proposed
cohorts. 2024 labels remain unread, and development-label completeness still needs
its authorized pre-fit check. Further algorithms, pressure outcomes, new seasons
or live availability would require a new contract, not an amendment after test
inspection.

### Retry-budget clarification before approval

The three permitted infrastructure retries are three individual interrupted-
operation attempts across the entire experiment, never three whole-pipeline
restarts. Preserve successful operations and their frozen inputs. The bound is
50 planned operations plus at most 3 identical interrupted-operation retries,
for at most 53 attempts. No extra candidate, fit or calibration is permitted.
