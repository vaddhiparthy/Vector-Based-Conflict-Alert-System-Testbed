FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Hatchling validates README metadata during build.
COPY pyproject.toml uv.lock README.md LICENSE /app/
RUN uv sync --frozen --no-dev

COPY src /app/src
COPY dashboard /app/dashboard
COPY web /app/web
COPY scripts /app/scripts
COPY scenarios /app/scenarios
COPY config /app/config
COPY monitoring /app/monitoring

ENV PYTHONPATH=/app/src

CMD ["uv", "run", "uvicorn", "vcas.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
