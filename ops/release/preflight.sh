#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/.env.production"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.prod.yml"}

fail() {
  echo "PRECHECK FAILED: $*" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is unavailable"
[ -f "$ENV_FILE" ] || fail "missing env file: $ENV_FILE"

# shellcheck source=../lib/env.sh
. "$PROJECT_ROOT/ops/lib/env.sh"
load_compose_env

DOMAIN=$(require_compose_env DOMAIN)
RELEASE_TAG=$(require_compose_env RELEASE_TAG)
POSTGRES_PASSWORD=$(require_compose_env POSTGRES_PASSWORD)
MINIO_ROOT_PASSWORD=$(require_compose_env MINIO_ROOT_PASSWORD)
MINIO_APP_PASSWORD=$(require_compose_env MINIO_APP_PASSWORD)
MINIO_BUCKET=$(require_compose_env MINIO_BUCKET)
BACKUP_DIR=$(require_compose_env BACKUP_DIR)

case "$DOMAIN" in
  localhost|127.0.0.1|*.localhost|*.example|*.invalid|*.test|example.com|*.example.com|example.net|*.example.net|example.org|*.example.org)
    fail "DOMAIN must be a real production hostname"
    ;;
esac
printf '%s\n' "$DOMAIN" | awk '
  length($0) > 253 { exit 1 }
  {
    count = split($0, labels, ".")
    if (count < 2) exit 1
    for (i = 1; i <= count; i++) {
      if (length(labels[i]) < 1 || length(labels[i]) > 63) exit 1
      if (labels[i] !~ /^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$/) exit 1
    }
  }
' || fail "DOMAIN has invalid DNS hostname syntax"

case "$MINIO_BUCKET" in
  *[!a-z0-9.-]*|.*|*.) fail "MINIO_BUCKET must use lowercase S3-compatible naming" ;;
esac
[ "${#MINIO_BUCKET}" -ge 3 ] && [ "${#MINIO_BUCKET}" -le 63 ] || fail "MINIO_BUCKET must be 3..63 characters"
case "$MINIO_BUCKET" in *..*|*-.*|*.-*) fail "MINIO_BUCKET has invalid dot/hyphen placement" ;; esac

case "$RELEASE_TAG" in
  *[!A-Za-z0-9._-]*|'') fail "RELEASE_TAG may contain only A-Z a-z 0-9 . _ -" ;;
esac

for value in "$POSTGRES_PASSWORD" "$MINIO_ROOT_PASSWORD" "$MINIO_APP_PASSWORD"; do
  normalized=$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')
  case "$normalized" in
    change_me|changeme|password|secret|minioadmin|replace_with_*|replace-me*|replace_me*|example_*|example-*)
      fail "placeholder/default secret detected"
      ;;
  esac
  [ "${#value}" -ge 16 ] || fail "production secrets must be at least 16 characters"
done

case "$BACKUP_DIR" in
  /*) ;;
  *) fail "BACKUP_DIR must be an absolute path" ;;
esac
case "$BACKUP_DIR" in
  "$PROJECT_ROOT"|"$PROJECT_ROOT"/*) fail "BACKUP_DIR must not be inside the application checkout" ;;
esac
[ -d "$BACKUP_DIR" ] || fail "BACKUP_DIR must already exist; mount off-host storage before deploy"
[ -w "$BACKUP_DIR" ] || fail "BACKUP_DIR must be writable"
PROJECT_FS=$(df -P "$PROJECT_ROOT" | awk 'NR==2 {print $1}')
BACKUP_FS=$(df -P "$BACKUP_DIR" | awk 'NR==2 {print $1}')
[ -n "$PROJECT_FS" ] && [ -n "$BACKUP_FS" ] || fail "could not determine backup filesystem"
[ "$PROJECT_FS" != "$BACKUP_FS" ] || fail "BACKUP_DIR must be on a different filesystem from the application checkout"

RELEASE_TAG="$RELEASE_TAG" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config -q

echo "Preflight OK: domain=$DOMAIN release=$RELEASE_TAG backup_dir=$BACKUP_DIR"
