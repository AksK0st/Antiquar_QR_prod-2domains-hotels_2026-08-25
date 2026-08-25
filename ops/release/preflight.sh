#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/.env.production"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.prod.yml"}

fail() {
  echo "PRECHECK FAILED: $*" >&2
  exit 1
}

validate_domain() {
  domain=$1
  case "$domain" in
    localhost|127.0.0.1|*.localhost|*.example|*.invalid|*.test|example.com|*.example.com|example.net|*.example.net|example.org|*.example.org)
      fail "production domain must be real: $domain"
      ;;
  esac
  printf '%s\n' "$domain" | awk '
    length($0) > 253 { exit 1 }
    {
      count = split($0, labels, ".")
      if (count < 2) exit 1
      for (i = 1; i <= count; i++) {
        if (length(labels[i]) < 1 || length(labels[i]) > 63) exit 1
        if (labels[i] !~ /^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$/) exit 1
      }
    }
  ' || fail "invalid DNS hostname syntax: $domain"
}

command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is unavailable"
[ -f "$ENV_FILE" ] || fail "missing env file: $ENV_FILE"

# shellcheck source=../lib/env.sh
. "$PROJECT_ROOT/ops/lib/env.sh"
load_compose_env

PRIMARY_DOMAIN=$(require_compose_env PRIMARY_DOMAIN)
SECONDARY_DOMAIN=$(require_compose_env SECONDARY_DOMAIN)
PUBLIC_SITES=$(require_compose_env PUBLIC_SITES)
DEFAULT_HOTEL_NAME=$(require_compose_env DEFAULT_HOTEL_NAME)
RELEASE_TAG=$(require_compose_env RELEASE_TAG)
POSTGRES_PASSWORD=$(require_compose_env POSTGRES_PASSWORD)
MINIO_ROOT_PASSWORD=$(require_compose_env MINIO_ROOT_PASSWORD)
MINIO_APP_PASSWORD=$(require_compose_env MINIO_APP_PASSWORD)
MINIO_BUCKET=$(require_compose_env MINIO_BUCKET)
BACKUP_DIR=$(require_compose_env BACKUP_DIR)

validate_domain "$PRIMARY_DOMAIN"
validate_domain "$SECONDARY_DOMAIN"
[ "$PRIMARY_DOMAIN" != "$SECONDARY_DOMAIN" ] || fail "PRIMARY_DOMAIN and SECONDARY_DOMAIN must differ"

SITE_COUNT=0
PRIMARY_FOUND=0
SECONDARY_FOUND=0
PRIMARY_HOTEL=
SECONDARY_HOTEL=
OLD_IFS=$IFS
IFS=';'
for entry in $PUBLIC_SITES; do
  hostname=${entry%%=*}
  hotel_name=${entry#*=}
  [ "$hostname" != "$entry" ] || fail "PUBLIC_SITES entry must be hostname=hotel name: $entry"
  hostname=$(printf '%s' "$hostname" | awk '{$1=$1; print}')
  hotel_name=$(printf '%s' "$hotel_name" | awk '{$1=$1; print}')
  [ -n "$hostname" ] && [ -n "$hotel_name" ] || fail "PUBLIC_SITES contains an empty hostname or hotel name"
  case "$hotel_name" in
    НАЗВАНИЕ_ВТОРОЙ_ГОСТИНИЦЫ|REPLACE_*|replace_*) fail "PUBLIC_SITES contains a placeholder hotel name" ;;
  esac
  validate_domain "$hostname"
  [ "$hostname" = "$PRIMARY_DOMAIN" ] || [ "$hostname" = "$SECONDARY_DOMAIN" ] || \
    fail "PUBLIC_SITES contains a domain not served by Caddy: $hostname"
  if [ "$hostname" = "$PRIMARY_DOMAIN" ]; then
    PRIMARY_FOUND=1
    PRIMARY_HOTEL=$hotel_name
  fi
  if [ "$hostname" = "$SECONDARY_DOMAIN" ]; then
    SECONDARY_FOUND=1
    SECONDARY_HOTEL=$hotel_name
  fi
  SITE_COUNT=$((SITE_COUNT + 1))
done
IFS=$OLD_IFS
[ "$SITE_COUNT" -eq 2 ] || fail "PUBLIC_SITES must contain exactly two domain-to-hotel mappings"
[ "$PRIMARY_FOUND" = "1" ] || fail "PUBLIC_SITES must include PRIMARY_DOMAIN"
[ "$SECONDARY_FOUND" = "1" ] || fail "PUBLIC_SITES must include SECONDARY_DOMAIN"
[ "$PRIMARY_HOTEL" != "$SECONDARY_HOTEL" ] || fail "the two domains must use different hotel names"
[ "$PRIMARY_HOTEL" = "$DEFAULT_HOTEL_NAME" ] || \
  fail "PRIMARY_DOMAIN must map to DEFAULT_HOTEL_NAME ($DEFAULT_HOTEL_NAME)"

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

echo "Preflight OK: domains=$PRIMARY_DOMAIN,$SECONDARY_DOMAIN release=$RELEASE_TAG backup_dir=$BACKUP_DIR"
