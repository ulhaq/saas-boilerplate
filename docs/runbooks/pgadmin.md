# pgAdmin in Production

pgAdmin runs on the server as part of `docker-compose.yml`, but its port is
published on the server's loopback only (`127.0.0.1:5050`). It is not reachable
from the internet and is not proxied by nginx - the only way in is an SSH tunnel.

## Setup

Add these to the `BACKEND_ENV` GitHub secret (it becomes `/opt/app/.env` on deploy):

```
PGADMIN_EMAIL=you@yourdomain.com
PGADMIN_PASSWORD=<long random password>
```

Both are required - `docker compose` refuses to start (and the deploy fails)
if either is missing. They only seed the first login; pgAdmin stores the account
in its `pgadmin_data` volume, so changing them later has no effect - change the
password from inside pgAdmin instead.

Optionally set `PGADMIN_PORT` in the same secret to use a different loopback port.

## Connecting

```bash
ssh -N -L 5050:127.0.0.1:5050 <user>@<server>
```

Then open http://localhost:5050 and log in with the credentials above.
`-N` keeps the session open without a shell; stop the tunnel with Ctrl+C.

Register the database once (Servers → Register → Server), it is saved in the volume:

| Field | Value |
|-------|-------|
| Host | `postgres` (the compose service name) |
| Port | `5432` |
| Maintenance database | value of `DB_NAME` |
| Username / Password | `DB_USER` / `DB_PASSWORD` for app access, or `postgres` / `POSTGRES_PASSWORD` for superuser |

Prefer `DB_USER` for day-to-day inspection; use the superuser only when you need it.

## Checking it is not exposed

On the server:

```bash
ss -tlnp | grep 5050   # should show 127.0.0.1:5050, never 0.0.0.0:5050
```
