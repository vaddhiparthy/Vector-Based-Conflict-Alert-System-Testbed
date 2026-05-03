FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

COPY src /app/src
COPY dashboard /app/dashboard
COPY web /app/web
COPY README.md /app/README.md
COPY LICENSE /app/LICENSE
COPY scenarios /app/scenarios
COPY config /app/config

ENV PYTHONPATH=/app/src

CMD ["uv", "run", "streamlit", "run", "dashboard/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
