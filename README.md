# Antiquar QR

QR-каталог исторических предметов: публичный React-интерфейс, административная часть, FastAPI API, PostgreSQL и MinIO.

## Production architecture

```text
Internet
  |
  | HTTPS :443
  v
Caddy
  |-- /api/*, /health/* --> FastAPI --> PostgreSQL
  |                                  \-> MinIO
  \-- /* ----------------> Nginx -> React static build
```

В production наружу публикуется только gateway (`80/443`). PostgreSQL, MinIO, backend и frontend находятся во внутренней Docker network.

QR использует неизменяемый `items.public_id` и URL `/i/<uuid>`. `slug` можно редактировать без поломки уже напечатанного QR.

## Repository layout

- `backend/` — FastAPI, SQLAlchemy, Alembic, image processing, admin auth.
- `frontend/` — React/TypeScript/Vite.
- `ops/caddy/` — production/CI gateway configuration.
- `ops/backup/` — backup, restore and retention.
- `ops/maintenance/` — session/storage cleanup and reconciliation entrypoint.
- `ops/release/` — production preflight, deploy and app-only rollback.
- `ops/systemd/` — example timers for backup and maintenance.
- `docker-compose.yml` — development stack only.
- `docker-compose.prod.yml` — production stack.
- `docker-compose.ci.yml` — isolated release smoke stack.

## Local development

1. Copy `.env.example` to `.env` and replace development credentials.
2. Start the dev stack:

```bash
docker compose up --build
```

Development intentionally uses Vite and Uvicorn hot reload and exposes local service ports. **Do not deploy `docker-compose.yml` to the Internet.**

Useful URLs in development:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`

## Database migrations

Create a migration after changing models:

```bash
docker compose exec backend alembic revision --autogenerate -m "description"
```

Apply migrations locally:

```bash
docker compose exec backend alembic upgrade head
```

Production migrations are a separate one-shot `migrate` service and run before application traffic is switched to the new backend.

## Admin account

Create an admin in a running environment:

```bash
docker compose exec backend python scripts/create_admin.py
```

Reset a password:

```bash
docker compose exec backend python scripts/reset_admin_password.py
```

Production sessions are server-side, the browser receives an `HttpOnly`, `Secure`, `SameSite=Strict`, `__Host-` cookie. Login is rate-limited by IP and username in the application. The production profile currently assumes one backend replica; use a shared limiter (for example Redis or proxy-level limiting) before horizontal scaling.

## Images

Uploads accept JPEG, PNG and WebP. Files are decoded, pixel-limited, EXIF orientation is applied, animated images are rejected, and the image is re-encoded before object storage. The original uploaded bytes are not stored.

If the installation contains images uploaded by an older version, first take a backup and run a dry-run:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml \
  --profile maintenance run --rm resanitize-images
```

Apply only after reviewing the output:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml \
  --profile maintenance run --rm resanitize-images --apply
```

## Production configuration

Copy `.env.production.example` to `.env.production` and replace every placeholder. At minimum set:

- `DOMAIN` — real DNS name pointing to the server;
- `RELEASE_TAG` — immutable release identifier, preferably a Git SHA/tag;
- PostgreSQL credentials;
- MinIO root credentials (bootstrap only);
- MinIO application credentials;
- `BACKUP_DIR` — absolute path on a separate/off-host mounted filesystem.

The backend fails closed in production for HTTP/localhost/reserved example URLs, default/placeholder secrets and weak required secrets.

Run the preflight before every release:

```bash
./ops/release/preflight.sh
```

## Production deploy

Prerequisites:

- DNS already points `DOMAIN` to the host;
- inbound `80/443` are open;
- PostgreSQL/MinIO ports are **not** exposed by the host firewall;
- `.env.production` contains real secrets and a new `RELEASE_TAG`;
- `BACKUP_DIR` is mounted and survives loss of the application host/disk.

Deploy:

```bash
./ops/release/deploy.sh
```

The script:

1. validates environment/compose and verifies that backup storage is mounted on a different filesystem;
2. builds tagged backend/frontend images;
3. starts PostgreSQL and MinIO and waits for PostgreSQL readiness;
4. creates/updates the restricted MinIO app user and bucket policy;
5. briefly stops application traffic and creates a pre-migration PostgreSQL + MinIO backup;
6. applies Alembic migrations;
7. starts backend/frontend/gateway and checks public readiness.

If backup fails before migrations start, the script attempts to restart the previously deployed backend/gateway containers. Once migrations have started, rollback is intentionally manual because schema compatibility must be assessed rather than guessed.

After deployment verify with a physical phone over mobile Internet:

- `https://<domain>/`;
- `https://<domain>/health/ready`;
- one `/i/<public_id>` QR route;
- its images;
- admin login/logout.

