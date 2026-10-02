# FastAPI Backend Project Guide

This file provides comprehensive guidance for working with this FastAPI multi-tenant backend project.

## Project Overview

**SaaS boilerplate backend** - multi-tenant FastAPI service with auth, organizations, RBAC, Stripe billing, audit log, GDPR tooling, and email/in-app notifications. Product code lives in `src/example/`, a minimal Projects feature that demonstrates every extension point.

**Key Characteristics:**
- Multi-tenant architecture with enforced tenant isolation
- Fine-grained RBAC with granular permissions (platform `Permission` + product `ExamplePermission`)
- Async/await throughout using SQLAlchemy async drivers
- Pydantic V2 for schema validation
- Alembic for database migrations
- Comprehensive pytest suite running against PostgreSQL
- Type hints throughout (enforced via ty)
- Line length limit: 88 characters

### Example product modules

| Path | Purpose |
|------|---------|
| `src/example/enums.py` | `ExamplePermission`, `ExampleAuditAction`, `ExampleUsageMetric.PROJECTS`, `ExampleErrorCode`, permission descriptions + per-role grants |
| `src/example/models/project.py` | Org-scoped, soft-deletable `Project` |
| `src/example/repositories/` | `ProjectRepository(OrganizationScopedRepository)` + `ExampleRepositoryManager` |
| `src/example/services/project.py` | `ProjectService(ResourceService)` - name uniqueness, plan capacity check, audit logging |
| `src/example/routers/projects.py` | `/v1/projects` CRUD guarded by `require_permission(ExamplePermission.X)` |
| `src/example/hooks.py` | `PLAN_CHANGED` handler (reports orgs above their project limit) |
| `src/example/worker.py` | `run_example_loop` - heartbeat loop recording `worker_run` rows |
| `src/example/config.py` | `ExampleSettings` (`env_prefix="example_"`) |
| `src/example/product.py` | `EXAMPLE` manifest (`ProductModule`): permissions, role grants, routers, hooks, worker loops, models |

---

## Architecture

### Platform core vs. product domain

The backend is split into a **generic SaaS platform** (auth, organizations, users,
RBAC, billing, audit, GDPR) and the **product domain**. The core never imports
domain code; the two are wired together in exactly one place:

| Piece | Path | Purpose |
|-------|------|---------|
| Hook registry | `src/platform/core/hooks.py` | Core emits `HookEvent`s (`MEMBER_ADDED`, `MEMBER_REMOVED`, `PLAN_CHANGED`); domain modules register async handlers |
| Platform enums | `src/platform/enums.py` | Core `Permission`, `AuditAction`, `ErrorCode`, `PlanFeature`, `UsageMetric`, `DEFAULT_ROLES` - no domain members allowed |
| Domain enums | `src/example/enums.py` | Product permissions, audit actions, error codes, usage metrics, plus per-role grant/description contributions |
| Domain hooks | `src/example/hooks.py` | Handlers for platform lifecycle events |
| Domain settings | `src/example/config.py` | Independent settings namespace extending the shared `EnvSettings` base |
| Product manifest | `src/platform/core/product.py` | `ProductModule`: everything a product contributes (permissions, role grants, routers, hooks, worker loops, models, emails) |
| Installed products | `src/products.py` | `PRODUCTS` list - the only assembly file that names a product package |
| Composition root | `src/bootstrap.py` | Merges core + every product's permissions/roles (`ALL_PERMISSIONS`, `PERMISSION_DESCRIPTIONS`, `DEFAULT_ROLES`) and registers their hooks, email subjects, and template directories via `bootstrap()` |

`bootstrap()` is called at startup by `src/main.py` (API) and `worker.py` (worker).
`src/main.py` includes each product's routers, `worker.py` starts its loops, and
`alembic/env.py` registers its models - all by iterating `PRODUCTS`.
Seeding code (Alembic initial migration, `src/init_db.py`, `tests/conftest.py`) must
import the composed sets from `src.bootstrap`, never from `src.platform.enums` directly.

The import-linter contracts in `pyproject.toml` forbid `src.platform` from importing
`src.example` and enforce the layering below in both packages - keep them pointed at
your product package when you rename it.

**Building a new product on this backend** - replace the domain and keep the core
(full guide: `docs/adding-a-domain-module.md`):
1. Replace `src/example/` with your package (enums, models, repositories, services, routers, hooks).
2. Declare its `ProductModule` (like `src/example/product.py`), list it in `src/products.py`, and update the import-linter contracts.
3. Replace the example migration and `tests/api/test_projects.py`; update the seeded Member role permissions in `src/init_db.py`.

### Layered Architecture: Routers > Services > Repositories > Models

- `routers/` - FastAPI route handlers; validate HTTP input, delegate to services
- `services/` - Business logic; coordinate repositories, raise `ClientException` on failures
- `repositories/` - SQLAlchemy data access; handle filtering, pagination, soft deletes
- `models/` - SQLAlchemy ORM entities
- `schemas/` - Pydantic request/response models
- `src/platform/core/` - Cross-cutting concerns: config, security (JWT/passwords), DI dependencies, error handling, rate limiting, hooks

