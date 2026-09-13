COMPOSE := docker compose -f docker-compose.dev.yml --env-file backend/.env

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
export MAILHOG_SMTP_PORT := $(call port,1025)
export MAILHOG_UI_PORT   := $(call port,8025)
export UMAMI_PORT        := $(call port,3001)

.PHONY: up up-local down build logs ps restart shell-backend shell-worker

# no-op rule so the numeric offset goal in `make up 1` isn't treated as a target
ifneq ($(EXTRA),)
.PHONY: $(EXTRA)
$(EXTRA):
	@:
endif

up:
	$(COMPOSE) up -d
	@echo "backend http://localhost:$(BACKEND_PORT)  frontend http://localhost:$(FRONTEND_PORT)"

up-local:
	$(COMPOSE) --profile local up -d
	@echo "backend http://localhost:$(BACKEND_PORT)  frontend http://localhost:$(FRONTEND_PORT)  pgadmin http://localhost:$(PGADMIN_PORT)  mailhog http://localhost:$(MAILHOG_UI_PORT)  umami http://localhost:$(UMAMI_PORT)"

down:
	$(COMPOSE) --profile local down --remove-orphans

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
