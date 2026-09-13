# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product

**SaaS Boilerplate** - a multi-tenant B2B SaaS starter: auth, organizations, RBAC, Stripe billing with plan limits, audit log, GDPR tooling, email + in-app notifications, and a bilingual (da/en) prerendered marketing site.

Product-specific code lives in one package per side - `backend/src/example/` and `frontend/src/example/` - currently a minimal **Projects** feature (org-scoped CRUD, permissions, a `projects` plan limit, a hook handler, a worker loop, marketing pages). It exists to exercise every extension point; replace it with the real product.

Starting a new product from this template:
- Replace/rename the `example` package on both sides - see `docs/adding-a-domain-module.md`.
- Set the product identity in `frontend/src/brand.ts` (name, domains, support email, legal entity) and `APP_NAME` / `EMAIL_FROM_*` in `backend/.env`.
- Adapt plan seeds (initial migration + product migration), plan copy (`planComparisonRows` / `planDescriptions` in the product locales), and the legal page templates (`frontend/src/platform/pages/{terms,privacy-policy}.vue`).
- Replace `frontend/public/{favicon.svg,logo.png,og-image.png}`.

## Repository Structure

Full-stack multi-tenant SaaS:
- `backend/` - FastAPI + Python, PostgreSQL, async SQLAlchemy, Alembic migrations. See `backend/CLAUDE.md`.
- `frontend/` - Vue 3 + TypeScript, Vite, Pinia, file-based routing. See `frontend/CLAUDE.md`.

Both sides are split into a generic SaaS **platform** package and the
**product** package (`src/platform/` + `src/example/`), wired together by a thin
assembly layer (`bootstrap.py` / `main.ts`). The platform never imports product
code - enforced by import-linter (backend) and ESLint (frontend).

## Running Locally

**Recommended: Docker Compose** (runs postgres, mailhog, backend, worker, and frontend together):

```bash
cp backend/.env.example backend/.env   # fill in secrets
make up-local                          # starts all services + pgadmin + mailhog
make up-local 1                        # port offset: adds 1 to every host port (for parallel git worktree stacks)
make down                              # stop everything
make logs                              # tail all logs
```

Services: backend API on `:8000`, frontend on `:5173`, pgadmin on `:5050`, mailhog UI on `:8025`.

**Without Docker** (run each in a separate terminal, `cd` first):

```bash
# Terminal 1 - backend API
cd backend && uv run poe dev

# Terminal 2 - background worker (product loops, GDPR retention, billing cleanup)
cd backend && uv run python worker.py

# Terminal 3 - frontend
cd frontend && npm run dev
```

The frontend dev server proxies `/v1` → `localhost:8000`.

## Two-Process Backend Architecture

The backend runs as **two separate processes**:

| Process | Entry point | What it does |
|---------|-------------|--------------|
| **API** | `src/main.py` (uvicorn) | Handles HTTP requests |
| **Worker** | `worker.py` | Runs product loops (the example heartbeat), GDPR retention, billing cleanup, and trial reminder loops as concurrent asyncio tasks |

Adding a new background loop: implement a `run_X_loop(session_factory)` coroutine and register it as a task in `worker.py`. Never start background tasks inside `main.py`'s lifespan - horizontal API scaling would cause duplicate runs.

## Permission Flow (Backend → Frontend)

Platform permissions are a `Permission` StrEnum in `backend/src/platform/enums.py`; product permissions are `ExamplePermission` in `backend/src/example/enums.py`. The composition root (`backend/src/bootstrap.py`) merges both into the seeded `DEFAULT_ROLES`. At login, the API returns the user's flattened permission list; the frontend stores it in `stores/auth.ts` and checks it via `hasPermission()` / `usePermission()` / `<PermissionGuard>`.

When adding a new permission-gated feature:
1. Add the enum value: platform features in `backend/src/platform/enums.py`, product features in `backend/src/example/enums.py`
2. Add a human-readable description to the `PERMISSION_DESCRIPTIONS` / `EXAMPLE_PERMISSION_DESCRIPTIONS` map in the same file
3. Assign it to the appropriate default roles (`DEFAULT_ROLES` / `EXAMPLE_DEFAULT_ROLE_PERMISSIONS`)
4. Guard the backend route with `require_permission(Permission.X)`
5. Guard frontend UI with `<PermissionGuard permission="x:y">` or `hasPermission('x:y')`

## Email / Notifications

Outbound email uses SMTP (mailhog in local dev).
Templates live in `backend/src/platform/templates/` (platform emails) and an optional product `templates/` directory (product emails, registered in `bootstrap()`). The worker sends emails via `asyncio.to_thread(send_email, ...)` so SMTP calls don't block the event loop. In-app notifications are written to the `notification` table alongside each email dispatch.
