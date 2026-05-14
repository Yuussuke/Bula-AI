.DEFAULT_GOAL := help

COMPOSE := docker compose
POSTGRES_IMAGE_NAME := bula_ai_postgres
POSTGRES_IMAGE_TAG := 18
POSTGRES_IMAGE := $(POSTGRES_IMAGE_NAME):$(POSTGRES_IMAGE_TAG)
POSTGRES_IMAGE_CONTEXT := docker/bula_ai_postgres

.PHONY: up down build rebuild logs shell build-postgres-image verify-postgres-image migrate pgq-install pgq-upgrade pgq-verify verify-postgres makemigrations create-admin test test-unit test-integration test-cov lint typecheck format reset-db help dependencies add-dependency

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
	docker run --rm \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_DB=postgres \
		--entrypoint verify-postgres-image \
		$(POSTGRES_IMAGE)

# --- Database ---
migrate:
	$(COMPOSE) exec api uv run alembic upgrade head

pgq-install:
	$(COMPOSE) exec api uv run pgq install

pgq-upgrade:
	$(COMPOSE) exec api uv run pgq upgrade

pgq-verify:
	$(COMPOSE) exec api uv run pgq verify --expect present

verify-postgres:
	$(COMPOSE) exec postgres sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -v ON_ERROR_STOP=1 \
		-c "CREATE EXTENSION IF NOT EXISTS vector;" \
		-c "CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;" \
		-c "CREATE EXTENSION IF NOT EXISTS pg_textsearch;" \
		-c "CREATE EXTENSION IF NOT EXISTS unaccent;" \
		-c "SELECT extname FROM pg_extension WHERE extname IN ('\''vector'\'', '\''vectorscale'\'', '\''pg_textsearch'\'', '\''unaccent'\'') ORDER BY extname;" \
		-c "SELECT to_tsvector('\''portuguese'\'', unaccent(U&'\''contraindica\00E7\00E3o'\'')) AS portuguese_fts_probe;"'

makemigrations:
	$(if $(MSG),,$(error Usage: make makemigrations MSG="describe what changed"))
	$(COMPOSE) exec api uv run alembic revision --autogenerate -m "$(MSG)"

create-admin:
	$(COMPOSE) exec -e ADMIN_PASSWORD api uv run python -m app.scripts.create_admin $(ARGS)

reset-db:
	$(COMPOSE) down -v && $(COMPOSE) up -d
	$(COMPOSE) exec postgres sh -lc 'until pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"; do sleep 1; done'
	"$(MAKE)" migrate
	"$(MAKE)" pgq-install

# --- Tests and quality ---
test:
	$(COMPOSE) up -d qdrant
	$(COMPOSE) exec api uv run pytest -v

# Run only backend unit tests inside the API container.
test-unit:
	$(COMPOSE) exec api uv run pytest -v tests/unit

# Run only backend integration tests inside the API container.
test-integration:
	$(COMPOSE) up -d qdrant
	$(COMPOSE) exec api uv run pytest -v tests/integration

test-cov:
	$(COMPOSE) exec api uv run --with pytest-cov pytest --cov=app --cov-report=term-missing

lint:
	$(COMPOSE) exec api uv run ruff check .

typecheck:
	$(COMPOSE) exec api uv run mypy app

lint-fix:
	$(COMPOSE) exec api uv run ruff check --fix .

format:
	$(COMPOSE) exec api uv run ruff format .

# --- Dependencies ---
dependencies:
	$(COMPOSE) run --rm api uv sync --frozen --no-dev
	$(COMPOSE) up -d --build api

add-dependency:
	$(if $(PACKAGE),,$(error Usage: make add-dependency PACKAGE="requests>=2.25.1"))
	$(COMPOSE) run --rm api uv add "$(PACKAGE)"
	$(MAKE) dependencies

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
	@echo "  make verify-postgres-image - Verify pgvector, pgvectorscale, pg_textsearch, unaccent, and FTS support"
	@echo "  make migrate        - Run database migrations"
	@echo "  make pgq-install    - Install PGQueuer database objects"
	@echo "  make pgq-upgrade    - Upgrade PGQueuer database objects"
	@echo "  make pgq-verify     - Verify PGQueuer database objects"
	@echo "  make verify-postgres - Verify extensions and FTS in the running PostgreSQL service"
	@echo "  make makemigrations - Generate a new migration (use MSG=\"...\")"
	@echo "  make create-admin   - Create an admin user inside the api container (optional ARGS=\"...\")"
	@echo "  make reset-db       - Destroy volumes and remigrate from scratch"
	@echo "  make test           - Run the test suite"
	@echo "  make test-unit      - Run backend unit tests"
	@echo "  make test-integration - Run backend integration tests"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make lint           - Check code style with Ruff"
	@echo "  make typecheck      - Check backend typing with mypy"
	@echo "  make lint-fix       - Automatically fix lint issues with Ruff"
	@echo "  make format         - Format code with Ruff"
	@echo "  make dependencies   - Sync dependencies from lockfile and rebuild api container"
	@echo "  make add-dependency - Add one dependency and sync (use PACKAGE=\"requests>=2.25.1\")"
	@echo ""
