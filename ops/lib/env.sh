# Safe helpers for reading Docker Compose env files without sourcing/eval.
# Caller must define PROJECT_ROOT and ENV_FILE before calling load_compose_env.

load_compose_env() {
  ENV_READER_FILE=${ENV_READER_FILE:-"$PROJECT_ROOT/ops/lib/env-reader.yml"}
  [ -f "$ENV_READER_FILE" ] || {
    echo "Missing env reader compose file: $ENV_READER_FILE" >&2
    return 1
  }
  COMPOSE_ENV_DUMP=$(
    docker compose --env-file "$ENV_FILE" -f "$ENV_READER_FILE" config --environment
  )
}

compose_env_value() {
  key=$1
  printf '%s\n' "$COMPOSE_ENV_DUMP" | awk -v key="$key" '
    index($0, key "=") == 1 {
      print substr($0, length(key) + 2)
      found = 1
      exit
    }
    END { if (!found) exit 1 }
  '
}

require_compose_env() {
  key=$1
  value=$(compose_env_value "$key" 2>/dev/null || true)
  [ -n "$value" ] || {
    echo "$key must be set in $ENV_FILE" >&2
    return 1
  }
  printf '%s' "$value"
}
