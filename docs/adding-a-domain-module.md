# Adding a Domain Module

How to add a new product/domain package (here called `acme`) next to - or instead of - `example`, on both sides of the stack. The rule everywhere: **the platform never imports your domain; your domain imports the platform; only the assembly layer knows both.**

## Backend (`backend/src/acme/`)

### 1. Create the package

Mirror the layout of `src/example/`:

```
src/acme/
├── __init__.py
├── enums.py          # AcmePermission, AcmeAuditAction, AcmeErrorCode, AcmePlanFeature,
│                     # AcmeUsageMetric + ACME_PERMISSION_DESCRIPTIONS,
│                     # ACME_DEFAULT_ROLE_PERMISSIONS, ACME_DEFAULT_ROLE_DESCRIPTIONS
├── hooks.py          # async handlers for platform HookEvents + register_acme_hooks()
├── models/           # SQLAlchemy models (import platform mixins/Base); __init__.py imports all
├── repositories/     # repos extending the platform base classes
│   └── manager.py    # AcmeRepositoryManager(RepositoryManager) adding your repos
├── services/         # business logic extending BaseService
├── routers/          # FastAPI routers, guarded with require_permission(AcmePermission.X)
├── schemas/          # Pydantic request/response models
├── templates/        # optional: emails/<locale>/<name>.html
└── email.py          # optional: ACME_EMAIL_SUBJECTS dict for register_email_subjects()
```

Conventions that carry over from `example`:

- Models declare `organization_id` FKs toward platform tables (never the reverse); repositories that hold tenant data extend `OrganizationScopedRepository` so unscoped queries fail loudly.
- Services raise `ClientException(AcmeErrorCode.X)`; the platform middleware renders the JSON error.
- Routers/services depend on `AcmeRepositoryManager` (FastAPI instantiates it via `Depends()` exactly like the platform one). Hook handlers receive the *platform* manager and wrap its session: `repos = AcmeRepositoryManager(repos.db)` - same transaction.

### 2. Wire it in `src/bootstrap.py` (the composition root)

```python
ALL_PERMISSIONS = [*core_enums.Permission, *ExamplePermission, *AcmePermission]
PERMISSION_DESCRIPTIONS = {**core_enums.PERMISSION_DESCRIPTIONS,
                           **EXAMPLE_PERMISSION_DESCRIPTIONS,
                           **ACME_PERMISSION_DESCRIPTIONS}
# merge ACME_DEFAULT_ROLE_PERMISSIONS into DEFAULT_ROLES the same way example does

def bootstrap() -> None:
    ...
    register_acme_hooks()
    register_email_subjects(ACME_EMAIL_SUBJECTS)        # if you send email
    add_template_directory("./src/acme/templates")      # if you ship templates
```

`bootstrap()` already runs at startup of both the API and the worker; the composed sets flow into `src/platform/core/composition.py` automatically.

### 3. Register the remaining assembly points

| Where | What |
|-------|------|
| `src/main.py` | `from src.acme.routers import ...` + `app.include_router(...)` |
| `alembic/env.py` | `from src.acme import models  # noqa: F401` (metadata registration - without this, autogenerate will try to drop your tables) |
| `worker.py` | `asyncio.create_task(run_acme_loop(ASYNC_SESSION_LOCAL))` if you need a background loop (never start loops in `main.py`); wrap each iteration in `track_worker_run("acme", interval)` (`src/platform/core/telemetry.py`) so it gets metrics and the overdue/failing alerts |
| `pyproject.toml` | add `src.acme` to the import-linter contract's `forbidden_modules` so the platform can't import it either |

### 4. Migrate and test

```bash
uv run alembic revision --autogenerate -m "acme tables"
uv run alembic upgrade head
uv run poe lint && uv run poe test
```

Add tests under `backend/tests/` (API tests get the seeded multi-tenant fixtures from `conftest.py` for free; your permissions/roles are seeded because `conftest` imports the composed sets from `src.bootstrap`).

## Frontend (`frontend/src/acme/`)

### 1. Create the package

```
src/acme/
├── index.ts          # module entry: registrations only (see step 2)
├── pages/            # file-based routes, merged into the app's route tree
├── components/       # auto-registered, same as platform components
├── stores/ + api/    # Pinia store is the data gateway; api module used only by the store
├── composables/ utils/ types/ constants.ts
├── locales/en.ts, da.ts   # message tree, deep-merged over platform messages
└── notifications/    # optional: notification presenter registrations
```

### 2. Register in the module entry (`src/acme/index.ts`)

```ts
import { registerNavItems } from '@/platform/navigation'
import '@/acme/notifications/...'   // side-effect: registerNotificationPresenter(...)

registerNavItems('main', [{ to: '/acme', labelKey: 'nav.acme', icon: ..., order: 25 }])
```

If your module owns the authenticated home page, set it from `main.ts` via `configureApp({ homeRoute: '/acme' })`.

### 3. Register the assembly points

| Where | What |
|-------|------|
| `vite.config.ts` | add `'src/acme/pages'` to `routesFolder` and `'src/acme/components'` to the Components plugin `dirs` |
| `src/plugins/i18n.ts` | import your locale files and add them to the `mergeMessages` chain |
| `src/main.ts` | `import '@/acme'` |
| `eslint.config.js` | add `'@/acme'`/`'@/acme/**'` to the platform `no-restricted-imports` patterns |

### 4. Verify

```bash
npm run typecheck && npm run lint && npm run build
```

The build regenerates `typed-router.d.ts` / `components.d.ts`; check the route diff is exactly your new pages.

## Replacing the product instead of adding one

Same steps - but first delete `src/example/` on both sides and strip its assembly references: `bootstrap.py`, `main.py` router includes, `alembic/env.py`, `worker.py` (backend); `main.ts`, `vite.config.ts`, `plugins/i18n.ts`, the ESLint pattern (frontend). The platform packages need no changes at all. Also drop the example migration (`alembic/versions/*_example_project_table.py`) and the `projects` plan limits it seeds, and update `src/brand.ts`, `planComparisonRows` and `planDescriptions` for the new product.
