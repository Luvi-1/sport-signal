# From a sports mechanism to a defensible model

Research-method design, 2026-10-11. This document records requirements for the
five-sport tactical extension. It is not a claim that the proposed analyses have
been implemented or that every important factor can be measured. Sport-specific
literature reviews and source audits determine the final targets and features.

## 1. Start with the question and the observation

Three useful questions require different evidence:

1. **Description:** What happened in the recorded sample, and in which contexts?
2. **Prediction:** Given information observable at a specified instant, how often
   does the subsequent outcome occur?
3. **Intervention:** What would change if the same athlete or team chose a
   different action?

A well-tested answer to the second question does not automatically answer the
third. Causal identification needs a sufficiently defined intervention, adequate
overlap of alternatives and justified control of confounding, among other
assumptions. The causal framework comes from [Hernán and Robins, *What If*](https://miguelhernan.org/whatifbook).
Our application of it is to require an explicit causal design before presenting
an angle, formation or shot-choice change as an improvement an athlete can expect.

For example, a defender being farther away may accompany a different shooter,
shot type, defensive scheme or possession stage. A model may use that association
to predict a recorded shot without identifying what would happen if only the
defender's position changed. Opponents also respond: a useful decision model
cannot assume that every other player remains fixed after a tactical change.

## 2. A feature needs two clocks and a measurement definition

Every proposed field should record both:

- **Physical event time:** when the state or action actually occurred
- **Information availability:** when a sensor, charting process or public feed
  made its value observable

A postgame annotation of a pre-snap formation can support retrospective research
about a pre-snap observable state. It does not demonstrate a live production feed.
Conversely, a variable in a row labelled with the snap time may describe something
that happened well after the snap. The row timestamp alone is insufficient.

Each feature specification should include source fields, units, coordinate frame,
physical meaning, timing, missing-value meaning, transformations and a quality
flag. Distinguish:

- **Measured or charted:** a recorded quantity with a known method and error
- **Provider-estimated:** tracking interpolation, extrapolation or an opaque score
- **Derived:** a transparent calculation from justified inputs
- **Unavailable:** an important quantity the current source cannot establish

These classes are not interchangeable. An inferred court bearing is not a racket
or bat angle; workload is not a fatigue diagnosis; a defensive-position snapshot
is not a complete trajectory. If a trajectory-derived speed is used, record the
sampling interval, missing frames, coordinate transforms and filtering window.
Filters that use future samples cannot enter a strictly pre-event feature.

## 3. Selection into the dataset is part of the target

Record what makes an event eligible before fitting anything. Important questions
include whether the source includes only successful actions, televised matches,
professional players, certain leagues, selected tournaments or visibly tracked
players. A large count of shots is not a large count of independent games or people.

An outcome-dependent inclusion rule changes the interpretation. A basketball
analysis restricted to official field-goal attempts, for example, must acknowledge
that foul treatment can depend on whether the shot was made. A model of recorded
shot releases has a different denominator. Neither by itself estimates the value
of choosing to shoot rather than passing or drawing a foul.

Quarantine rules must be based on provenance, parsing, timing or measurement
validity. Freeze them before inspecting model errors. Publish both the original
eligible count and exclusions by reason, game and period; a cleaner sample may
represent a narrower population. Missing tracking must not be filled with a
fictional unoccupied court or an assumed unpressured player.

## 4. Match the evaluation to the intended use

The split unit should reflect the proposed deployment. Randomly distributing
shots from the same game across train and test can answer a much easier question
than prediction on future games. Structured validation should be designed around
the dependence and extrapolation of interest, rather than adopted mechanically.
[Roberts et al. (2017)](https://doi.org/10.1111/ecog.02881) provides the general
structured-data rationale; the following choices are project design decisions.

- Use whole games or matches and chronological development/calibration/test
  partitions when reliable dates and enough coverage exist
- For player-specific claims, additionally examine support per player and, where
  feasible, a held-out-player sensitivity analysis. A future-game test with known
  players and an unseen-player test answer different questions
- For very small sources, report prespecified grouped exploratory validation,
  individual held-out-game scores and variation. Do not create the appearance of
  a large independent test by counting correlated shots as independent trials
- If all source outcomes were visible during quality research, say so. A later
  performance-blind protocol can improve discipline without undoing that exposure
- Freeze candidates, feature groups, exclusions, selection criteria and report
  slices before performance inspection. Any subsequent change is a new experiment

Repeatedly optimising a finite validation score can overfit the selection process
itself. [Cawley and Talbot (2010)](https://jmlr.org/papers/v11/cawley10a.html)
shows why an apparently rigorous comparison can still be selection-biased. This
motivates bounded candidate sets, nested selection when feasible and retaining
negative comparisons rather than repeatedly choosing new winners on the test.

## 5. Compare mechanisms as well as algorithms

A useful comparison should reveal which information contributes, not merely which
library has the best score. After the source contracts are complete, prespecify
feature-group comparisons such as context only, geometry, opponent context and
verified prior history. All compared models must use the same eligible rows.
Changing both rows and features confounds the interpretation of an improvement.

Include an appropriate constant/context baseline and an interpretable statistical
model before a more flexible challenger. A simple geometry model may be more
informative than another large generic classifier. Complexity should follow the
sample size, quality and question. Published performance on a different target,
league or prediction instant is background evidence, not a head-to-head result.

An ablation measures predictive contribution under the fitted procedure. It is not
the causal importance of a physical factor. Redundant correlated variables can
mask one another, and missing measurements can leave important mechanisms absent
even when the observed features predict well.

## 6. Probability quality, calibration and uncertainty

Use log loss and an explicitly defined Brier score for categorical probabilities.
Proper scoring rules reward the predictive distribution, rather than only its
most likely label; the foundation is [Gneiting and Raftery (2007)](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf).
Declare class order, clipping policy and whether binary Brier uses one class or
the sum over both classes. Accuracy can accompany these measures, but cannot
replace them or establish calibration.

Evaluate raw and calibrated probabilities. Fit calibration only in a designated
development partition or through an explicitly nested procedure. Temperature
scaling is a candidate, not a promise: [Guo et al. (2017)](https://proceedings.mlr.press/v70/guo17a.html)
tested it on image/document neural-network tasks, not these sports sources.

Show reliability plots with bin counts, mean predictions and observed frequencies.
Report the binning rule, sparse bins and uncertainty. Binned calibration estimates
trade resolution against statistical precision, as examined by
[Arrieta-Ibarra et al. (2022)](https://www.jmlr.org/beta/papers/v23/22-0658.html).
A low expected calibration error alone is not a reliability guarantee.

When comparing models, use paired event losses and account for game/match
clustering where support allows. With only a few independent games, even a
cluster-aware interval can be unstable; show the game-level results and avoid
precision claims based on thousands of resampled shots. The dependence and
few-cluster cautions are supported by [Cameron and Miller (2015)](https://escholarship.org/uc/item/1jq5d0pq).
Further repeated-player/team dependence may remain after clustering by game.
Model disagreement is not a confidence interval, and bootstrap intervals do not
cover unmeasured confounding, source-selection bias or measurement error.

### Continuous mechanics and spatial execution targets

Do not force every mechanics question into a win/loss classifier. Speed, location
and angle errors need their own units and targets. Report point error such as MAE
and RMSE against an appropriate development-only baseline. If predicting a full
distribution, use a prespecified continuous score, such as CRPS for a scalar or
an energy score for a spatial vector, alongside interval/region coverage and
sharpness. These scores are also discussed by
[Gneiting and Raftery (2007)](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf).
Keep sign conventions explicit: all repository loss tables should say which
direction is better.

Measurement agreement is a separate evaluation. A reconstructed joint angle
should be checked against an appropriate reference before its apparent precision
is used to support a performance model. An accurate speed estimate does not
validate a force or injury estimate derived from the same video.

Treat censored observations honestly. A serve that hits the net does not have an
observed ground-bounce coordinate beyond it. An analysis of measured bounces is
conditional on that measurement existing; a model for all attempts must represent
the censored or categorical branch rather than invent a landing location. The
same distinction applies to intended aim, executed placement and point success.
Separate analysis of each can be valuable without claiming to estimate the others.

## 7. Interpretation that respects the observed support

Begin with count-labelled descriptive views, comparable contexts and model error
slices. Avoid drawing smooth response curves through regions with no support.
Partial-dependence plots can create unrealistic combinations when predictors are
correlated. Accumulated local effects provide one alternative for summarising
model behaviour, described by [Apley and Zhu (2020)](https://doi.org/10.1111/rssb.12377).
Neither plot becomes causal merely by avoiding obvious extrapolation.

Any scenario view must state what changed, what was held fixed, the comparable
sample support, what the model omits and when it should decline to answer. For a
joint-angle or technique question that cannot be measured, show the evidence map
and required measurement, rather than an invented numerical recommendation.

## 8. Tests required before an event-level model is released

These are planned acceptance criteria, not assertions that tests already exist:

1. Changing current or future outcomes does not change earlier feature values,
   chosen configurations, fitted transforms or development-only calibration
2. Current-event terminal flags, final rally length, post-event score and provider
   target-derived quality scores cannot enter the feature allowlist
3. Duplicate IDs, conflicting records, coordinate-unit errors, reversed court
   orientation and malformed sequences fail closed or enter an explicit quarantine
4. A repeated event is not counted twice; substitutions and interrupted sequences
   update the correct participant and state
5. Whole-game partition membership and all prior-history cutoffs are verified
6. Probability label order, finite range, sum and calibration transformations are
   checked independently of the model implementation
7. Measurement flags survive through inference and the interface; missing or
   extrapolated observations do not silently become direct measurements
8. Raw restricted data, player-level derivatives and model artifacts are excluded
   from publication unless the exact source terms permit their release

## Reading scope

This is a targeted methodological reference map, not a systematic review. Primary
author/journal records and available original text were inspected for the specific
claims cited. The full causal textbook was not exhaustively reviewed; the causal
assumptions section was inspected through the indexed author-hosted text. Source
rights, sport mechanics and actual schema coverage are documented separately.

