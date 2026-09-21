COMPOSE := docker compose -f docker-compose.dev.yml --env-file backend/.env

# Opt-in profiles from backend/.env (e.g. observability,analytics). A --profile
# flag replaces COMPOSE_PROFILES rather than adding to it, so up-local merges them.
comma := ,
ENV_PROFILES := $(shell sed -n 's/^COMPOSE_PROFILES=\([^[:space:]\#]*\).*/\1/p' backend/.env 2>/dev/null)

# Optional numeric argument after the target (e.g. `make up 1`) is an offset
# added to every published host port, so each git worktree can run its own
# stack side by side. `make up OFFSET=1` works too. Default offset is 0.
EXTRA := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
OFFSET := $(if $(EXTRA),$(firstword $(EXTRA)),0)

ifneq ($(OFFSET),$(shell printf '%s' '$(OFFSET)' | tr -cd '0-9'))
$(error port offset must be a number, got "$(OFFSET)")
endif

port = $(shell echo $$(( $(1) + $(OFFSET) )))

export BACKEND_PORT      := $(call port,8000)
export FRONTEND_PORT     := $(call port,5173)
export POSTGRES_PORT     := $(call port,5432)
export PGADMIN_PORT      := $(call port,5050)
export MAILPIT_SMTP_PORT := $(call port,1025)
export MAILPIT_UI_PORT   := $(call port,8025)
export UMAMI_PORT        := $(call port,3001)
export FARO_PORT         := $(call port,12347)

.PHONY: up up-local down build logs ps restart shell-backend shell-worker obs-up obs-down

# no-op rule so the numeric offset goal in `make up 1` isn't treated as a target
ifneq ($(EXTRA),)
.PHONY: $(EXTRA)
$(EXTRA):
	@:
endif

up:
	$(COMPOSE) up -d
	@echo "backend http://localhost:$(BACKEND_PORT)  frontend http://localhost:$(FRONTEND_PORT)  pgadmin http://localhost:$(PGADMIN_PORT)"

up-local:
	COMPOSE_PROFILES=local$(if $(ENV_PROFILES),$(comma)$(ENV_PROFILES)) $(COMPOSE) up -d
	@echo "backend http://localhost:$(BACKEND_PORT)  frontend http://localhost:$(FRONTEND_PORT)  pgadmin http://localhost:$(PGADMIN_PORT)  mailpit http://localhost:$(MAILPIT_UI_PORT)  umami http://localhost:$(UMAMI_PORT) (profile analytics)"

down:
	$(COMPOSE) --profile local --profile observability --profile analytics down --remove-orphans

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

restart:
	$(COMPOSE) restart

shell-backend:
	$(COMPOSE) exec backend bash

shell-worker:
	$(COMPOSE) exec worker bash

# Local monitoring stack (Grafana/Prometheus/Loki/Tempo, shared by all worktree
# stacks) plus this stack's Alloy agent. Set OTEL_EXPORTER_OTLP_ENDPOINT and
# LOG_FORMAT=json in backend/.env for the API/worker to report. See observability/README.md.
OBS := docker compose -f docker-compose.observability.yml -p observability

obs-up:
	$(OBS) up -d
	$(COMPOSE) --profile observability up -d alloy
	@echo "grafana http://localhost:3030 (admin/admin)"

obs-down:
	$(COMPOSE) --profile observability rm -sf alloy
	$(OBS) down
