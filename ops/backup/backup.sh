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
case "$BACKUP_DIR" in /*) ;; *) echo "BACKUP_DIR must be absolute" >&2; exit 1;; esac
mkdir -p "$BACKUP_DIR"
BACKUP_DIR=$(CDPATH= cd -- "$BACKUP_DIR" && pwd)
case "$BACKUP_DIR" in "$PROJECT_ROOT"|"$PROJECT_ROOT"/*) echo "BACKUP_DIR must not live inside the application checkout" >&2; exit 1;; esac

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$BACKUP_DIR/$STAMP"
mkdir -m 700 "$DEST"

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

cleanup_failed() {
  code=$?
  if [ "$code" -ne 0 ]; then
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
printf 'created_at_utc=%s\npostgres_db=%s\nminio_bucket=%s\n' "$STAMP" "$POSTGRES_DB" "$MINIO_BUCKET" > "$DEST/manifest.txt"
(
  cd "$DEST"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)

trap - EXIT INT TERM
echo "Backup complete: $DEST"

if [ "${BACKUP_APPLY_RETENTION:-1}" = "1" ]; then
  python3 "$PROJECT_ROOT/ops/backup/retention.py" "$BACKUP_DIR"
fi
