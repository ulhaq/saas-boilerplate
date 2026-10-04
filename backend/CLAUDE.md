# FastAPI Backend Project Guide

This file provides comprehensive guidance for working with this FastAPI multi-tenant backend project.

## Project Overview

**SaaS boilerplate backend** - multi-tenant FastAPI service with auth, organizations, RBAC, Stripe billing, audit log, GDPR tooling, and email/in-app notifications. Product code lives in `src/example/`, a minimal Projects feature that demonstrates every extension point.

**Key Characteristics:**

- Multi-tenant architecture with enforced tenant isolation
- Fine-grained RBAC with granular permissions (foundation `Permission` + product `ExamplePermission`)
- Async/await throughout using SQLAlchemy async drivers
- Pydantic V2 for schema validation
- Alembic for database migrations
- Comprehensive pytest suite running against PostgreSQL
- Type hints throughout (enforced via ty)
- Line length limit: 88 characters

### Example product modules

| Path                              | Purpose                                                                                                                                 |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `src/example/enums.py`            | `ExamplePermission`, `ExampleAuditAction`, `ExampleHookEvent.PROJECT_CREATED` (emitted by `ProjectService`), `ExampleUsageMetric.PROJECTS`, `ExampleErrorCode`, permission descriptions + per-role grants |
| `src/example/models/project.py`   | Org-scoped, soft-deletable `Project`                                                                                                    |
| `src/example/repositories/`       | `ProjectRepository(OrganizationScopedRepository)` + `ExampleRepositoryManager`                                                          |
| `src/example/services/project.py` | `ProjectService(ResourceService)` - name uniqueness, plan capacity check, audit logging                                                 |
| `src/example/routers/projects.py` | `/v1/projects` CRUD guarded by `require_permission(ExamplePermission.X)`                                                                |
| `src/example/hooks.py`            | `ENTITLEMENTS_CHANGED` handler (reports orgs above their project limit)                                                                         |
| `src/example/emails.py`           | `project-created` subjects (templates in `src/example/templates/`), the `example.projects` notification category (email opt-in) and the `NotificationRule` sending it on `PROJECT_CREATED` |
| `src/example/worker.py`           | `run_example_loop` - heartbeat loop recording `worker_run` rows                                                                         |
| `src/example/config.py`           | `ExampleSettings` (`env_prefix="example_"`)                                                                                             |
| `src/example/product.py`          | `EXAMPLE` manifest (`Module`): permissions, role grants, routers, hook events and handlers, notification rules, worker loops, models                                    |

---

## Architecture

### Foundation core, optional modules, product domain

The backend is split into a **generic SaaS foundation** (`src/foundation/`: auth,
organizations, users, RBAC, audit, GDPR, notifications), the optional modules -
**billing** (`src/billing/`: plans, subscriptions, usage, Stripe) and
**marketing** (`src/marketing/`: the waitlist and contact-form endpoints the
marketing site posts to) - and the **product domain** (`src/example/`). The
foundation imports none of them, and they don't import each other; all plug in
through the same manifest, wired together in exactly one place:

| Piece              | Path                           | Purpose                                                                                                                                                                                               |
| ------------------ | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hook registry      | `src/foundation/core/hooks.py`   | `HookEvent`s (`MEMBER_ADDED`, `MEMBER_REMOVED`, `ORGANIZATION_CREATED`, `ORGANIZATION_DELETING`, `OWNERSHIP_TRANSFERRED`, `ENTITLEMENTS_CHANGED`); a module declares its own events in its manifest (`hook_events`, a `StrEnum` with `"<module>.<event>"` values, e.g. `ExampleHookEvent`) and emits them with `emit`; modules list async handlers in their manifest, and `bootstrap()` refuses a handler for an event no installed module declares. Handling another module's event imports its enum - narrow the independence contract for that pair       |
| Entitlements       | `src/foundation/core/entitlements.py` | What an organization may use (features, limits, usage). Billing provides `PlanEntitlements`; without it, `UNLIMITED`                                                                         |
| Marketing module   | `src/marketing/`               | Waitlist sign-ups and the contact form (its email + migration); manifest `MARKETING` in `src/marketing/module.py`                                                                         |
| Billing module     | `src/billing/`                 | Own layers, enums, settings (`BillingSettings`), templates, hooks and migration; manifest `BILLING` in `src/billing/module.py`; `BillingRepositoryManager` adds its repositories                  |
| Foundation enums     | `src/foundation/enums.py`        | Core `Permission`, `AuditAction`, `ErrorCode`, `PlanFeature`, `UsageMetric`, `DEFAULT_ROLES` - no domain members allowed                                                                              |
| Domain enums       | `src/example/enums.py`         | Product permissions, audit actions, error codes, usage metrics, plus per-role grant/description contributions                                                                                         |
| Domain hooks       | `src/example/hooks.py`         | Handlers for foundation lifecycle events                                                                                                                                                                |
| Domain settings    | `src/example/config.py`        | Independent settings namespace extending the shared `EnvSettings` base                                                                                                                                |
| Product manifest   | `src/foundation/core/module.py` | `Module`: everything a product contributes (permissions, role grants, routers, hooks, worker loops, models, emails, notification categories)                                                                            |
| Installed modules  | `src/products.py`              | `PRODUCTS` (the product) and `MODULES` (`BILLING`, `MARKETING` + products) - the only assembly file that names them                                                                                                |
| Composition root   | `src/bootstrap.py`             | Merges core + every product's permissions (`ALL_PERMISSIONS`, `PERMISSION_DESCRIPTIONS`, for seeding) and, via `bootstrap()`, installs one read-only `Composition` (`src/foundation/core/composition.py`: default roles, hooks, email subjects, template directories, entitlements) that foundation code reads with `composition.current()`; `AUDIT_ACTION` composes every module's audit actions for the audit-log filter |

