# Observability

Self-hosted logs, metrics, traces, browser errors and alerting with the Grafana
stack. Everything is **off by default**; the app runs unchanged without it.

```
APP HOST (docker-compose.yml, profile `observability`)       MONITORING HOST (docker-compose.observability.yml)
┌──────────────────────────────────────────────┐             ┌───────────────────────────────────────────┐
│ backend / worker ── OTLP traces+metrics ─┐   │             │ Prometheus :9090  metrics (OTLP receiver) │
│ container stdout (JSON logs) ─ docker ───┼─▶ Alloy agent ──┼▶ Loki       :3100  logs                   │
│ browser ── /collect (host nginx) ─ Faro ─┘   │             │ Tempo      :4318  traces                  │
└──────────────────────────────────────────────┘             │ Grafana    :3030  dashboards + alerts     │
                                                             └───────────────────────────────────────────┘
```

| Signal | Source | Where it lands |
|---|---|---|
| Request traces (FastAPI, SQL, outgoing Stripe HTTP) | `src/platform/core/telemetry.py` | Tempo |
| HTTP metrics (rate, status, latency per route) | FastAPI instrumentation | Prometheus `http_server_request_duration_seconds_*` |
| Worker loops (runs, failures, duration, last success) | `track_worker_run()` | Prometheus `worker_*` |
| Stripe webhook outcomes | `record_webhook_event()` | Prometheus `billing_webhook_events_total` |
| Logs (redacted, with `trace_id`) | container stdout, `LOG_FORMAT=json` | Loki, labels `service_name`, `level` |
| Browser errors + web vitals | `frontend/src/platform/lib/telemetry.ts` (Faro) | Loki `{service_name="browser"}` |

Provisioned from this directory (edit the files, not the UI): data sources with
log ↔ trace links, the **App overview** dashboard, and alert rules emailed to
`ALERT_EMAIL`:

| Alert | Fires when |
|---|---|
| API 5xx error rate above 5% | for 5 min |
| API p95 latency above 1s | for 10 min |
| Worker loop overdue | a loop hasn't succeeded for 2x its interval, or the worker stops reporting |
| Worker loop failing | any loop iteration raised in the last hour |
| Stripe webhook failures | any webhook ended `failed` (permanent) or `retry` (transient) in 15 min |
| Frontend exception spike | > 20 browser exceptions in 10 min |

## Local development

```bash
make obs-up          # monitoring stack + this dev stack's Alloy agent; Grafana: http://localhost:3030 (admin/admin)
make obs-down
```

Then enable reporting in `backend/.env` and recreate the stack (`make up-local`):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4318
LOG_FORMAT=json          # Loki reads level/trace_id from JSON lines
COMPOSE_PROFILES=observability
```

and in `frontend/.env`: `VITE_FARO_URL=/collect` (the vite dev server proxies it
to the agent). Alert emails go to the dev stack's Mailpit (http://localhost:8025).

Processes run on the host (`uv run poe dev`) can't resolve `alloy`; leave
`OTEL_EXPORTER_OTLP_ENDPOINT` unset for those. Tests never export.

## Production

1. **Monitoring host** (a separate small server, so monitoring survives the app
   host failing; the same server works too):
   ```bash
   cp observability/.env.example observability/.env   # admin password, SMTP, ALERT_EMAIL, OBSERVABILITY_INGEST_BIND
   docker compose -f docker-compose.observability.yml -p observability --env-file observability/.env up -d
   ```
   The ingest ports (9090, 3100, 4318) accept **unauthenticated writes**: bind
   them to a private network address (e.g. a Hetzner private network) and allow
   only the app host in the firewall. Docker-published ports bypass `ufw`.
   Grafana binds to `127.0.0.1:3030` by default; put it behind nginx with TLS,
   or reach it over an SSH tunnel.

   **Same server as the app:** let the deploy run it instead - put the contents
   of `observability/.env` in an `OBSERVABILITY_ENV` repository secret. Each
   deploy copies this directory, writes the `.env` and recreates the stack, so
   dashboard/alert edits ship with the app. Set
   `OBSERVABILITY_INGEST_BIND=172.17.0.1` (the `docker0` bridge address) so the
   ingest ports are reachable from the agent but not from the internet, and
   leave `OBSERVABILITY_HOST` unset on the app side (it defaults to
   `host.docker.internal`, which resolves to that address).

2. **App host** - add to the `BACKEND_ENV` secret (it is also the compose `.env`):
   ```bash
   COMPOSE_PROFILES=observability
   OBSERVABILITY_HOST=10.0.0.3            # the monitoring host's private address
   OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4318
   LOG_FORMAT=json
   ```
   The deploy copies `observability/` to the server and starts the agent with
   the stack.

3. **Browser telemetry** - add `VITE_FARO_URL=/collect` to the `FRONTEND_ENV`
   secret and the `/collect` location from `etc.nginx.sites-available.example` to
   the host nginx.

## Privacy

- Logs are redacted before they leave the process (`src/platform/core/logging.py`);
  traces record SQL with bind placeholders, never values.
- Faro runs without session tracking and without user identity, so nothing is
  stored in the visitor's browser (no cookie consent needed). URL parameters
  carrying secrets (`?token=`, ...) are redacted before sending
  (`scrubUrls` in `frontend/src/platform/lib/telemetry.ts`).
- The agent needs the Docker socket to read container logs, which is
  root-equivalent access on the app host.
- Mention error monitoring in your privacy policy.

## Extending

- New background loop: wrap each iteration in
  `with track_worker_run("name", interval_seconds):` - it appears on the
  dashboard and in both worker alerts automatically.
- New metric: create an instrument from `_meter` in `telemetry.py` (instruments
  are no-ops until telemetry is enabled). OTLP names map to Prometheus as
  `a.b.c` + unit `s` → `a_b_c_seconds`, counters get `_total`.
- Dashboards/alerts: edit `grafana/dashboards/*.json` and
  `grafana/provisioning/alerting/rules.yaml`, then restart Grafana.
