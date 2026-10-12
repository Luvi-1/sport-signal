# Baseball measured-mechanics protocol: NO-FIT DRAFT

Status: **not approved for numerical fitting**. This fixes a proposed population,
measurement allowlist, deterministic group memberships and finite comparison
budget before any fit. Descriptive source QA has already inspected outcomes, so
this is not a human-blind or prospective experiment. Independent method review
and explicit experiment approval must precede implementation or execution.

## Source, rights and population

- Source: [OpenBiomechanics](https://github.com/drivelineresearch/openbiomechanics/tree/44b98dae05cceb016f080ab39d105c85b8639084), commit `44b98dae05cceb016f080ab39d105c85b8639084`
- Data and biomechanics documentation: [CC BY-NC-SA 4.0 with additional affiliation exclusion](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md); software MIT is a separate license. Credit OpenBiomechanics Project, Driveline Baseball Research & Development. Local independent noncommercial eligibility was confirmed; this is not approval for commercial use or a publication license review
- Source reports consent, de-identification and Western IRB/WCG WB-DLR-115. Use aggregate reports only, without re-identification, individual physiology/health interpretation or recruitment/selection ranking
- Prespecified primary cohort: **571 adult swings from 82 athletes**, each with age at least 18, recorded exit velocity and paired HitTrax incoming-pitch context. The four proposed body fields and four context fields are complete in all 571 rows
- Flow: 677 swings/98 athletes; exclude 34 under-18 swings/5 athletes; retain 643 adult swings/93 adults; exclude 5 missing exit-velocity records to obtain 638/92; 67 of those lack paired context; primary 571/82
- The 638-row exit-velocity cohort is **not** a silently substituted primary or a second trial selected by score. No minor-inclusive sensitivity fit is authorized by this draft
- Hitting uses a machine near 65 mph, about 40 ft away. There is one session per athlete. The predominantly collegiate population is not representative of live MLB pitching

## Exact estimand and clocks

For an adult athlete represented by the recorded machine-hitting protocol, assess
whether four source-processed foot-plant body angles improve the **association
between recorded exit velocity and measured incoming-pitch context** on held-out
athletes, among recorded swings with the paired measurements available.

Unit: a recorded swing. Outcome: `exit_velo_mph_x`, mph, ball speed after contact.
Population/denominator: exactly the 571 paired adult records. Observation stage:
retrospective, execution-conditioned foot-plant kinematics and pitch context.
Horizon: the same recorded swing's ball exit after contact. Missing contact/context
is not recoded as a miss. It is not an all-pitch, contact-probability, pre-pitch,
causal stance-intervention or future-session forecast.

Physical foot plant precedes contact, but source filtering/event extraction uses
processed trials and online latency is unverified. A foot-plant association does
not become a causally available early-event forecast. Session and athlete effects
cannot be separated. Grouped testing addresses new-athlete transport in this
laboratory sample; it does not establish future-session/season or professional
transfer.

## Frozen feature allowlist

The pinned [hitting dictionary](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/baseball_hitting/README.md)
provides the following processed POI definitions. Angles are degrees; no trigonometric
expansion, learned feature search, extra extrema or automatically discovered aliases.

| Source field | Physical quantity and event | Convention |
|---|---|---|
| `lead_knee_launchpos_x` | Lead knee flexion at foot plant | Joint x; positive flexion, extension decreasing |
| `rear_hip_launchpos_x` | Rear hip flexion at foot plant | Joint x; flexion positive, extension negative |
| `rear_elbow_launchpos_x` | Rear elbow flexion at foot plant | Joint x; flexion positive, extension negative |
| `torso_pelvis_launchpos_x` | Torso relative to pelvis axial angle at foot plant | Dictionary explicitly identifies physical z despite x suffix; positive torso toward mound/pelvis toward catcher |

The relative axial POI is identical to another provided representation; retain only
the listed canonical field. This is schema/source-definition verification, not
independent anatomical/sensor validation. The generic source processed conventions
and each listed POI's event are documented; a reviewer must confirm the interpretation
is sufficient for this bounded association before the predictive gate opens. Unknown
computation details cannot be filled in from a suggestive name.

Context-only features, four linear terms:

| Source field | Definition | Unit |
|---|---|---|
| `pitch` | Incoming machine-pitch speed | mph |
| `pitch_angle` | Provider's recorded descent angle; do not invent an undocumented sign interpretation | degrees |
| `horizontal_distance` | Offset from zone center, positive inside to right-handed hitter | inches |
| `vertical_distance` | Offset from zone center, positive above center | inches |

Use each source convention once; do not mirror body POIs or pitch offsets again by
hitter side. No handedness, age, body size, playing level, athlete/session identity,
bat specifications or arbitrary source text enters either model. The age value is
eligibility-only. Foot plant uses 100% bodyweight lead-force threshold; foot contact
uses 10% and is distinct. Marker sampling is 360 Hz with 20 Hz filtering; force
sampling is 1080 Hz with 40 Hz filtering. The small CSVs do not provide verified
elapsed event times. None are invented as a timing feature.

Exclude current/duplicated exit velocity, all bat speeds and bat-derived velocity
components/aliases, contact attack angle, launch/carry/spray, predicted ball-in-play
result, unverified impact coordinates, outcome-bearing filenames and target-derived
statistics. Marker-derived and Blast speed remain separate descriptive outcomes;
there is no target shopping between them. No contact-outcome fields are candidate
features. Feature construction uses an explicit allowlist, never a blacklist plus
all remaining numeric fields.

## Fixed rows, splits and preprocessing

`python -m experiments.tactical.mechanics --sport baseball` validates pinned bytes,
produces only descriptions, and freezes a private split plan under ignored storage.
The public aggregate summary records that plan's SHA-256, not its memberships.

1. Hash each source group with SHA-256 of `measured-mechanics-descriptive-v1|baseball|` plus the source athlete key; sort the digests, assign consecutive groups round-robin to outer folds 0–4
2. Keep all swings of each athlete together. For each outer training set, order its group digests by SHA-256 of `inner-{outer_fold}|` plus the digest, then round-robin into four inner folds
3. Do not use outcomes, body values, levels or group sizes to alter this membership. Review exact memberships before fitting; changing the source/version/plan restarts review
4. Use identical 571 rows for every feature block and baseline. The reviewed rows have complete primary predictors; if that changes, **stop**, rather than introduce opportunistic imputation or vary denominators across models
5. Within each fit, give every training athlete equal total weight: row weight `N_train / (G_train * n_athlete_train)`. Fit weighted column means and population variances on that training fold only; transform validation/test using those values. A zero-variance training column is set to zero and excluded from penalization, with a count logged
6. Fit an unpenalized intercept. Standardize outcome neither globally nor within folds. No transform, normalizer or target statistic may be fitted on held-out athletes

The descriptors and grouping are generated now, but no model has been constructed
or evaluated. There is no final untouched lockbox in this proposal: the five outer
folds estimate a fixed nested procedure and must be described as such.

## Finite numerical budget, to execute only after approval

- Reference 0: athlete-weighted training mean exit velocity
- Primary reference: weighted ridge on the four pitch-context terms
- Primary candidate: the same weighted ridge on four pitch-context plus four body terms
- Ridge minimizes the sum of weighted squared errors plus alpha times the sum of squared standardized coefficients, with an unpenalized intercept; use float64 and scikit-learn Ridge with deterministic `solver="svd"`, not an iterative/convergence-selected solver
- Exact grid for each ridge block: alpha in `{0.1, 1, 10, 100}`; no other candidates, interactions or nonlinear methods in this first protocol
- Inner selection: smallest macro-athlete MAE over the four complete inner held-out folds; equal mean over athletes. A tie within `1e-12` mph picks the larger alpha. Each feature block selects independently using only its outer training athletes
- Refit that selected block once on all outer training athletes, then save predictions for that outer test fold before inspecting its scores
- Maximum budget: 5 outer folds × (2 blocks × 4 alphas × 4 inner fits + 2 outer refits) = **170 ridge fits**, plus five training-mean references. No seed searches, repeated outer reshuffles, trial fitting, feature substitutions or extra target fits
- No automatic retry budget is granted: an interrupted/failed numerical experiment stops for review rather than silently restarting
- Designated reporting candidate stays the augmented ridge procedure. If the locked comparison fails, report failure and withhold improvement claims; do not select a new winner/fallback using outer test scores

## Primary comparison and uncertainty

Primary outcome: the equal-athlete mean of per-athlete MAE in mph, based on saved
outer-fold predictions. Primary contrast: augmented minus context-only macro-athlete
MAE on identical rows. Report absolute values and differences. Secondary summaries:
mean of each athlete's RMSE, row-weighted MAE/RMSE, each outer fold's aggregate contrast and
the reference-mean results. Define the former exactly as
`macro_RMSE = (1/G) * sum_g sqrt((1/n_g) * sum_{i in g} (y_i - prediction_i)^2)`.
Thus square-root within each athlete first, then average the G athlete RMSEs equally;
it is not the square root of the mean athlete MSE. This definition is fixed before
any fit or score inspection. No athlete rankings or individual case plots.

Proposed practical reporting threshold, requiring approval before fitting: an
absolute reduction of at least **0.5 mph** in macro-athlete MAE, with the paired
bootstrap 95% upper limit below zero. This is a project reporting threshold, not a
validated biological improvement, coaching prescription or guarantee of useful
professional transfer. Publish a negative result as such. No level/side subgroup
searching or post-hoc threshold relaxation.

Uncertainty: 2,000 paired resamples of whole held-out athletes, random seed 20261011,
using already saved out-of-fold losses; percentile 2.5/97.5% interval of the primary
contrast. Use NumPy Generator(PCG64(20261011)) and draw a (2000, 82) array uniformly
from the 82 athlete indices; percentile endpoints use linear interpolation between
sorted bootstrap contrasts. Also disclose all five outer-fold contrasts. Resampling these predictions
conditions on this fitted nested procedure and overlapping training sets; it does
not capture full training/selection uncertainty, sensor bias or population bias.
It must not be described as a causal effect interval.

**No calibration or prediction-interval fit** is part of this budget. MAE/RMSE do not
establish calibrated probabilistic predictions. No residual-scaled interval, separate
recalibrator or calibration claim may be added after seeing outer outcomes.

## Stop/open gates

Keep descriptive-only if any gate fails: source/pin/eligibility terms; consent and
aggregate-only publication controls; adult/cohort/join reproducibility; source-field
physical definition review; duplicate/alias exclusions; group split no-overlap;
complete primary covariates; data/code/contract hashes; independent numerical method
review and explicit approval. Before a future release also require fold-only
preprocessing and outcome-mutation tests, independent metric recomputation, saved
prediction parity and source-specific permission review for aggregates/figures/weights.

No current adapter exposes fitting, calibration, scoring, hyperparameter or model
loading options. A protocol file or private membership plan is not approval to fit.
