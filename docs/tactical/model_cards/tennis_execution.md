# Collegiate intended-target and serve-execution distribution

Status: the prespecified final evaluation is complete and independently numerically verified. Distribution remains subject to the source-specific notices and separate aggregate privacy/release review.

## Analyst question

How well do fixed pooled and partially pooled hurdle distributions describe held-out-player net/bounce execution around stated targets?

## Population and measurement

BYU experimental serving, eight NCAA men. 548 recorded non-let attempts: 437 measured bounces and 111 net-censored attempts; 19 lets excluded from the 567-attempt source. Ages unverified; aggregate-only safeguards apply.

## Target and observation contract

Observed-data probability of net versus a measured two-dimensional bounce conditional on a non-let recorded attempt. No invented net bounce, completed-point win target or inferred point-pair transition.

## Feature blocks

Stated target, serve period and region known for the attempt. Exclude current observed speed or outcome from predictors; no guessed intention. Coordinates are metres.

## Development and evaluation design

Eight leave-player-out folds, two fixed hurdle models per fold (16 fits), no hyperparameter selection or post-hoc calibration. B0 uses pooled counts/Gaussian moments; B1 uses fixed period/region partial pooling with strength 20 and fixed covariance regularization. Save all outer predictions before losses.

## Comparison and uncertainty

Proper observed-data joint negative log density, equal-player and attempt weighting; separate bounce-only spatial diagnostics on 437 bounces. Eight-player bootstrap uncertainty is exploratory. The 0.02-nat threshold is a prespecified project convention, not a sport-wide practical benchmark.

## Limits and prohibited interpretation

Only eight collegiate players; no temporal/new-session or professional transfer. Conditional non-let selection is disclosed. Net censoring contains no observed bounce coordinate. No individual/pseudonymous player scores, body/health profile, causal coaching or simulated win surface presented as measured ground truth.

## Fixed final result

Equal-player joint observed-data NLL was 2.629705 for pooled B0 and 2.445547 for partial-pooling B1: difference −0.184158, exploratory 95% player interval [−0.243560, −0.113282]. On 437 measured bounces, equal-player spatial error changed from 1.159488 m to 1.060489 m. The fixed reporting threshold was met within this eight-player practice sample. The uncertainty remains exploratory; there is no professional, temporal or causal transfer claim.

See [the complete benchmark](../BENCHMARK_RESULTS.md) for all prespecified streams and failures, including results that did not improve.

## Reproduction, attribution and use

The [public protocol](../TENNIS_EXECUTION_PROTOCOL_PUBLIC.md) preserves the numerical specification while removing individual source values. The original executed protocol, source hashes, training-only preprocessing, attempt journal and selection freeze remain in the private audit installation; release-copy provenance documents the presentation-only revision. [Source notice](../notices/MECHANICS_ATTRIBUTION.md) applies independently of software licensing. Use the local aggregate workbench for support-aware interpretation; it does not serve trained weights or live recommendations.

This is AI-assisted research software with independent AI-assisted review and automated tests. It is not externally certified or production-ready. All raw/row-level data, fitted tactical weights and private participant artifacts remain outside the controlled release.
