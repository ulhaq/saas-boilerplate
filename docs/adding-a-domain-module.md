# Adding a Domain Module

How to add a new product/domain package (here called `acme`) next to - or instead of - `example`, on both sides of the stack. The rule everywhere: **the foundation never imports your domain; your domain imports the foundation; only the assembly layer knows both.** The optional modules (billing, marketing) follow the same rule and are independent of your product too: reach plan limits and features through the foundation's entitlements, never billing's code.

## Backend (`backend/src/acme/`)

### 1. Create the package

Mirror the layout of `src/example/`:

```
src/acme/
├── __init__.py
├── enums.py          # AcmePermission, AcmeAuditAction, AcmeErrorCode, AcmePlanFeature,
│                     # AcmeUsageMetric, AcmeHookEvent + ACME_PERMISSION_DESCRIPTIONS,
│                     # ACME_DEFAULT_ROLE_PERMISSIONS, ACME_DEFAULT_ROLE_DESCRIPTIONS
├── hooks.py          # async handlers for HookEvents (listed in product.py)
├── models/           # SQLAlchemy models (import foundation mixins/Base); __init__.py imports all
├── repositories/     # repos extending the foundation base classes
│   └── manager.py    # AcmeRepositoryManager(RepositoryManager) adding your repos
├── services/         # business logic extending BaseService
├── routers/          # FastAPI routers, guarded with require_permission(AcmePermission.X)
├── schemas/          # Pydantic request/response models
├── templates/        # optional: emails/<locale>/<name>.html (+ emails/mjml/<locale>/ sources)
├── emails.py         # optional: ACME_EMAIL_SUBJECTS dict (manifest `email_subjects`)
└── product.py        # the Module manifest (see step 2)
```

Conventions that carry over from `example`:

