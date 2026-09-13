#!/bin/bash
# Runs once when the Postgres container initializes from a fresh data directory.
# Creates scoped users:
#   DB_USER              → owns the app DB schema (DML + DDL for Alembic)
#   DB_UMAMI_USER  → owns the umami DB (Umami runs its own Prisma migrations)
set -e

psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
  GRANT CONNECT ON DATABASE $POSTGRES_DB TO $DB_USER;
  GRANT ALL ON SCHEMA public TO $DB_USER;
  ALTER SCHEMA public OWNER TO $DB_USER;

  CREATE USER $DB_UMAMI_USER WITH PASSWORD '$DB_UMAMI_PASSWORD';
  CREATE DATABASE umami OWNER $DB_UMAMI_USER;
EOSQL
