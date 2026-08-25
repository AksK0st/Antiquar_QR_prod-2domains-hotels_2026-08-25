#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <previous-release-tag>" >&2
  exit 2
fi

PREVIOUS_TAG=$1
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/.env.production"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.prod.yml"}

[ -f "$ENV_FILE" ] || { echo "Missing env file: $ENV_FILE" >&2; exit 1; }

case "$PREVIOUS_TAG" in
  *[!A-Za-z0-9._-]*|'') echo "Invalid release tag" >&2; exit 2 ;;
esac

cat >&2 <<'WARNING'
This rolls back APPLICATION IMAGES ONLY. It does not downgrade PostgreSQL.
The operation is blocked by default because an older application may be incompatible
with the current database schema or data. Restore a tested backup when compatibility
is not proven.
WARNING

if [ "${ALLOW_APP_ONLY_ROLLBACK:-}" != "1" ]; then
  cat >&2 <<'BLOCKED'
Blocked: database compatibility with the target release has not been confirmed.
After verifying the target application is backward-compatible with the CURRENT database,
rerun with ALLOW_APP_ONLY_ROLLBACK=1.
BLOCKED
  exit 1
fi

RELEASE_TAG="$PREVIOUS_TAG" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
  up -d --no-build --no-deps backend frontend gateway

echo "Application rollback requested: release=$PREVIOUS_TAG"
