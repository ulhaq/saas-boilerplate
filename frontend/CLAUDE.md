# Frontend

Vue 3 + TypeScript SPA for the SaaS boilerplate: the signed-in app (auth, organizations, users, roles, settings), the optional billing module (plans, subscriptions, checkout) and the example product's Projects feature. The marketing site (home, pricing, legal pages) is the separate `site/` package on its own domain; the app links to its terms/privacy pages via `legalUrl()` in `foundation/constants.ts`. Built with Vite, Pinia state management, file-based routing via `unplugin-vue-router`, Tailwind + Reka UI components.

## Commands (`cd frontend` first)

```bash
npm run dev       # dev server on :5173 (proxies /v1 → localhost:8000)
npm run build     # production build
npm run typecheck # vue-tsc -b (checks the app and the config files)
npm run gen:api   # regenerate src/api-schema.ts from ../backend/openapi.internal.json
npm test          # component tests (vitest); npm run test:watch to iterate
npm run test:e2e  # end-to-end (playwright; needs the dev stack running)
```

## Project Structure

The source tree mirrors the backend's split: a generic SaaS shell under
`src/foundation/`, the optional billing module under `src/billing/`, the product
under `src/example/`, and a thin assembly layer at the `src/` root.
**`src/foundation` must never import from `src/billing` or `src/example`, and
billing never imports the product** - enforced by `no-restricted-imports` ESLint
rules.

```
src/
├── foundation/         # generic SaaS shell (auth, orgs, users, roles, settings)
│   ├── api/          # Axios client + domain API modules (auth, users, roles, ...)
│   ├── components/
│   │   ├── ui/       # Base shadcn-style components (Button, Input, Dialog, Card, etc.)
│   │   ├── common/   # Shared app components (DataTable, PageHeader, ConfirmDialog, PermissionGuard)
│   │   ├── layout/   # AppSidebar, AppTopbar, MobileSidebar
│   │   └── users/, roles/, organizations/
│   ├── composables/  # useDataTable, useErrorHandler, usePermission, useNotificationPresenter, ...
│   ├── layouts/      # DashboardLayout, AuthLayout
│   ├── locales/      # foundation i18n strings (en, da)
│   ├── pages/        # login, register, users, roles, settings/**, notifications
│   ├── stores/       # auth, users, roles, organizations, notifications, ui, ...
│   ├── types/
│   ├── config.ts     # appConfig (homeRoute, upgradeRoute, onboardingRoute)
│   ├── entitlements.ts # plan features/limits - a module provides them, else unlimited
│   ├── navigation.ts # sidebar + settings nav registries - modules register items
│   ├── banners.ts · routeGuards.ts # dashboard banners, extra navigation guards
├── billing/          # optional module: plans, subscriptions, Stripe checkout
│   ├── api/, stores/subscription.ts, components/, composables/, types.ts
│   ├── pages/        # settings/billing.vue, billing/success|cancel.vue
│   ├── entitlements.ts # the plan as the foundation's Entitlements + app-access guard
│   ├── notifications.ts # presenters for `billing.*` in-app notifications
│   ├── locales/      # subscription.*, notifications.billing.*, nav.subscription
│   └── index.ts      # manifest: messages + setup() registering all of the above
├── example/          # the product (self-contained vertical slice - replace it)
│   ├── api/projects.ts · stores/projects.ts · components/projects/
│   ├── pages/        # dashboard.vue, projects/index.vue
│   ├── components/, types/, constants.ts
│   ├── locales/      # product i18n strings, deep-merged over foundation messages
│   └── index.ts      # manifest (Module): messages, homeRoute, nav setup
├── brand.ts          # product identity: name, marketing + app origins
├── plugins/          # i18n setup (merges foundation + product messages)
├── router/           # Router config + navigation guards, seo.ts (head tags)
├── products.ts       # `products` and `modules` (billing + products) - the only runtime file naming them
└── main.ts           # assembly: runs each module's setup(), sets the homeRoute
```

**Foundation extension points** (how billing and the product hook in without the
foundation knowing about them): the `Module` manifest in `foundation/module.ts`,
`registerNavItems()` / `registerSettingsNavItems()` in `foundation/navigation.ts`,
`registerNotificationPresenter()` in `foundation/composables/useNotificationPresenter.ts`,
`configureApp()` in `foundation/config.ts`, `provideEntitlements()` in
`foundation/entitlements.ts`, `registerBanner()` in `foundation/banners.ts`,
`registerRouteGuard()` in `foundation/routeGuards.ts`, and the locale deep-merge in
`plugins/i18n.ts`. Foundation code asks `useEntitlements()` for plan features and
limits (`hasFeature`, `limitFor`) - never the billing store. To run without
billing, drop it from `src/products.ts` and `modulePackages` in
`products.config.js` and delete `src/billing/` (`node scripts/remove-billing.mjs`
does exactly that - CI runs it on a throwaway checkout and checks the app
again): every feature is then on, with no limits.

