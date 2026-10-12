# Laboratory mechanics candidate and research design

Status: research specification only, updated after the permitted bounded source inspection. Eligibility was confirmed for independent noncommercial local research; five small official data CSVs and source documentation were inspected without fitting any model. See [OPENBIOMECHANICS_AUDIT.md](OPENBIOMECHANICS_AUDIT.md) for the pinned source, exact schema/outcome definitions, quality findings, duplicate exclusions and cohort recommendation. This is a distinct laboratory component, not a substitute for MLB game tracking.

## Why retain this alternative

The [official OpenBiomechanics datasheet](https://github.com/drivelineresearch/openbiomechanics/blob/main/DATASHEET.md) describes real body/segment signals and points of interest, with 677 swings from 98 athletes and 411 fastball trials from 100 athletes. A subset of hitting trials has paired HitTrax outcomes. The population is predominantly collegiate, with small other-level subsets. The [data license](https://github.com/drivelineresearch/openbiomechanics/blob/main/LICENSE-DATA.md) is separate from the code license and has additional use restrictions.

This could demonstrate actual measured angles and timing while keeping the professional-game scope honest. It cannot establish that a learned college laboratory relationship applies to an MLB hitter facing live pitching, or that a recommended stance change causes better game outcomes.

## Bounded scientific question

The actual summary schema confirms relevant body angles and outcomes. A candidate analysis is **how measured lower-body/trunk timing and geometry relate to bat speed in the recorded laboratory task**. Report the task condition, measurement events, repeated-trial structure and uncertainty. A secondary, separately selected cohort can examine measured bat/contact variables and paired exit velocity, with explicit accounting for unmatched/absent contact outcomes.

This is an execution-conditioned mechanics study. Full-swing points of interest occur after swing initiation and cannot be sold as a pre-pitch prediction. An early-event forecast would require truncating raw signals at a named event, causally detecting that event without future frames, and selecting only features available by then.

## Measurement gate before model fitting

The bounded audit has inspected the anonymized summary schema. Retain these checks before committing to a target or expanding to full signals:

- Athlete/trial/session identifiers and whether participants overlap across releases
- Recording condition: tee, machine or other task; instruction/effort; pitch/ball speed if applicable
- Marker/segment definitions, anatomical/global coordinate frames, handedness reflections, units, sampling frequency and filtering
- Event definitions such as foot contact, peak segment rotation and bat–ball impact
- Which angles/timing measures are directly recorded, model-estimated or derived
- Trial quality flags, missing markers, inconsistent event order and paired HitTrax join keys
- Outcome meaning and whether missing values indicate failed trials, no contact, missing equipment capture or filtering
- Competition level/age distribution for aggregate transport limits, without creating identifiable athlete profiles or clinical/selection recommendations

Do not infer undocumented labels from filenames, estimate nonexistent stance from handedness, or treat simulated/interpolated values as measured motion.

## Validation and baselines

With fewer than 100 hitting athletes, random swing splits can mostly test recognition of the same people. They do not demonstrate new-athlete generalization.

1. Prespecify an athlete-grouped outer evaluation, with all trials from each athlete together. The audit confirms exactly one session per athlete, so athlete/session effects cannot be separated and a future-session temporal test is unavailable
2. Choose hyperparameters inside athlete-grouped development folds, including scaling/imputation/feature selection. Use a nested protocol or a genuinely held-out athlete test partition; freeze it before outcome-based selection
3. Compare a training mean, a small regularized model using a few scientifically specified body/timing variables, and one modest nonlinear model. Keep the same inputs and rows across models
4. For a secondary contact-quality task, use an explicit mechanical baseline before adding body variables. Distinguish mediation through bat speed from association at fixed bat speed; do not “control for everything” indiscriminately
5. Report MAE/RMSE, calibration of any prediction intervals, athlete-cluster uncertainty, and error by competition level/task condition where sample support permits
6. A player-identity/random-intercept model can describe repeated measurements, but its held-out-athlete prediction must use the population fallback. Do not use the test athlete's outcomes to estimate their intercept
7. Do not import a biomechanical variable mathematically derived from the target into a supposed independent forecast. Record shared-sensor/definition coupling

The useful result may be a measured-mechanics explorer with uncertainty and a negative predictive finding. It need not be a high-performing model, an optimization engine or a clinical predictor.

## Why pitching torque is not the first public demonstration target

Joint torque is a model-derived biomechanical quantity with important clinical associations, but it is not ligament force or injury probability. A small laboratory surrogate model would require stronger measurement, population and external validation before supporting health decisions. A transparent hitting-kinematics analysis avoids turning an available joint-load column into an unsupported injury score. The broader pitching science remains documented in `baseball_biomechanics_review.md`.

## Inspection update

Hitting is a pitching-machine task around 65 mph from 40 ft, not tee or live MLB pitching. The source has 677 swings/98 athletes; 672 exit-velocity observations/97 athletes and a distinct 604-row HitTrax-context subset/87 athletes. The recommended adult-only primary cohort has 638 exit-velocity swings/92 athletes, or 571 paired-context swings/82 athletes. Marker bat-contact speed and Blast sensor speed differ meaningfully; velocity-component aliases can nearly reconstruct the marker target. Outcome-bearing C3D filenames must be scrubbed from candidate inputs and displayed logs. Exact units, timing, exclusion groups and consent/de-identification notes are in the audit. A recorded-exit-velocity target is an alternative to bat speed that must be chosen before fitting, with contact-selection and sensor caveats.
