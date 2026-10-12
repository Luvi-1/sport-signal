# WSL shot geometry and recorded defensive context

Status: the prespecified final evaluation is complete and independently numerically verified. Distribution remains subject to the source-specific notices and separate aggregate privacy/release review.

## Analyst question

Among eligible recorded non-penalty shots, does recorded defensive geometry add predictive information beyond shot geometry on exactly the same cases?

## Population and measurement

FA Women’s Super League, 457 source matches. Native 120 × 80 event coordinates are standardized units, not metres. Recorded freeze frames are incomplete views, not full tracking.

## Target and observation contract

Goal conditional on a valid recorded non-penalty shot. This does not model whether a shot should have been taken or compare unchosen passes.

## Feature blocks

G: distance, goal opening, lateral geometry, broad body part and restart context. R: G plus selected recorded goalkeeper/opponent geometry. Exclude later ball endpoint, final shot result and post-shot events.

## Development and evaluation design

325 development matches (8,204 eligible shots), 60 calibration matches (1,651), and 72 later evaluation matches (1,855). Inner season-forward selection uses C in {0.1, 1, 10}; fixed references, geometry logistic models and defensive-context logistic models; 24 optimizer operations. Fit preprocessing only on its training partition. Three fixed regularized intercept/slope logit recalibrations use the held-out calibration period and declared identity fallbacks.

## Comparison and uncertainty

Primary: calibrated R minus calibrated G log loss on the fixed matched defensive-geometry cohort. Report full and matched denominators separately, Brier and reliability, and 2,000 match-cluster paired bootstrap draws. Missing defensive context is not silently dropped only for the better model.

## Limits and prohibited interpretation

Selective recording, absent defenders, coordinate standardization and shot-opportunity selection limit interpretation. Associations do not establish a causal effect of moving a defender or changing an angle. Injury/readiness, intention, complete player motion and joint mechanics are unavailable.

## Fixed final result

On 1,855 identical held-out shots across 72 matches, calibrated geometry G had log loss 0.323582 and Brier 0.093846; recorded-defense R had 0.309887 and 0.090047. The paired log-loss difference was −0.013695 nats/shot, with 95% match-cluster interval [−0.020777, −0.006477]. The fixed descriptive usefulness yardstick was met. This is an association within the represented WSL shots, not a causal defensive intervention.

See [the complete benchmark](../BENCHMARK_RESULTS.md) for all prespecified streams and failures, including results that did not improve.

## Reproduction, attribution and use

The exact [protocol](../SOCCER_PROTOCOL_DRAFT.md), source hashes, training-only preprocessing, attempt journal and selection freeze define the experiment. [Source notice](../notices/STATSBOMB_NOTICE.md) applies independently of software licensing. Use the local aggregate workbench for support-aware interpretation; it does not serve trained weights or live recommendations.

This is AI-assisted research software with independent AI-assisted review and automated tests. It is not externally certified or production-ready. All raw/row-level data, fitted tactical weights and private participant artifacts remain outside the controlled release.
