# Vector-Based Conflict Alert System Testbed

This repository implements a deterministic simulation testbed for a vector-based conflict alert system. It is built for local research, replay, inspection, and visualization of aircraft-pair conflict logic.

## Implemented System

| Area | Implementation |
| --- | --- |
| Physics and coordinates | Coordinate conversion, motion integration, closest-approach calculations, and alert thresholds |
| Surveillance sources | Synthetic, replay, and simulator-mode adapters behind a shared source switch |
| Conflict engine | Threaded pair lifecycle processing, risk scoring, alert records, and audit chain verification |
| Scenarios | Canonical, generated, BlueSky-style, and performance scenarios |
| API | FastAPI endpoints for scenario execution, history replay, audit drilldown, client config, WebSocket snapshots, and Prometheus metrics |
| Visualization | Radar-style browser demo, Cesium globe demo, Streamlit dashboard, and replay scrubber |
| Observability | Prometheus metrics, Grafana dashboard templates, trace/snapshot helpers, and audit rows |
| Infrastructure | Docker Compose, VPS compose file, Terraform scaffold, monitoring templates |

## Architecture

```text
scenario or surveillance source
  -> normalized frames
  -> vector geometry and pair screening
  -> risk scoring
  -> alert lifecycle state
  -> audit chain and metrics
  -> API / WebSocket / dashboard / radar demo
```

## Repository Layout

| Path | Purpose |
| --- | --- |
| `src/vcas/` | Core engine, API, configuration, surveillance adapters, risk, observability, and utilities |
| `tests/` | Regression tests for API, physics, surveillance, scenarios, grid index, and engine behavior |
| `scenarios/` | Canonical, generated, BlueSky-style, and performance scenario files |
| `web/` | Browser radar/globe/demo assets |
| `dashboard/` | Streamlit controller and replay surface |
| `config/` | Runtime risk, surveillance, and wind configuration |
| `monitoring/` | Prometheus, Grafana, and UptimeRobot templates |
| `infra/terraform/` | Deployment scaffold |
| `docs/` | MkDocs pages, ADRs, demo parameters, and knowledge bank |
| `scripts/` | Smoke, benchmark, scenario generation, replay, and launch helpers |

## Local Setup

Python dependencies use `uv`:

```powershell
uv sync
```

On Windows/OneDrive paths, use copy mode if hardlinks fail:

```powershell
$env:UV_CACHE_DIR = "cache\uv"
$env:UV_LINK_MODE = "copy"
uv sync
```

Optional local configuration:

```powershell
Copy-Item .env.example .env
```

Synthetic scenarios do not require external credentials.

## Run

Start the API:

```powershell
uv run uvicorn vcas.api.main:app --host 0.0.0.0 --port 8000
```

Or use the Windows launcher:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_vcas_radar.ps1
```

Local URLs:

- Health: `http://localhost:8000/health`
- Radar demo: `http://localhost:8000/demo/radar.html`
- Basic viewer: `http://localhost:8000/demo/index.html`
- Metrics: `http://localhost:8000/metrics`

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/run-synthetic?scenario=...` | Run a synthetic scenario and return alerts |
| `GET /api/run-synthetic?scenario=...&with_history=true` | Return replay snapshots for scrubber playback |
| `GET /api/run?source_mode=synthetic\|replay\|simulator` | Run through the configured source switch |
| `GET /api/alerts` | Return audit rows for the latest run |
| `GET /api/audit-drilldown?alert_id=...` | Return the audit chain and trigger frames for one alert |
| `GET /api/audit-chain-verify` | Verify hash-chain integrity |
| `GET /api/client-config` | Expose non-secret client runtime settings |
| `GET /metrics` | Export Prometheus metrics |
| `WS /ws/surveillance` | Stream aircraft and alert snapshots |

## Validation

```powershell
uv run pytest -q
uv run python scripts\smoke_demo.py
uv run python scripts\benchmark_load.py --aircraft-count 200 --duration-s 5 --max-ms-per-frame 1000
```

The test suite covers deterministic physics, coordinate behavior, scenario execution, API response shape, surveillance source handling, and benchmark paths.

## Demo Configuration

Default synthetic mode:

```text
VCAS_SOURCE_MODE=synthetic
VCAS_SCENARIO_PATH=scenarios/canonical/head_on.yml
```

Optional external values:

- `VCAS_CESIUM_TOKEN`
- `VCAS_OPENSKY_USERNAME`
- `VCAS_OPENSKY_PASSWORD`
- `VCAS_REPLAY_AIRPORT`
- `VCAS_REPLAY_START_UTC`
- `VCAS_REPLAY_DURATION_S`
- `VCAS_REPLAY_CACHE_ROOT`

See [`docs/demo_parameter_reference.md`](docs/demo_parameter_reference.md) for the full runtime parameter reference.

## Current Limits

- Replay mode depends on external OpenSky credentials and cached data availability.
- BlueSky integration is YAML-driven playback, not a shipped BlueSky engine sidecar.
- ML serving is guarded by an HTTP client toggle; no model-serving container is included.
- Generated scenarios and screenshots are development artifacts, not benchmark claims.

## License and Use

Source is published for review, learning, and private evaluation under the repository license. Operational, governmental, academic, or commercial deployment is outside the public testbed scope and requires explicit author authorization.
