#!/bin/bash
# Runs once when the Postgres container initializes from a fresh data directory.
# Creates scoped users:
#   DB_USER        → owns the app DB schema (DML + DDL for Alembic)
#   DB_UMAMI_USER  → owns the umami DB (Umami runs its own Prisma migrations);
#                    skipped when DB_UMAMI_USER is empty
# Values are passed as psql variables (:"ident" / :'literal'), so they are quoted
# safely whatever characters they contain.
set -e

run_psql() {
  psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "$POSTGRES_DB" "$@"
}

run_psql -v db_user="$DB_USER" -v db_password="$DB_PASSWORD" <<-'EOSQL'
  CREATE USER :"db_user" WITH PASSWORD :'db_password';
  GRANT ALL ON SCHEMA public TO :"db_user";
  ALTER SCHEMA public OWNER TO :"db_user";
EOSQL

if [ -n "$DB_UMAMI_USER" ]; then
  run_psql -v umami_user="$DB_UMAMI_USER" -v umami_password="$DB_UMAMI_PASSWORD" <<-'EOSQL'
    CREATE USER :"umami_user" WITH PASSWORD :'umami_password';
    CREATE DATABASE umami OWNER :"umami_user";
EOSQL
fi

# Dev only (set in docker-compose.dev.yml): the test suite creates and drops its
# own `<db>_test_*` databases as DB_USER. Never set in production.
if [ "${DB_USER_CREATEDB:-false}" = "true" ]; then
  run_psql -v db_user="$DB_USER" <<-'EOSQL'
    ALTER ROLE :"db_user" CREATEDB;
EOSQL
fi
