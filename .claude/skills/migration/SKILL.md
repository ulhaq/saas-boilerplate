---
name: migration
description: Scaffold and apply an Alembic migration for the FastAPI backend. Creates or updates a migration file with upgrade/downgrade logic, then applies it. Follows project preference of adding to existing staged migrations rather than creating new files.
argument-hint: <description> [--new]
---

# Migration

Scaffold and apply an Alembic migration based on the user's description or current model changes.

## Arguments

The user invoked this with: $ARGUMENTS

Parse the arguments:
- The main argument is a short description of what the migration does (e.g. "add stripe_customer_id to organizations")
- `--new` flag forces creation of a new migration file instead of adding to an existing staged one

## Workflow

### Step 1 - Check for an existing staged migration

Run:
```bash
cd backend && ls alembic/versions/ | tail -5
```

Then read the most recent migration file. A migration is "staged" (not yet applied to the database) if it hasn't been committed or if the user is actively working on a feature branch. When in doubt, ask the user whether to add to the existing file or create a new one.

**Per project preference**: add to an existing staged migration file rather than creating a new file, unless `--new` was passed or there is no suitable staged migration.

### Step 2 - Generate the migration

```bash
cd backend && alembic revision --autogenerate -m "<description>"
```

If adding to an existing file instead, skip this command and edit the existing file directly.

### Step 3 - Review and complete the migration

Read the generated (or existing) migration file. Autogenerate often misses:
- Index creation for foreign keys and frequently-filtered columns
- Server defaults for new non-nullable columns
- Custom SQL that SQLAlchemy can't detect

Complete or correct the `upgrade()` and `downgrade()` functions as needed. Ensure `downgrade()` is the exact inverse of `upgrade()`.

### Step 4 - Apply the migration

```bash
cd backend && alembic upgrade head
```

Report the output to the user. If the migration fails, diagnose from the error and fix the migration file, then re-apply.

### Step 5 - Verify

Run a quick sanity check:
```bash
cd backend && alembic current
```

Report the current revision to confirm success.

## Conventions

- Migration filenames follow Alembic's default `<rev>_<description>.py` pattern
- Always add indexes for: FK columns, `organization_id`, columns used in `WHERE` filters
- For new non-nullable columns on existing tables, always provide a `server_default` in `upgrade()` then remove it in a follow-up if desired
- `down_revision` must chain correctly - verify the chain when editing an existing file