Enforced by import-linter (`uv run poe lint`), for `src/platform/` and `src/example/` alike:
- Each layer imports only the layers below it: `routers > services > billing > repositories > models | schemas` (`billing` is the platform's payment-provider adapter; `models` and `schemas` must not import each other).
- Routers never import repositories or models directly - always go through a service.
- `core` imports none of these layers - no exceptions. Where a core helper needs a model's data, it declares the shape it reads as a `Protocol` (e.g. `UserLike` in `core/security.py`) instead of importing the model.

### Key patterns

**Generic base classes** - `ResourceService[T]` and `SQLResourceRepository[T]` provide standard CRUD behavior. Domain-specific classes extend these; avoid duplicating CRUD logic.

**Dependency injection** - `src/platform/services/access.py` provides the auth/authz FastAPI dependencies: `authenticate()`, `require_permission(Permission.X)`, `require_plan_feature()`, `require_limit()` and `require_owner()`. `RepositoryManager` in `src/platform/repositories/repository_manager.py` is the DI container for platform repositories; product code depends on `ExampleRepositoryManager` (`src/example/repositories/manager.py`) instead.

**Transactions** - Each request runs in one transaction, committed when the endpoint returns (before the response and its background tasks) and rolled back if it raises. Depend on the session only via `DbSession` (`src/platform/core/database.py`), never `Depends(get_db)` - the default scope would commit after the response; `tests/unit/test_db_session_scope.py` enforces this. Services do not call `commit()`. The one exception is a write that must survive the error it reports (MFA failed-attempt counter, refresh-token reuse revocation): call `repos.commit_before_raise()` and raise immediately. Worker loops open their own `session.begin()` per iteration.

**Error handling** - Raise `ClientException(ErrorCode.X)` from services; the middleware in `src/platform/core/middlewares.py` converts these to consistent JSON error responses. Error codes are defined in `src/platform/enums.py` (platform) and `src/example/enums.py` (product).

**Multi-tenancy** - Users and resources belong to an `Organization`. Organization isolation is enforced at the repository level via `organization_id` foreign keys. Repositories extending `OrganizationScopedRepository` are **loud by default**: generic queries raise `UnscopedQueryError` unless `set_organization_scope()` was called; intentional cross-tenant access (auth identity lookups, workers, webhook handlers) must use the explicit `.unscoped` accessor.

**Plan limits** - Plan settings (`billing_plan_setting`) hold per-plan limits keyed by metric (`seats`, `projects`, ...). Use `BaseService._require_capacity(metric, org_id, current_count)` for "how many can exist" limits and `require_limit(metric)` (`services/access.py`) / `track_usage()` (`billing/dependencies.py`) for per-period usage counters.

**Permissions** - Fine-grained RBAC using the `Permission` enum (`src/platform/enums.py`) plus `ExamplePermission` (`src/example/enums.py`). Users have roles; roles have permissions. Use `require_permission()` on routes to enforce access.

**Observability** - `src/platform/core/telemetry.py`: OpenTelemetry traces/metrics, enabled only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (tests force it off). Wrap each worker-loop iteration in `with track_worker_run("name", interval):` so it gets run/failure/duration metrics and the overdue/failing alerts; log lines carry `trace_id`. Setup and dashboards: `observability/README.md`.

**Query features** - Repositories support dynamic filtering via `ComparisonOperator` (eq, lt, gte, contains, in, between, etc.), pagination (`page_number`, `page_size`), and sorting.

### Database migrations
Add columns/tables in models, then `alembic revision --autogenerate`.
Prefer adding to an existing staged migration file over creating a new one.
The initial migration holds the platform schema and seeds (permissions, plans, seat limits); product tables and product plan limits go in product migrations.

### Testing
- Tests run against the app's **PostgreSQL** server (`settings.db_connection`: docker compose builds `DB_CONNECTION` from the `DB_*` parts in `.env`; outside compose `Settings` does the same), never the app database itself: each xdist worker creates and drops its own `<db>_test_<worker>` database, so the role needs `CREATEDB`. The dev stack grants that at postgres init (`DB_USER_CREATEDB`); run `uv run poe test` - without a `DB_CONNECTION` (only compose and CI set one) the app settings point at `localhost:$POSTGRES_PORT` (default 5432, `APP_ENV=local` only)
- `tests/conftest.py` provides: async test client, pre-seeded organizations/users/roles/permissions, and per-test table truncation (`RESTART IDENTITY`, so seeded ids are stable)
- `asyncio_mode = auto` (set in `pytest.ini`); all test functions can be `async`
- Platform tests must not import product code - use a test-local enum where a metric/feature is needed


## Commands (`cd backend` first)

```bash
# Format code
uv run poe format

# Lint (ty + ruff + import-linter boundary/layer contracts)
uv run poe lint

# Run all tests
uv run poe test

# Run a single test
uv run pytest ./tests/api/test_auth.py::test_register_an_account -v

# Start dev server
uv run poe dev

# Database setup (runs migrations + seeds data)
python -m src.init_db

# Drop all tables
python -m src.init_db drop

# Database migrations
alembic revision --autogenerate -m "description"   # Create migration
alembic upgrade head                               # Apply migrations
alembic downgrade -1                               # Rollback last migration
```

**Package manager:** `uv` (use `uv add`, `uv run`, etc.)
