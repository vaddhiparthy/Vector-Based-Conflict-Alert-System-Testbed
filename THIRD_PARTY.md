# Third-Party Dependencies and Attribution

This project uses the following external software/components.

## Runtime stack

- FastAPI (BSD-3-Clause)
- NumPy (BSD)
- Pydantic (MIT)
- SQLAlchemy (MIT)
- psycopg (LGPL-3.0)
- redis-py (MIT)
- structlog (Apache 2.0)
- Prometheus Python client (Apache 2.0)
- hypothesis (Apache 2.0)
- ruff (MIT)
- sqlfluff (BSD-3-Clause)
- detect-secrets (Apache 2.0)

## Browser and visualization stack

- CesiumJS (Apache 2.0) – used in `web/globe.html` via the official Cesium build distribution
- Plotly (MIT)
- Streamlit (Apache 2.0)

## Surveillance and replay

- pyopensky (MIT) – optional OpenSky historical fetch used to build deterministic replay caches

## Observability (deferred)
- OpenTelemetry (Apache 2.0)
- Locust (MIT)
- PyTorch (BSD) and TorchServe (BSD-derived)
- MinIO Python client (Apache 2.0)
- Flask/uvicorn components via `uvicorn[standard]` (BSD-style license stack)

## Policy

Any dependency brought in for a concrete phase should include one-line purpose note
in that module’s docstring or ADR file so execution intent is auditable.
