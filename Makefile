.DEFAULT_GOAL := help
.PHONY: up down build rebuild logs shell migrate makemigrations test test-cov lint format reset-db help

# --- Docker ---
build:
	docker compose build

up:
	docker compose up -d

rebuild: build up

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec api bash

# --- Database ---
migrate:
	docker compose exec api uv run alembic upgrade head

makemigrations:
	@read -p "Migration message: " msg; \
	docker compose exec api uv run alembic revision --autogenerate -m "$$msg"

reset-db:
	docker compose down -v && docker compose up -d
	sleep 3
	$(MAKE) migrate

# --- Testes e Qualidade ---
test:
	docker compose exec api pytest

test-cov:
	docker compose exec api pytest --cov=app --cov-report=term-missing

lint:
	docker compose exec api ruff check .

format:
	docker compose exec api ruff format .

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
	@echo "  make makemigrations - Generate a new migration (prompts for message)"
	@echo "  make reset-db       - Destroy volumes and remigrate from scratch"
	@echo "  make test           - Run the test suite"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make lint           - Check code style with Ruff"
	@echo "  make format         - Format code with Ruff"
	@echo ""