`bootstrap()` is called at startup by `src/main.py` (API) and `worker.py` (worker).
`src/main.py` includes each module's routers, `worker.py` starts its loops, and
`alembic/env.py` registers its models - all by iterating `MODULES`.
To run without an optional module, drop it from `MODULES`, delete its
migration and point the next migration's `down_revision` at the one before it.
Without billing every feature is on, with no limits (the product's
project-limit seed skips itself without billing's tables); without marketing
the `/v1/waitlist` and `/v1/contact` endpoints are gone.
Seeding code (`src/sync_permissions.py`, `src/init_db.py`, `tests/conftest.py`) must
import the composed sets from `src.bootstrap`, never from `src.foundation.enums` directly.

The import-linter contracts in `pyproject.toml` forbid `src.foundation` from importing
`src.example` and enforce the layering below in both packages - keep them pointed at
your product package when you rename it.

**Building a new product on this backend** - replace the domain and keep the core
(full guide: `docs/adding-a-domain-module.md`):

1. Replace `src/example/` with your package (enums, models, repositories, services, routers, hooks).
2. Declare its `Module` (like `src/example/product.py`), list it in `src/products.py`, and update the import-linter contracts.
3. Replace the example migration and `tests/api/test_projects.py`; update the seeded Member role permissions in `src/init_db.py`.

### Layered Architecture: Routers > Services > Repositories > Models

- `routers/` - FastAPI route handlers; validate HTTP input, delegate to services
- `services/` - Business logic; coordinate repositories, raise `ClientException` on failures
- `repositories/` - SQLAlchemy data access; handle filtering, pagination, soft deletes
- `models/` - SQLAlchemy ORM entities
- `schemas/` - Pydantic request/response models. Response models extend `ResponseSchema` (`src/foundation/core/schema.py`) so defaulted fields are required in the OpenAPI schema - the frontend's generated types depend on it.
- `src/foundation/core/` - Cross-cutting concerns: config, security (JWT/passwords), DI dependencies, error handling, rate limiting, hooks

Enforced by import-linter (`uv run poe check`), for `src/foundation/`, `src/billing/` and `src/example/` alike:

- `src.foundation` imports neither `src.billing` nor the product; billing does not import the product.
- Each layer imports only the layers below it: `routers > services > provider > repositories > models | schemas` (`provider` is billing's payment-provider adapter; `models` and `schemas` must not import each other).
- Routers never import repositories or models directly - always go through a service.
- `core` imports none of these layers - no exceptions. Where a core helper needs a model's data, it declares the shape it reads as a `Protocol` (e.g. `UserLike` in `core/security.py`) instead of importing the model.

### Key patterns

**Generic base classes** - `ResourceService[T]` and `SQLResourceRepository[T]` provide standard CRUD behavior. Domain-specific classes extend these; avoid duplicating CRUD logic.

**Dependency injection** - `src/foundation/services/access.py` provides the auth/authz FastAPI dependencies: `authenticate()`, `require_permission(Permission.X)`, `require_plan_feature()`, `require_limit()` and `require_owner()`. `RepositoryManager` in `src/foundation/repositories/repository_manager.py` is the DI container for foundation repositories; billing code depends on `BillingRepositoryManager` (`src/billing/repositories/manager.py`) and product code on `ExampleRepositoryManager` (`src/example/repositories/manager.py`) instead.

**Transactions** - Each request runs in one transaction, committed when the endpoint returns (before the response and its background tasks) and rolled back if it raises. Depend on the session only via `DbSession` (`src/foundation/core/database.py`), never `Depends(get_db)` - the default scope would commit after the response; `tests/unit/test_db_session_scope.py` enforces this. Services do not call `commit()`. The one exception is a write that must survive the error it reports (MFA failed-attempt counter, failed password sign-ins in `login_throttle`, refresh-token reuse revocation): call `repos.commit_before_raise()` and raise immediately. Worker loops open their own `session.begin()` per iteration. Don't hold row or advisory locks across calls to Stripe or other external services: checkout and trial take none (duplicate Stripe customers are prevented by an idempotency key in `get_or_create_customer`); cancel/resume/switch-plan lock the subscription row because they write state from Stripe's response, and every Stripe call is bounded by `STRIPE_TIMEOUT_SECONDS` (`configure_stripe` in `src/billing/provider/stripe_provider.py`). A hook handler never calls an external service: a foundation operation must not fail because a provider is down. Record the wanted state and let a worker loop push it (e.g. ownership transfer sets `BillingAccount.pending_customer_email`; `run_customer_sync_loop` pushes it to Stripe and retries).

**Error handling** - Raise `ClientException(ErrorCode.X)` from services; the middleware in `src/foundation/core/middlewares.py` converts these to consistent JSON error responses. Error codes are defined in `src/foundation/enums.py` (foundation), `src/billing/enums.py` (billing) and `src/example/enums.py` (product).

**Multi-tenancy** - Users and resources belong to an `Organization`. Organization isolation is enforced at the repository level via `organization_id` foreign keys. Repositories extending `OrganizationScopedRepository` are **loud by default**: generic queries raise `UnscopedQueryError` unless `set_organization_scope()` was called; intentional cross-tenant access (auth identity lookups, workers, webhook handlers) must use the explicit `.unscoped` accessor.

**Plan limits** - The foundation asks the installed `Entitlements` (`composition.current().entitlements`), never billing directly. Use `BaseService._require_capacity(metric, org_id, count)` for "how many can exist" limits - `count` is an async callable it runs after taking the organization's capacity lock (`lock_capacity`, held until commit), so concurrent requests can't both take the last slot; call it right before adding the resource. Seats count members plus pending invitations, and joining re-checks the limit, `BaseService._require_feature()` / `require_plan_feature()` for features, and `require_limit(metric)` (`services/access.py`) for per-period usage counters - it counts one use and enforces the limit in a single atomic step, inside the request's transaction. With billing installed, the answers come from the organization's plan: plan settings (`billing_plan_setting`) hold limits keyed by metric (`seats`, `projects`, ...). The plan that applies is the subscription's while its status is in `ENTITLED_STATUSES` (`src/billing/enums.py`: active, trialing, past_due), otherwise the free plan - a paused trial included. The app reads the same policy from `SubscriptionOut.has_access`, so don't keep status lists elsewhere.

**GDPR export** - `GET /v1/users/me/export` returns the foundation's data about the user (profile, memberships, API tokens, audit log, notifications, notification preferences) plus each module's share: a module storing personal data sets `user_data_export` in its manifest (billing: organizations billed to the user's email; marketing: their waitlist sign-up).

**Permissions** - Fine-grained RBAC using the `Permission` enum (`src/foundation/enums.py`) plus `ExamplePermission` (`src/example/enums.py`). Users have roles; roles have permissions. Use `require_permission()` on routes to enforce access. Nobody hands out more access than they hold: anything that grants or revokes permissions (a role's permissions, a user's roles, an invitation's roles, an API token) checks `assert_can_grant(current_user, permissions)` (`services/access.py`) - owners hold every permission, so they're never limited.

**Realtime events** - `publish_to_user(session, user_id, RealtimeEvent(type, organization_id, data))` (`src/foundation/core/realtime.py`) tells the user's open app tabs that something changed; it is sent after the transaction commits (`after_commit` in `core/database.py`) and dropped on rollback. Events are best-effort hints - keep `data` small, no personal data - and the app re-fetches on them. The broker is Redis pub/sub when `REDIS_URL` is set (required outside `local`; one relay task per API process fans events out to its streams), otherwise in-process (`LocalBroker`; tests always use it). `GET /v1/events` (`routers/events.py`, `services/realtime.py`) streams the signed-in user's events for their current organization as SSE (`core/sse.py`), with keep-alives every `REALTIME_HEARTBEAT_SECONDS`, and ends after `REALTIME_STREAM_MAX_SECONDS` so the app reconnects with a current token. Name a new event type in a `StrEnum` like `NotificationEvent` (`src/foundation/enums.py`).

**Observability** - `src/foundation/core/telemetry.py`: OpenTelemetry traces/metrics, enabled only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (tests force it off). Wrap each worker-loop iteration in `with track_worker_run("name", interval):` so it gets run/failure/duration metrics and the overdue/failing alerts; log lines carry `trace_id`. Setup and dashboards: `observability/README.md`.

**Query features** - Repositories support dynamic filtering via `ComparisonOperator` (eq, lt, gte, contains, in, between, etc.), pagination (`page_number`, `page_size`), and sorting.

### API schema and the frontend's types

`src/main.py` mounts every router from one ordered `ROUTERS` list of `RouterMount`s (product routers come from the manifests). `public=False` keeps a router out of the served OpenAPI schema (`/docs`, for API-token consumers); never hide individual routes with `include_in_schema=False` - visibility is decided per mount. `internal_openapi()` builds the full schema (every route) that the frontend's API types are generated from.

`uv run poe openapi` writes both: `openapi.json` (public) and `openapi.internal.json` (every route), from code defaults only (no `.env`). Run it after changing a request/response schema or a route, then `npm run gen:api` in `frontend/`, and commit the results - CI fails when either is stale. The pre-commit hook does all of this when backend code changes.

### Database migrations

Add columns/tables in models, then `alembic revision --autogenerate`.
Prefer adding to an existing staged migration file over creating a new one.
The initial migration holds the foundation schema; billing's migration its tables and plan seeds (plans, prices, seat limits); product tables and product plan limits go in product migrations. Permissions are not migrated: `python -m src.sync_permissions` (`sync_permissions` in `services/permission.py`) runs after `alembic upgrade head` on every deploy and in `init_db` - it adds missing declared permissions and grants all of them to every Owner role, idempotently. Other roles are left to their owners; permissions no longer declared are reported, not deleted.

### Testing

- Tests run against the app's **PostgreSQL** server (`settings.db_connection`: docker compose builds `DB_CONNECTION` from the `DB_*` parts in `.env`; outside compose `Settings` does the same), never the app database itself: each xdist worker creates and drops its own `<db>_test_<worker>` database, so the role needs `CREATEDB`. The dev stack grants that at postgres init (`DB_USER_CREATEDB`); run `uv run poe test` - without a `DB_CONNECTION` (only compose and CI set one) the app settings point at `localhost:$POSTGRES_PORT` (default 5432, `APP_ENV=local` only)
- `tests/conftest.py` provides: async test client, pre-seeded organizations/users/roles/permissions, and per-test table truncation (`RESTART IDENTITY`, so seeded ids are stable)
- `asyncio_mode = auto` (set in `pytest.ini`); all test functions can be `async`
- Foundation tests must not import product code - use a test-local enum where a metric/feature is needed
- An optional module's tests live in `tests/<module>/` (`tests/billing/`, `tests/marketing/`); a foundation or product test that relies on a module's behaviour (plan gating, free subscriptions, Stripe sync) is marked with its name (`@pytest.mark.billing`). `uv run poe test-foundation-only` (`TEST_WITHOUT_MODULES=optional` - every module that isn't a product - applied by the `tests.preload` plugin) runs the suite on an app without them and skips those - CI runs both, so the foundation keeps working on its own. A module's fixtures live in `tests/<module>/plugin.py`, loaded only while it is installed, and nothing outside `tests/<module>/` imports the module at file level - so deleting the module's package and test folder leaves the suite intact. `scripts/remove_module.py <module>` removes a module for good (package, migration - re-chaining the next one, contracts, tests); CI runs it for every optional module on a throwaway checkout and checks lint, migrations and tests again. A module's migration file must end in `_<module>.py`. Don't hard-code counts that depend on installed modules (derive them from `ALL_PERMISSIONS`)

## Commands (`cd backend` first)

```bash
# Format & fix code
uv run poe fix

# Lint (ty + ruff + import-linter boundary/layer contracts)
uv run poe check

# Run all tests
uv run poe test

# Run them on an app without the optional modules (CI runs both)
uv run poe test-foundation-only

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
