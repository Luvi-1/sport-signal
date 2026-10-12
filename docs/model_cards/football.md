# Model card: football

## Target

NFL designated-home win conditional on a completed, non-tied regular-season result

## Intended use

Non-commercial educational, reproducible historical research and a learning portfolio. No automatic wagering, lineup decisions, scouting claims, financial commitments, or production SLA. Outcomes are estimated, never guaranteed.

## Data and evaluation

- Source: [dataset documentation](../sources/football.md)
- Modeled source events: 3,891
- Train: 3,078 events, 2010-09-09 through 2022-01-09
- Calibration: 269 events, 2022-09-08 through 2023-01-08
- Test: 544 events, 2023-09-07 through 2025-01-05
- Model: `{'family': 'logistic', 'C': 0.1}`
- Temperature: 1.122705, fit only on the calibration partition
- Seed: 20261011
- Artifact ID: `dc5389b213f9de9d`

Five prespecified candidates are compared using two chronological expanding-window folds within the training period. A classifier is fitted on the training period only, then temperature-calibrated on a later validation period. No training or calibration labels cross the corresponding availability cutoff. Test-time historical features roll forward as earlier results become available; parameters remain frozen.

## Held-out comparison

| Model | Accuracy | Log loss | Brier | Top-label ECE |
| --- | ---: | ---: | ---: | ---: |
| training_prior | 54.41% | 0.68958 | 0.24821 | 0.01270 |
| elo | 63.97% | 0.64868 | 0.22821 | 0.04575 |
| elo_calibrated | 63.97% | 0.65096 | 0.22947 | 0.05232 |
| selected_uncalibrated | 64.34% | 0.63953 | 0.22444 | 0.02852 |
| selected_calibrated | 64.34% | 0.63949 | 0.22443 | 0.02866 |

## Availability and leakage controls

All outcome-derived features require result availability strictly before the predicted event date. Same-day results are batched. Current-match scores only create the target; IDs, dates and current-match statistics are excluded from the estimator feature matrix. Tennis pre-tournament ranks are explicitly mapped to outcome-independent A/B sides. Scaling is fitted within each training fold. A mutation test verifies changing a match result cannot change that match's or earlier features.

## Limitations

Small holdout and only 32 franchises. Tied games excluded. No quarterbacks, injuries, coaching, weather, or roster features. The 16-to-17-game season change is a distribution shift.

Retrospective source corrections and uncertain provider publication delays remain. No calibrated individual confidence interval is provided; aggregate bootstrap intervals are approximate performance uncertainty only. Historical performance can drift and does not establish future performance.

## Reproduction and operation

Run `python -m sportslab run --sport football` after installing pinned dependencies. See the root README for snapshot locks, inference, and security. [Complete metrics](../../reports/football/evaluation.json) include all candidates, split counts, class counts, per-year results, software versions and input hashes.

[Monitoring and deployment gaps](../deployment.md)
