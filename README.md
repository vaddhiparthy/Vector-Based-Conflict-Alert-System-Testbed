# vCAS

## Vector-Based Conflict Alert System Testbed

This repository implements a research testbed for a vector-based conflict alert architecture inspired by the public concept described by the author and intended for simulation-only demonstration. It is engineered as a reproducible local stack for:

- deterministic surveillance-to-conflict math
- auditable pair state transitions across screening threads
- risk scoring composition and deterministic ML fallback behavior
- replayable demonstrations from synthetic and recorded sources

The project is organized as a modular monorepo with explicit interfaces between:

- coordinate/physics math
- surveillance ingestion adapters
- threaded conflict lifecycle processing
- risk evaluation
- web-serving and observability
- infrastructure services

## License and Use

Source is published for review, learning, and private evaluation only.
Operational, governmental, academic, and commercial deployment is not part of this public testbed; any non-local deployment decisions require explicit author authorization.  

This repository defaults to a non-commercial, author-restricted posture and all public usage should follow the author-defined policy for citation and distribution.

## Current Build State

Refer to [`BUILD_STATE.md`](BUILD_STATE.md) for the current checkpoint and blocked actions.

## Knowledge Base

- [`vCAS Knowledge Bank`](docs/wiki/vcas_knowledge_bank.md)

## Local Runtime

```text
cd /path/to/vCAS
uv sync
cp .env.example .env  # optional for synthetic-only demo
.\.venv\Scripts\python.exe -m uvicorn vcas.api.main:app --host 0.0.0.0 --port 8000
```

If .env is present but `python.exe` is not found by your shell, use:

```text
powershell -ExecutionPolicy Bypass -File scripts\start_vcas_radar.ps1
```

If you hit a `python.exe` not found popup from command windows, use the local launcher:

```text
scripts\start_vcas_radar.bat
```

or

```text
powershell -ExecutionPolicy Bypass -File scripts\start_vcas_radar.ps1
```

The app now reads values from local `.env` directly on startup, so adding tokens there is enough for local runs.

Core runtime services are:

- PostgreSQL 16
- Redis 7
- MinIO (S3-compatible storage)

## API / demo endpoints

- `GET /api/run-synthetic?scenario=...` runs a scenario and returns alerts.
- `GET /api/run-synthetic?scenario=...&with_history=true` returns a per-frame snapshot list for scrubber replay.
- `GET /api/run?source_mode=synthetic|replay|simulator` runs using the same source switch used by settings.
- `GET /api/alerts` returns in-memory audit rows for the last run.
- `GET /api/audit-chain-verify` checks hash-chain integrity.
- `GET /metrics` exposes Prometheus counters and gauges.

## Front-end

- `web/index.html` provides a lightweight WebSocket viewer and run-with-history scrubber.
- `dashboard/app.py` provides a Streamlit controller with replay scrubber and pair drill-down.
- `web/radar.html` provides a live/replay animated radar-style map for movement and alert visualization.

## Performance check

Run a deterministic 200-aircraft throughput check for the browser-rate target:

```text
uv run python scripts/benchmark_load.py --aircraft-count 200 --duration-s 5 --max-ms-per-frame 1000
```

## Radar demo (flight radar-style animation)

For synthetic demo (no external credentials), set:

```text
VCAS_SOURCE_MODE=synthetic
VCAS_SCENARIO_PATH=scenarios/canonical/head_on.yml
```

Recommended test flow:

1. Start with:
   `powershell -ExecutionPolicy Bypass -File scripts\start_vcas_radar.ps1`
2. Open `http://localhost:8000/health` (should return JSON `status: ok`)
3. Open `http://localhost:8000/demo/radar.html`
4. Click **Run scenario + animate**

For synthetic demo (no external credentials), set:

```text
VCAS_SOURCE_MODE=synthetic
VCAS_SCENARIO_PATH=scenarios/canonical/head_on.yml
```

The radar page reads these environment-driven values from `/api/client-config`:

- `VCAS_CESIUM_TOKEN`
- `VCAS_OPENSKY_USERNAME`
- `VCAS_OPENSKY_PASSWORD`

Replay-mode extras are optional:

- `VCAS_OPENSKY_USERNAME`
- `VCAS_OPENSKY_PASSWORD`
- `VCAS_REPLAY_AIRPORT` (default: `KAZO`)
- `VCAS_REPLAY_START_UTC`
- `VCAS_REPLAY_DURATION_S`
- `VCAS_REPLAY_CACHE_ROOT`

Where to check tokens and required inputs:

- [`docs/demo_parameter_reference.md`](docs/demo_parameter_reference.md)
- [`BUILD_STATE.md`](BUILD_STATE.md)

Optional: add tokens to your environment or `.env` and restart the API.

For exact credentials needed per external service and copy/paste `.env` examples, use:

- [`docs/demo_parameter_reference.md`](docs/demo_parameter_reference.md)

## Planned Execution Model

- Single task completion pattern with checkpoint updates.
- No hidden behavior: every state transition and pair movement is logged.
- No feature is presented as complete unless it has deterministic evidence in code or test artifacts.
