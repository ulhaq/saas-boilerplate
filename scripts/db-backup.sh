#!/usr/bin/env bash
# Usage: ./scripts/db-backup.sh
#
# Runs pg_dump via the postgres Docker container (must already be running),
# or native pg_dump if available on the host.
#
# Environment variables (override defaults):
#   DB_NAME          - default: app_db
#   DB_USER          - default: username
#   DB_PASSWORD      - default: (empty)
#   BACKUP_DIR       - default: ./backups
#   KEEP_DAYS        - default: 30 (prune backups older than this)
#   COMPOSE_SERVICE  - postgres service name in docker-compose (default: postgres)
set -euo pipefail

cd "$(dirname "$0")/.."

DB_NAME="${DB_NAME:-app_db}"
DB_USER="${DB_USER:-app_user}"
DB_PASSWORD="${DB_PASSWORD:-}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-30}"
COMPOSE_SERVICE="${COMPOSE_SERVICE:-postgres}"

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "Backing up database '$DB_NAME' to $BACKUP_FILE ..."

if command -v pg_dump &>/dev/null; then
  PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "$DB_USER" \
    --no-password --format=plain --clean --if-exists "$DB_NAME" \
    | gzip > "$BACKUP_FILE"
else
  docker compose exec -T "$COMPOSE_SERVICE" \
    sh -c "PGPASSWORD='$DB_PASSWORD' pg_dump -U '$DB_USER' --clean --if-exists '$DB_NAME'" \
    | gzip > "$BACKUP_FILE"
fi

echo "Backup complete: $BACKUP_FILE ($(du -sh "$BACKUP_FILE" | cut -f1))"

# Prune old backups
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime "+${KEEP_DAYS}" -delete
echo "Pruned backups older than ${KEEP_DAYS} days."
