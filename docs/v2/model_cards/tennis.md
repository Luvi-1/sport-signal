# V2 model card: Tennis

## Intended use and target

ATP men's singles winner, conditional on a supported completed score; retirements, walkovers, defaults and unsupported scores are excluded.

Historical research and hypothetical matchup comparison. The output is an estimated
outcome distribution, not a guarantee or a deployed live decision service. Side A
is designated home in team sports; tennis sides are canonicalized by stable IDs
independently of outcome. Input factors are descriptive, not causal explanations.

## Frozen architecture

50 finite, explicitly whitelisted pre-event features.
Selected base configurations use three earlier chronological folds. Nonnegative
ensemble weights use out-of-fold predictions; separate later-period temperature
calibration uses no new-test outcomes. The ensemble was the main model before
scoring, regardless of which individual row subsequently ranks first.

- logistic_C10.0: 0.267478
- boost_leaves15: 0.238594
- random_forest_depth6: 0.232282
- extra_trees_depth10: 0.261646

Ensemble calibration temperature: 1.025400.

Training: 2010-01-03 to 2023-11-27
(37,927 events). Calibration: 2024-01-01
to 2024-11-24 (2,955 events).

## Measured new-period results

Test: 2025-01-06 to 2025-12-17
(2,728 events).

- Accuracy: 65.47%
- Calibrated log loss: 0.611858; uncalibrated: 0.612192
- Brier: 0.212576
- Ten-bin top-label ECE: 0.018407
- Ensemble minus refitted V1 log loss: -0.004130
- Approximate paired weekly-bootstrap 95% interval: [-0.0071, -0.0012]

Binary Brier uses positive-class squared error; soccer uses summed classwise
squared error. Calibration is assessed with reliability curves and bin counts,
not inferred from Brier alone. Aggregate intervals do not describe one match.
All candidates and negative results remain in the complete comparison.

## Material limitations

Dates are tournament-start proxies. Features are frozen from strictly earlier results delayed by 21 days, conditional on realized matchups whose later-round opponents were not known at tournament start. This is not an actual all-fixtures tournament-start forecast. No injury or verified match-time information; historical last-ten features use a documented deterministic ordering approximation.

Corrected historical snapshots are not guaranteed as-issued live inputs. Earlier
test outcomes update history only after their availability cutoff; classifiers
remain frozen. Performance under unseen future seasons, rule changes, missing
feeds and new participants requires prospective validation. Subgroup stability,
operational monitoring and service-level reliability are not established.

## Provenance and rights

Selection manifest SHA-256: `33e22536a5866f6cf03d42f335c87243d49a1a3977508e8f38fa62d1424680cd`.
The public development report records code, source/data, model and runtime hashes.
Only trust locally generated joblib files. Provider rights remain separate from
the original MIT code; tennis-derived artifacts are conservatively CC BY-NC-SA 4.0.

[All comparisons and reliability](../../../reports/v2/RESULTS.md) ·
[Protocol](../PROTOCOL.md) · [Inference and reproduction](../REPRODUCE.md) ·
[Data rights](../../../DATA_LICENSES.md)
