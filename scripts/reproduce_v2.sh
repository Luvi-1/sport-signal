#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/sportslab-matplotlib}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/sportslab-cache}"
# Preserve rather than overwrite any published report or previous local fit.
archive="artifacts/reproductions/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$archive"
if [ -d reports/v2 ]; then mv reports/v2 "$archive/published-v2-reports"; fi
if [ -d artifacts/v2 ]; then mv artifacts/v2 "$archive/previous-v2-artifacts"; fi
# A fresh V1 fit changes run metadata and model serialization hashes. Preserve
# the prior staging manifest, then re-audit the same locked cached source bytes.
if [ -f data/v2/manifest.json ]; then mv data/v2/manifest.json "$archive/previous-source-manifest.json"; fi
bash scripts/reproduce.sh
python scripts/stage_v2_data.py --frozen-nfl
python -m experiments.v2.run develop --sport all
python -m experiments.v2.run evaluate --sport all --unlock-new-holdout
python scripts/summarize_v2.py
if [ -f "$archive/published-v2-reports/LICENSE.md" ]; then cp "$archive/published-v2-reports/LICENSE.md" reports/v2/LICENSE.md; fi
python - "$archive" <<'PY'
import json,sys
from pathlib import Path
archive=Path(sys.argv[1])/'published-v2-reports'
for sport in ['soccer','baseball','football','tennis']:
    previous=archive/sport/'evaluation.json'
    if not previous.exists():continue
    before=json.loads(previous.read_text());after=json.loads((Path('reports/v2')/sport/'evaluation.json').read_text())
    assert before['test']==after['test'], f'{sport}: test cohort changed'
    for model,metrics in before['metrics'].items():
        for key in ['accuracy','log_loss','brier','top_label_ece_10_bins']:
            difference=abs(metrics[key]-after['metrics'][model][key])
            assert difference<1e-6, f'{sport}/{model}/{key} differs by{difference}; inspect software/data versions'
print('Reproduction checks passed for all available archived published metrics')
PY
