# Baseball numerical protocol: review draft

**Status: proposed, not approved or executed.** No predictive fit, score, model
selection, recalibration or test evaluation may start until independent review
and the project owner's explicit approval. This document does not open that gate.
The completed stage-one module remains descriptive. Its observed context
fractions are not fitted or calibrated predictions.

## 1. Estimand and useful claim

Among MLB regular-season Retrosheet delivered pitches that have valid
reconstructed prefix context and an identifiable conventional swing/take label,
estimate the conditional probability of a swing before the next delivered
pitch; separately estimate bat-ball contact conditional on an eligible swing.
The horizon is one delivery and the unit is one pitch. The sample is retrospective
and conditional on the current realized pitch category, not a prospectively known
all-delivery population. There are no measured physical pitch types, locations,
velocities, bat stances or joint angles.

The practical question is whether the already observed within-PA outcome
sequence adds useful anticipation beyond count and game context. This is not a
test that choosing a particular pitch or swing causes a better baseball outcome.
It cannot rank unthrown pitches or recommend a causal strategy.

The source is the six pinned 2023–2025 official EV/parsed-play archives. Retrosheet
notice and hashes must accompany any permitted output. Raw, row derivatives,
player-level predictions and weights remain local unless separately cleared.
These releases are retrospective; the split below is event-date chronological,
not proof that the historical annotation was available live.

## 2. Cohort and target taxonomy

Use exactly `baseball.py`'s validated current-pitch eligibility, with its source
and parser hashes frozen in the approved contract. Swing takes values 0 for B/C
and 1 for F/S/T/X. Contact conditional on swing is 0 for S and 1 for F/T/X. A foul
tip is bat-ball contact. X is excluded when the current event identifies a bunt
or interference. L/M/O, P/Q/R/Y, H, I, K/U and any interference-marked current
delivery are outside the conventional targets. A/V/N and pickoff/modifier
characters are not deliveries. Empty strings generate no invented label.

Retain earlier eligible pitches in PAs that later contain a bunt, pitchout or
interference. Unknown U makes its later PA count uncertain; do not backfill from
the terminal count. Impossible/source-conflicting counts and exceptional
three-ball walk PAs are explicitly excluded without clipping. Retain the known
SEA202503280/pn42 source anomaly as an identifiable QA exclusion. This creates a
quality-controlled conditional cohort, not every pitch in MLB.

Exclude delivered prefixes whose exact date is ambiguous at a suspension
boundary. Preserve their recorded ordering/counts and original/resume interval;
do not equate the first resumed source row's date with every newly materialized
pitch's physical date. This excludes 10 development-2023 deliveries and three
2024 deliveries under the conservative parser rule, with no 2025 cases. The
final eligible swing denominators are 713,338 / 704,671 / 705,223 and the
swing-conditioned contact denominators are 338,840 / 337,665 / 336,314 across
2023 / 2024 / 2025. Later-year values are eligibility QA, not performance.

Each model and ablation must use the same target-specific row IDs. No favorable
target- or context-dependent resampling, oversampling or class balancing. A
game-ending incomplete PA retains its observed eligible pitches and never gets
an invented next-pitch target. PA and game identity stay intact across splits.

## 3. Frozen chronology and fold membership

Use each game's conservative full date span: the union of parsed source-record
dates validated against raw suspension/resumption boundaries and every retained
delivery date interval, including excluded ambiguous deliveries. A parsed date
is a record/completion date; it does not independently establish every pitch's
physical date inside an interrupted cumulative string. Do not substitute gid's
date or split a suspended game between folds.

| Partition | Exact rule | Source-game count before pitch eligibility |
|---|---|---:|
| Initial development fit | All 2023 regular-season games | 2,430 |
| Selection | 2024 games with maximum event date ≤ 2024-06-30 | 1,261 |
| Calibration | 2024 games with minimum event date ≥ 2024-07-01 | 1,167 |
| Boundary exclusion | 2024 games spanning both intervals | 1 |
| Final evaluation | All 2025 regular-season games | 2,430 |

The boundary exclusion is BOS202406260, recorded on June 26 and resumed August
26. These membership counts were obtained from dates only, not predictive
scores. Save a hashed game/PA/pitch membership manifest before any fit.

Choose candidates using selection only. After selection, refit each designated
finalist on 2023 plus the selection games; fit no preprocessing or classifier on
calibration games. Fit the predeclared recalibrator on calibration alone. Keep
all 2025 predictions sealed until every designated model has completed them.
Source labels and QA were inspected, so describe 2025 as performance-blind after
source QA, never human-blind or prospective.

