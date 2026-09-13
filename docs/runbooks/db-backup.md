# Database Backup & Restore

## Backup

Run `scripts/db-backup.sh` to create a compressed pg_dump of the database.

The script auto-detects the runtime: if `pg_dump` is on the host it runs natively;
otherwise it falls back to `docker compose exec` against the running postgres container.

```bash
# With defaults (DB_NAME=app_db, DB_USER=username, BACKUP_DIR=./backups)
./scripts/db-backup.sh

# Override connection details (native pg_dump path)
DB_HOST=localhost DB_PORT=5432 DB_NAME=app_db \
DB_USER=username DB_PASSWORD=secret BACKUP_DIR=/var/backups/app \
./scripts/db-backup.sh

# Override the Docker Compose service name (default: postgres)
COMPOSE_SERVICE=postgres-prod ./scripts/db-backup.sh
```

Backups are written as `<DB_NAME>_<timestamp>.sql.gz` in `BACKUP_DIR` (default `./backups`).
Files older than `KEEP_DAYS` (default 30) are pruned automatically.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_NAME` | `app_db` | Database name |
| `DB_USER` | `username` | Database user (matches `DB_USER` in `backend/.env`) |
| `DB_PASSWORD` | _(empty)_ | Database password |
| `DB_HOST` | `localhost` | Host (native pg_dump only) |
| `DB_PORT` | `5432` | Port (native pg_dump only) |
| `BACKUP_DIR` | `./backups` | Output directory |
| `KEEP_DAYS` | `30` | Retention window in days |
| `COMPOSE_SERVICE` | `postgres` | Docker Compose service name (Docker fallback only) |

### Recommended schedule

Run daily via cron or a managed scheduler. Example crontab entry:

```
0 2 * * * DB_PASSWORD=secret BACKUP_DIR=/var/backups/app \
  /opt/app/scripts/db-backup.sh >> /var/log/app-backup.log 2>&1
```

## Restore

```bash
./scripts/db-restore.sh backups/app_db_20260514T020000Z.sql.gz
```

The script prompts for confirmation before overwriting the target database.
Like the backup script it auto-detects Docker vs native `psql`.

## Verify a backup

```bash
# List contents without restoring
gunzip -c backups/app_db_20260514T020000Z.sql.gz | head -20

# Restore to a temporary database to verify integrity
DB_NAME=app_db_verify ./scripts/db-restore.sh backups/app_db_20260514T020000Z.sql.gz
```

## Before a migration

Always take a manual backup before applying Alembic migrations in production:

```bash
./scripts/db-backup.sh
cd backend && alembic upgrade head
```

## Disaster recovery

1. Provision a fresh PostgreSQL instance.
2. Create the scoped DB user and database (mirrors what `postgres/init.sh` does on first start):
   ```sql
   CREATE USER username WITH PASSWORD 'secret';
   CREATE DATABASE app_db OWNER username;
   ```
3. Run restore: `DB_NAME=app_db DB_USER=username DB_PASSWORD=secret ./scripts/db-restore.sh <latest-backup>`
4. Apply any migrations that post-date the backup: `cd backend && alembic upgrade head`
5. Point the application at the new host via `DB_CONNECTION` env var in `backend/.env`.
