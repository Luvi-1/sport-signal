# Basketball numerical protocol draft: fixed ACB forward procedure

**DRAFT, NOT APPROVED. Fitting remains prohibited.** This is a reviewable proposal,
not an implementation or a record of model performance. Freeze reviewed protocol,
source/contract/parser hashes and package versions only after independent review
and explicit parent approval. No future-game scores have been produced here.

## 1. Estimand, games and measurement

Probability of a make conditional on a recorded field-goal release in the ten
sampled SkillCorner Liga ACB games, including fouled misses. Actual parser source,
rights, feet units, hoop (-40.75,0), exact release frame and quality definitions
are in `basketball_parser.md`; source commit is
`4bbed2e35e8fdd2cf083e8c8b280b3e5381a2c66`.

Fixed initial development: 114243,114234,114169,114099,114086, in that order.
Fixed sequential evaluation: 178442,179612,184439,188630,191313. Later labels can
enter only the predeclared past-only refit after their prediction is immutable.
No outer score is inspected until all five prediction files have been saved.
Source QA previously inspected some later aggregate outcomes, so this is not a
human-blind/prospective validation claim.

All 1,459 releases remain the declared population; 1,433 event-geometry rows are
the primary supported context cohort. Missing geometry receives a separately
reported pooled fallback. Do not silently restrict to conventional box-score FGA.
Provider xG/shotQuality, contest/blocked/assisted/foul outcomes, full-season
aggregates, end-frame fields, shooter/defender identities, player ability and
mechanics are not features. This is retrospective annotated release context,
not proven online delivery or a model of the preceding choice to shoot.

## 2. Exactly four fixed candidates

A: Beta(1,1) global make rate from all past recorded releases with a valid label:
`(makes+1)/(releases+2)`.

B: cells defined by three flag × distance `[0,6),[6,14),[14,22),[22,infinity)` ft;
`(cell_makes + 20*A)/(cell_n+20)`. Cell training uses eligible event-geometry rows;
unseen/empty cells equal A. No alternative cutpoints or prior concentrations.

C: L2 logistic, C=1, intercept, log1p(distance_ft), three,
absolute_hoop_bearing_rad, shot_clock_seconds and shot-clock-missing indicator.

D: identical to C plus log1p(nearest_defender_distance_ft) and its interaction
with three (multiply the unstandardized log-distance by the 0/1 three indicator,
then standardize that interaction using training only).

All logistic fits: float64, lbfgs, L2, unpenalized intercept, max_iter=2000,
tol=1e-8, no class weighting or row resampling. No feature/hyperparameter search,
random seeds search, trees, splines, networks, ensembles or player effects.

Preprocessing is refitted only on eligible rows from strictly earlier games.
Impute missing/invalid shot clock to training median; if no valid training clock
exists, use a fixed 12-second numerical fallback. Include the missingness flag.
Undefined bearing at the exact hoop is encoded as zero with an additional bearing-
missing indicator. That indicator is a fixed, explicit addition to the current candidate contract
proposed for review. This draft chooses the indicator; no later score chooses
between adding it and excluding those rows.
Standardize continuous columns by population mean/std from training; zero std
uses scale 1. Three/missing indicators are not standardized. No clipping, score-
dependent trimming, learned distance bins or future-game imputation.

Both C and D train on identical event-geometry rows. If a past training set has
only one label class, use A for that stream and disclose the deterministic
fallback. A row lacking eligible geometry receives A under every candidate,
never invented coordinates/defenders. Preserve both the all-release interface
(with fallback) and common supported-cohort results.

## 3. Fixed development budget and stop before the outer pass

Development verification consists of exactly four expanding-game folds:
train first 1/2/3/4 development games and validate the next development game.
The candidates are fixed; these folds characterize stability, not select a winner
or tune parameters. Budget: **8 logistic fits** (C/D ×4 folds), plus analytic A/B.
No candidate can be changed after looking at these diagnostics without a new
protocol and approval before any outer prediction. Run and disclose all four development folds; none may be omitted to conceal
an unfavorable diagnostic.

The designated comparison is D minus C. A/B are mandatory baselines. D remains
the designated context model even if it loses; report a negative result rather
than selecting a final-test winner. No calibrated-model claim: **zero fitted
recalibrators** in this ten-game study.

## 4. Five-game automated forward schedule and exact budget

For each evaluation game in fixed order:

1. Build training rows/labels from all strictly earlier games only
2. Refit training-only preprocessing and C/D with unchanged forms and C=1;
   recompute A/B analytically
