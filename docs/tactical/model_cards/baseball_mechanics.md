# Adult laboratory body-angle and contact association

Status: the prespecified final evaluation is complete and independently numerically verified. Distribution remains subject to the source-specific notices and separate aggregate privacy/release review.

## Analyst question

Do a fixed body-only foot-plant angle block and incoming machine-pitch context improve held-out-athlete exit-velocity estimation?

## Population and measurement

OpenBiomechanics adult paired cohort: 571 trials from 82 athletes, predominantly collegiate, one session per athlete. Machine pitching at roughly 65 mph from 40 feet. It is separate from MLB event prediction.

## Target and observation contract

Recorded exit velocity in mph. Marker and independent sensor bat speeds remain separately named measurements, not interchangeable targets or hidden predictors.

## Feature blocks

Incoming-pitch speed (mph), descent angle (degrees), and horizontal/vertical zone offsets (inches); add lead-knee, rear-hip and rear-elbow flexion plus torso-relative-to-pelvis axial angle at foot plant (degrees). Preserve each source convention; the torso field's x suffix does not define its physical rotation axis. Exclude target-sharing velocity components, duplicate aliases, outcome-bearing filenames and contact/outcome-derived features. Offline-filtered signals support execution-conditioned association.

## Development and evaluation design

Fixed five outer athlete folds and four inner athlete folds, equal-athlete weighting, ridge alpha .1/1/10/100, 170 ridge fits plus five mean references, no retries. Exact constant training columns are excluded. Save all outer predictions before scoring. One session per athlete precludes future-session validation.

## Comparison and uncertainty

Compare body+context ridge with context ridge and mean reference. Primary equal-athlete MAE; report RMSE definitions explicitly, trial-weighted sensitivity and athlete-cluster uncertainty. A 0.5 mph improvement threshold with upper interval below zero is a project reporting threshold, not biological importance.

## Limits and prohibited interpretation

Small laboratory population, task/sensor differences, selected paired cohort and session/athlete confounding. No causal stance prescription, professional-game transfer, health, injury, readiness or individual-selection claim. Adult-only exclusion changes the population deliberately. Public reports omit identities, pseudolabels, individual fold/athlete profiles and trial predictions.

## Fixed final result

Equal-athlete MAE was 5.925761 mph for context ridge and 6.125848 mph for body+context ridge: difference +0.200087 mph, 95% participant-cluster interval [−0.039580, 0.457915]. The mean reference was lower still at 5.845214 mph. The fixed angle block did not demonstrate useful held-out-athlete improvement in this cohort. This does not establish that biomechanics is irrelevant or identify a harmful angle.

See [the complete benchmark](../BENCHMARK_RESULTS.md) for all prespecified streams and failures, including results that did not improve.

## Reproduction, attribution and use

The exact [protocol](../BASEBALL_MECHANICS_PROTOCOL_DRAFT.md), source hashes, training-only preprocessing, attempt journal and selection freeze define the experiment. [Source notice](../notices/MECHANICS_ATTRIBUTION.md) applies independently of software licensing. Use the local aggregate workbench for support-aware interpretation; it does not serve trained weights or live recommendations.

This is AI-assisted research software with independent AI-assisted review and automated tests. It is not externally certified or production-ready. All raw/row-level data, fitted tactical weights and private participant artifacts remain outside the controlled release.
