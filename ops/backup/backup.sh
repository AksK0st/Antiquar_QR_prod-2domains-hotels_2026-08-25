#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/.env.production"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.prod.yml"}

[ -f "$ENV_FILE" ] || { echo "Missing env file: $ENV_FILE" >&2; exit 1; }
# shellcheck source=../lib/env.sh
. "$PROJECT_ROOT/ops/lib/env.sh"
load_compose_env

BACKUP_DIR=$(require_compose_env BACKUP_DIR)
POSTGRES_DB=$(require_compose_env POSTGRES_DB)
POSTGRES_USER=$(require_compose_env POSTGRES_USER)
MINIO_BUCKET=$(require_compose_env MINIO_BUCKET)
RELEASE_TAG=$(compose_env_value RELEASE_TAG 2>/dev/null || printf 'unknown')
BACKUP_APPLY_RETENTION=$(compose_env_value BACKUP_APPLY_RETENTION 2>/dev/null || printf '1')
BACKUP_QUIESCE_WRITES=$(compose_env_value BACKUP_QUIESCE_WRITES 2>/dev/null || printf '1')
case "$BACKUP_APPLY_RETENTION" in 0|1) ;; *) echo "BACKUP_APPLY_RETENTION must be 0 or 1" >&2; exit 1;; esac
case "$BACKUP_QUIESCE_WRITES" in 0|1) ;; *) echo "BACKUP_QUIESCE_WRITES must be 0 or 1" >&2; exit 1;; esac
case "$BACKUP_DIR" in /*) ;; *) echo "BACKUP_DIR must be absolute" >&2; exit 1;; esac
[ -d "$BACKUP_DIR" ] || { echo "BACKUP_DIR must already exist and be mounted: $BACKUP_DIR" >&2; exit 1; }
[ -w "$BACKUP_DIR" ] || { echo "BACKUP_DIR is not writable: $BACKUP_DIR" >&2; exit 1; }
BACKUP_DIR=$(CDPATH= cd -- "$BACKUP_DIR" && pwd)
case "$BACKUP_DIR" in "$PROJECT_ROOT"|"$PROJECT_ROOT"/*) echo "BACKUP_DIR must not live inside the application checkout" >&2; exit 1;; esac
PROJECT_FS=$(df -P "$PROJECT_ROOT" | awk 'NR==2 {print $1}')
BACKUP_FS=$(df -P "$BACKUP_DIR" | awk 'NR==2 {print $1}')
[ -n "$PROJECT_FS" ] && [ -n "$BACKUP_FS" ] || { echo "Could not determine backup filesystem" >&2; exit 1; }
[ "$PROJECT_FS" != "$BACKUP_FS" ] || { echo "BACKUP_DIR must be on a different filesystem from the application checkout" >&2; exit 1; }

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$BACKUP_DIR/$STAMP"
mkdir -m 700 "$DEST"

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

BACKEND_WAS_RUNNING=0
GATEWAY_WAS_RUNNING=0
if [ "$BACKUP_QUIESCE_WRITES" = "1" ]; then
  RUNNING_SERVICES=$(compose ps --status running --services 2>/dev/null || true)
  printf '%s\n' "$RUNNING_SERVICES" | grep -qx backend && BACKEND_WAS_RUNNING=1 || true
  printf '%s\n' "$RUNNING_SERVICES" | grep -qx gateway && GATEWAY_WAS_RUNNING=1 || true

  if [ "$BACKEND_WAS_RUNNING" = "1" ] || [ "$GATEWAY_WAS_RUNNING" = "1" ]; then
    echo "Quiescing application writes for a consistent DB/object snapshot..."
    compose stop gateway backend >/dev/null
  fi
fi

restore_services() {
  if [ "$BACKEND_WAS_RUNNING" = "1" ]; then
    compose start backend >/dev/null
  fi
  if [ "$GATEWAY_WAS_RUNNING" = "1" ]; then
    compose start gateway >/dev/null
  fi
}

restore_services_best_effort() {
  restore_services >/dev/null 2>&1 || echo "WARNING: failed to restart application after backup attempt" >&2
}

BACKUP_COMPLETE=0
cleanup_failed() {
  code=$?
  restore_services_best_effort
  if [ "$code" -ne 0 ] && [ "$BACKUP_COMPLETE" = "0" ]; then
    echo "Backup failed; removing incomplete backup: $DEST" >&2
    rm -rf "$DEST"
  fi
  exit "$code"
}
trap cleanup_failed EXIT INT TERM

echo "[1/3] PostgreSQL dump"
compose exec -T db sh -ec \
  'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$DEST/database.dump"

echo "[2/3] Object storage mirror"
BACKUP_DIR="$BACKUP_DIR" compose --profile maintenance run --rm --no-deps \
  --entrypoint /bin/sh minio-tools -ec \
  'mc alias set local http://minio:9000 "$MINIO_APP_USER" "$MINIO_APP_PASSWORD" >/dev/null && mc mirror --overwrite "local/$MINIO_BUCKET" "/backup/'"$STAMP"'/objects"'

echo "[3/3] Manifest and checksums"
DB_REVISION=$(
  compose exec -T db sh -ec \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"' \
    2>/dev/null || printf 'uninitialized'
)
printf 'backup_format=1\ncreated_at_utc=%s\nconfigured_release_tag=%s\ndatabase_revision=%s\npostgres_db=%s\nminio_bucket=%s\n' \
  "$STAMP" "$RELEASE_TAG" "$DB_REVISION" "$POSTGRES_DB" "$MINIO_BUCKET" > "$DEST/manifest.txt"
(
  cd "$DEST"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)
BACKUP_COMPLETE=1

restore_services
trap - EXIT INT TERM
echo "Backup complete: $DEST"

if [ "$BACKUP_APPLY_RETENTION" = "1" ]; then
  python3 "$PROJECT_ROOT/ops/backup/retention.py" "$BACKUP_DIR"
fi
