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
├── hooks.py          # async handlers for platform HookEvents (listed in product.py)
├── models/           # SQLAlchemy models (import platform mixins/Base); __init__.py imports all
├── repositories/     # repos extending the platform base classes
│   └── manager.py    # AcmeRepositoryManager(RepositoryManager) adding your repos
├── services/         # business logic extending BaseService
├── routers/          # FastAPI routers, guarded with require_permission(AcmePermission.X)
├── schemas/          # Pydantic request/response models
├── templates/        # optional: emails/<locale>/<name>.html
├── email.py          # optional: ACME_EMAIL_SUBJECTS dict (manifest `email_subjects`)
└── product.py        # the ProductModule manifest (see step 2)
```

Conventions that carry over from `example`:

- Models declare `organization_id` FKs toward platform tables (never the reverse); repositories that hold tenant data extend `OrganizationScopedRepository` so unscoped queries fail loudly.
- Services raise `ClientException(AcmeErrorCode.X)`; the platform middleware renders the JSON error.
- Routers/services depend on `AcmeRepositoryManager` (FastAPI instantiates it via `Depends()` exactly like the platform one). Hook handlers receive the _platform_ manager and wrap its session: `repos = AcmeRepositoryManager(repos.db)` - same transaction.

### 2. Declare its manifest (`src/acme/product.py`)

Everything the package plugs into the platform goes in one `ProductModule` (`src/platform/core/product.py`) - see `src/example/product.py`:

```python
ACME = ProductModule(
    name="acme",
    models=models,                                   # registers your tables for Alembic
    permissions=list(AcmePermission),
    permission_descriptions={**ACME_PERMISSION_DESCRIPTIONS},
    default_role_permissions=ACME_DEFAULT_ROLE_PERMISSIONS,
    routers=[RouterMount(router=widgets.router, tags=["Widgets"])],  # public=False hides it from the API schema
    hooks={HookEvent.MEMBER_ADDED: [on_member_added]},
    worker_loops=[run_acme_loop],                    # wrap each iteration in track_worker_run("acme", interval)
    email_subjects=ACME_EMAIL_SUBJECTS,              # if you send email
    template_directory=Path(__file__).resolve().parent / "templates",
)
```

### 3. Install it

| Where             | What                                                                                                                                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/products.py` | add `ACME` to `PRODUCTS` - `bootstrap()`, the API router includes, the worker loops and Alembic's model registration all iterate `MODULES`, which includes it                                                                                                       |
| `pyproject.toml`  | in the import-linter contracts, add `src.acme` next to (or instead of) `src.example`: the platform contract's `forbidden_modules` (so the platform can't import it), the layers contract's `containers`, and the routers contract's module lists |

Never start loops in `main.py` - `worker.py` runs them in a single process.

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
├── index.ts          # manifest: messages, homeRoute, setup() (see step 2)
├── pages/            # file-based routes, merged into the app's route tree
├── components/       # auto-registered, same as platform components
├── stores/ + api/    # Pinia store is the data gateway; api module (typed `api` calls) used only by the store
├── composables/ utils/ constants.ts
├── types/            # aliases of the generated API schema: Schema<'WidgetOut'>
├── locales/en.ts, da.ts   # message tree, deep-merged over platform messages
└── notifications/    # optional: notification presenter registrations
```

### 2. Declare its manifest (`src/acme/index.ts`)

The module entry default-exports a `ProductModule` (`src/platform/product.ts`) - see `src/example/index.ts`:

```ts
const acme: ProductModule = {
  name: 'acme',
  messages: { da, en },          // deep-merged over the platform locales
  homeRoute: '/acme',            // optional: where signed-in users land
  setup() {                      // runs once at startup
    registerNavItems('main', [{ to: '/acme', labelKey: 'nav.acme', icon: ..., order: 25 }])
    // registerNotificationPresenter(...)
  },
}
export default acme
```

### 3. Install it

| Where                | What                                                                                                                                    |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `src/products.ts`    | import the manifest and add it to `products` - `main.ts` runs its `setup()` and home route, `plugins/i18n.ts` merges its messages       |
| `products.config.js` | add `'acme'` to `productPackages` - Vite reads it (via `modulePackages`) for `src/acme/pages` and `src/acme/components`, ESLint for the boundary rules |

### 4. Verify

```bash
(cd ../backend && uv run poe openapi) && npm run gen:api   # your endpoints' types
npm run typecheck && npm run lint && npm run build
```

The build regenerates `typed-router.d.ts` / `components.d.ts`; check the route diff is exactly your new pages.

## Replacing the product instead of adding one

Same steps - but delete `src/example/` on both sides and drop it from the installed lists: `src/products.py` and the import-linter contracts (backend); `src/products.ts` and `products.config.js` (frontend). The platform packages need no changes at all. Also drop the example migration (`alembic/versions/*_example_project_table.py`) and the `projects` plan limits it seeds, and update `src/brand.ts`, `planComparisonRows` and `planDescriptions` for the new product.
