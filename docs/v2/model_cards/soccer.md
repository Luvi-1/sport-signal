# V2 model card: Soccer

## Intended use and target

English Premier League: designated home win, draw or away win after full time.

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

- logistic_C0.1: 0.382349
- boost_leaves7: 0.065557
- random_forest_depth6: 0.227947
- extra_trees_depthNone: 0.250589
- dixon_coles: 0.073559

Ensemble calibration temperature: 1.139262.

Training: 2015-08-08 to 2024-05-19
(3,420 events). Calibration: 2024-08-16
to 2025-05-25 (380 events).

## Measured new-period results

Test: 2025-08-15 to 2026-05-24
(380 events).

- Accuracy: 47.63%
- Calibrated log loss: 1.026548; uncalibrated: 1.030172
- Brier: 0.616659
- Ten-bin top-label ECE: 0.040824
- Ensemble minus refitted V1 log loss: -0.004669
- Approximate paired weekly-bootstrap 95% interval: [-0.0145, +0.0037]

Binary Brier uses positive-class squared error; soccer uses summed classwise
squared error. Calibration is assessed with reliability curves and bin counts,
not inferred from Brier alone. Aggregate intervals do not describe one match.
All candidates and negative results remain in the complete comparison.

## Material limitations

Limited to EPL teams and schedules. Promoted teams can have sparse history. Draw probabilities and sparse reliability bins require particular care.

Corrected historical snapshots are not guaranteed as-issued live inputs. Earlier
test outcomes update history only after their availability cutoff; classifiers
remain frozen. Performance under unseen future seasons, rule changes, missing
feeds and new participants requires prospective validation. Subgroup stability,
operational monitoring and service-level reliability are not established.

## Provenance and rights

Selection manifest SHA-256: `85a88e022cd848b511b75c9ce4d3e238c88c0cbbb3dd35811a073d14644dfc4a`.
The public development report records code, source/data, model and runtime hashes.
Only trust locally generated joblib files. Provider rights remain separate from
the original MIT code; tennis-derived artifacts are conservatively CC BY-NC-SA 4.0.

[All comparisons and reliability](../../../reports/v2/RESULTS.md) ·
[Protocol](../PROTOCOL.md) · [Inference and reproduction](../REPRODUCE.md) ·
[Data rights](../../../DATA_LICENSES.md)
