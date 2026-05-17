# vCAS Parameter Reference (Demo-Run Focus)

Use this as the single source of truth for running the local demo without secrets.

All values come from environment variables (or a local `.env` file loaded by your shell).

## Environment Matrix

`[REQ]` = needed for synthetic run + radar UI  
`[REQ_REPLAY]` = needed for replay source mode  
`[OPT]` = optional for local demo

| Variable | Meaning (plain words) | Default | Demo Requirement |
|---|---|---|---|
| `VCAS_DEBUG` | Turn extra app debug logging on/off | `false` | `[OPT]` |
| `VCAS_LOG_LEVEL` | Log verbosity (`INFO`, `DEBUG`, etc.) | `INFO` | `[OPT]` |
| `VCAS_SOURCE_MODE` | Which data source to use (`synthetic`, `replay`, `simulator`) | `synthetic` | `[REQ]` if using `/api/run` |
| `VCAS_SCENARIO_PATH` | Scenario file path for synthetic mode | `scenarios/canonical/head_on.yml` | `[REQ]` for synthetic |
| `VCAS_SURVEILLANCE_RATE_HZ` | Simulation/input tick rate | `1` | `[OPT]` |
| `VCAS_SURVEILLANCE_CONFIG` | Optional YAML config file for defaults | `config/surveillance.yaml` | `[OPT]` |
| `VCAS_CELL_SIZE_M` | Spatial grid cell size (meters) | `4000` | `[OPT]` |
| `VCAS_PROTECTED_RADIUS_M` | Horizontal protected radius | `1852` | `[OPT]` |
| `VCAS_PROTECTED_HEIGHT_M` | Vertical protected height | `609.6` | `[OPT]` |
| `VCAS_THREAD1_T_TC_S` | Thread-1 entry threshold in seconds | `900` | `[OPT]` |
| `VCAS_THREAD2A_T_TC_S` | Imminent conflict threshold in seconds | `300` | `[OPT]` |
| `VCAS_PERSISTENT_CLOSE_SECONDS` | How long continuous closing must persist | `15` | `[OPT]` |
| `VCAS_P_FP_WEIGHT` | Flight-plan risk weight in composite score | `0.20` | `[OPT]` |
| `VCAS_P_PHYS_WEIGHT` | Physics risk weight in composite score | `0.30` | `[OPT]` |
| `VCAS_P_ML_WEIGHT` | ML risk weight in composite score | `0.50` | `[OPT]` |
| `VCAS_ML_ENABLED` | Toggle ML use (`true/false`) | `false` | `[OPT]` |
| `VCAS_ML_SERVICE_URL` | ML service URL (used only if ML enabled) | `http://localhost:8080/predictions/vcas-lstm` | `[OPT]` |
| `VCAS_ML_TIMEOUT_S` | ML timeout in seconds | `1.2` | `[OPT]` |
| `VCAS_ML_CIRCUIT_FAILURE_THRESHOLD` | Fail count before ML circuit opens | `3` | `[OPT]` |
| `VCAS_ML_CIRCUIT_OPEN_SECONDS` | ML backoff after failures | `30` | `[OPT]` |
| `VCAS_REDIS_URL` | Redis connection string for runtime | `redis://localhost:6379/0` | `[OPT]` (required if running full infra stack) |
| `VCAS_POSTGRES_URL` | PostgreSQL connection string | `postgresql+psycopg://vcas:vcas@localhost:5432/vcas` | `[OPT]` (required for persistence modes) |
| `VCAS_MINIO_ENDPOINT` | MinIO hostname:port | `localhost:9000` | `[OPT]` |
| `VCAS_MINIO_ACCESS_KEY` | MinIO access key | `""` | `[OPT]` |
| `VCAS_MINIO_SECRET_KEY` | MinIO secret key | `""` | `[OPT]` |
| `VCAS_OPENSKY_USERNAME` | OpenSky username | `""` | `[REQ_REPLAY]` |
| `VCAS_OPENSKY_PASSWORD` | OpenSky password | `""` | `[REQ_REPLAY]` |
| `VCAS_REPLAY_AIRPORT` | ICAO code used in replay | `KAZO` | `[REQ_REPLAY]` |
| `VCAS_REPLAY_START_UTC` | Replay window start UTC | `2026-01-01T00:00:00Z` | `[REQ_REPLAY]` |
| `VCAS_REPLAY_DURATION_S` | Replay window duration in seconds | `3600` | `[REQ_REPLAY]` |
| `VCAS_REPLAY_CACHE_ROOT` | Local cache folder for replay tracks | `cache/opensky` | `[REQ_REPLAY]` |
| `VCAS_FLIGHT_PLAN_WINDOW_S` | Flight-plan inference lookback window | `30` | `[OPT]` |
| `VCAS_WIND_PROFILE` | Wind profile file | `config/wind.yaml` | `[OPT]` |
| `VCAS_CESIUM_TOKEN` | Cesium ion token for map tiles | `""` | `[OPT]` |
| `TELEGRAM_BOT_TOKEN` | Optional Telegram alerting token | `""` | `[OPT]` |
| `OPENWEATHER_API_KEY` | Optional weather feed key | `""` | `[OPT]` |
| `VCAS_AERODROME_LAT` | Aerodrome center latitude | `42.2343889` | `[REQ]` for radar coordinate conversion |
| `VCAS_AERODROME_LON` | Aerodrome center longitude | `-85.5515556` | `[REQ]` for radar coordinate conversion |
| `VCAS_AERODROME_ALT_M` | Aerodrome center altitude (m) | `100` | `[REQ]` for coordinate conversion |

