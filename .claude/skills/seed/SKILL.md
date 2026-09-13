---
name: seed
description: Run or reset dev database seed data for organizations, users, roles, and billing plans. Use to restore a clean dev environment or repopulate after schema changes.
argument-hint: reset
---

# Seed

Seed the development database with baseline data: organizations, users, roles, permissions, and billing plans.

## Arguments

The user invoked this with: $ARGUMENTS

- No argument: run seed data on top of the current database state
- `reset`: drop all tables, re-run migrations, then seed fresh data

## Workflow

### Option A - Fresh reset (when `reset` is passed)

```bash
cd backend && python -m src.init_db drop && python -m src.init_db
```

`drop` removes all tables. `init_db` then re-runs all Alembic migrations and seeds the data.

### Option B - Seed only (no argument)

```bash
cd backend && python -m src.init_db
```

Runs migrations to head and seeds data. Safe to run multiple times if the seed script is idempotent; if it raises a duplicate-key error, use `reset` instead.

### After seeding

Report to the user what was created. Read `backend/src/init_db.py` (or equivalent seed script) to summarize the seeded entities:
- Which organizations were created
- Which users were created and their credentials
- Which roles and permissions were assigned
- Which billing plans are available

If the seed script file cannot be found at `backend/src/init_db.py`, search for it:
```bash
find backend/src -name "init_db*" -o -name "seed*" | head -5
```

## Common use cases

- After pulling a branch with new migrations: run `reset` to get a clean state
- After adding a new model: add seed entries to the seed script, then run without `reset` to append
- Before running e2e tests: run `reset` to ensure deterministic starting state
