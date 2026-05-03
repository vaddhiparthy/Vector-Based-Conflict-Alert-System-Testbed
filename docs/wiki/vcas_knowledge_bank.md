# vCAS Knowledge Bank

## Project Scope Snapshot

**Project:** vCAS — Vector Conflict Alert System testbed  
**Mode:** Local, simulation-first research scaffold  
**Repository path:** `C:/Users/vaddh/OneDrive/Documents/Projects/Creations/Live/vCAS`  
**Current build marker:** `Last completed task: 8.20`

vCAS implements a deterministic, auditable conflict-detection pipeline from
surveillance frame ingestion to alert emission. The intent is a reproducible
research demonstration, not an operational deployment.

## Scope Delivered to Date

Implemented and wired:

- Deterministic core kinematics and state modeling in `src/vcas/physics/` and `src/vcas/core/`
- 3D spatial indexing + pair generation in `src/vcas/index/`
- Threaded conflict lifecycle (`thread1`, `thread2a`, `thread2b`) with audit-chain persistence
- Risk scoring stack:
  - physics score `p_phys`
  - flight-plan score `p_fp`
  - ML client + circuit-breaker `p_ml`
  - blend/floor/composition in `src/vcas/risk/composite.py`
- Synthetic and replay adapters via normalized `SurveillanceFrame`
- Observability:
  - JSON logs (structlog)
  - Prometheus counters/gauges
  - OpenTelemetry wrappers with OTLP hooks
- Public surfaces:
  - FastAPI demo APIs and websocket stream
  - Streamlit dashboard
  - Cesium-facing static demo scaffold
- CI/CD and infra:
  - CI workflow (`ci.yml`)
  - Nightly replay workflow (`nightly.yml`)
  - Mainline publish/build workflow (`release.yml`)
  - Grafana, Prometheus, Jaeger, MinIO, postgres, redis in compose
- Golden output workflow and benchmark scaffolding (`golden/`, `scripts/benchmark_load.py`, `scripts/locustfile.py`)

## Current Runtime Surface

See `.env.example` and `src/vcas/config/settings.py` for full runtime variables.

Notable toggles:

- `VCAS_SOURCE_MODE` (`synthetic | replay | simulator`)
- `VCAS_ML_ENABLED` (when false, ML contributes only via 0 floor behavior)
- `VCAS_LOG_LEVEL`
- `VCAS_THREAD1_T_TC_S`, `VCAS_THREAD2A_T_TC_S`, `VCAS_PERSISTENT_CLOSE_SECONDS`

## Current Evidence

- Unit tests in `tests/` for physics, grid, engine, risk, surveillance, simulator
- Golden/replay checks in `scripts/nightly_replay_check.py` (LFBO one-hour path)
- End-to-end smoke in `scripts/smoke_demo.py`

## Remaining Human Actions

- OpenSky credentials (for task 5.5 cache/credential-backed replay)
- BlueSky dependency install validation (task 5.9)
- Cesium token (task 6.3)
- Oracle/Cloudflare tasks in 8.10–8.13 if you want full public deployment mode

## Build State

See [`BUILD_STATE.md`](../BUILD_STATE.md).

