# Soccer numerical protocol draft: recorded WSL shot context

**DRAFT, NOT APPROVED. Fitting remains prohibited.** This specifies a proposed
numerical budget for independent review and parent approval. No model, prediction,
calibration fit, held-out score or test-driven change is produced by this document.
If approved, freeze these exact bytes, source/contract/parser hashes and environment
versions before the first numerical fit. A changed protocol needs a new review.

## 1. Estimand and data boundary

Estimate goal probability conditional on a recorded, valid non-penalty WSL shot
at its retrospectively annotated shot state. Every miss type is included.
Population/source pin, 120×80 native units, source rights and target separation are
exactly those in `soccer_parser.md` and the reviewed measurement contract. The
source has missing/interrupted coverage and a multi-year gap; neither men's
football nor current 2026 deployment is validated by this experiment.

Fixed outer partitions:

- Development: seasons 4,42,90; 325 games, 8,204 currently eligible shots
- Calibration: season 281, match date <2024-01-01; 60 games; labels still locked
- Final test: season 281, match date >=2024-01-01; 72 games; labels still locked

Whole matches are indivisible. No player/team effects, as-of histories, external
weather/injury data, provider xG, continuous tracking or mechanics are included.
No test outcome-by-context analysis is permitted before the frozen scoring pass.
Later aggregate outcomes were seen in earlier source QA, so this is not claimed
to be human-blind or prospective.

## 2. Cohorts and absent measurements

Full geometry cohort: parser-eligible shots with finite distance and goal angular
width. Bearing undefined exactly at goal centre is encoded as zero plus an
explicit missing-bearing indicator; this is mathematical imputation, not a
measured direction. All original eligibility/exclusions remain visible.

Matched defense cohort: full geometry plus exactly one valid recorded opposition
keeper, finite nearest-recorded-opponent distance, zero malformed player
coordinates/unknown team flags/unknown opponent roles, and defined recorded outfield shooting-triangle
count. This does not mean every defender was observed. Compare every matched
candidate on exactly the same rows at each split. No actual missing keeper is
placed on the goal line. Retain full-cohort baseline coverage and counts excluded
by each matched requirement.

The record-level invalid-coordinate/unknown-team rules are fixed without labels.
No goalkeeper or defender coordinate clipping beyond parser validation. If a
proven parser error requires new eligibility, retain the original run and amend
the protocol; do not silently retune a held-out cohort.

## 3. Fixed candidates and transformations

Seven reporting streams, with no additional model families:

1. Full A: Beta(1,1) global rate `(goals+1)/(n+2)`
2. Full B: fixed zone/body cells, shrunk with concentration 20 toward Full A
3. Full G: regularized logistic geometry/context model
4. Matched A: Beta(1,1), trained on matched rows only
5. Matched B: identical fixed cells, shrunk toward Matched A
6. Matched G: same geometry form, trained on matched rows only
7. Matched R: Matched G plus the four fixed recorded-defense terms below

B cells cross distance `[0,6),[6,12),[12,18),[18,24),[24,36),[36,infinity)` native
units; goal angular width `[0,.25),[.25,.5),[.5,1),[1,pi]` radians; body group
Head / Foot / Other-or-unknown. Left/right feet combine. The cell rate is
`(cell_goals + 20*global_rate)/(cell_n+20)`. An unseen cell equals the global rate.
These bins/priors never change by model score.

G numeric columns: log1p(distance_native), goal_angular_width_rad,
abs(goal_bearing_rad), bearing-missing indicator, abs(lateral_offset_native).
Categorical columns: fixed broad body group, shot_type, play_pattern. Missing
categorical values become the literal `Missing`; fit one-hot vocabulary on the
training block only, unknown future levels map to all-zero columns. No interactions
or feature pruning by significance. Standardize continuous columns using training
population mean/std; zero-variance columns use scale 1. Binary and one-hot columns
are not standardized. No class weighting, oversampling or sample weighting.

R adds keeper_depth_native, abs(keeper_lateral_offset_native),
log1p(nearest_recorded_opponent_native), and recorded_outfield_in_goal_triangle.
They use the same training-only standardization rule. The last is a count of
recorded occupants, not a count of all defenders. Do not add event player IDs,
recorded total-player counts, outcome annotations, shot endpoint, provider xG,
assists, later events, pressure labels, first-time/technique flags, or any new
feature after review.

