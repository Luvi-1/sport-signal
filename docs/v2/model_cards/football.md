# V2 model card: Football

## Intended use and target

NFL regular-season winner, conditional on a completed non-tied game.

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

- logistic_C0.1: 0.292561
- boost_leaves7: 0.235319
- random_forest_depth6: 0.224253
- extra_trees_depthNone: 0.247867

Ensemble calibration temperature: 0.937804.

Training: 2010-09-09 to 2024-01-07
(3,619 events). Calibration: 2024-09-05
to 2025-01-05 (272 events).

## Measured new-period results

Test: 2025-09-04 to 2026-01-04
(271 events).

- Accuracy: 63.84%
- Calibrated log loss: 0.631009; uncalibrated: 0.630532
- Brier: 0.221376
- Ten-bin top-label ECE: 0.048021
- Ensemble minus refitted V1 log loss: -0.010691
- Approximate paired weekly-bootstrap 95% interval: [-0.0231, +0.0033]

Binary Brier uses positive-class squared error; soccer uses summed classwise
squared error. Calibration is assessed with reliability curves and bin counts,
not inferred from Brier alone. Aggregate intervals do not describe one match.
All candidates and negative results remain in the complete comparison.

## Material limitations

No quarterback availability, injuries, depth charts, weather or play-by-play strength. Small annual sample and season changes make uncertainty substantial. Ties are outside the modeled target.

Corrected historical snapshots are not guaranteed as-issued live inputs. Earlier
test outcomes update history only after their availability cutoff; classifiers
remain frozen. Performance under unseen future seasons, rule changes, missing
feeds and new participants requires prospective validation. Subgroup stability,
operational monitoring and service-level reliability are not established.

## Provenance and rights

Selection manifest SHA-256: `874b2c8cba33d672ca56f020b0df032b848f4672bd960f133920a613ec1880ea`.
The public development report records code, source/data, model and runtime hashes.
Only trust locally generated joblib files. Provider rights remain separate from
the original MIT code; tennis-derived artifacts are conservatively CC BY-NC-SA 4.0.

[All comparisons and reliability](../../../reports/v2/RESULTS.md) ·
[Protocol](../PROTOCOL.md) · [Inference and reproduction](../REPRODUCE.md) ·
[Data rights](../../../DATA_LICENSES.md)
