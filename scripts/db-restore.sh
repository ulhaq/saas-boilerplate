#!/usr/bin/env bash
# Usage: ./scripts/db-restore.sh <backup-file.sql.gz>
#
# Runs psql via the postgres Docker container (must already be running),
# or native psql if available on the host.
#
# Environment variables (override defaults):
#   DB_NAME          - default: app_db
#   DB_USER          - default: app_user
#   DB_PASSWORD      - default: (empty)
#   COMPOSE_SERVICE  - postgres service name in docker-compose (default: postgres)
set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" ]]; then
  echo "Usage: $0 <backup-file.sql.gz>"
  exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Error: file not found: $BACKUP_FILE"
  exit 1
fi

DB_NAME="${DB_NAME:-app_db}"
DB_USER="${DB_USER:-app_user}"
DB_PASSWORD="${DB_PASSWORD:-}"
COMPOSE_SERVICE="${COMPOSE_SERVICE:-postgres}"

echo "WARNING: This will overwrite the database '$DB_NAME'."
read -r -p "Type 'yes' to continue: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "Aborted."
  exit 0
fi

echo "Restoring $BACKUP_FILE into '$DB_NAME' ..."

if command -v psql &>/dev/null; then
  gunzip -c "$BACKUP_FILE" | PGPASSWORD="$DB_PASSWORD" psql \
    -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "$DB_USER" "$DB_NAME"
else
  gunzip -c "$BACKUP_FILE" | docker compose exec -T "$COMPOSE_SERVICE" \
    sh -c "PGPASSWORD='$DB_PASSWORD' psql -U '$DB_USER' '$DB_NAME'"
fi

echo "Restore complete."
