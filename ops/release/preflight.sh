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
BACKUP_DIR=$(require_compose_env BACKUP_DIR)

case "$DOMAIN" in
  localhost|127.0.0.1|*.localhost|*.example|*.invalid|*.test|example.com|*.example.com|example.net|*.example.net|example.org|*.example.org)
    fail "DOMAIN must be a real production hostname"
    ;;
esac

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

RELEASE_TAG="$RELEASE_TAG" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config -q

echo "Preflight OK: domain=$DOMAIN release=$RELEASE_TAG backup_dir=$BACKUP_DIR"