## Runtime notes

- For the first successful local demo, only the following are truly needed:
  - `VCAS_SOURCE_MODE=synthetic`
  - `VCAS_SCENARIO_PATH=scenarios/canonical/head_on.yml`
  - Any of the Redis/Postgres URLs if you run the whole compose stack; if not, backend still serves API/UI.
- OpenSky fields (`VCAS_OPENSKY_*`) are only required for replay mode.
- Cesium token is optional for the current vCAS radar UI and the Cesium globe UI (`/demo/globe.html`).
  Without a token, the globe runs with no imagery layer (no external tile server calls).
- `.env` file values are automatically loaded by the app at startup.

### Fastest synthetic-only start (zero external keys)

For a synthetic local check, you only need:

1. `VCAS_SOURCE_MODE=synthetic`
2. `VCAS_SCENARIO_PATH=scenarios/canonical/head_on.yml`

No OpenSky, Cesium, Telegram, or OpenWeather values are required for `/api/run-synthetic`, `/demo/radar.html`, or `/demo/globe.html` to work.

### Start command that avoids python launcher issues

Use the local venv python directly (this avoids missing `python.exe`/launcher popup problems):

```text
cd /path/to/vCAS
.\.venv\Scripts\python.exe -m uvicorn vcas.api.main:app --host 0.0.0.0 --port 8000
```

Or run the provided scripts:

```text
scripts\start_vcas_radar.bat
```
```text
powershell -ExecutionPolicy Bypass -File scripts\start_vcas_radar.ps1
```

Then open:
- `http://localhost:8000/health`
- `http://localhost:8000/demo/radar.html`

## External service list

