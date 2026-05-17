#!/usr/bin/env sh
set -eu

echo "=== vCAS smoke suite ==="
uv sync
uv run pytest -q
uv run python scripts/smoke_demo.py
echo "=== smoke complete ==="
if [ "${VCAS_RUN_BENCHMARK:-0}" = "1" ]; then
  echo "=== optional perf check ==="
  uv run python scripts/benchmark_load.py --aircraft-count 120 --duration-s 3 --max-ms-per-frame 1000
fi
