# Model card: tennis

## Target

ATP men's singles player A win conditional on a supported completed-match score; A is the lexicographically smaller player ID

## Intended use

Non-commercial educational, reproducible historical research and a learning portfolio. No automatic wagering, lineup decisions, scouting claims, financial commitments, or production SLA. Outcomes are estimated, never guaranteed.

## Data and evaluation

- Source: [dataset documentation](../sources/tennis.md)
- Modeled source events: 40,896
- Train: 32,214 events, 2010-01-03 through 2021-12-05
- Calibration: 2,826 events, 2022-01-03 through 2022-11-27
- Test: 5,856 events, 2023-01-02 through 2024-12-18
- Model: `{'family': 'hist_gradient_boosting', 'leaves': 15, 'l2': 10.0}`
- Temperature: 1.056378, fit only on the calibration partition
- Seed: 20261011
- Artifact ID: `81dc0660284b8bac`

Five prespecified candidates are compared using two chronological expanding-window folds within the training period. A classifier is fitted on the training period only, then temperature-calibrated on a later validation period. No training or calibration labels cross the corresponding availability cutoff. Test-time historical features roll forward as earlier results become available; parameters remain frozen.

## Held-out comparison

| Model | Accuracy | Log loss | Brier | Top-label ECE |
| --- | ---: | ---: | ---: | ---: |
| training_prior | 49.90% | 0.69358 | 0.25022 | 0.01478 |
| elo | 63.70% | 0.63110 | 0.22081 | 0.02749 |
| elo_calibrated | 63.70% | 0.62891 | 0.22004 | 0.01247 |
| selected_uncalibrated | 65.22% | 0.61524 | 0.21395 | 0.02216 |
| selected_calibrated | 65.22% | 0.61447 | 0.21366 | 0.01489 |

## Availability and leakage controls

All outcome-derived features require result availability strictly before the predicted event date. Same-day results are batched. Current-match scores only create the target; IDs, dates and current-match statistics are excluded from the estimator feature matrix. Tennis pre-tournament ranks are explicitly mapped to outcome-independent A/B sides. Scaling is fitted within each training fold. A mutation test verifies changing a match result cannot change that match's or earlier features.

## Limitations

Men's main-tour singles only. Actual match dates are unavailable, so tournament-start dates plus a conservative 21-day result delay are used. Evaluation conditions on realized matchups; later-round opponents need not be known at tournament start, so this is not a bracket forecast. Within-tournament updates use deterministic event-ID order, not verified chronology, so Elo and last-ten features are approximations. No within-tournament form or injury features. Retirements, walkovers, defaults and unsupported/inconsistent scores are excluded; probabilities are conditional on completing a supported match.

Retrospective source corrections and uncertain provider publication delays remain. No calibrated individual confidence interval is provided; aggregate bootstrap intervals are approximate performance uncertainty only. Historical performance can drift and does not establish future performance.

## Reproduction and operation

Run `python -m sportslab run --sport tennis` after installing pinned dependencies. See the root README for snapshot locks, inference, and security. [Complete metrics](../../reports/tennis/evaluation.json) include all candidates, split counts, class counts, per-year results, software versions and input hashes.

[Monitoring and deployment gaps](../deployment.md)

## Data-derived output rights

Tennis data and covered adaptations are CC BY-NC-SA 4.0, credited to Jeff Sackmann / Tennis Abstract and the preserved Kadantte snapshot. This project's MIT code license does not override non-commercial or share-alike requirements. No raw data or trained weights are distributed in Git.
