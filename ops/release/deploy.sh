#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/.env.production"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.prod.yml"}

ENV_FILE="$ENV_FILE" COMPOSE_FILE="$COMPOSE_FILE" "$PROJECT_ROOT/ops/release/preflight.sh"

# shellcheck source=../lib/env.sh
. "$PROJECT_ROOT/ops/lib/env.sh"
load_compose_env
RELEASE_TAG=$(require_compose_env RELEASE_TAG)
DOMAIN=$(require_compose_env DOMAIN)

compose() {
  RELEASE_TAG="$RELEASE_TAG" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "[1/5] Build immutable application images: $RELEASE_TAG"
compose build backend frontend migrate

echo "[2/5] Start stateful dependencies"
compose up -d db minio

echo "[3/5] Bootstrap bucket/application storage credentials"
compose up --no-build --abort-on-container-exit --exit-code-from minio-init minio-init

echo "[4/5] Apply database migrations"
compose up --no-build --abort-on-container-exit --exit-code-from migrate migrate

echo "[5/5] Start application and gateway"
compose up -d --no-build backend frontend gateway

if command -v curl >/dev/null 2>&1; then
  echo "Waiting for public readiness..."
  i=0
  until curl --fail --silent --show-error --max-time 5 "https://$DOMAIN/health/ready" >/dev/null; do
    i=$((i + 1))
    [ "$i" -lt 24 ] || {
      echo "Deployment started but public readiness did not become healthy." >&2
      compose ps
      exit 1
    }
    sleep 5
  done
fi

compose ps
echo "Deploy OK: https://$DOMAIN release=$RELEASE_TAG"
