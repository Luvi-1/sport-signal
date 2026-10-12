# MLB pitch-outcome sequence tendencies

Status: the prespecified final evaluation is complete and independently numerically verified. Distribution remains subject to the source-specific notices and separate aggregate privacy/release review.

## Analyst question

Does the recent observed pitch-outcome sequence improve swing and conditional-contact prediction beyond game/count context?

## Population and measurement

Retrosheet MLB regular seasons 2023–2025, 7,289 games. Hybrid raw-event/parsed-play reconstruction handles cumulative prefixes, substitutions and suspended-game ambiguity. These are pitch-outcome symbols, not measured pitch types or trajectories.

## Target and observation contract

Separate binary targets: swing among eligible delivered pitches; contact among eligible swings. The second is conditional on a selected action and cannot be pooled with the first.

## Feature blocks

Count, handedness, outs, occupied bases, batting side, inning and score bands, delivery band and three preceding observed pitch-outcome codes. No actor IDs, current pitch outcome, future pitches, pitch location or inferred stance.

## Development and evaluation design

2023 training; chronological first portion of 2024 for selection (1,261 games), remaining portion for calibration (1,167), with one suspension crossing the boundary excluded; 2025 evaluation (2,430 games). C in {0.03, 0.3, 3}; constant/context/history tables and context/sequence logistic models. 38 operations: 26 optimizer fits and 12 analytic builds, fixed fallback on declared failure.

## Comparison and uncertainty

Primary: calibrated sequence-minus-context logistic swing log loss; practical project threshold −0.001 nats and upper paired game-cluster interval below zero. Conditional-contact and history-table contrasts are secondary. Report binary Brier, LL clipped at 1e−12, reliability and 2,000 game-cluster bootstrap draws.

## Limits and prohibited interpretation

Source reference adjudication verifies representation, not physical ground truth. Pitch selection, location, speed, opponent intent and swing mechanics are unmeasured. Association does not identify effects of a different pitch or stance. The separate lab companion studies measured angles in a different population.

## Recorded numerical execution

Both sequence-logistic C=3 selection candidates reached the fixed 1,000-iteration limit and were recorded as failed. They were not retried with a different solver or a larger budget. The other 16 selection procedures completed, followed by all ten designated refits and all ten calibrations, within the 38-operation budget. The process recorded about 25.9 minutes wall time and 2,166,558,720 bytes peak resident memory. These execution facts do not establish final predictive improvement.

## Fixed final result

On 705,223 eligible 2025 delivered pitches across 2,430 games, calibrated context and sequence logistic swing log losses were 0.658826 and 0.658472. Difference −0.000354 nats, 95% game-cluster interval [−0.000411, −0.000293], below the fixed 0.001-nat practical threshold. Brier changed from 0.233468 to 0.233300. The secondary contact-given-swing comparison used 336,314 swings and had difference −0.001106 nats; it cannot replace the primary swing conclusion.

See [the complete benchmark](../BENCHMARK_RESULTS.md) for all prespecified streams and failures, including results that did not improve.

## Reproduction, attribution and use

The exact [protocol](../BASEBALL_PROTOCOL_DRAFT.md), source hashes, training-only preprocessing, attempt journal and selection freeze define the experiment. [Source notice](../notices/RETROSHEET_NOTICE.txt) applies independently of software licensing. Use the local aggregate workbench for support-aware interpretation; it does not serve trained weights or live recommendations.

This is AI-assisted research software with independent AI-assisted review and automated tests. It is not externally certified or production-ready. All raw/row-level data, fitted tactical weights and private participant artifacts remain outside the controlled release.
