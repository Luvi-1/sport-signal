# Model card: baseball

## Target

MLB designated-home win conditional on a completed, non-tied result

## Intended use

Non-commercial educational, reproducible historical research and a learning portfolio. No automatic wagering, lineup decisions, scouting claims, financial commitments, or production SLA. Outcomes are estimated, never guaranteed.

## Data and evaluation

- Source: [dataset documentation](../sources/baseball.md)
- Modeled source events: 22,762
- Train: 15,473 events, 2015-04-05 through 2021-10-03
- Calibration: 2,430 events, 2022-04-07 through 2022-10-05
- Test: 4,859 events, 2023-03-30 through 2024-09-30
- Model: `{'family': 'logistic', 'C': 10.0}`
- Temperature: 0.964345, fit only on the calibration partition
- Seed: 20261011
- Artifact ID: `ec70850bddd61581`

Five prespecified candidates are compared using two chronological expanding-window folds within the training period. A classifier is fitted on the training period only, then temperature-calibrated on a later validation period. No training or calibration labels cross the corresponding availability cutoff. Test-time historical features roll forward as earlier results become available; parameters remain frozen.

## Held-out comparison

| Model | Accuracy | Log loss | Brier | Top-label ECE |
| --- | ---: | ---: | ---: | ---: |
| training_prior | 52.13% | 0.69267 | 0.24976 | 0.01460 |
| elo | 54.78% | 0.69637 | 0.25092 | 0.06868 |
| elo_calibrated | 54.78% | 0.68404 | 0.24552 | 0.01931 |
| selected_uncalibrated | 54.83% | 0.68340 | 0.24520 | 0.01860 |
| selected_calibrated | 54.83% | 0.68357 | 0.24528 | 0.02079 |

## Availability and leakage controls

All outcome-derived features require result availability strictly before the predicted event date. Same-day results are batched. Current-match scores only create the target; IDs, dates and current-match statistics are excluded from the estimator feature matrix. Tennis pre-tournament ranks are explicitly mapped to outcome-independent A/B sides. Scaling is fitted within each training fold. A mutation test verifies changing a match result cannot change that match's or earlier features.

## Limitations

No starting-pitcher, lineup, bullpen, park, travel, or weather features. Designated home does not verify venue neutrality. Suspended-game results are delayed until completion; same-day doubleheaders do not share results.

Retrospective source corrections and uncertain provider publication delays remain. No calibrated individual confidence interval is provided; aggregate bootstrap intervals are approximate performance uncertainty only. Historical performance can drift and does not establish future performance.

## Reproduction and operation

Run `python -m sportslab run --sport baseball` after installing pinned dependencies. See the root README for snapshot locks, inference, and security. [Complete metrics](../../reports/baseball/evaluation.json) include all candidates, split counts, class counts, per-year results, software versions and input hashes.

[Monitoring and deployment gaps](../deployment.md)