- **OpenSky Network**: `VCAS_OPENSKY_USERNAME`, `VCAS_OPENSKY_PASSWORD`  
  Source: [OpenSky Network account](https://opensky-network.org)  
  Required only for replay cache generation and replay playback.
- **Cesium ion**: `VCAS_CESIUM_TOKEN`  
  Source: [Cesium ion tokens](https://ion.cesium.com/)  
  Optional unless adding full globe-based tiles in future versions.
- **Telegram**: `TELEGRAM_BOT_TOKEN`  
  Source: [Telegram BotFather](https://t.me/BotFather)  
  Optional alert routing only.
- **OpenWeather**: `OPENWEATHER_API_KEY`  
  Source: [OpenWeather API keys](https://openweathermap.org/api)  
  Optional.

## How to get each key (step by step)

### OpenSky Network (`VCAS_OPENSKY_USERNAME`, `VCAS_OPENSKY_PASSWORD`)

1. Create a normal OpenSky account at [OpenSky Network](https://opensky-network.org).
2. Log in.
3. Use your OpenSky login credentials directly as:
   - `VCAS_OPENSKY_USERNAME=<your login email or username>`
   - `VCAS_OPENSKY_PASSWORD=<your OpenSky password>`
4. Start replay mode with:
   - `VCAS_SOURCE_MODE=replay`
  - `VCAS_REPLAY_AIRPORT=KAZO` (or any ICAO airport)

Notes:
- These are not API keys. They are your existing OpenSky account credentials.
- Keep them empty for synthetic demo.

### Cesium token (`VCAS_CESIUM_TOKEN`)

1. Create/Sign in to a Cesium account at [Cesium ion](https://ion.cesium.com/).
2. Open the token section in your profile.
3. Create a token with default map tiles access (or viewer-only).
4. Set:
   - `VCAS_CESIUM_TOKEN=<your token>`
5. Restart API service after changing `.env`.

Notes:
- The current UI still works in 2D without this token.
- If you keep it blank, map rendering stays in radar mode with no map imagery dependency.

### Telegram bot token (`TELEGRAM_BOT_TOKEN`)

1. Open Telegram and chat with `@BotFather` at [Telegram](https://t.me/BotFather) or search the bot inside your app.
2. Run `/newbot`.
3. Choose a display name and a unique bot username ending in `bot`.
4. Copy the **bot token** BotFather sends back.
5. Set:
   - `TELEGRAM_BOT_TOKEN=<bot_token>`
6. Restart API after updating.

Notes:
- This is optional.
- Without extra bot wiring, alerts may not push anywhere yet unless related Telegram handlers are enabled.

### OpenWeather API key (`OPENWEATHER_API_KEY`)

1. Create an [OpenWeather](https://openweathermap.org/) account.
2. Go to API key section in your account.
3. Create a new key (free tier works for basic checks).
4. Set:
   - `OPENWEATHER_API_KEY=<key>`
5. Restart API after updating.

Notes:
- Optional today for weather enrichment.

## Copy-paste `.env` block for all services

```text
# Put this in .env (fill in only what you need)
VCAS_SOURCE_MODE=synthetic
VCAS_SCENARIO_PATH=scenarios/canonical/head_on.yml
VCAS_AERODROME_LAT=42.2343889
VCAS_AERODROME_LON=-85.5515556
VCAS_AERODROME_ALT_M=100

# Replay mode (optional)
VCAS_OPENSKY_USERNAME=
VCAS_OPENSKY_PASSWORD=
VCAS_REPLAY_AIRPORT=KAZO
VCAS_REPLAY_START_UTC=2026-01-01T00:00:00Z
VCAS_REPLAY_DURATION_S=3600
VCAS_REPLAY_CACHE_ROOT=cache/opensky

# Optional external integrations
VCAS_CESIUM_TOKEN=
TELEGRAM_BOT_TOKEN=
OPENWEATHER_API_KEY=
```

## Useful defaults for quick test

```text
VCAS_SOURCE_MODE=synthetic
VCAS_SCENARIO_PATH=scenarios/canonical/head_on.yml
VCAS_DEBUG=false
VCAS_LOG_LEVEL=INFO
VCAS_SURVEILLANCE_RATE_HZ=1
```

## Endpoint map

- Health: `GET /health`
- Client config: `GET /api/client-config`
- Synthetic replay payload: `GET /api/run-synthetic?scenario=...&with_history=true`
- Source-switch run: `GET /api/run?source_mode=synthetic|replay|simulator`
- Live websocket: `/ws/surveillance`
- Radar UI: `/demo/radar.html`
