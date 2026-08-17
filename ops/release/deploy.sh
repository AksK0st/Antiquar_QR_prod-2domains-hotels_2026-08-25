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
POSTGRES_DB=$(require_compose_env POSTGRES_DB)
POSTGRES_USER=$(require_compose_env POSTGRES_USER)

compose() {
  RELEASE_TAG="$RELEASE_TAG" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "[1/7] Build immutable application images: $RELEASE_TAG"
compose build backend frontend migrate

echo "[2/7] Start stateful dependencies"
compose up -d db minio

echo "Waiting for PostgreSQL readiness..."
i=0
until compose exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  i=$((i + 1))
  [ "$i" -lt 24 ] || { echo "PostgreSQL did not become ready" >&2; exit 1; }
  sleep 2
done

echo "[3/7] Bootstrap bucket/application storage credentials"
compose up --no-build --abort-on-container-exit --exit-code-from minio-init minio-init

echo "[4/7] Stop application traffic for a cross-storage pre-migration backup"
compose stop gateway backend >/dev/null 2>&1 || true
TRAFFIC_STOPPED=1
MIGRATION_STARTED=0
restore_old_app_on_early_failure() {
  code=$?
  if [ "$code" -ne 0 ] && [ "$TRAFFIC_STOPPED" = "1" ] && [ "$MIGRATION_STARTED" = "0" ]; then
    echo "Release failed before migrations; restarting the previously deployed containers." >&2
    compose start backend gateway >/dev/null 2>&1 || true
  fi
  exit "$code"
}
trap restore_old_app_on_early_failure EXIT INT TERM
ENV_FILE="$ENV_FILE" COMPOSE_FILE="$COMPOSE_FILE" "$PROJECT_ROOT/ops/backup/backup.sh"

echo "[5/7] Apply database migrations"
MIGRATION_STARTED=1
compose up --no-build --abort-on-container-exit --exit-code-from migrate migrate

echo "[6/7] Start application and gateway"
compose up -d --no-build backend frontend gateway
TRAFFIC_STOPPED=0
trap - EXIT INT TERM

echo "[7/7] Verify public readiness"
if command -v curl >/dev/null 2>&1; then
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
else
  echo "WARNING: curl is not installed; public readiness was not verified by deploy.sh" >&2
fi

compose ps
echo "Deploy OK: https://$DOMAIN release=$RELEASE_TAG"
