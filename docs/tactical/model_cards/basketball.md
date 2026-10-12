# ACB release geometry and defensive contest context

Status: the prespecified final evaluation is complete and independently numerically verified. Distribution remains subject to the source-specific notices and separate aggregate privacy/release review.

## Analyst question

Across five later sampled games, how do distance/clock and nearest-defender features change same-release predictive loss?

## Population and measurement

Ten SkillCorner Liga ACB games, 1,459 recorded releases. Includes fouled misses, so the denominator differs from official box-score field-goal attempts. This is a small ACB demonstration, not a general NBA model.

## Target and observation contract

Made shot conditional on a recorded field-goal release. No possession-level recommendation or prediction of an unchosen shot.

## Feature blocks

Distance and bearing to the source hoop at (−40.75, 0) feet, three-point flag, shot clock; D adds nearest-defender distance and a fixed interaction. Representation agreement/direct-detection quality defines prespecified comparison cohorts. Blocked/assisted/shot-quality annotations are excluded as features.

## Development and evaluation design

First five chronological games for development. Freeze preprocessing, candidate definitions and update schedule, then save the next game’s predictions before its labels update later training, for five prequential games. Eight development and ten sequential logistic fits. No fitted recalibrator or hyperparameter search.

## Comparison and uncertainty

References A/B, geometry C and defender D on identical cases. Report per-game and pooled log loss/Brier/reliability, fixed fallback coverage, and leave-one-game-out sensitivity. No headline confidence interval or significance claim from five games.

## Limits and prohibited interpretation

Tracking/event agreement is same-provider consistency, not independent physical accuracy. Some locations are estimated or absent. Five sequential test games are not one static untouched-model test. No causal contest effect, general NBA transfer, or complete biomechanics claim.

## Fixed final result

The primary 708-release event-geometry cohort across five sequential evaluation games gave C log loss 0.672584/Brier 0.239815 versus D 0.665462/0.236313. The −0.007122-nat pooled difference was favorable in only three of five games, so the predeclared consistency yardstick failed. No headline confidence interval or league-wide superiority is claimed. All 719 releases and stricter geometry-quality cohorts remain separately reported.

See [the complete benchmark](../BENCHMARK_RESULTS.md) for all prespecified streams and failures, including results that did not improve.

## Reproduction, attribution and use

The exact [protocol](../BASKETBALL_PROTOCOL_DRAFT.md), source hashes, training-only preprocessing, attempt journal and selection freeze define the experiment. [Source notice](../notices/../../research/notices/SKILLCORNER_BASKETBALL_MIT.txt) applies independently of software licensing. Use the local aggregate workbench for support-aware interpretation; it does not serve trained weights or live recommendations.

This is AI-assisted research software with independent AI-assisted review and automated tests. It is not externally certified or production-ready. All raw/row-level data, fitted tactical weights and private participant artifacts remain outside the controlled release.
