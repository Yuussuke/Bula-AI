.DEFAULT_GOAL := help

COMPOSE := docker compose
POSTGRES_IMAGE_NAME := bula_ai_postgres
POSTGRES_IMAGE_TAG := 0.8.1-pg16
POSTGRES_IMAGE := $(POSTGRES_IMAGE_NAME):$(POSTGRES_IMAGE_TAG)
POSTGRES_IMAGE_CONTEXT := docker/bula_ai_postgres
POSTGRES_VERIFY_CONTAINER := bula-ai-postgres-image-verify

.PHONY: up down build rebuild logs shell build-postgres-image verify-postgres-image migrate makemigrations create-admin test test-cov lint format reset-db help dependencies add-dependency

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

build-postgres-image:
	docker build -t $(POSTGRES_IMAGE) $(POSTGRES_IMAGE_CONTEXT)

verify-postgres-image: build-postgres-image
	@set -e; \
	docker rm -f $(POSTGRES_VERIFY_CONTAINER) >/dev/null 2>&1 || true; \
	docker run -d \
		--name $(POSTGRES_VERIFY_CONTAINER) \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_DB=postgres \
		$(POSTGRES_IMAGE) >/dev/null; \
	cleanup() { docker rm -f $(POSTGRES_VERIFY_CONTAINER) >/dev/null 2>&1 || true; }; \
	trap cleanup EXIT; \
	echo "Waiting for temporary PostgreSQL container..."; \
	for attempt in 1 2 3 4 5 6 7 8 9 10; do \
		if docker exec $(POSTGRES_VERIFY_CONTAINER) pg_isready -U postgres -d postgres >/dev/null 2>&1; then \
			break; \
		fi; \
		if [ "$$attempt" = "10" ]; then \
			docker logs $(POSTGRES_VERIFY_CONTAINER); \
			exit 1; \
		fi; \
		sleep 2; \
	done; \
	docker exec $(POSTGRES_VERIFY_CONTAINER) psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
		-c "CREATE EXTENSION IF NOT EXISTS vector;" \
		-c "CREATE EXTENSION IF NOT EXISTS unaccent;" \
		-c "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'unaccent') ORDER BY extname;" \
		-c "SELECT to_tsvector('portuguese', unaccent('contraindicação')) AS portuguese_fts_probe;"

# --- Database ---
migrate:
	$(COMPOSE) exec api uv run alembic upgrade head

makemigrations:
	@msg="$(MSG)"; \
	if [ -z "$$msg" ]; then \
		read -p "Migration message: " msg; \
	fi; \
	$(COMPOSE) exec api uv run alembic revision --autogenerate -m "$$msg"

create-admin:
	$(COMPOSE) exec -e ADMIN_PASSWORD api uv run python -m app.scripts.create_admin $(ARGS)

reset-db:
	$(COMPOSE) down -v && $(COMPOSE) up -d
	sleep 3
	make migrate

# --- Tests and quality ---
test:
	$(COMPOSE) exec api uv run pytest -v

test-cov:
	$(COMPOSE) exec api uv run --with pytest-cov pytest --cov=app --cov-report=term-missing

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
	@echo "  make build-postgres-image  - Build the first-party PostgreSQL image"
	@echo "  make verify-postgres-image - Verify pgvector, unaccent, and FTS support"
	@echo "  make migrate        - Run database migrations"
	@echo "  make makemigrations - Generate a new migration (prompts for message; or use MSG=\"...\")"
	@echo "  make create-admin   - Create an admin user inside the api container (optional ARGS=\"...\")"
	@echo "  make reset-db       - Destroy volumes and remigrate from scratch"
	@echo "  make test           - Run the test suite"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make lint           - Check code style with Ruff"
	@echo "  make lint-fix       - Automatically fix lint issues with Ruff"
	@echo "  make format         - Format code with Ruff"
	@echo "  make dependencies   - Sync dependencies from lockfile and rebuild api container"
	@echo "  make add-dependency - Add one dependency and sync (prompts for package name)"
	@echo ""
