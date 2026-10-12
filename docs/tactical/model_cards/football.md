# NFL retrospectively charted at-snap tendencies

Status: the prespecified final evaluation is complete and independently numerically verified. Distribution remains subject to the source-specific notices and separate aggregate privacy/release review.

## Analyst question

Do formation/personnel and motion/box/hash blocks add information about realized dropback beyond ordinary game context?

## Population and measurement

Eligible competitive regular-season run/pass plays with validated nflverse/FTN joins. Physical setup is retrospectively charted at the snap and annual source publication follows games.

## Target and observation contract

Realized dropback, including sacks and scrambles. This is not the original offensive play-call intent.

## Feature blocks

A: down, distance, field position, clocks, score and timeouts. B adds normalized formation/personnel. C adds motion, box/backfield counts and starting hash. Pressure, rushers, routes, time to throw and other post-snap results are excluded.

## Development and evaluation design

2023 training: 33,836 plays/272 games. 2024 weeks 1–9 selection: 16,824/138; weeks 10–18 calibration: 16,511/134. Frozen 2025 evaluation: 32,813/272. Prespecified logistic/gradient-boosting grids, six refits and seven calibrations: 46 optimizer operations plus four count builds. Train-only transforms.

## Comparison and uncertainty

Primary calibrated logistic C minus A on identical cases. Report all prespecified raw/calibrated blocks and tree comparisons, log loss/Brier, reliability, game-cluster uncertainty and week-cluster sensitivity. Reliability bin edges use the exact serialized floating-point convention described in RELIABILITY_BIN_CONVENTIONS.md.

## Limits and prohibited interpretation

An at-snap physical state is not necessarily available before offense chose the play or in a live feed. Provider changes and retrospective charting limit transport. No blocking assignments, full player geometry, leverage, original intention or verified readiness. Repeated-team dependence is not fully resolved by game clustering.

## Fixed final result

On 32,813 2025 plays across 272 games, calibrated logistic A had log loss 0.573844/Brier 0.195338; C had 0.522502/0.173469. Paired log-loss difference −0.051342 nats, 95% game-cluster interval [−0.057899, −0.044665]. The fixed game/week-sensitivity yardstick was met. Most of the logistic change appeared in the formation/personnel block B (loss 0.523804), with a smaller further C change. The predeclared calibrated full tree loss was 0.486625; it remains a secondary comparison rather than a newly selected test winner.

See [the complete benchmark](../BENCHMARK_RESULTS.md) for all prespecified streams and failures, including results that did not improve.

## Reproduction, attribution and use

The exact [protocol](../FOOTBALL_PROTOCOL_DRAFT.md), source hashes, training-only preprocessing, attempt journal and selection freeze define the experiment. [Source notice](../notices/NFLVERSE_FTN_NOTICE.md) applies independently of software licensing. Use the local aggregate workbench for support-aware interpretation; it does not serve trained weights or live recommendations.

This is AI-assisted research software with independent AI-assisted review and automated tests. It is not externally certified or production-ready. All raw/row-level data, fitted tactical weights and private participant artifacts remain outside the controlled release.
