# Reproduce the expanded benchmark

Run from an editable checkout with pinned core dependencies installed. No GPU,
paid API, account-gated weights or Laya installation is needed for V2.

```bash
python -m pip install -e .
bash scripts/reproduce_v2.sh
```

This deliberately preserves existing V2 reports and local model artifacts under
a timestamped local archive before fitting again. The prior source manifest is
preserved too, because regenerated V1 run metadata changes its guard hashes.
Cached source bytes and staged data still face the same immutable hash checks. It then:

1. Reproduces V1 and validates its original source locks; NFL uses the bundled,
   odds-free CC-BY 4.0 normalized input with distinct source/representation hashes
2. Stages the additional frozen seasons and documented source-schema/identity fixes
3. Fits development candidates using only purged pre-holdout history
4. Freezes all four selected configurations, stacking weights, calibrators and hashes
5. Explicitly unlocks the same published new-period cohorts for reproduction
6. Generates every comparison and checks metrics against preserved published values

This is reproduction of an already published experiment, not a new unseen test.
Running newly chosen ideas against these now-known outcomes is exploratory;
reserve a fresh period for any new improvement claim. Platform arithmetic can
produce very small differences; the checker allows 1e-6 and otherwise stops.

## Inspect the stages separately

```bash
python scripts/stage_v2_data.py --frozen-nfl
python -m experiments.v2.run develop --sport all
# Review all four selection manifests and the global freeze first
python -m experiments.v2.run evaluate --sport all --unlock-new-holdout
python scripts/summarize_v2.py
```

These commands refuse to silently overwrite existing selection/evaluation files.
Use the top-level reproduction script to preserve previous outputs before reruns.
`--original-nfl` is a separate strict source-byte mode and requires the original
cached provider download; it never silently falls back to changed upstream bytes.

## Analyze a hypothetical matchup

```bash
python scripts/analyze_matchup.py --sport football --side-a KC --side-b BUF --date 2026-02-01
python scripts/analyze_matchup.py --sport tennis --side-a 104745 --side-b 104925 --date 2026-02-01 --surface Hard --rank-a 200 --rank-b 7
```

These are hypothetical input examples, not assertions of actual fixtures or
correct historical rankings. Use verified pre-event rankings for a real analysis.
The output provides estimated probabilities, historical rating/form differences,
base-model disagreement and warnings. Disagreement is not a statistical confidence
interval, and input differences are not causal explanations or betting advice.

The fast entrypoint updates historical state once and computes only the requested
row. Tests verify equivalence to the full sequential feature builder, including
same-day and delayed-availability cases. Its source hashes are returned alongside
the frozen model-selection hash. The guarded fast entrypoint stays locked until all four published evaluations
exist and verifies both model and historical-input hashes. The original
`experiments.v2.predict` module is retained only as a full-history reference for
tests; it predates this entrypoint gate and must not be used before the new-holdout
seal is released. Prefer the guarded script for normal use.

Only load joblib artifacts produced locally by trusted code. The example historical
snapshot is not a live fixture/results feed; stale history must not be presented
as a current forecast. No production SLA or automated action is implied.

## Verify two independent checkouts

After fitting a separate checkout from the same verified source snapshots:

```bash
python scripts/check_reproduction.py /path/to/reference /path/to/reproduced --output reproduction-check.json
```

The checker verifies identical normalized input and feature bytes, identical
prediction identities and model sets, and bounded numerical differences for
every saved V1/V2 probability and reported accuracy/log-loss/Brier/ECE value.
It rejects a same-directory comparison, changed inputs and nonfinite predictions.
It checks supplied files; evidence that training was independently rerun comes
from the actual reproduction execution, not from this comparison alone.
