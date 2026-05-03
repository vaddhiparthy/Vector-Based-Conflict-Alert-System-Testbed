#!/usr/bin/env bash

set -eu
set -o pipefail

export DEBIAN_FRONTEND=noninteractive

VCAS_USER="${VCAS_USER:-root}"
WORKDIR="/opt/vcas"
RUNTIME_COMPOSE="/opt/vcas/docker-compose.runtime.yml"
REPO_URL="${VCAS_REPO_URL:-}"
REPO_DIR="${VCAS_REPO_DIR:-/opt/vcas/repo}"
VCAS_ENV_FILE="/etc/vcas/runtime.env"
IMAGE_TAG="${VCAS_IMAGE_TAG:-latest}"
API_IMAGE="${VCAS_GHCR_API_IMAGE:-ghcr.io/openai/vcas-api:${IMAGE_TAG}}"
DASHBOARD_IMAGE="${VCAS_GHCR_DASHBOARD_IMAGE:-ghcr.io/openai/vcas-dashboard:${IMAGE_TAG}}"

mkdir -p "${WORKDIR}"
mkdir -p /etc/vcas

apt-get update
apt-get install -y ca-certificates curl docker.io docker-compose-plugin git

systemctl enable docker
systemctl start docker

cat > "${VCAS_ENV_FILE}" <<EOF
VCAS_REDIS_URL=${VCAS_REDIS_URL:-redis://redis:6379/0}
VCAS_POSTGRES_URL=${VCAS_POSTGRES_URL:-postgresql+psycopg://vcas:vcas@postgres:5432/vcas}
VCAS_MINIO_ENDPOINT=${VCAS_MINIO_ENDPOINT:-minio:9000}
VCAS_ML_ENABLED=${VCAS_ML_ENABLED:-false}
EOF
chmod 600 "${VCAS_ENV_FILE}"

if [ -n "${REPO_URL}" ]; then
  mkdir -p "${REPO_DIR}"
  if [ ! -d "${REPO_DIR}/.git" ]; then
    git clone "${REPO_URL}" "${REPO_DIR}" || true
  else
    (cd "${REPO_DIR}" && git pull --ff-only || true)
  fi
fi

if [ -f "${REPO_DIR}/docker-compose.yml" ]; then
  echo "Using repository compose override from ${REPO_DIR}/docker-compose.yml"
  cat > "${RUNTIME_COMPOSE}" <<EOF
services:
  vcas-api:
    image: ${API_IMAGE}
    environment:
      - VCAS_REDIS_URL
      - VCAS_POSTGRES_URL
      - VCAS_MINIO_ENDPOINT
      - VCAS_ML_ENABLED
    ports:
      - "8000:8000"
  dashboard:
    image: ${DASHBOARD_IMAGE}
    ports:
      - "8501:8501"
EOF
else
  cat > "${RUNTIME_COMPOSE}" <<EOF
services:
  vcas-api:
    image: ${API_IMAGE}
    environment:
      - VCAS_REDIS_URL
      - VCAS_POSTGRES_URL
      - VCAS_MINIO_ENDPOINT
      - VCAS_ML_ENABLED
    ports:
      - "8000:8000"
  dashboard:
    image: ${DASHBOARD_IMAGE}
    environment:
      - VCAS_REDIS_URL
    ports:
      - "8501:8501"
EOF
fi

docker compose -f "${RUNTIME_COMPOSE}" --env-file "${VCAS_ENV_FILE}" pull
docker compose -f "${RUNTIME_COMPOSE}" --env-file "${VCAS_ENV_FILE}" up -d
