#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/sportslab-matplotlib}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/sportslab-cache}"
python -m unittest discover -s tests -v
for sport in soccer baseball tennis; do
  python -m sportslab run --sport "$sport"
done
python scripts/reproduce_frozen_nfl.py --mode frozen
python scripts/summarize_results.py
