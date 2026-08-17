#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/.env.production"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.prod.yml"}

[ -f "$ENV_FILE" ] || { echo "Missing env file: $ENV_FILE" >&2; exit 1; }

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

# These jobs are deliberately one-shot and fail the maintenance run if a
# dependency is unavailable or if reconciliation finds broken references.
compose --profile maintenance run --rm cleanup-sessions
compose --profile maintenance run --rm storage-cleanup
compose --profile maintenance run --rm reconcile-storage
