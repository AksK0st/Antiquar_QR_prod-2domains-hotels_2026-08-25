#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: CONFIRM_RESTORE=YES BACKUP_DIR=/mnt/offhost $0 <backup-stamp>" >&2
  exit 2
fi
: "${CONFIRM_RESTORE:?Set CONFIRM_RESTORE=YES after reviewing the restore target}"
[ "$CONFIRM_RESTORE" = "YES" ] || { echo "CONFIRM_RESTORE must equal YES" >&2; exit 2; }

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/.env.production"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.prod.yml"}
[ -f "$ENV_FILE" ] || { echo "Missing env file: $ENV_FILE" >&2; exit 1; }
# shellcheck source=../lib/env.sh
. "$PROJECT_ROOT/ops/lib/env.sh"
load_compose_env
BACKUP_DIR=$(require_compose_env BACKUP_DIR)

STAMP=$1
SRC="$BACKUP_DIR/$STAMP"
[ -f "$SRC/database.dump" ] || { echo "Missing database.dump in $SRC" >&2; exit 1; }
[ -f "$SRC/SHA256SUMS" ] || { echo "Missing SHA256SUMS in $SRC" >&2; exit 1; }

(cd "$SRC" && sha256sum -c SHA256SUMS)

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Stopping traffic and application writes..."
compose stop gateway backend || true

echo "Restoring PostgreSQL..."
compose exec -T db sh -ec \
  'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl' \
  < "$SRC/database.dump"

echo "Restoring object storage..."
BACKUP_DIR="$BACKUP_DIR" compose --profile maintenance run --rm --no-deps \
  --entrypoint /bin/sh minio-tools -ec \
  'mc alias set local http://minio:9000 "$MINIO_APP_USER" "$MINIO_APP_PASSWORD" >/dev/null && mc mirror --overwrite --remove "/backup/'"$STAMP"'/objects" "local/$MINIO_BUCKET"'

echo "Running migrations and restarting application..."
compose run --rm migrate
compose up -d backend frontend gateway
compose exec -T backend python scripts/reconcile_storage.py

echo "Restore completed. Verify /health/ready and perform an application smoke test."
