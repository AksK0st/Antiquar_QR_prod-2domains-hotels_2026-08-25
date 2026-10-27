#!/usr/bin/env bash
# Run on the Linux VPS as root. No passwords are embedded here.
set -Eeuo pipefail
umask 077

PROJECT=/opt/antiquar
NEXT=/opt/antiquar-new
PROJECT_NAME=antiquar
DEFAULT_BACKUP=/root/backups/2026-10-05_23-26-43
SNAPSHOT=''
STAGE=''
ROLLBACK_ARMED=0
SERVICES_PAUSED=0
AUTO_ROLLBACK=${AUTO_ROLLBACK:-1}
MAIN_PID=$BASHPID
SCRIPT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")"

die() {
  printf 'ERROR: %s\n' "$*" >&2
  abort_deployment 1 "$LINENO"
}
log() { printf '\n>>> %s\n' "$*"; }
abort_deployment() {
  local rc=$1 line=$2 rollback_rc
  # A failed command substitution reports failure to the main shell; only it recovers.
  if [[ "$BASHPID" != "$MAIN_PID" ]]; then exit "$rc"; fi
  trap - ERR INT TERM
  set +e
  printf '\nДеплой остановлен, код ошибки %s, строка %s.\n' "$rc" "$line" >&2
  if [[ "$ROLLBACK_ARMED" == 1 && "$AUTO_ROLLBACK" == 1 && "${MODE:-}" != rollback && -f "$SNAPSHOT/READY" ]]; then
    printf 'Выполняю автоматический откат из %s...\n' "$SNAPSHOT" >&2
    printf 'failed: rc=%s line=%s\n' "$rc" "$line" > "$SNAPSHOT/FAILED"
    # The rollback child takes the same lock. No recursive automatic rollback.
    flock -u 9
    AUTO_ROLLBACK=0 bash "$SCRIPT_PATH" rollback "$SNAPSHOT" 9>&-
    rollback_rc=$?
    if [[ "$rollback_rc" == 0 ]]; then
      printf 'Автоматический откат завершён и проверен. Деплой новой версии не выполнен.\n' >&2
    else
      printf 'Автоматический откат тоже завершился ошибкой %s. Требуется ручное восстановление.\n' "$rollback_rc" >&2
      printf 'Откат: bash /root/deploy_antiquar.sh rollback %q\n' "$SNAPSHOT" >&2
    fi
  elif [[ "$SERVICES_PAUSED" == 1 && "${MODE:-}" != rollback && "$ROLLBACK_ARMED" == 0 ]]; then
    # Only backup creation has started; production data and code are still unchanged.
    printf 'Возвращаю прежние сервисы после ошибки создания резервной копии...\n' >&2
    docker start "$MINIO_ID" >/dev/null && compose_at "$PROJECT" up -d --no-deps backend frontend gateway
    if [[ "$?" != 0 ]]; then printf 'Не удалось запустить прежние сервисы; проверь контейнеры.\n' >&2; fi
  elif [[ -n "$SNAPSHOT" && -f "$SNAPSHOT/READY" ]]; then
    printf 'Точка отката: %s\nОткат: bash /root/deploy_antiquar.sh rollback %q\n' "$SNAPSHOT" "$SNAPSHOT" >&2
  else
    printf 'Полная точка отката ещё не создана. Не запускайте восстановление из неполных файлов.\n' >&2
  fi
  exit "$rc"
}
on_error() { local rc=$?; abort_deployment "$rc" "$1"; }
trap 'on_error "$LINENO"' ERR
trap 'abort_deployment 130 "$LINENO"' INT
trap 'abort_deployment 143 "$LINENO"' TERM

usage() {
  cat <<'USAGE'
Deploy latest code and REPLACE database and MinIO data:
  bash /root/deploy_antiquar.sh deploy [backup-directory]
Deploy code ONLY, keeping existing database and photos:
  bash /root/deploy_antiquar.sh code-only
Continue this deployment AFTER MinIO has been repaired (replace PostgreSQL only):
  bash /root/deploy_antiquar.sh resume [backup-directory]
Continue AFTER PostgreSQL has been restored (keep existing database and MinIO):
  bash /root/deploy_antiquar.sh start
Verify an already running version without restarting or restoring data:
  bash /root/deploy_antiquar.sh verify
Restore code, database and MinIO from a deployment snapshot:
  bash /root/deploy_antiquar.sh rollback /root/antiquar-rollbacks/<stamp>
USAGE
}

