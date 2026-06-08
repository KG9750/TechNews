# Briefing Host Deployment

The MVP runs as one Python service on an always-on Briefing Host through Docker Compose. Keep real `.env` files, archive paths, sync targets, and credential values out of git and out of GitHub comments.

## Host Setup

1. Install Docker with Docker Compose.
2. Create two host directories:
   - one archive root for `ARCHIVE_LOCAL_ROOT`
   - one mounted NAS/cloud sync target for `ARCHIVE_SYNC_TARGET`
3. Copy `.env.example` to `.env` on the Briefing Host and fill every required value there.
4. Generate `ADMIN_PASSWORD_HASH` with the Operations Console password helper:

```bash
python - <<'PY'
import os
from getpass import getpass
from technews_briefing.operations_console import hash_admin_password

password = getpass("Admin password: ")
salt = os.urandom(16)
print(hash_admin_password(password, salt=salt))
PY
```

## Compose Runtime

Validate the resolved Compose file before starting the service:

```bash
docker compose config --quiet
```

Start or refresh the service:

```bash
docker compose up -d --build
```

Run the redacted deployment health check:

```bash
docker compose exec technews-briefing python -m technews_briefing.deployment health --require-configured
```

The service also exposes a redacted JSON health endpoint on the host loopback interface:

```bash
curl http://127.0.0.1:8080/healthz
```

The health check reports scheduler configuration, Feishu/model/admin configuration presence, archive root writability, sync target writability, and SQLite data-store initialization. It redacts secret values, recipient ids, archive paths, and sync targets.

## Volumes

`docker-compose.yml` mounts:

- `technews-data` at `/var/lib/technews/data` for the SQLite operations store.
- `ARCHIVE_LOCAL_ROOT` as a bind mount at the same path inside the container.
- `ARCHIVE_SYNC_TARGET` as a bind mount at the same path inside the container.

Using the same archive and sync paths inside the container keeps Archive Package metadata labels consistent with the local-first archive contract while still keeping real host paths outside tracked files.

## Backup And Sync Responsibilities

The Briefing Administrator owns:

- backing up the `technews-data` Docker volume
- backing up `ARCHIVE_LOCAL_ROOT`
- ensuring `ARCHIVE_SYNC_TARGET` remains mounted and writable before daily runs
- monitoring Docker health status and host disk capacity
- rotating Feishu, model, admin, and session secrets if exposure is suspected

Cloud or NAS sync tooling remains host-level infrastructure for the MVP. The app records archive write and sync status, but it does not replace host backup policy.