## Rollback

Application-only rollback:

```bash
./ops/release/rollback-app.sh <previous-release-tag>
```

This deliberately **does not downgrade PostgreSQL**. Use it only when migrations introduced after the target release are backward-compatible. For incompatible schema changes, restore a tested backup instead of attempting an improvised Alembic downgrade in production.

Keep old application images until the release has been stable long enough to make rollback unnecessary.

## Backup

Create a backup (the directory must already be mounted, writable and on a different filesystem from the checkout):

```bash
BACKUP_DIR=/mnt/offhost/antiquar ./ops/backup/backup.sh
```

The backup contains:

- PostgreSQL custom-format dump;
- MinIO object mirror;
- manifest;
- SHA-256 checksums.

After a successful backup the retention job keeps the seven newest backups plus one backup for each of the previous four ISO weeks by default. Disable automatic pruning for a run with `BACKUP_APPLY_RETENTION=0`.

A Docker volume or ordinary directory on the same application filesystem is **not** considered a backup. The production `BACKUP_DIR` must be a pre-mounted separate/off-host filesystem; the scripts fail closed instead of silently creating a local fallback directory. Application secrets are deliberately **not** copied into these backups and must be backed up separately in a password manager/secret store.

### Restore

A restore is destructive. Stop and verify the target first:

```bash
CONFIRM_RESTORE=YES BACKUP_DIR=/mnt/offhost/antiquar \
  ./ops/backup/restore.sh <YYYYMMDDTHHMMSSZ>
```

Restore verifies checksums, stops application writes, restores PostgreSQL and MinIO, applies current migrations, restarts the app and runs storage reconciliation.

Perform a real restore drill in a disposable environment before relying on backups and repeat it periodically.

## Maintenance

Daily maintenance:

```bash
./ops/maintenance/daily.sh
```

It:

1. removes expired admin sessions;
2. retries durable MinIO cleanup jobs;
3. checks DB ↔ object-storage consistency and primary-image invariants;
4. removes MinIO objects that have had no DB record for at least 24 hours.

The grace period protects uploads that may still be in flight. Any unresolved cleanup/reconciliation problem produces a non-zero exit code so a timer/monitor can alert on it.

Example systemd units are in `ops/systemd/`. They assume checkout path `/opt/antiquar`; edit `WorkingDirectory`, `ExecStart` and environment paths if deployment uses another directory.

## Health checks

- `/health/live` — process is running.
- `/health/ready` — PostgreSQL is queryable and the configured MinIO bucket is accessible.

Caddy and the backend container use readiness before routing traffic.

## Logs and audit

Backend logs are structured JSON and include request ID, method/path/status/duration and relevant security/storage events. Passwords and raw session tokens must never be logged.

Content/admin actions are persisted to `admin_audit_logs`, including login/logout, item/collection mutations and image operations.

Docker production logs rotate (`10 MB × 5` per service by default). Host-level disk monitoring is still required.

## CI / release gate

`.github/workflows/ci.yml` blocks the release path on:

- Python compilation and backend unit tests;
- frontend `npm ci`, lint and production build;
- production/CI compose validation;
- full prod-like stack build;
- migrations on an empty PostgreSQL;
- admin auth/session checks;
- CRUD and optimistic locking;
- image validation/primary-image behavior;
- immutable QR route;
- direct SPA route through the gateway;
- readiness and release smoke tests.

Run what is available locally:

```bash
python -m pytest -q backend/tests
python -m compileall -q backend
```

Frontend validation requires installed dependencies:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

## External production checks that code cannot guarantee

The repository can provide health endpoints, scripts and timers, but the following must be configured outside the application:

- HTTPS DNS/domain ownership and certificate issuance;
- host firewall/security group;
- off-host backup storage;
- uptime checks and alert delivery;
- CPU/RAM/disk monitoring;
- periodic restore drill;
- physical QR test after the real domain is live.

A release is not considered operationally complete until those checks are in place.
