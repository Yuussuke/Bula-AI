.DEFAULT_GOAL := help

COMPOSE := docker compose

.PHONY: up down build rebuild logs shell migrate makemigrations test test-cov lint format reset-db help dependencies add-dependency

# --- Docker ---
build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

rebuild: build up

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

shell:
	$(COMPOSE) exec api bash

# --- Database ---
migrate:
	$(COMPOSE) exec api uv run alembic upgrade head

makemigrations:
	@msg="$(MSG)"; \
	if [ -z "$$msg" ]; then \
		read -p "Migration message: " msg; \
	fi; \
	$(COMPOSE) exec api uv run alembic revision --autogenerate -m "$$msg"

reset-db:
	$(COMPOSE) down -v && $(COMPOSE) up -d
	sleep 3
	make migrate

# --- Tests and quality ---
test:
	$(COMPOSE) exec api uv run pytest -v

test-cov:
	$(COMPOSE) exec api uv run pytest --cov=app --cov-report=term-missing

lint:
	$(COMPOSE) exec api uv run ruff check .

lint-fix:
	$(COMPOSE) exec api uv run ruff check --fix .

format:
	$(COMPOSE) exec api uv run ruff format .

# --- Dependencies ---
dependencies:
	$(COMPOSE) run --rm api uv sync --frozen --no-dev
	$(COMPOSE) up -d --build api

add-dependency:
	@read -p "Package name (e.g. requests or requests@2.25.1): " package; \
	$(COMPOSE) run --rm api uv add "$$package"; \
	make dependencies

# --- Help ---
help:
	@echo ""
	@echo "  make build          - Build the Docker images"
	@echo "  make up             - Start the containers in the background"
	@echo "  make rebuild        - Build images and start containers"
	@echo "  make down           - Stop and remove containers"
	@echo "  make logs           - View real-time logs"
	@echo "  make shell          - Access the api bash shell"
	@echo "  make migrate        - Run database migrations"
	@echo "  make makemigrations - Generate a new migration (prompts for message; or use MSG=\"...\")"
	@echo "  make reset-db       - Destroy volumes and remigrate from scratch"
	@echo "  make test           - Run the test suite"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make lint           - Check code style with Ruff"
	@echo "  make format         - Format code with Ruff"
	@echo "  make dependencies   - Sync dependencies from lockfile and rebuild api container"
	@echo "  make add-dependency - Add one dependency and sync (prompts for package name)"
	@echo ""
