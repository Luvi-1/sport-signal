# Model card: soccer

## Target

English Premier League home win / draw / away win at full time

## Intended use

Non-commercial educational, reproducible historical research and a learning portfolio. No automatic wagering, lineup decisions, scouting claims, financial commitments, or production SLA. Outcomes are estimated, never guaranteed.

## Data and evaluation

- Source: [dataset documentation](../sources/soccer.md)
- Modeled source events: 3,800
- Train: 2,660 events, 2015-08-08 through 2022-05-22
- Calibration: 380 events, 2022-08-05 through 2023-05-28
- Test: 760 events, 2023-08-11 through 2025-05-25
- Model: `{'family': 'logistic', 'C': 0.1}`
- Temperature: 1.122493, fit only on the calibration partition
- Seed: 20261011
- Artifact ID: `ef14ab366162c5cc`

Five prespecified candidates are compared using two chronological expanding-window folds within the training period. A classifier is fitted on the training period only, then temperature-calibrated on a later validation period. No training or calibration labels cross the corresponding availability cutoff. Test-time historical features roll forward as earlier results become available; parameters remain frozen.

## Held-out comparison

| Model | Accuracy | Log loss | Brier | Top-label ECE |
| --- | ---: | ---: | ---: | ---: |
| training_prior | 43.42% | 1.06715 | 0.64611 | 0.00815 |
| elo | 55.66% | 0.96903 | 0.57555 | 0.04373 |
| elo_calibrated | 55.66% | 0.96465 | 0.57255 | 0.02363 |
| selected_uncalibrated | 54.47% | 0.95714 | 0.56843 | 0.02958 |
| selected_calibrated | 54.47% | 0.95759 | 0.56849 | 0.03377 |

## Availability and leakage controls

All outcome-derived features require result availability strictly before the predicted event date. Same-day results are batched. Current-match scores only create the target; IDs, dates and current-match statistics are excluded from the estimator feature matrix. Tennis pre-tournament ranks are explicitly mapped to outcome-independent A/B sides. Scaling is fitted within each training fold. A mutation test verifies changing a match result cannot change that match's or earlier features.

## Limitations

One league only. No lineup, injury, fixture congestion, or player-level information. One upstream date bug was independently verified and corrected. Draw probability remains hard to estimate.

Retrospective source corrections and uncertain provider publication delays remain. No calibrated individual confidence interval is provided; aggregate bootstrap intervals are approximate performance uncertainty only. Historical performance can drift and does not establish future performance.

## Reproduction and operation

Run `python -m sportslab run --sport soccer` after installing pinned dependencies. See the root README for snapshot locks, inference, and security. [Complete metrics](../../reports/soccer/evaluation.json) include all candidates, split counts, class counts, per-year results, software versions and input hashes.

[Monitoring and deployment gaps](../deployment.md)
