# V2 model card: Baseball

## Intended use and target

MLB regular-season winner, conditional on a completed non-tied game.

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

- logistic_C0.1: 0.275500
- boost_leaves7: 0.245794
- random_forest_depth6: 0.241923
- extra_trees_depth10: 0.236783

Ensemble calibration temperature: 1.046856.

Training: 2015-04-05 to 2023-10-01
(20,333 events). Calibration: 2024-03-20
to 2024-09-30 (2,429 events).

## Measured new-period results

Test: 2025-03-18 to 2025-09-28
(2,430 events).

- Accuracy: 56.21%
- Calibrated log loss: 0.680308; uncalibrated: 0.680363
- Brier: 0.243707
- Ten-bin top-label ECE: 0.004877
- Ensemble minus refitted V1 log loss: +0.000880
- Approximate paired weekly-bootstrap 95% interval: [-0.0022, +0.0042]

Binary Brier uses positive-class squared error; soccer uses summed classwise
squared error. Calibration is assessed with reliability curves and bin counts,
not inferred from Brier alone. Aggregate intervals do not describe one match.
All candidates and negative results remain in the complete comparison.

## Material limitations

No confirmed starting pitchers, batting lineups, injuries, weather or park features. Suspended results are delayed to completion. Oakland/Athletics historical franchise continuity is documented in the source audit.

Corrected historical snapshots are not guaranteed as-issued live inputs. Earlier
test outcomes update history only after their availability cutoff; classifiers
remain frozen. Performance under unseen future seasons, rule changes, missing
feeds and new participants requires prospective validation. Subgroup stability,
operational monitoring and service-level reliability are not established.

## Provenance and rights

Selection manifest SHA-256: `b8612ae1b31299eaabdff02470b537c274e32e476e324262096b948a852e8db5`.
The public development report records code, source/data, model and runtime hashes.
Only trust locally generated joblib files. Provider rights remain separate from
the original MIT code; tennis-derived artifacts are conservatively CC BY-NC-SA 4.0.

[All comparisons and reliability](../../../reports/v2/RESULTS.md) ·
[Protocol](../PROTOCOL.md) · [Inference and reproduction](../REPRODUCE.md) ·
[Data rights](../../../DATA_LICENSES.md)