MODE=${1:---help}
case "$MODE" in
  -h|--help) usage; exit 0 ;;
  deploy|code-only|rollback|resume|start|verify) ;;
  *) usage; die 'Неизвестный режим' ;;
esac
[[ "$EUID" == 0 ]] || die 'Запускай скрипт под root на VPS'
for cmd in docker gzip tar python3 flock timeout curl sha256sum; do
  command -v "$cmd" >/dev/null || die "Не найдена команда: $cmd"
done
docker compose version >/dev/null
exec 9>/root/.antiquar-deploy.lock
flock -n 9 || die 'Другой деплой уже выполняется'
# Compose reads the intended tag from each version's .env.production.
unset RELEASE_TAG

compose_at() {
  local directory=$1
  shift
  docker compose -p "$PROJECT_NAME" --project-directory "$directory" \
    --env-file "$directory/.env.production" -f "$directory/docker-compose.prod.yml" "$@"
}

container_id() {
  local service=$1
  docker ps -aq --filter "label=com.docker.compose.project=$PROJECT_NAME" \
    --filter "label=com.docker.compose.service=$service"
}

DB_ID=$(container_id db)
MINIO_ID=$(container_id minio)
[[ -n "$DB_ID" && "$DB_ID" != *$'\n'* ]] || die 'Ожидался один контейнер antiquar/db'
[[ -n "$MINIO_ID" && "$MINIO_ID" != *$'\n'* ]] || die 'Ожидался один контейнер antiquar/minio'
MINIO_VOLUME=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}' "$MINIO_ID")
[[ -n "$MINIO_VOLUME" ]] || die 'MinIO /data должен быть подключён через Docker volume'
MINIO_PATH=$(docker volume inspect -f '{{.Mountpoint}}' "$MINIO_VOLUME")
[[ -d "$MINIO_PATH" && "$MINIO_PATH" == /* && "$MINIO_PATH" != / ]] || die 'Некорректный путь MinIO volume'

wait_healthy() {
  local service=$1 id state health
  for ((attempt=0; attempt<90; attempt++)); do
    id=$(container_id "$service")
    if [[ -n "$id" && "$id" != *$'\n'* ]]; then
      state=$(docker inspect -f '{{.State.Status}}' "$id")
      health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id")
      [[ "$state" == running && "$health" == healthy ]] && return 0
      [[ "$state" == exited || "$state" == dead ]] && die "Контейнер $service остановился"
    fi
    sleep 2
  done
  die "$service не стал healthy за 180 секунд"
}

validate_archive() {
  python3 - "$1" <<'PY'
import sys, tarfile
from pathlib import PurePosixPath
with tarfile.open(sys.argv[1], 'r:gz') as archive:
    count = 0
    for member in archive:
        path = PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts:
            raise SystemExit('Unsafe archive path: ' + member.name)
        if not (member.isfile() or member.isdir()):
            raise SystemExit('Unsupported archive member: ' + member.name)
        count += member.isfile()
    if not count:
        raise SystemExit('Empty MinIO archive')
PY
}

prepare_data() {
  local source=$1
  [[ -s "$source/postgres.sql.gz" && -s "$source/minio.tar.gz" ]] || die "Нет бэкапов в $source"
  gzip -t "$source/postgres.sql.gz"
  validate_archive "$source/minio.tar.gz"
  STAGE=$(mktemp -d /root/antiquar-restore.XXXXXX)
  gzip -dc "$source/postgres.sql.gz" > "$STAGE/postgres.sql"
  [[ -s "$STAGE/postgres.sql" ]] || die 'SQL-бэкап пуст'
  mkdir "$STAGE/minio-data"
  tar --numeric-owner -xzf "$source/minio.tar.gz" -C "$STAGE/minio-data"
  [[ -s "$STAGE/minio-data/.minio.sys/format.json" ]] || die 'Архив не является бэкапом всего MinIO /data'
}

restore_data() {
  log 'Останавливаю MinIO и заменяю его данные'
  docker stop "$MINIO_ID" >/dev/null
  # The path is obtained and validated through Docker's existing volume mount.
  find "$MINIO_PATH" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
  cp -a "$STAGE/minio-data/." "$MINIO_PATH/"
  docker start "$MINIO_ID" >/dev/null
  wait_healthy minio
  restore_postgres
}

restore_postgres() {
  log 'Заменяю PostgreSQL данными из бэкапа'
  compose_at "$PROJECT" exec -T db sh -ec \
    'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -v target_db="$POSTGRES_DB" -v target_owner="$POSTGRES_USER"' <<'SQL'
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname = :'target_db' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS :"target_db";
CREATE DATABASE :"target_db" OWNER :"target_owner";
SQL
  compose_at "$PROJECT" exec -T db sh -ec \
    'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    < "$STAGE/postgres.sql" > "$STAGE/postgres-restore.log"
}

start_application() {
  wait_healthy db
  wait_healthy minio
  log 'Настраиваю доступ приложения к MinIO и выполняю миграции'
  local bucket policy_file
  # Override the scalar Compose command with explicit shell arguments.
  bucket=$(compose_at "$PROJECT" run --rm --no-deps --entrypoint /bin/sh minio-init \
    -ec 'printf "%s" "$MINIO_BUCKET"')
  [[ "$bucket" =~ ^[a-z0-9][a-z0-9.-]+[a-z0-9]$ ]] || die 'Некорректное имя bucket'
  policy_file=$(mktemp /root/antiquar-app-policy.XXXXXX)
  python3 - "$PROJECT/ops/minio/app-policy.template.json" "$policy_file" "$bucket" <<'PY'
import json, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text().replace('__BUCKET__', sys.argv[3])
json.loads(text)
Path(sys.argv[2]).write_text(text)
PY
  chmod 644 "$policy_file"
  # Render the policy with Python on the host; no sed is required in the mc image.
  timeout 180 docker compose -p "$PROJECT_NAME" --project-directory "$PROJECT" \
    --env-file "$PROJECT/.env.production" -f "$PROJECT/docker-compose.prod.yml" \
    run --rm --no-deps --entrypoint /bin/sh \
    -v "$policy_file:/tmp/antiquar-app-policy.json:ro" minio-init -ec '
      mc --config-dir /tmp/mc-init alias set --api S3v4 local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
      mc --config-dir /tmp/mc-init ready local >/dev/null
      mc --config-dir /tmp/mc-init mb --ignore-existing "local/$MINIO_BUCKET"
      mc --config-dir /tmp/mc-init admin user add local "$MINIO_APP_USER" "$MINIO_APP_PASSWORD"
      mc --config-dir /tmp/mc-init admin policy create local antiquar-app /tmp/antiquar-app-policy.json
      mc --config-dir /tmp/mc-init admin policy attach local antiquar-app --user "$MINIO_APP_USER"
    '
  rm -f -- "$policy_file"
  compose_at "$PROJECT" run --rm --no-deps migrate
  log 'Запускаю backend и frontend'
  compose_at "$PROJECT" up -d --force-recreate --no-deps backend frontend
  wait_healthy backend
  wait_healthy frontend
  log 'Запускаю gateway'
  compose_at "$PROJECT" up -d --force-recreate --no-deps gateway
  verify_application
}

verify_application() {
  # Uses the project's non-destructive reconciliation command, no delete-orphans.
  compose_at "$PROJECT" exec -T -e PYTHONPATH=/backend backend python scripts/reconcile_storage.py
  local domains domain
  domains=$(compose_at "$PROJECT" exec -T gateway sh -ec 'printf "%s\n" "$PRIMARY_DOMAIN" "$SECONDARY_DOMAIN"')
  while IFS= read -r domain; do
    [[ -n "$domain" ]] || continue
    curl --fail --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused \
      --max-time 20 --resolve "$domain:443:127.0.0.1" "https://$domain/" -o /dev/null
    printf 'HTTPS OK: %s\n' "$domain"
  done <<< "$domains"
  compose_at "$PROJECT" ps
}

if [[ "$MODE" == verify ]]; then
  [[ -f "$PROJECT/.env.production" ]] || die 'Нет серверного .env.production'
  STAMP=$(sed -n 's/^RELEASE_TAG=deploy-//p' "$PROJECT/.env.production")
  [[ "$STAMP" =~ ^[0-9]{8}-[0-9]{6}$ ]] || die 'Не найдена версия текущего деплоя'
  SNAPSHOT="/root/antiquar-rollbacks/$STAMP"
  wait_healthy db
  wait_healthy minio
  wait_healthy backend
  wait_healthy frontend
  verify_application
  if [[ -f "$SNAPSHOT/READY" ]]; then printf 'committed\n' > "$SNAPSHOT/COMMITTED"; fi
  log 'Работающая версия проверена. Деплой завершён.'
  exit 0
fi

if [[ "$MODE" == start ]]; then
  [[ -f "$PROJECT/.env.production" ]] || die 'Нет серверного .env.production'
  STAMP=$(sed -n 's/^RELEASE_TAG=deploy-//p' "$PROJECT/.env.production")
  [[ "$STAMP" =~ ^[0-9]{8}-[0-9]{6}$ ]] || die 'Не найдена версия текущего деплоя'
  SNAPSHOT="/root/antiquar-rollbacks/$STAMP"
  [[ -f "$SNAPSHOT/READY" ]] || die 'Нет полной точки отката текущего деплоя'
  [[ ! -f "$SNAPSHOT/COMMITTED" ]] || die 'Этот деплой уже завершён; для следующего обновления используй code-only'
  compose_at "$PROJECT" config -q
  ROLLBACK_ARMED=1
  compose_at "$PROJECT" stop gateway backend frontend
  start_application
  printf 'committed\n' > "$SNAPSHOT/COMMITTED"
  ROLLBACK_ARMED=0
  SERVICES_PAUSED=0
  log 'Деплой завершён'
  printf 'Откат: bash /root/deploy_antiquar.sh rollback %q\n' "$SNAPSHOT"
  exit 0
fi

if [[ "$MODE" == resume ]]; then
  [[ -f "$PROJECT/.env.production" ]] || die 'Нет серверного .env.production'
  STAMP=$(sed -n 's/^RELEASE_TAG=deploy-//p' "$PROJECT/.env.production")
  [[ "$STAMP" =~ ^[0-9]{8}-[0-9]{6}$ ]] || die 'Не найдена версия текущего деплоя'
  SNAPSHOT="/root/antiquar-rollbacks/$STAMP"
  [[ -f "$SNAPSHOT/READY" ]] || die 'Нет полной точки отката текущего деплоя'
  [[ ! -f "$SNAPSHOT/COMMITTED" ]] || die 'Этот деплой уже завершён; восстановление через resume запрещено'
  (cd "$SNAPSHOT" && sha256sum -c SHA256SUMS)
  SOURCE=${2:-$DEFAULT_BACKUP}
  [[ -s "$SOURCE/postgres.sql.gz" ]] || die 'Не найден PostgreSQL-бэкап'
  gzip -t "$SOURCE/postgres.sql.gz"
  STAGE=$(mktemp -d /root/antiquar-resume.XXXXXX)
  gzip -dc "$SOURCE/postgres.sql.gz" > "$STAGE/postgres.sql"
  [[ -s "$STAGE/postgres.sql" ]] || die 'SQL-бэкап пуст'
  compose_at "$PROJECT" config -q
  wait_healthy minio
  wait_healthy db
  log 'Продолжаю деплой после исправления MinIO'
  ROLLBACK_ARMED=1
  compose_at "$PROJECT" stop gateway backend frontend
  restore_postgres
  start_application
  printf 'committed\n' > "$SNAPSHOT/COMMITTED"
  ROLLBACK_ARMED=0
  SERVICES_PAUSED=0
  rm -rf -- "$STAGE"
  log 'Деплой завершён'
  printf 'Откат: bash /root/deploy_antiquar.sh rollback %q\n' "$SNAPSHOT"
  exit 0
fi

if [[ "$MODE" == rollback ]]; then
  SNAPSHOT=${2:?Укажи папку точки отката}
  [[ -f "$SNAPSHOT/READY" ]] || die 'Точка отката неполная'
  (cd "$SNAPSHOT" && sha256sum -c SHA256SUMS)
  [[ -f "$SNAPSHOT/old-project-path" ]] || die 'Нет пути предыдущего кода'
  OLD_PROJECT=$(cat "$SNAPSHOT/old-project-path")
  [[ "$OLD_PROJECT" == /opt/antiquar-before-* ]] || die 'Некорректный путь предыдущего кода'
  if [[ ! -d "$OLD_PROJECT" ]]; then
    cmp -s "$SNAPSHOT/env.production" "$PROJECT/.env.production" || die 'Предыдущий код этой точки отката не найден'
  fi
  prepare_data "$SNAPSHOT"
  log 'Останавливаю приложение для отката'
  if [[ -f "$PROJECT/docker-compose.prod.yml" ]]; then
    compose_at "$PROJECT" stop gateway backend frontend
  else
    compose_at "$OLD_PROJECT" stop gateway backend frontend
  fi
  if [[ -d "$OLD_PROJECT" ]]; then
    mv "$PROJECT" "/opt/antiquar-failed-$(date +%Y%m%d-%H%M%S)"
    mv "$OLD_PROJECT" "$PROJECT"
  fi
  # Restore original immutable image IDs to the old tags, including shared tags.
  while IFS=$'\t' read -r image_ref image_id; do
    docker image tag "$image_id" "$image_ref"
  done < "$SNAPSHOT/application-images.tsv"
  restore_data
  start_application
  rm -rf -- "$STAGE"
  printf 'rolled back\n' > "$SNAPSHOT/ROLLED_BACK"
  log 'Откат выполнен. Проверь вход в админку и фотографии карточек.'
  exit 0
fi

[[ -f "$PROJECT/.env.production" && -f "$PROJECT/docker-compose.prod.yml" ]] || die 'Не найден текущий проект'
[[ -f "$NEXT/docker-compose.prod.yml" && -d "$NEXT/backend" && -d "$NEXT/frontend" ]] || die 'Нет распакованного проекта /opt/antiquar-new'
[[ -f "$NEXT/backend/scripts/reconcile_storage.py" ]] || die 'В новой версии нет reconcile_storage.py'
STAMP=$(date +%Y%m%d-%H%M%S)
OLD_PROJECT="/opt/antiquar-before-$STAMP"
SNAPSHOT="/root/antiquar-rollbacks/$STAMP"
[[ ! -e "$OLD_PROJECT" && ! -e "$SNAPSHOT" ]] || die 'Папка версии уже существует'

log 'Сохраняю серверные настройки в новой версии'
cp -p "$PROJECT/.env.production" "$NEXT/.env.production"
chmod 600 "$NEXT/.env.production"
python3 - "$NEXT/.env.production" "deploy-$STAMP" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
lines = path.read_text().splitlines()
lines = [line for line in lines if not line.lstrip().startswith(('RELEASE_TAG=', 'export RELEASE_TAG='))]
lines.append('RELEASE_TAG=' + sys.argv[2])
path.write_text('\n'.join(lines) + '\n')
PY
# Ensure a caller's environment cannot accidentally override the saved tag.
unset RELEASE_TAG
compose_at "$NEXT" config -q
compose_at "$PROJECT" config -q

if [[ "$MODE" == deploy ]]; then
  log 'Проверяю и распаковываю загруженные бэкапы до остановки сайта'
  prepare_data "${2:-$DEFAULT_BACKUP}"
fi
log 'Собираю новые backend/frontend, пока старая версия работает'
compose_at "$NEXT" build backend frontend

mkdir -p "$SNAPSHOT"
cp -p "$PROJECT/.env.production" "$SNAPSHOT/env.production"
printf '%s\n' "$OLD_PROJECT" > "$SNAPSHOT/old-project-path"
for service in backend frontend; do
  id=$(container_id "$service")
  [[ -n "$id" && "$id" != *$'\n'* ]] || die "Не найден текущий $service"
  docker inspect -f '{{.Config.Image}}{{printf "\t"}}{{.Image}}' "$id" >> "$SNAPSHOT/application-images.tsv"
done

log 'Останавливаю запись и создаю резервную копию текущих данных'
SERVICES_PAUSED=1
compose_at "$PROJECT" stop gateway backend frontend
compose_at "$PROJECT" exec -T db sh -ec \
  'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl' \
  | gzip > "$SNAPSHOT/postgres.sql.gz"
gzip -t "$SNAPSHOT/postgres.sql.gz"
docker stop "$MINIO_ID" >/dev/null
tar -czf "$SNAPSHOT/minio.tar.gz" -C "$MINIO_PATH" .
validate_archive "$SNAPSHOT/minio.tar.gz"
docker start "$MINIO_ID" >/dev/null
wait_healthy minio
(cd "$SNAPSHOT" && sha256sum postgres.sql.gz minio.tar.gz > SHA256SUMS)
printf 'complete\n' > "$SNAPSHOT/READY"
ROLLBACK_ARMED=1

log 'Переключаю код на новую версию'
mv "$PROJECT" "$OLD_PROJECT"
mv "$NEXT" "$PROJECT"
if [[ "$MODE" == deploy ]]; then
  restore_data
fi
start_application
printf 'committed\n' > "$SNAPSHOT/COMMITTED"
ROLLBACK_ARMED=0
SERVICES_PAUSED=0
if [[ -n "$STAGE" ]]; then
  rm -rf -- "$STAGE"
fi
log 'Деплой завершён'
printf 'Точка отката: %s\n' "$SNAPSHOT"
printf 'Откат: bash /root/deploy_antiquar.sh rollback %q\n' "$SNAPSHOT"
printf 'Проверь вход в админку, карточки и фотографии обеих гостиниц.\n'