There is no adaptive refit during 2025, no test-based model swap and no moving
the boundary after seeing performance. A missing source or protocol failure
requires a documented new version before unlocking the test, not a quiet retry
with different choices.

## 4. Exact predictors and histories

Context logistic predictors are categorical encodings of:

- Count as one of the 12 valid balls–strikes pairs
- Batter/pitcher hand pair LL/LR/RL/RR and hand-method flag
- Outs 0/1/2 and the eight base-occupancy combinations
- Batting side 0/1 and inning band 1–3, 4–6, 7–9, 10+
- Batting score difference bands ≤−5, −4, −3, −2, −1, 0, 1, 2, 3, 4, ≥5

The sequence version uses exactly that context plus:

- Delivered-pitch index in this PA, banded 1, 2, 3, 4, 5, 6, 7+
- The immediately previous delivered outcome category
- Separate two-pitches-back and three-pitches-back categories; pad with START

Use individual lag fields, not a post-selected cross-product of the entire
suffix. Prior administrative A/V affect reconstructed count but are not delivery
lags. Mid-PA substitutions retain the already observed prefix while the active
actor/hand changes. Pitch strings, current symbols, terminal event, post-state,
next player, final scores, current/season-complete player outcomes, dates and
parsed responsibility actors are prohibited predictors.

Player IDs, gid and PA ID are for audit/grouping only in this first contract.
No player random effects or player-history rates are fitted. Thus unseen players
use exactly the same context model with no cold-start identity parameter. This
limits player-specific scouting claims but avoids an undeclared history cutoff.
All lags are reconstructed before the current delivery; no future suffix enters.

One-hot encode the listed categorical fields with `handle_unknown='ignore'`,
`drop=None`, no minimum-frequency merging and float64 sparse output. Fit the
encoder on the applicable fit partition only. Missing/unknown hand is not filled
from a future row: follow the parser's eligibility policy. Report unseen encoded
categories explicitly. No scaling, imputation, feature selection, interaction
search, target encoding or synthetic data.

## 5. Fixed candidates and selection budget

Run the following nine candidates separately for each target:

1. Constant rate: beta(1,1) smoothed training successes/opportunities
2. Context table: count × hand pair, pseudo-count strength 100 toward the
   training constant; unseen cell returns that constant
3. History table: count × hand pair × previous delivered category, strength 100
   toward its candidate-2 parent; unseen history cell returns its parent
4–6. Context logistic regression with C ∈ {0.03, 0.3, 3.0}
7–9. Context-plus-sequence logistic regression with the same three C values

All logistic fits use L2 penalty, `solver='lbfgs'`, intercept, `class_weight=None`,
`max_iter=1000`, `tol=1e-8`, float64 and no warm starts. Thread limit is 2.
Optimizer nonconvergence is a failed candidate; do not add iterations or try a
new solver after examining its score. Randomized operations use seed 20261011.

The entire selection budget is 18 fits/estimators: nine per target. The three
tables/constants have no tunable parameter. Select C separately for context and
sequence by lowest uncalibrated mean selection log loss. Differences ≤1e-6 nats
are ties, resolved by the smaller C. No AUC, accuracy, subgroup or contact result
breaks a swing tie. If a whole logistic block fails, its predeclared fallback is
the context table and the comparison is flagged unavailable, not redefined.

Designate five final procedures per target before test access: constant, context
table, history table, selected context logistic and selected sequence logistic.
Refit those ten procedures once on the refit partition. No neural model, boosted
tree, external decision engine, extra candidate or feature family is part of
this first numerical budget. Adding one requires a new reviewed contract before
any test evaluation, not justification by a disappointing test result.

## 6. Fixed calibration

For each of the ten designated procedures, fit one logistic intercept/slope
recalibrator on the disjoint calibration games. For raw probability p, set
z=logit(clip(p, 1e−6, 1−1e−6)), q=sigmoid(a*z+b), and minimize mean Bernoulli
negative log likelihood plus 1e−4*((a−1)^2+b^2). Use deterministic L-BFGS-B,
start (a,b)=(1,0), bounds a∈[0,10], b∈[−10,10], maxiter=200, ftol=1e−12.

Probability clipping is solely numerical stabilization; it is never count
clipping. Save parameters, convergence and boundary status. A failed or
boundary-hitting recalibrator does not trigger an alternative method: show raw
results, flag calibrated comparison unavailable and withhold a calibrated
improvement claim. No isotonic search or recalibrator selection on test.

