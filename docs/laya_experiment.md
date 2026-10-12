# Laya experiment: scope and reproducibility

This is an optional, identity-blinded **pretrained Laya zero-shot benchmark**, not a
Laya model trained or calibrated for sports. No API purchase, hosted inference,
account creation, or dataset upload is involved. Model inputs are evaluated locally
on CPU. The main sports models do not depend on this optional experiment.

## Frozen protocol

- Exactly 200 evenly spaced rows per sport, ordered by date and event ID, from the
  existing untouched holdout. Selection never uses outcomes or model performance.
- Before inference, `reports/laya/frozen_manifest.json` records selected IDs,
  source-artifact hashes, feature serialization hashes, question wording and the
  pinned model revision. A changed manifest is rejected rather than silently replaced.
- The same rows are scored for Laya, the selected calibrated/uncalibrated model,
  the training prior and available Elo baselines.
- Only the explicit numeric feature whitelist, its fixed definitions and the sport
  enter the input. No team/player names, fixture identifiers, dates or outcome labels
  enter the input. A/B is the original pregame orientation; all binary sports exclude
  ties upstream, while soccer uses B win / draw / A win.
- Probabilities come from Laya's per-label distribution, not its entropy-derived
  `confidence` field. Output probability validity and actual tokenizer truncation are
  checked. All inputs must fit the English checkpoint's 512-token window.
  The SDK rounds each probability to four decimals. Sums are renormalized only
  within the resulting mathematical tolerance of 0.00005 times the class count;
  larger errors or non-finite/out-of-range values stop the experiment.
- No sports fine-tuning, probability recalibration, prompt search or choice of a
  favorable subset is performed. The first ten rows per sport are also checked with
  reversed option order as a diagnostic only; those outputs never select the model.
- Accuracy, log loss, Brier score and reliability bins are reported. Binary Brier
  score is the positive-class squared error; soccer uses the sum over three classes.
  Neither accuracy nor a Brier improvement by itself proves good calibration.
- This is a limited, evenly spaced historical subset, not proof of future advantage
  or betting profitability. Identity blinding reduces direct historical-result
  memorization risk but does not prove pretraining contamination is impossible.

## Installation

Use an isolated optional environment; do not change the main model environment.
The executed environment used the official PyTorch CPU wheel index and PyPI.

```sh
python -m venv --system-site-packages .venv-laya
.venv-laya/bin/python -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.14.1+cpu'
.venv-laya/bin/python -m pip install --index-url https://pypi.org/simple \
  'laya==0.4.2' 'transformers==5.19.0' 'huggingface_hub==2.2.0' \
  'safetensors==0.8.0' 'socksio==1.0.0'
.venv-laya/bin/python scripts/evaluate_laya.py --prepare-only
.venv-laya/bin/python scripts/evaluate_laya.py --threads 2
```

The system site packages supply the project's existing pandas, NumPy, SciPy and
scikit-learn stack. `socksio` is needed for this environment's existing network proxy;
the proxy configuration is not changed. Checkpoints/cache and the optional virtual
environment are excluded from publication. The code loads only the English
`convaiinnovations/laya` checkpoint at revision
`7b928d828b7b0e022f929d9bd2e44165aa270148`, using CPU eager inference.

The English weights are approximately 843 MB. The public Hub is accessed without
credentials. Initial model download requires network access; subsequent runs can
reuse the local cache. Each completed prediction is checkpointed to
`artifacts/{sport}/laya_predictions.jsonl`, permitting a same-manifest resume.

## Results

Completed on **2026-10-11**, with 800 actual held-out predictions, 200 per sport.
No inference rows were dropped. Lower log loss and Brier score are better.

| Sport | Laya log loss | Selected calibrated log loss | Laya accuracy | Selected accuracy | Laya Brier | Selected Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Soccer | 1.1735 | 0.9743 | 32.5% | 51.0% | 0.7147 | 0.5798 |
| Baseball | 0.7065 | 0.6830 | 50.0% | 57.0% | 0.2566 | 0.2448 |
| American football | 0.7359 | 0.6381 | 38.0% | 62.0% | 0.2712 | 0.2244 |
| Tennis | 0.6965 | 0.5713 | 49.0% | 70.0% | 0.2517 | 0.1945 |

Laya also had worse log loss than the training-prior and calibrated-Elo baselines
in every sport on these same subsets. It is **not selected for the forecasting
core**. This negative result applies to the stated pretrained checkpoint, fixed
numerical feature representation and protocol; it is not an evaluation of a
future sports-fine-tuned Laya model or text-based injury/news extraction.

Reversing option order on the first ten frozen rows per sport changed a class
probability by as much as 0.3632 (soccer), 0.2843 (baseball), 0.2543 (football),
and 0.1297 (tennis). This is a diagnostic with only ten rows per sport, not an
estimate of the population frequency of option-order failures.

CPU execution used two threads, with median inference times of 1.72–1.82 seconds
per row, peak RSS 2,918 MiB, and maximum input length 325 tokens. The initial
ten-real-row smoke check took 17.99 seconds. The final verification independently
validated all 800 stored probability records and reproduced every comparator's
accuracy, log loss and Brier score from the frozen rows. All seven offline
protocol tests pass; syntax compilation and optional-environment dependency
checks also pass.

The authoritative measured output is `reports/laya/evaluation.json`. A `running`
status or an absent output means the experiment has not completed. The final report
records hardware-relevant runtime, peak RSS, tokenizer budget, per-sport metrics,
and option-order sensitivity. No result is inferred from the vendor's benchmarks.

## Official sources and known limitations

- [Official package](https://pypi.org/project/laya/): Apache-2.0; package pinned at 0.4.2
- [Model files](https://huggingface.co/convaiinnovations/laya/tree/main): English,
  multilingual and typed-decisions checkpoints; only English is used here
- [API documentation](https://nandhakishorm.github.io/laya/reference/agent/): typed
  outputs, revision pinning and truncation behavior
- [Fine-tuning guide](https://nandhakishorm.github.io/laya/finetune/): domain labels,
  separate calibration and held-out evaluation are needed for specialization
- [Project benchmarks](https://github.com/NandhaKishorM/laya/blob/main/BENCHMARKS.md):
  base transfer and overconfidence limitations; these do not measure sports forecasting

Fixed-format output prevents invented output categories. It does not prevent a
wrong class, an inaccurate probability or failure on a new numerical domain.

## Publication and data license

Only code, aggregate metrics and the frozen selection manifest are intended for
publication. Per-case prediction files remain under excluded `artifacts/`. The
combined Laya report and manifest include tennis-derived material and are
conservatively distributed under **CC BY-NC-SA 4.0**, consistent with the tennis
source restriction and attribution in the main data documentation. This does not
change Laya's own Apache-2.0 software/model license or the project's code license.

`reports/laya/code_provenance.json` records the script digest used for initial
inference. Later cache-validation hardening does not change the frozen inputs,
model, prompt or stored predictions. Offline tests in `tests/test_laya_experiment.py`
cover schema, serialization blinding, selection, bounded rounding and corrupted
cache rejection without requiring Laya, torch, model weights or network access.
Actual token-budget verification is an integration check performed using the pinned
Laya tokenizer and formatter; it is not simulated by the offline unit tests.

The SDK issued a temperature-range warning for its `choice:11+` calibration entry.
This benchmark uses only two or three outcome classes, so the warned entry is not
selected. No calibration setting is manually changed for this experiment.
