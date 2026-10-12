# Local release validation

Recorded 2026-10-11 UTC. This records executed checks, not a production-service
certification. Development and review were substantially AI-assisted.

## What passed

- **107 offline automated tests**, including source parsers, score/date validation,
  delayed availability, outcome mutation, split embargoes, train/save/load/predict,
  Laya serialization and caching, V2 feature/state behavior, holdout-access gates,
  report rendering and independent-reproduction comparisons
- Syntax compilation of source, scripts and tests; shell syntax checks; CLI help
- Editable installation in a separate pinned-dependency environment; `pip check`
  reported no broken requirements; core and V2 CLI entrypoints worked from outside
  the checkout
- Independent recomputation of every saved V2 model, raw/calibrated/ensemble and
  baseline probability for all **5,809 new-period events**: maximum numerical
  difference **2.22e-16**. All reported accuracy/log-loss/Brier/ECE values and both
  paired-bootstrap comparisons per sport reproduced
- Actual historical fast-inference parity for all four sports: maximum probability
  difference **5.55e-17** from the stored ensemble output. Reversed tennis player
  and rank order correctly reversed the probability mapping
- Original **57-file V1 snapshot** remained byte-identical
- All-four V2 code/protocol/source/data/model selection hashes remained unchanged
  between pre-unlock review and completed evaluation. No held-out winner switching
- Calibration/improvement figure visual inspection and valid relative documentation
  links; generated reports use actual recorded values

## Independent end-to-end reproduction

A separate checkout reran `scripts/reproduce_v2.sh`, including V1 regeneration,
source staging, every V2 development fit/calibrator/ensemble, the global freeze,
and evaluation of the published cohorts. It used independently verified copies of
cached public source bytes. The original full NFL provider CSV was deliberately
absent, exercising the licensed normalized snapshot path.

The checker compared **24 normalized-input and feature files** byte for byte,
plus every saved probability and four headline metrics for **90 reported model
variants** across V1 and V2. V1 predictions and metrics reproduced exactly. V2's
maximum probability difference was **2.96e-7** and maximum metric difference was
**1.20e-8**, within the predetermined **1e-6** tolerance. Small floating-point
optimizer/parallel-reduction differences mean the refit is not claimed bitwise
identical. Accuracy and the scientific conclusions were unchanged.

[Machine-readable reproduction check](v2/reproduction_check.json) ·
[Reproduction instructions](../docs/v2/REPRODUCE.md)

## Publication boundary

The release ZIP is built from an explicit allowlist and includes a per-file SHA256
manifest. It contains code, documentation, aggregate reports/plots and the
explicitly licensed normalized NFL snapshot. Raw downloads, per-event derived
files, model/checkpoint weights, environments, caches, logs and credentials are
excluded. Common credential-pattern checks found no matches; this is not an
exhaustive security audit.

Tests were also run from the extracted source archive. Hosted GitHub Actions
execution is not established by this local record; its workflow definition is
included. Publication and a live operational service are separate steps.

The Laya experiment's separate 800-row validation and optional environment checks
are documented [here](../docs/laya_experiment.md). Dataset rights and limitations
remain in [DATA_LICENSES.md](../DATA_LICENSES.md).