3. Load the next game's allowlisted context and quality masks without labels
4. Write its A/B/C/D probabilities, fallback flags, cohort membership and
   preprocessing/training-ID hashes; record file SHA-256 in the prediction log
5. Only after hash verification, admit that game's labels into the history
   available to the **next** game. Do not compute or display current loss,
   calibration, residuals or candidate comparisons

After all five files are saved, a distinct scoring pass may join outcomes.
Budget: **10 outer logistic fits** (C/D ×5), plus analytic A/B. No additional
regularization choices, threshold sweeps, optimization restarts or score-driven
fit retries. Numerical failures stop the affected procedure for diagnosis;
parser/fitting corrections retain the original manifest and label the corrected
rerun exploratory, rather than pretending the outer test was reset.

Event-derived location/bearing are already offense-normalized. The inferred
per-team/period raw rotation is QA metadata, not a predictor. Its use of later
same-period releases is retrospective; no online orientation claim is made.

## 5. Measurement sensitivities without extra fitting

Primary cohort: parser event-geometry-eligible rows, same rows for A/B/C/D.
All-release with A fallback is a mandatory coverage/interface sensitivity.

Apply the same frozen predictions to these prespecified nested evaluation masks:

- Both raw/event location and named-defender distance agree within 0.1 ft
- The distinct 1-ft consistency sensitivity
- The 0.1-ft mask with shooter and named defender both directly detected

There is no raw-derived new feature/model in this protocol, so these sensitivities
are **subgroup scoring of the same fitted procedure, not extra refits**. Report
per-game support and quality exclusions; no threshold is selected by outcomes.
Raw agreement is representation consistency, not independent physical accuracy;
the named defender may differ from the nearest raw opponent. Do not claim that
subset performance corrects source measurement error.

## 6. Reporting, uncertainty and claims

Primary: shot-weighted paired mean log loss D minus C in nats/release, on common
supported rows across all five evaluation games. Secondary: paired Brier.
Clip scores to [1e-6,1-1e-6] only for numerical evaluation. Independently recompute
scores from immutable predictions and targets. Show each evaluation game's
n/makes/fallback count and paired differences. Report equal-game-weighted
comparison and exactly five leave-one-evaluation-game-out aggregate differences,
without refitting or reselecting anything.

No p-values or headline bootstrap confidence intervals: five independent games
cannot justify reliable league-wide superiority. AUROC is secondary only when
both labels occur; do not silently average undefined game AUROCs. Reliability
bins fixed at [0,.2),[.2,.4),[.4,.6),[.6,.8),[.8,1]; show n/mean prediction/observed
rate, mark n<30 low support. These are diagnostics, not fitted recalibration.

Practical question: is D's mean log loss at least 0.005 nats/release lower than
C, with no Brier worsening and the same sign in at least four of five games?
Report this predeclared exploratory yardstick, absolute changes, coverage and
leave-one-game sensitivity without claiming it establishes a population effect.
Failure cannot select C as a newly validated winner or trigger a new model search.

The only permitted points interpretation is immediate field-goal points
`(2 or 3)*P(make)`, conditional on release. It excludes foul rewards/free throws,
rebounds, turnovers and continuation. No ranking of passing versus shooting,
player/defender skill, NBA transfer, joint mechanics or causal coaching effects.

## 7. Gates

Before any fit: independently review the proposed bearing-missing indicator,
all features/cohorts/fit budgets, record approval, freeze environment and code,
run parser/leakage/integrity tests and prepare the prediction-before-label log.
The current workbench remains `predictive_gate: closed`. Local-only summaries and
MIT notice do not authorize external publication; any release remains explicit,
source-specific, and separate from model review.


## Binary-target validity gate, review amendment before approval

At every authorized training, selection, calibration or sequential evaluation
label-read stage, every prespecified eligible case must have an explicit finite
binary target in {0,1}. A null, unknown, malformed or nonbinary target is an
execution/measurement stop for that stage. Save the affected source lineage locally,
report the count and seek contract review. Never silently discard those rows,
impute a miss, switch to a target-known subset or change a same-row comparison
denominator. This gate is tested with synthetic null/unknown targets before fitting;
checking future labels waits until their prescribed stage unlock.


### Score convention clarification before freeze

Binary Brier is `mean((p_raw_or_calibrated - y)^2)` using the saved un-clipped
probability for the named stream; it is not the sum over two classes. Clip to
[1e-6, 1-1e-6] for natural-log loss only. Any percentile interval uses NumPy
quantile `method="linear"`; resample sorted match IDs with `default_rng(20261011)`.
This clarification adds no fits, comparisons or outcome-dependent choices.