**Reusing this frontend for a new product**: edit `src/brand.ts`, then replace
`src/example/` - point the import in `src/products.ts` at your package's manifest
and change its folder name in `productPackages` in `products.config.js` (read by
`vite.config.ts` for pages/components and by the ESLint boundary rules).

**Product-provided i18n keys the foundation reads**: `planDescriptions.<PlanName>` and
`planComparisonRows` (read by billing's page), and optionally `seo.*` overrides. Everything else the foundation renders is defined in
the foundation locales; billing's strings are in `billing/locales`.

### Example product: Projects

- **`example/pages/projects/index.vue`** - `DataTable` list with search/sort, create/edit dialog (`ProjectForm.vue`), delete, and a `PlanQuota` bar for the `projects` plan limit (`useEntitlements().limitFor`).
- **`example/pages/dashboard.vue`** - authenticated home (`configureApp({ homeRoute: '/dashboard' })`).
- **`example/api/projects.ts`** + **`example/stores/projects.ts`** - `/projects` endpoints behind a gateway store.

Permissions: `read:project`, `create:project`, `update:project`, `delete:project`.

## Routing

Routes are auto-generated by `unplugin-vue-router` from merged page roots: `src/foundation/pages/**` plus each module's `pages/**` (`src/billing/pages/**`, `src/example/pages/**`; see `products.config.js` and `routesFolder` in `vite.config.ts`). No manual route definitions - adding a file in any root creates a route; a module's `pages/settings/x.vue` nests under the foundation's settings layout.

Route metadata is declared with YAML frontmatter in each page file:

```vue
<route lang="yaml">
meta:
  layout: dashboard # 'dashboard' | 'auth'
  requiresAuth: true
  permission: users:read # optional - guards the route
  breadcrumb: nav.users
</route>
```

The router guard in `src/router/index.ts` enforces `requiresAuth`, `guestOnly`, and `permission` checks.

## State Management

**`stores/auth.ts`** - Auth + authorization:

- `user`, `accessToken`, `permissions[]`, `organizations[]`
- `initialize()` - silent refresh from httponly cookie (called once on app load)
- `login()` / `logout()` / `switchOrganization()`
- `hasPermission(name)` - checks flattened permissions from user roles

**`stores/ui.ts`** - UI state:

- `sidebarOpen` - mobile sidebar toggle

## Data Access: Stores are the Gateway

**The rule: components and pages access server data only through a Pinia store. Never import `@/api/*` from a component or page.**

The layering is strict and one-directional:

```
component / page  →  store (gateway)  →  api module  →  client.ts (axios)
```

- **`api/*` modules** are an implementation detail of the store layer. They are imported _only_ by stores. They stay as thin, stateless functions wrapping a single endpoint.
- **`stores/*`** own every read and write for their domain. A store action makes the API call **and** updates store state in the same place, so state can never drift from the server. Callers never have to "call the API and then also patch the store" - that double-step is the anti-pattern this rule exists to kill.
- **Components/pages** call store actions and read store state (or getters). They hold only local UI state (form fields, dialog open/closed, loading flags for that component's own async calls).

Concretely, this is the pattern to avoid:

```ts
// WRONG - component calls the API directly, then manually re-syncs the store
await projectsApi.remove(id)
projectsStore.removeFromList(id)
```

```ts
// RIGHT - one store action does the call and the state update
await projectsStore.remove(id) // calls projectsApi.remove + mutates state internally
```

**Every server-data domain needs a store**, even if it's just a thin gateway with no cached state (e.g. `billing`, `users`, `roles`, `gdpr`, `auditLogs`, `permissions`). A "passthrough" store action that calls the api module and returns the result is the correct minimum - it keeps the access path uniform and gives one place to add caching/optimistic updates later.

Store ↔ api naming must match the domain (`stores/organizations.ts` ↔ `api/organizations.ts`). Don't split one domain's logic across a singular store and a plural api module.

## API Layer

`src/foundation/api/client.ts` - Axios instance with:

- Request interceptor: attaches `Authorization: Bearer <token>`
- Response interceptor: on 401, queues concurrent requests, refreshes token, retries - or clears session and redirects to login on failure
- `withCredentials: true` for httponly refresh token cookie

API modules (`api/auth.ts`, `api/users.ts`, etc.) export plain functions that call the shared client through its typed layer, `api` (also in `client.ts`):

```ts
api.get('/roles/{identifier}', { path: { identifier: id } }) // AxiosResponse<RoleOut>
api.post('/roles', { body: data })
api.get('/users', { query: params })
api.post('/auth/token', { form: { username, password } }) // form-encoded endpoints
```

The path, method, path params, body and response type are checked against the generated schema, so a wrong URL, a missing param or a stale response type fails `npm run typecheck`. Don't pass a response type yourself (`get<RoleOut>`) - it comes from the schema. Query params aren't checked (list filters are dynamic `field__op` keys). Use `apiClient` directly only for what the typed layer can't express. Add new endpoints in the relevant domain module. **These modules are imported only by stores (see "Data Access" above), never by components or pages.**

### API types are generated - never hand-write them

`src/api-schema.ts` is generated from `backend/openapi.internal.json`, the schema of every route that the backend writes (`uv run poe openapi`). The files in `foundation/types/` (and a product's `types/`) alias it by schema name: `export type RoleOut = Schema<'RoleOut'>` (`Schema` is in `foundation/types/api.ts`). A type with no backend schema (e.g. form state) stays hand-written. Narrow a generated field only where the backend declares a plain string the frontend relies on as a union - say so in a comment (see `foundation/types/billing.ts`).

After changing a backend request/response schema: `cd backend && uv run poe openapi`, then `npm run gen:api`, and commit the backend's schema files + `src/api-schema.ts` (the pre-commit hook does this when backend code changes). CI regenerates them and fails if they are out of date.

## Components

### UI Components (`components/ui/`)

Headless Reka UI + Radix Vue primitives styled with Tailwind. Do not modify these unless fixing a bug - treat as a library.

### Common Components

- **`DataTable`** - generic paginated table. Use with `useDataTable` composable for fetch/sort/filter/pagination logic
- **`PageHeader`** - standard page title + action slot
- **`ConfirmDialog`** - global confirmation modal, triggered via `useConfirm()`
- **`PermissionGuard`** - wraps content that requires a permission: `<PermissionGuard permission="users:write">`
- **`EmptyState`** - empty list state with title + description

### Writing Components

- Use `<script setup lang="ts">` exclusively
- Props: `defineProps<{ ... }>()`
- Emit types: `defineEmits<{ (e: 'update', val: string): void }>()`
- Loading state: local `ref<boolean>` + disable interactive elements during async ops
- Errors: catch in try/catch, pass to `useErrorHandler()` for translated toast messages

## Forms

Use VeeValidate + Zod:

```ts
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import * as z from 'zod'

const schema = z.object({ email: z.string().email() })
const { handleSubmit, errors } = useForm({ validationSchema: toTypedSchema(schema) })
```

Field errors render inline. API errors go through `useErrorHandler` → toast.

## Permissions

Check in templates with `PermissionGuard`, in logic with `usePermission()`:

```ts
const { hasPermission } = usePermission()
if (hasPermission('billing:write')) { ... }
```

Permission names follow `resource:action` convention (e.g., `users:read`, `roles:write`).

## Internationalization

All user-facing strings go through `vue-i18n`. Use `const { t } = useI18n()` in script, `$t('key')` in templates. Foundation strings live in `src/foundation/locales/{en,da}.ts`; product strings in `src/example/locales/{en,da}.ts`. Each product's manifest hands its trees over, and they are deep-merged in `src/plugins/i18n.ts`, so product files can extend shared namespaces (e.g. `nav.*`, `errors.fields.*`). Add keys to both locales of the owning package.

Key namespaces: `auth.*`, `nav.*`, `common.*`, `settings.*`, `errors.api.*`, `errors.fields.*`

## Testing

Component tests live in `tests/unit/`, mirroring the `src/` path of the code they test (`tests/unit/billing/pages/settings/billing.test.ts` tests `src/billing/pages/settings/billing.vue`), and run with Vitest in a simulated DOM (`happy-dom`, `@vue/test-utils`); `vitest.config.ts` reuses the Vite config. `billing.test.ts` is the model: mount the page per state with a real Pinia store whose API-calling actions are replaced by `vi.fn()`, mock `useConfirm`/`useToast` with `vi.mock`, then assert what the user sees and which store action a click calls. Look up visible text through i18n keys (`i18n.global.t(...)`), not hard-coded copy. Fixtures use the generated API types, so `npm run typecheck` flags fixtures that drift from the backend. CI runs `npm test`.

Foundation tests must not depend on billing or product content - their locale strings are merged in at runtime, so assert foundation keys only, and stub `useEntitlements` (`vi.mock('@/foundation/entitlements')`) rather than reaching into billing's store.

## Styling

Tailwind CSS with a CSS variable-based theme (HSL tokens defined in `src/assets/index.css`). Use `cn()` from `@/foundation/lib/utils` to merge classes conditionally. Dark mode is supported via the theme variables.

## Conventions

- **Components**: PascalCase filenames
- **Pages**: kebab-case filenames
- **Composables/utilities**: camelCase, `use` prefix for composables
- **API modules**: camelCase with `Api` suffix (e.g., `usersApi`)
- Path alias `@` maps to `src/`
- Auto-imported: Vue reactivity APIs, vue-router composables, Pinia helpers - no explicit imports needed for these
- Auto-registered: all components in `src/foundation/components/` and `src/example/components/` - no explicit imports needed
