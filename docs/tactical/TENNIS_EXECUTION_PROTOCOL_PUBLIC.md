# Tennis execution distribution protocol: NO-FIT DRAFT

Status: **not approved for numerical fitting**. This fixes a small candidate
comparison and group plan for the BYU practice experiment; no models, calibrators,
likelihood scores or target-versus-feature correlations have been computed. Source
QA and marginal target/error descriptions have been inspected. This is not a
human-blind or prospective study.

## Source, use and measurement limits

[BYU tennis serves](https://github.com/nsandholtz/byu_tennis_serves/tree/fd435d9158ad5671c819bee3c47a47d7161a42cb),
commit `fd435d9158ad5671c819bee3c47a47d7161a42cb`. Repository README and
[LICENSE](https://github.com/nsandholtz/byu_tennis_serves/blob/fd435d9158ad5671c819bee3c47a47d7161a42cb/LICENSE)
state MIT, copyright (c) 2026 Nate Sandholtz. Retain the complete license notice
when distributing covered material. Attribute Nathan Sandholtz, Ryan Hanson,
Ron Hager, Stephanie Kovalchik and Gilbert Fellingham. No supplied compiled binary,
posterior sample or simulated win surface is run or imported.

Eight NCAA Division I men's players used four stated targets each, across eight
collection sessions. Players can recur across sessions and share sessions. Raw
identifiers remain private; publish only approved aggregate results. The [primary
paper, Section 3 footnote 2](https://arxiv.org/html/2607.28500v2), reports BYU IRB
#2025-487 determined that the study fell outside the regulatory human-subjects-research
definition and was therefore outside IRB oversight. This is a determination, not an
IRB-approval claim. Participant ages and individual consent details remain unverified;
collegiate membership does not establish either. Review any additional requirements
before fitting or external dissemination. No individual coaching,
health, readiness, maturity or selection rankings.

Coordinates are real measured meters, not event-category proxies. Source frame:
origin at net/center-service-line intersection in the returner's half; x is depth
away from net and y is lateral, positive toward deuce. Marked target locations are
joined exactly by player and region, shared across both serve periods. Bounce water
marks were measured by tape distance and a digital angle finder then converted to
Cartesian coordinates; speeds are radar mph. Section 3 footnote 4 reports a nominal
radar accuracy specification of ±3% of the reading; this is not independently
validated per-attempt accuracy or a coordinate-error bound.

`serve_period` is a supplied experimental first/second period; `(session, player,
index)` repeats 21 times and is not a point-pair key. The extended key including
period and region is unique in the pinned snapshot. Retain every source row; do not
reconstruct a first-fault/second-serve chain. No point winner is observed. Professional
simulated reward surfaces are not labels for this cohort.

## Exact population and estimand

The source has **567 attempts**, 401 first-period and 166 second-period, and 32
marked targets. Exclude exactly **19 lets**, including five without bounce coordinates.
The fixed primary denominator is **548 recorded non-let attempts**: **437 observed
bounce pairs and 111 net-censored attempts**. Raw source has 451 observed bounce
pairs, including 14 lets. All 111 net-censored non-lets remain in the primary task.

Estimand: the joint observed-data distribution of net contact versus clearance and,
conditional on clearance, measured two-dimensional displacement from the exact
stated target, for a recorded non-let attempt by a held-out player in this collegiate
practice sample, conditional on assigned region and supplied serve period.

This is conditional on a retrospectively known non-let status. It is not an
all-attempt pre-serve forecast. No missing net bounce is treated as a zero, an out,
an unobserved ordinary Gaussian draw with invented coordinates, or a completed point.
No likelihood term for an unobserved net bounce will be evaluated.

Physical clocks: stated target/assigned condition precedes the attempt; radar speed
and bounce are post-impact measurements. Current radar speed, clear-net indicator,
bounce, error and current let flag are **not predictor inputs**. Let status defines
the conditional denominator only. Speed stays a descriptive QA variable: 23 speeds
are missing across all source attempts; observed speed extrema remain local-only.
No silent clipping is applied. No joint angles, racket pose, spin or response latency
are measured.

## Fixed groups and support

The adapter creates a private, deterministic leave-one-player-out plan: order player
keys by SHA-256 of `measured-mechanics-descriptive-v1|tennis|` plus the source key;
fold i withholds the entire ith player across **all** sessions, periods and regions.
The local ignored manifest stores group memberships; the aggregate report publishes
only its hash and number of groups. Freeze its bytes before any fit.

Eight outer folds, no inner tuning, no validation-selected forms and no fitted
recalibrator. Train on seven players and score the eighth, for each fold. Assigned
region and period cells, exact target, training support and session overlap are
recorded privately; any aggregate support display suppresses small identifiable
cells. This tests held-out players under some shared session conditions. It does
not establish later-session prediction. The 14 supported player/session cells and
64 player/period/region cells are finite empirical support, not 64 independent people.

All 548 rows enter both candidate procedures. Use target-relative error in meters
for observed bounces: e = (shot_x − target_x, shot_y − target_y). No mirroring,
standardization, target-center replacement, learned clusters, feature search,
handedness effect or held-out-player random effect. Give training attempts equal
weight; state this differs from the equal-player primary evaluation weighting.

## Two fixed low-complexity procedures

Each is an explicit **observed-data hurdle model**, not a latent reconstruction of
where a net serve would have bounced. A Bernoulli branch models net contact. A
bivariate Gaussian describes target-relative error **conditional on an observed
clearance bounce**. Gaussian shape is a bounded working model, not a proven serve
mechanism. The test can return a negative result.

### B0: pooled reference

In the seven-player training set, let N be all non-let attempts and Nnet net hits.
Use `p_net = (Nnet + 1) / (N + 2)`, a fixed Beta(1,1) smoothing convention.
From the n observed training bounces compute the 2-D mean mu and raw second moment
Q = mean(e e-transpose). Set covariance Sigma = Q − mu mu-transpose + 0.0025 I.
The mean predicted bounce is that attempt's known stated target plus mu.

### B1: period-by-region shrinkage candidate

Use the same training-only pooled quantities above. Eight fixed cells are the two
supplied periods crossed with the four source regions. No player effect is fitted.
For a cell with Nc attempts and Nnet,c net hits:

`p_net,c = (Nnet,c + 20 * p_net,pool) / (Nc + 20)`.

For its nc observed bounces, let Sc = sum(e) and Tc = sum(e e-transpose). Use
`mu_c = (Sc + 20 * mu_pool) / (nc + 20)` and
`Q_c = (Tc + 20 * Q_pool) / (nc + 20)`;
`Sigma_c = Q_c − mu_c mu_c-transpose + 0.0025 I`.

A cell with no training attempts or bounces falls back algebraically to the pooled
branch quantities. Report such support failures. The 0.0025 m² diagonal addition is
a fixed numerical regularizer (0.05 m squared), **not** a claimed sensor error. Means
and covariance use raw moments with n denominators, not an unspecified sample
covariance library default. Use float64, stable Cholesky-based log densities, and
fail on nonfinite or nonpositive-definite results rather than clip losses.

**Finite candidate grid:** exactly two model forms, B0 and B1, with singleton
constants smoothing=1, shrinkage=20, diagonal addition=0.0025 m². Eight folds × two
models = **16 ordinary parameter fits**. No outer-selected shrinkage, covariance
floor, family, context feature, ellipse level, seed search, refits or nonlinear model.
No automatic retry budget is granted: an interrupted/failed numerical experiment
stops for review rather than silently restarting. No candidate winner is selected
from outer scores. B1 is the designated comparison;
failure is reported without replacing it with a newly chosen model.

If an outer training fold has fewer than 100 non-let attempts, 50 observed bounces
or three distinct training players with observed bounces, stop and keep the work
descriptive. These are predeclared numerical stability/support gates, not proof of
population adequacy. If any of the 548 primary rows changes eligibility, stop for a
new protocol review rather than drop inconvenient cases.

## Scores and a single primary comparison

Save all eight paired held-out-player prediction files before any performance
inspection. Use the mixed observed-data negative log likelihood (natural logs,
continuous density referenced to square meters):

- Net hit: `−log(p_net)`
- Observed clearance bounce e: `−log(1 − p_net) − log Normal2(e; mu, Sigma)`

The density can exceed one, so continuous NLL can be negative; no clipping or
conversion to an alleged point-win probability. Net cases contribute only their
branch mass. This scores all 548 non-lets while keeping censoring explicit.

Primary score is the unweighted mean of each player's average joint NLL; primary
contrast is B1 minus B0 on identical rows. Report absolute nats/attempt and the
paired contrast, with both the equal-player and attempt-weighted means. The proposed
practical reporting threshold is **0.02 nats per attempt** reduction, pending
pre-fit review; this is a project threshold, not established tennis utility.

Secondary diagnostics: net Brier score on all 548; conditional location NLL and
mean Euclidean error of predicted bounce location on the 437 observed bounces;
90% Gaussian ellipse coverage conditional on observed bounces, using the fixed
Mahalanobis-squared cutoff `−2 log(0.1) = 4.605170186`. Compare coverage with the stated
90% as a diagnostic, not a claim of established calibration. No uncertainty region
is attached to unobserved net coordinates. No accuracy statement about all attempts
may be made from bounce-only error.

## Uncertainty and reporting constraints

Privately retain the eight held-out-player paired losses, fixed pseudonymous
labels and support counts for numerical auditing only. These individual and
small-cell participant diagnostics, trial records and rankings remain local-only
and are not part of this public protocol or aggregate release. Public displays
contain no player-level results. The numerical comparison and uncertainty
specification below are unchanged.

Proposed uncertainty: 2,000 paired player-cluster bootstrap resamples, seed 20261011,
percentile 95% interval for the equal-player NLL contrast, from already saved
out-of-player losses. Use NumPy Generator(PCG64(20261011)) and draw an array of
shape (2000, 8) uniformly from player indices 0–7; percentile endpoints use linear
interpolation between sorted bootstrap contrasts. Show the eight paired differences
without ranking. Also report the range of contrasts when scoring excludes each
source session in turn, with predictions unchanged: average within remaining players,
then average equally over players with at least one remaining attempt, and disclose
that number. Do not select a method from this sensitivity.

Eight players are not enough for precise broad-population inference, players share
sessions, and outer training sets overlap. A player bootstrap does not remove shared
session dependence or capture training/selection/data biases. Session-exclusion
sensitivity is not an independent future-session validation experiment. No broad
calibration or professional transfer claim follows, even with a narrow conditional
interval. No recalibration of any form is permitted in this protocol.

## Gates and stopping rules

Before fitting: independently review source eligibility/copyright/participant-use
terms, exact measurement/error definitions, frozen memberships, full denominator and
net/let missingness checks, no point-pair invention, finite model formulas and metric
implementation; then obtain explicit approval. Unit-test formulas on synthetic data
only before any future source fit. Verify all source/code/contract hashes.

Stop and remain descriptive for unresolved measurement definitions, inadequate
support, malformed/missing targets, unmatched rows, nonfinite coordinates, violated
censoring, changed source bytes, changed population or unresolved required permission.
Do not silently substitute MCP directional labels, professional simulated rewards,
net zeros or current radar measurements. Before any release require independent
metric recomputation, saved prediction parity and separate privacy/rights approval
for each aggregate report, figure or fitted artifact. A draft protocol is not a fit
permission; the shipped adapter has no fitting/scoring interface.
