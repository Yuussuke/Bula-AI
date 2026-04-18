# Bula AI

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white)

*A Retrieval-Augmented Generation (RAG) assistant bringing clarity to Brazilian medication leaflets through AI and clean architecture.*

> Preview space reserved for a future GIF/screenshot demonstrating the end-to-end flow.
>
> Suggested placement: upload a leaflet, ask a question, and show the grounded response.

Bula AI helps people understand Brazilian medication leaflets (bulas) through natural language questions. Users upload a PDF and receive responses grounded in retrieved passages from the document, reducing hallucination risk and improving answer traceability.

## Context and Objectives

This repository is intentionally written for two audiences: thesis reviewers and professional evaluators.

| Audience | Why Bula AI matters | What this repository demonstrates |
|---|---|---|
| Academic (TCC) | Applies AI to a relevant public-health communication problem in Brazil. | Problem framing, RAG methodology, architecture decisions, and technical rigor. |
| Professional (Portfolio) | Shows practical backend engineering for an AI product. | Modular architecture, testing strategy, migrations, observability, and DX tooling. |

Primary objectives:

- Improve accessibility of medication information without sacrificing reliability.
- Prioritize grounded responses using retrieval over free-form generation.
- Keep the codebase maintainable, testable, and reproducible.

## Current Scope

- User authentication with JWT.
- PDF leaflet upload and metadata management.
- Retrieval-oriented question answering flow.
- API-first backend for integration with frontend clients.
- Request tracing and structured logging for debugging and monitoring.

## Architecture Overview

The backend follows a modular monolith structure, organized by domain:

- auth
- bulas
- rag
- chat

Each module follows layered responsibilities:

- router: HTTP contract and response handling.
- service: business rules and orchestration.
- repository: database access.
- schemas: request and response validation.
- models: persistence mapping.

```mermaid
flowchart LR
   U[Client or Frontend] --> R[FastAPI Router]
   R --> S[Service Layer]
   S --> REPO[Repository Layer]
   REPO --> PG[(PostgreSQL)]
   S --> RET[Retriever Orchestration]
   RET --> Q[(Qdrant Vector Store)]
   RET --> LLM[Maritaca LLM]
   LLM --> S
   S --> R
   R --> U
```

## Tech Stack

- **Backend:** Python 3.12, FastAPI (async)
- **Database:** PostgreSQL
- **ORM and Migrations:** SQLAlchemy 2 async, Alembic
- **Auth:** JWT, Argon2id-based password hashing
- **AI and Retrieval:** LangChain, Maritaca API integration, Qdrant-ready retrieval architecture
- **Tooling:** uv, Ruff, pytest, pytest-asyncio, pytest-cov
- **Infrastructure:** Docker, Docker Compose, Makefile workflows

## Academic and Professional Quality Criteria

The project is developed with criteria that support both thesis evaluation and engineering quality:

- Clear problem definition and technical scope.
- Reproducible execution flow.
- Separation of concerns and consistent module boundaries.
- Automated tests for core behavior.
- Traceability through structured logs and correlation IDs.
- Versioned database evolution through migrations.

Example production-style structured log:

```json
{
   "event": "http_request_completed",
   "level": "info",
   "timestamp": "2026-04-18T19:32:51.287Z",
   "correlation_id": "3f8d98dd-ef74-40de-a8ac-2ed2f6f92909",
   "method": "POST",
   "path": "/api/v1/auth/login",
   "status_code": 200,
   "duration_ms": 87.42,
   "user_id": 12
}
```

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Make (recommended)

### Running the project

1. (Optional) Copy the example environment file and adjust values if needed:

   ```bash
   cp .env.example .env
   ```

   PowerShell alternative:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start all services with a single command:

   ```bash
   make up
   ```

   Docker Compose alternative:

   ```bash
   docker compose up -d
   ```

   Docker will build the backend image and start both the API and the database.

### Accessing the API

Once the containers are running, open your browser or use `curl` to reach the health-check endpoint:

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

The interactive API docs (Swagger UI) are also available at:

```
http://localhost:8000/docs
```

### API Testing with Bruno

The repository includes a ready-to-use Bruno collection in [Bruno/bula-ai-api](Bruno/bula-ai-api). The login request stores the JWT token automatically in the environment and authenticated requests reuse it via Bearer auth, improving developer experience when validating endpoints.

Main files:

- [Bruno/bula-ai-api/opencollection.yml](Bruno/bula-ai-api/opencollection.yml)
- [Bruno/bula-ai-api/Authentication/Login.yml](Bruno/bula-ai-api/Authentication/Login.yml)
- [Bruno/bula-ai-api/Authentication/get-my-profile.yml](Bruno/bula-ai-api/Authentication/get-my-profile.yml)

## Useful Commands

- Start services: `make up`
- Stop services: `make down`
- Follow logs: `make logs`
- Run migrations: `make migrate`
- Run tests: `make test`
- Run tests with coverage: `make test-cov`
- Lint: `make lint`
- Format: `make format`

## Roadmap

- Improve retrieval quality and context ranking.
- Expand chat experience and conversation memory handling.
- Add broader integration coverage for critical user flows.
- Consolidate evaluation metrics for academic reporting.

## Language Note

The engineering documentation, architecture terms, and commit history follow English conventions to align with global software standards. At the same time, the product domain, source documents, and NLP evaluation context are Brazilian Portuguese, because the real-world healthcare scenario addressed by this project is Brazilian.

## Note

This README is intentionally written as a public project showcase for both thesis reviewers and professional portfolio readers. Internal coding-agent rules and development constraints are documented in AGENTS.md.
