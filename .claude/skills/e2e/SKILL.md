---
name: e2e
description: Run a named user flow end-to-end against the dev stack using the locust load-test script or a named playwright scenario. Supported flows: signup, login, billing, invite, org-switch.
argument-hint: <flow-name> [--users N] [--duration Ns]
---

# E2E

Run a named end-to-end user flow against the local dev stack.

## Arguments

The user invoked this with: $ARGUMENTS

Parse the arguments:
- First argument: flow name (e.g. `signup`, `login`, `billing`, `invite`, `org-switch`)
- `--users N`: number of concurrent users for load test (default: 1)
- `--duration Ns`: run duration in seconds (default: 30s)

## Prerequisites

Before running, verify the dev stack is up:

```bash
curl -s http://localhost:8000/health || echo "Backend not running"
curl -s http://localhost:5173 || echo "Frontend not running"
```

If either is down, remind the user to start the services:
- Backend: `cd backend && uv run fastapi dev src/main.py --host 0.0.0.0 --port 8000`
- Frontend: `cd frontend && npm run dev`

## Supported Flows

### Locust load test (all flows)

The project has a locust file at `backend/locustfile.py`. Run it headlessly for a quick smoke test:

```bash
cd backend && uv run locust -f locustfile.py --headless \
  --users <N> --spawn-rate 1 --run-time <duration> \
  --host http://localhost:8000 2>&1 | tail -30
```

### Flow-specific guidance

Read `backend/locustfile.py` to understand available tasks. Then map the flow name to relevant API paths:

| Flow | Key endpoints to exercise |
|---|---|
| `signup` | `POST /v1/auth/register`, `POST /v1/auth/login` |
| `login` | `POST /v1/auth/login`, `GET /v1/users/me` |
| `billing` | `GET /v1/billing/plans`, `POST /v1/billing/subscriptions` |
| `invite` | `POST /v1/organizations/{id}/invites`, `GET /v1/invites/{token}` |
| `org-switch` | `POST /v1/auth/switch-organization`, `GET /v1/users/me` |

For flows not covered by locust tasks, use `curl` to exercise the endpoints manually and verify responses:

```bash
# Example: test login flow
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access_token')
echo "Token: ${TOKEN:0:20}..."

curl -s http://localhost:8000/v1/users/me \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## Playwright

If a `playwright/` or `e2e/` directory exists in the project root, check for a script matching the flow name and run it:

```bash
ls playwright/ 2>/dev/null || ls e2e/ 2>/dev/null
```

If found: `npx playwright test --grep <flow-name>`

## Reporting

After the run, report:
- Which endpoints were hit
- HTTP status codes seen (flag any non-2xx)
- Response times if available from locust output
- Any errors or unexpected responses