## 7. Main comparison, uncertainty and reporting

The one primary comparison is calibrated sequence logistic minus calibrated
context logistic swing log loss on identical eligible 2025 rows. Report the
absolute nats-per-pitch difference. A useful-improvement claim requires a point
reduction of at least 0.001 nats/pitch and a paired 95% game-bootstrap interval
entirely below zero. This threshold is a proposed practical screen, not proof
of baseball utility or causal value. Freeze it before fitting.

Use 2,000 paired bootstrap samples of whole games, with replacement, seed
20261011. Sort the target's eligible evaluation-game IDs lexicographically and
initialize `numpy.random.default_rng(20261011)` once. In each draw, sample
exactly that list's length uniformly with replacement; share the selected game
indices across the paired procedures. Each draw recomputes pitch-weighted
aggregate losses from game-level
loss sums and denominator counts. The interval is the percentile interval at
quantiles 0.025 and 0.975, calculated with `numpy.quantile(method='linear')`.
Do not bootstrap individual pitches, refit
inside these intervals or claim that they include model-selection/data-bias
uncertainty. Report raw and calibrated log loss and Brier score for all ten
designated procedures, along with fixed 10 equal-width reliability bins and
their denominators. AUROC and accuracy at 0.5 are secondary diagnostics.
Accuracy predicts class 1 when p≥0.5. Reliability bins are left-closed and
right-open, except the final bin includes 1; no equal-frequency rebinning.

For every selection and evaluation log-loss calculation, clip only the
probability to [1e−12, 1−1e−12], use natural logarithms, and average
−[y*log(p)+(1−y)*log(1−p)] over eligible observations. Its units are nats per
eligible delivered pitch, or nats per eligible swing for the contact task.
Binary Brier is mean((p−y)^2), using the original probability; it is dimensionless
and is not the sum of two class-wise errors. Bootstrap differences use exactly
these conventions. Label the metric definition, units and target denominator
in every result file. The distinct [1e−6, 1−1e−6] calibration-input logit clip
in §6 is a fixed transform, not the evaluation-metric clip.

Contact-given-swing, history-table comparisons and count/hand/inning/base/score
slices are secondary/exploratory; no additional superiority declaration from the
best slice. Report all predeclared results, including failure. A negative result
does not select a different test-set winner or authorize a new grid. Show
unseen-category rates and subgroup support. Model display abstains below 200
training opportunities or 20 distinct training games for its displayed context;
always show denominator and uncertainty limitations. This abstention affects
display only: it must not silently improve the all-eligible benchmark cohort.

## 8. Resources, acceptance and release

Resource cap: 2 CPU threads, 8 GiB memory and 6 wall-clock hours for the complete
selection/refit/calibration pass. No GPU or remote compute purchase. On a cap or
memory failure, preserve diagnostics and pause; do not reduce samples or change
the grid by looking at results. Bootstrap may use an additional 30 minutes on
the same two threads using per-game loss summaries. Record wall time, CPU time,
peak resident memory, package versions and seed.

Before fitting: independent approval of this exact contract, source/parser and
fold hashes, all parser tests, a stratified raw/reference inspection checklist,
and future-suffix feature-invariance checks. Parser agreement is same-provider
representation consistency, not independently validated physical measurement.

Freeze the reference-check sample as follows, using 2023 only: one eligible
delivery from each supported count × hand-pair cell (at most 48), plus ten full
PAs per stratum for two-strike fouls, bunt strike three, retained NP, omitted NP,
runner interruption, mid-PA pitcher change, pinch hitter, suspended-date change,
automatic count change and extra-inning runner placement. Select the smallest
SHA-256 values of `20261011|gid|pa|delivery_index` within each stratum; take all
when fewer than ten exist, union overlaps, and add every explicitly excluded
2023 count/adjudication PA. Save membership before reviewing model error. Inspect
the raw record window and official parsed reference together for count, active
actors/hands, bases/outs/runs, date and terminal label. Require zero unexplained
disagreements; a failure blocks fitting until the parser and the entire sample
are rechecked. This is a representation/reference check, not a claim that a
second independent observer validated physical bat contact.

Before any numerical release: frozen predictions, independently recomputed
metrics/denominators, inference parity, clean pinned-data reproduction, protected
baseline hash check, source-specific publication review and clear conditional-
association limitations. Do not publish raw/row-level source data or apply the
code license to it. A failed or purely descriptive result remains a valid
portfolio artifact. No part of this draft changes the closed predictive gate.

The information used here was obtained free of charge from and is copyrighted by
Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".