- Models declare `organization_id` FKs toward foundation tables (never the reverse); repositories that hold tenant data extend `OrganizationScopedRepository` so unscoped queries fail loudly.
- Services raise `ClientException(AcmeErrorCode.X)`; the foundation middleware renders the JSON error.
- Routers/services depend on `AcmeRepositoryManager` (FastAPI instantiates it via `Depends()` exactly like the foundation one). Hook handlers receive the _foundation_ manager and wrap its session: `repos = AcmeRepositoryManager(repos.db)` - same transaction. A handler never calls an external service (a foundation operation must not fail because a provider is down) - record the wanted state and let a worker loop push it.
- **Your own hook events**: declare them as a `StrEnum` (`AcmeHookEvent`, values prefixed `"acme."`), list it in the manifest's `hook_events`, and `await emit(AcmeHookEvent.X, repos=self.repos, ...)` from a service - see `ExampleHookEvent.PROJECT_CREATED`. Document each event's kwargs next to it. `bootstrap()` refuses a value declared twice and a handler for an event no installed module declares. Handling another module's event means importing its enum, so that module becomes a dependency: allow just that import in the independence contract (`ignore_imports = ["src.acme.** -> src.crm.enums"]`), and remove it together with the module.
- **Notifications**: declare a category (`notification_categories`) and a `NotificationRule` (`notification_rules`) for the event - the foundation notifies the organization's members holding the rule's permission, in-app and/or by email as each prefers, with the event kwargs the rule lists as payload and email data; your services only emit events (see `src/example/emails.py`). Put what a notification shows in the event's kwargs (names, not just ids). Add an email template and subject for the rule's `email_template`, and a frontend presenter for its `notification_type` (`registerNotificationPresenter`). Use `deliver_notification` from a hook handler only when recipients aren't "members with a permission".
- **Plan limits and features** go through the foundation, so they work with or without billing: "how many can exist" limits with `await self._require_capacity(AcmeUsageMetric.WIDGETS, organization_id, self.repo.count)` right before inserting (it takes a per-organization lock, so concurrent requests can't both take the last slot), features with `require_plan_feature(AcmePlanFeature.X)` on a route or `self._require_feature(...)` in a service, and `composition.current().entitlements.limit(...)` to read a limit (e.g. in an `ENTITLEMENTS_CHANGED` handler). Without billing installed every feature is on and nothing is limited.

### 2. Declare its manifest (`src/acme/product.py`)

Everything the package plugs into the foundation goes in one `Module` (`src/foundation/core/module.py`) - see `src/example/product.py`:

```python
ACME = Module(
    name="acme",
    models=models,                                   # registers your tables for Alembic
    permissions=list(AcmePermission),
    permission_descriptions={**ACME_PERMISSION_DESCRIPTIONS},
    audit_actions=list(AcmeAuditAction),              # listed in the audit-log filter
    default_role_permissions=ACME_DEFAULT_ROLE_PERMISSIONS,
    routers=[RouterMount(router=widgets.router, tags=["Widgets"])],  # public=False hides it from the API schema
    hook_events=list(AcmeHookEvent),                 # events you emit, for other modules to handle
    hooks={HookEvent.MEMBER_ADDED: [on_member_added]},
    worker_loops=[run_acme_loop],                    # wrap each iteration in track_worker_run("acme", interval)
    email_subjects=ACME_EMAIL_SUBJECTS,              # if you send email
    template_directory=Path(__file__).resolve().parent / "templates",
)
```

Also available: `default_role_descriptions`, `email_campaigns` / `email_link_keys` (UTM tagging of your emails' links), and `user_data_export` - if your module stores personal data about a user (anything keyed by their id or email), an async function returning it, which the GDPR export (`GET /v1/users/me/export`) lists under your module's name (see `src/billing/gdpr.py`). `entitlements` is for a module that sells plans - billing provides it.

### 3. Install it

| Where             | What                                                                                                                                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/products.py` | add `ACME` to `PRODUCTS` - `bootstrap()`, the API router includes, the worker loops and Alembic's model registration all iterate `MODULES`, which includes it                                                                                                       |
| `pyproject.toml`  | in the import-linter contracts, add `src.acme` next to (or instead of) `src.example`: the foundation contract's `forbidden_modules` (so the foundation can't import it), the independence contract's `modules` (so it and the optional modules stay apart), the layers contract's `containers`, and the routers contract's module lists |

Never start loops in `main.py` - `worker.py` runs them in a single process.

### 4. Migrate and test

```bash
uv run alembic revision --autogenerate -m "acme tables"   # one migration per module, chained last
uv run alembic upgrade head
uv run python -m src.sync_permissions                       # your permissions reach the DB and every Owner role
uv run poe check && uv run poe test && uv run poe test-foundation-only
```

Permissions are never seeded by migrations: `sync_permissions` adds the declared ones on every deploy (CI runs it after `alembic upgrade head`) and `init_db` runs it too. To seed plan limits for your metrics, insert `billing_plan_setting` rows in your migration only when billing's tables exist (see `*_example_project_table.py`), so the product still migrates without billing.

Add tests under `backend/tests/` (API tests get the seeded multi-tenant fixtures from `conftest.py` for free; your permissions/roles are seeded because `conftest` imports the composed sets from `src.bootstrap`). A test that relies on billing behaviour (a plan limit, a plan feature) gets `@pytest.mark.billing`, so `test-foundation-only` skips it; don't hard-code counts that depend on the installed modules.

## Frontend (`frontend/src/acme/`)

### 1. Create the package

```
src/acme/
├── index.ts          # manifest: messages, homeRoute, setup() (see step 2)
├── pages/            # file-based routes, merged into the app's route tree
├── components/       # auto-registered, same as foundation components
├── stores/ + api/    # Pinia store is the data gateway; api module (typed `api` calls) used only by the store
├── composables/ utils/ constants.ts
├── types/            # aliases of the generated API schema: Schema<'WidgetOut'>
├── locales/en.ts, da.ts   # message tree, deep-merged over foundation messages
└── notifications/    # optional: notification presenter registrations
```

### 2. Declare its manifest (`src/acme/index.ts`)

The module entry default-exports a `Module` (`src/foundation/module.ts`) - see `src/example/index.ts`:

```ts
const acme: Module = {
  name: 'acme',
  messages: { da, en },          // deep-merged over the foundation locales
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

Plan limits and features come from `useEntitlements()` (`@/foundation/entitlements`: `limitFor`, `hasFeature`, `loadLimits`, `planSummary`) - never billing's store - so the product works without billing; `<PlanQuota>`, `<PlanLimitReached>` and `<LockedOverlay>` render them.

### 4. Verify

```bash
(cd ../backend && uv run poe openapi) && npm run gen:api   # your endpoints' types
npm run build && npm run typecheck && npm run lint && npm test
```

Build first: it generates `typed-router.d.ts`, `components.d.ts` and `auto-imports.d.ts` (gitignored), which the type-check reads (`npm run dev` generates them too). Check the route list is exactly your new pages.

## Replacing the product instead of adding one

Same steps - but delete `src/example/` on both sides (and `backend/tests/api/test_projects.py`) and drop it from the installed lists: `src/products.py` and the import-linter contracts (backend); `src/products.ts` and `products.config.js` (frontend). The foundation packages need no changes at all. Also drop the example migration (`alembic/versions/*_example_project_table.py`, which seeds the `projects` plan limits), and update `src/brand.ts`, `planComparisonRows` and `planDescriptions` for the new product.

## Keeping or dropping the optional modules

Billing (plans, subscriptions, Stripe; both sides) and marketing (the waitlist and contact-form endpoints the `site/` posts to; backend only) are installed by default. CI already checks that the foundation and the product work without them: it removes them from a throwaway checkout with the scripts below and runs lint, the migrations and the tests again (backend), and build, type-check, lint and tests (frontend).

To drop one for good, in `backend/` run `uv run python scripts/remove_module.py billing` (or `marketing`), then `uv run poe fix && uv run poe check && uv run poe test` and reset the database. The script does these steps, which you can also do by hand:

1. Remove it from `MODULES` (and its import) in `src/products.py`.
2. Delete its package (`src/billing/`) and its migration (`alembic/versions/*_billing.py`), and point the next migration's `down_revision` (and `Revises:`) at the one before it.
3. Remove it from the import-linter contracts in `pyproject.toml` (every list naming `src.billing...`).
4. Delete its tests: `tests/<module>/` (fixtures included), and the tests elsewhere marked with its name (`@pytest.mark.billing`) along with helpers only they use - `poe check` points at any left.
5. Reset the database (`python -m src.init_db drop && python -m src.init_db`).

For billing on the frontend, run `node scripts/remove-billing.mjs` in `frontend/`. Without billing every feature is on and nothing is limited; without marketing the `/v1/waitlist` and `/v1/contact` endpoints are gone (drop the site's forms too).