All logistic fits: L2 penalty, unpenalized intercept, lbfgs, float64,
max_iter=2000, tol=1e-8, C in the exact set {0.1,1,10}. No spline, tree, neural,
ensembled or extra calibration family. A convergence warning/nonfinite result
stops that stream for diagnosis; no opportunistic solver/hyperparameter expansion.

## 4. Development-only selection and exact fit budget

Two expanding-season folds: train season 4, validate 42; then train 4+42,
validate 90. For each of Full G, Matched G and Matched R, evaluate all three C
values on that stream's eligible rows. Select C independently per stream by
shot-weighted pooled validation log loss across both folds. A difference <=1e-6
nats/shot is a tie; choose smaller C (stronger regularization). No alternative
selection metric, subgroup winner or final-test fallback selection.

Budget: **18 inner logistic fits** (3 streams ×3 C ×2 folds), then **3 final
logistic fits** on all development data using chosen C. Analytic A/B estimates
require no optimizer and have no tunable alternatives. No extra resampling,
repeated random seeds or model fitting is permitted by this budget. If any
training split has only one outcome class, use its smoothed A prediction for that
stream and disclose the prespecified degeneracy fallback.

## 5. Fixed calibration procedure

Keep base models trained only on the 325 development games. For each of the three
logistic streams, fit one intercept/slope recalibrator on its corresponding
60-game calibration cohort:

`p_cal = sigmoid(a + b*logit(clip(p_raw,1e-6,1-1e-6)))`

Minimize summed negative log likelihood plus `0.5*(a^2+(b-1)^2)`, with bounds
`a in [-10,10]`, `b in [0,5]`, starting at `(0,1)`. Use deterministic L-BFGS-B,
maxiter=2000, ftol=1e-10, gtol=1e-8. Fixed identity fallback `(0,1)` if there are
fewer than 100 calibration rows, fewer than 10 goals or fewer than 10 misses;
also use identity and clearly flag a numerical failure. No fallback is chosen by
held-out performance. Maximum **3 recalibration fits**, no tuning. A/B baselines
remain raw. No calibration labels enter base coefficients or feature selection.

The primary designated comparison is **calibrated Matched R versus calibrated
Matched G** on identical final-test shots. Raw matched predictions and the full
baseline streams are mandatory secondary reports, never substitute winners.
The designated model remains R even if it fails to improve; report that failure
and withhold improvement claims. Final test cannot select a different model.

## 6. Frozen prediction and scoring pass

Write/hash per-shot raw and calibrated test probabilities, cohort masks, chosen
C, preprocessing state and train/calibration ID hashes before joining test labels.
Persist a prediction manifest. Independent code recomputes metrics from immutable
predictions/labels. Scores clip probabilities only to [1e-6,1-1e-6].

Primary metric: paired log-loss difference R minus G, nats per shot (negative
favors R). Secondary: paired Brier difference. Also report games, shots, goals,
coverage, AUROC when both classes exist, average predicted probability and actual
conversion. Equal-game-weighted paired differences are a fixed sensitivity.

Uncertainty: 2,000 paired match-cluster bootstrap resamples, seed 20261011,
percentile 2.5/97.5% interval, fixed models (no refitting). This is conditional
sampling uncertainty, not model-selection/source-bias uncertainty. One primary
comparison only. No multiple-comparison significance narrative for subgroups.

Reliability bins are fixed [0,.05), [.05,.10), [.10,.20), [.20,.40), [.40,.60),
[.60,1]. Report every bin's n/predicted mean/observed rate; n<50 is explicitly
low support, with no smooth confidence promise. Exploratory descriptive slices
are body group and the fixed distance bins, reported with counts; no further
candidate changes, thresholds or model choice based on them.

Practical question: does recorded defense lower mean log loss by at least
0.005 nats/shot without worsening Brier, while preserving the stated coverage?
This is a prespecified descriptive usefulness yardstick, not a guaranteed domain
standard, an automatic deployment approval, or a hypothesis-test substitute.
Report absolute differences and coverage even when the threshold is not met.

## 7. Release and stopping conditions

Stop at parser/rights/protocol blockers, model nonconvergence, failed prediction
integrity, target leakage or unapproved source changes. No automated gate opens
fitting. Required next steps: independent protocol review, resolution of comments,
parent's explicit approval, then frozen implementation. Publication of raw rows,
derivatives, plots and any weights remains separately reviewed under StatsBomb's
custom terms with attribution and the original supplied logo. No causal coaching,
goalkeeper skill, shot-choice or body-mechanics claims follow from this task.


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
