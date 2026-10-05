#!/usr/bin/env bash
# Place this script in the project root, beside the Compose file.
# Usage: bash backup.sh [Docker Compose options]
# Example: bash backup.sh --env-file .env.production -f docker-compose.prod.yml
# Do not edit items or upload/delete media while the backup is running.
# MinIO data is expected at /data inside the minio container.

set -Eeuo pipefail

trap 'printf "ERROR: Backup stopped at line %s. Incomplete files may remain.\n" "$LINENO" >&2' ERR

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
compose=(docker compose "$@")

for command_name in docker gzip tar; do
  command -v "$command_name" > /dev/null || {
    printf 'ERROR: Required command is missing: %s\n' "$command_name" >&2
    exit 1
  }
done

# Resolve the running MinIO container before writing any backup files.
minio_id="$("${compose[@]}" ps -q minio)"
if [[ -z "$minio_id" || "$minio_id" == *$'\n'* ]]; then
  printf 'ERROR: Expected one running minio container. Check Compose options.\n' >&2
  exit 1
fi

mkdir -p backups
backup_dir="backups/$(date +%F_%H-%M-%S)"
mkdir -- "$backup_dir"
archive_path="$backup_dir.tar.gz"

printf '[1/5] Backing up PostgreSQL...\n'
"${compose[@]}" exec -T db sh -c \
  'pg_dump -U "${POSTGRES_USER:?POSTGRES_USER is not set}" -d "${POSTGRES_DB:?POSTGRES_DB is not set}" --no-owner --no-acl' \
  | gzip > "$backup_dir/postgres.sql.gz"
gzip -t "$backup_dir/postgres.sql.gz"

printf '[2/5] Copying MinIO data...\n'
docker cp "$minio_id:/data/." "$backup_dir/minio-data"

printf '[3/5] Packing and checking MinIO data...\n'
tar -czf "$backup_dir/minio.tar.gz" -C "$backup_dir/minio-data" .
tar -tzf "$backup_dir/minio.tar.gz" > /dev/null

printf '[4/5] Packing both backups...\n'
# Keep the incomplete archive under a separate name until verification passes.
tar -czf "$archive_path.partial" -C "$backup_dir" postgres.sql.gz minio.tar.gz
tar -tzf "$archive_path.partial" > /dev/null
mv -- "$archive_path.partial" "$archive_path"

printf '[5/5] Removing the temporary unpacked MinIO copy...\n'
rm -r -- "$backup_dir/minio-data"

printf '\nSUCCESS: %s/%s\n' "$PWD" "$archive_path"
ls -lh -- "$archive_path"
printf 'Download the final archive to another computer.\n'
