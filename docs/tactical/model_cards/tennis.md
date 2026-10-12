# Professional charted serve-direction tendencies

Status: the prespecified final evaluation is complete and independently numerically verified. Distribution remains subject to the source-specific notices and separate aggregate privacy/release review.

## Analyst question

Can context and past charted tendencies improve first/second-serve direction probabilities in men’s and women’s corpora?

## Population and measurement

Volunteer Match Charting Project singles matches. Four separately evaluated cells: first/second serves × men’s/women’s corpora. Quarantine and prefix/score rules are fixed before fitting; raw point order is not assumed chronological.

## Target and observation contract

Charted serve-direction category for an eligible first or second serve. Categories are not measured landing coordinates, speeds, spin or numerical angles.

## Feature blocks

Validated pre-serve score/context and previous charted history under one explicit Date + 21-day availability embargo. The embargo is a conservative assumption, not verified completion/publication time. Exclude notes, current/future outcomes and after-serve information.

Model weights, preprocessing and calibration stay frozen during evaluation. The
prespecified day-start history state continues to admit older matches when their
assumed Date + 21-day availability has passed; it is not a static end-of-training
history snapshot. Same-day histories remain frozen, while current-match score
replay uses only earlier completed points and the already-observed first fault
for the second-serve task.

## Development and evaluation design

2010–2022 fitting, 2023 selection, 2024 calibration, fixed 2025 evaluation admitted by 2026-01-22. Availability applies at every fit boundary. Backoff B0, history B1, multinomial logistic L (C .1/1/10), and admitted fixed boosted-tree N (15/31 leaves); fixed resource probe and calibration. Four threads, 49 optimizer-reservation cap and 5,400 charged CPU seconds.

## Comparison and uncertainty

Family choice uses only 2023 selection with the fixed simplicity tie rule; calibration never reselects a family. The primary contrast is point-weighted log loss for the calibrated designated model minus calibrated B1. Report all available same-cell raw/calibrated procedures, match/server-macro sensitivities, reliability, 2,000 match-cluster draws and event-time sensitivity. Four primary cells use 98.75% intervals; a claim requires at least 0.005 nats reduction and an adjusted upper interval below zero.

## Limits and prohibited interpretation

Volunteer match selection, ambiguous/mistimed metadata, categorical annotations and missing execution measurements limit generalization. No direction intervention/causal claim or live availability guarantee. Reliability edges preserve the bound floating-point convention.

## Recorded interruption

An executor interruption left second-serve men’s L(C=0.1) without a result. Its attempt remains consumed and was not repeated or assigned an invented score. The completed first-serve cells remain unchanged. Independently reviewed recovery completed the remaining original candidates and calibration, with an explicit conservative CPU debit. The final development ledger contains 41 reserved slots: 31 succeeded, nine convergence warnings and one interrupted without a result. The men's second-serve logistic family is unavailable after the remaining candidates exhausted their declared convergence attempts. Other planned family streams remain available; no replacement comparator was added.

Budget-charged CPU was 4,889.386 seconds under the 5,400-second cap: 1,193.370 measured completed CPU seconds plus a 3,696.016-second conservative debit for the unobserved interruption interval. The debit is not measured runtime. Reduced candidate coverage and numerical failures are part of the result. See [recovery record](../TENNIS_RECOVERY.md).

The recovery-process peak RSS was 480,874,496 bytes. The maximum recorded completed-process peak before interruption was 1,012,756,480 bytes; the interrupted fit's actual peak is unknown. The smaller recovery value is not the whole study's peak-memory measurement.

## Fixed final result

Across 224,495 eligible 2025 serves, the four cells retained their development choices. First-serve B1 losses were 0.918142 (men) and 1.037946 (women); no improvement over the same designated reference is claimed. Men’s second-serve N improved over B1 from 1.031664 to 1.012053: difference −0.019611 nats, adjusted 98.75% match interval [−0.026122, −0.013424], meeting the fixed rule. Women’s second-serve N changed 0.998930 to 0.994443: difference −0.004486, interval [−0.009604, 0.000329], failing the rule. Full raw/calibrated methods and dependence sensitivities remain in the report; the unavailable men’s second-serve L family stays explicit.

See [the complete benchmark](../BENCHMARK_RESULTS.md) for all prespecified streams and failures, including results that did not improve.

## Reproduction, attribution and use

The exact [protocol](../TENNIS_PROTOCOL_DRAFT.md), source hashes, training-only preprocessing, attempt journal and selection freeze define the experiment. [Source notice](../notices/MCP_NOTICE.md) applies independently of software licensing. Use the local aggregate workbench for support-aware interpretation; it does not serve trained weights or live recommendations.

This is AI-assisted research software with independent AI-assisted review and automated tests. It is not externally certified or production-ready. All raw/row-level data, fitted tactical weights and private participant artifacts remain outside the controlled release.
