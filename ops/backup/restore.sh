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
case "$STAMP" in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z) ;;
  *) echo "Invalid backup stamp: $STAMP" >&2; exit 2 ;;
esac
SRC="$BACKUP_DIR/$STAMP"
[ -f "$SRC/database.dump" ] || { echo "Missing database.dump in $SRC" >&2; exit 1; }
[ -f "$SRC/SHA256SUMS" ] || { echo "Missing SHA256SUMS in $SRC" >&2; exit 1; }
[ -f "$SRC/manifest.txt" ] || { echo "Missing manifest.txt in $SRC" >&2; exit 1; }

(cd "$SRC" && sha256sum -c SHA256SUMS)

manifest_value() {
  key=$1
  awk -F= -v key="$key" '$1 == key { print substr($0, length(key) + 2); found=1; exit } END { if (!found) exit 1 }' "$SRC/manifest.txt"
}

BACKUP_FORMAT=$(manifest_value backup_format)
BACKUP_DB=$(manifest_value postgres_db)
BACKUP_BUCKET=$(manifest_value minio_bucket)
TARGET_DB=$(require_compose_env POSTGRES_DB)
TARGET_BUCKET=$(require_compose_env MINIO_BUCKET)
[ "$BACKUP_FORMAT" = "1" ] || { echo "Unsupported backup format: $BACKUP_FORMAT" >&2; exit 1; }
[ "$BACKUP_DB" = "$TARGET_DB" ] || { echo "Backup database '$BACKUP_DB' does not match target '$TARGET_DB'" >&2; exit 1; }
[ "$BACKUP_BUCKET" = "$TARGET_BUCKET" ] || { echo "Backup bucket '$BACKUP_BUCKET' does not match target '$TARGET_BUCKET'" >&2; exit 1; }

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Stopping traffic and application writes..."
compose stop gateway backend || true

echo "Ensuring stateful services are running..."
compose up -d db minio
POSTGRES_DB=$(require_compose_env POSTGRES_DB)
POSTGRES_USER=$(require_compose_env POSTGRES_USER)
i=0
until compose exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  i=$((i + 1))
  [ "$i" -lt 24 ] || { echo "PostgreSQL did not become ready" >&2; exit 1; }
  sleep 2
done

echo "Bootstrapping object-storage bucket and application credentials..."
compose run --rm --no-deps minio-init

echo "Restoring PostgreSQL..."
compose exec -T db sh -ec \
  'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl --single-transaction' \
  < "$SRC/database.dump"

echo "Restoring object storage..."
BACKUP_DIR="$BACKUP_DIR" compose --profile maintenance run --rm --no-deps \
  --entrypoint /bin/sh minio-tools -ec \
  'until mc alias set local http://minio:9000 "$MINIO_APP_USER" "$MINIO_APP_PASSWORD" >/dev/null 2>&1 && mc ready local >/dev/null 2>&1; do sleep 2; done; mc mirror --overwrite --remove "/backup/'"$STAMP"'/objects" "local/$MINIO_BUCKET"'

echo "Running migrations and restarting application..."
compose run --rm --no-deps migrate
compose up -d backend frontend gateway
compose exec -T backend python scripts/reconcile_storage.py

echo "Restore completed. Verify /health/ready and perform an application smoke test."
