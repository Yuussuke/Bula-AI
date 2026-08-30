# Bula AI

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-pytest-0A9EDC?logo=pytest&logoColor=white)

*A Retrieval-Augmented Generation (RAG) assistant bringing clarity to Brazilian medication leaflets through AI and clean architecture.*

> Preview space for screenshot demonstrating the end-to-end flow.
><img width="1900" height="900" alt="image" src="https://github.com/user-attachments/assets/b9ae14d2-d798-44d9-868b-1afc51fc7448" />
> <br>
><img width="1900" height="900" alt="image" src="https://github.com/user-attachments/assets/508ba5e6-1918-4167-8823-a8894c06a661" />
>  <br>
> <img width="1900" height="900" alt="image" src="https://github.com/user-attachments/assets/8319776e-718f-4095-929f-a86ea82cc43d" />
> <br>
><img width="1900" height="900" alt="image" src="https://github.com/user-attachments/assets/c3e68a69-7995-4dcf-b235-bba389e42915" />
> 

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

- **Backend:** Python 3.14, FastAPI (async)
- **Database:** PostgreSQL 18 via the first-party `bula_ai_postgres` image
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
   The PostgreSQL service uses the first-party GHCR image
   `ghcr.io/yuussuke/bula_ai_postgres:18`. If the package visibility is
   private, authenticate with `docker login ghcr.io` before running `make up`.

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

The repository includes a ready-to-use Bruno collection in [bruno/bula-ai-api](bruno/bula-ai-api). The login request stores the JWT token automatically in the environment and authenticated requests reuse it via Bearer auth, improving developer experience when validating endpoints.

Main files:

- [bruno/bula-ai-api/opencollection.yml](bruno/bula-ai-api/opencollection.yml)
- [bruno/bula-ai-api/Authentication/Login.yml](bruno/bula-ai-api/Authentication/Login.yml)
- [bruno/bula-ai-api/Authentication/get-my-profile.yml](bruno/bula-ai-api/Authentication/get-my-profile.yml)
- [bruno/bula-ai-api/chat/direct-ask.yml](bruno/bula-ai-api/chat/direct-ask.yml)
- [bruno/bula-ai-api/bulas/upload-file.yml](bruno/bula-ai-api/bulas/upload-file.yml)

## Useful Commands

- Start services: `make up`
- Stop services: `make down`
- Follow logs: `make logs`
- Run migrations: `make migrate`
- Install PGQueuer objects: `make pgq-install`
- Upgrade PGQueuer objects: `make pgq-upgrade`
- Verify PGQueuer objects: `make pgq-verify`
- Verify PostgreSQL extensions and FTS: `make verify-postgres`
- Create an admin user: `make create-admin ARGS="--email admin@example.com --full-name 'Admin User'"`
- Discover ANVISA records: `make download-anvisa-bulas ARGS="--headless --discover Amoxicilina"`
- Download pinned ANVISA targets: `make download-anvisa-bulas ARGS="--headless --targets scripts/anvisa_targets.json --limit 1"`
- Preview the system seed: `make seed-system-bulas ARGS="--admin-email admin@example.com --dry-run"`
- Run tests: `make test`
- Run tests with coverage: `make test-cov`
- Lint: `make lint`
- Format: `make format`

Public registration through `/api/v1/auth/register` always creates regular
`user` accounts. Administrative users are created through the internal
management command exposed by `make create-admin`.

PDF ingestion runs through a separate PGQueuer worker. On a new local database,
run `make migrate` for application tables and `make pgq-install` for queue
tables before uploading bulas.

The ingestion worker relies on the Compose restart policy for database listener
resilience: `docker-compose.yml` runs it with `restart: always` and
`--shutdown-on-listener-failure`, so a broken PGQueuer listener exits and is
restarted by the supervisor instead of maintaining custom reconnect logic in the
application process. Jobs left in `picked` state by an interrupted worker become
eligible for another worker after
`RAG_INGESTION_STALE_JOB_RETRY_AFTER_SECONDS` (five minutes by default). Active
jobs send heartbeats and are not reclaimed while they continue processing.

For local or operator debugging, set `RAG_INGESTION_DEBUG=true` and optionally
`RAG_INGESTION_DEBUG_PATH=tmp/rag-ingestion-debug` before starting the API and
worker. Each ingestion run writes a manifest, parsed markdown, and chunking
result artifacts under the configured path. These files can contain parsed bula
text, so keep the path local/private and inspect warnings with `make logs`.

Small adjacent Markdown sections are grouped into fewer semantic chunking
requests by default. `PROCESSING_CHUNK_BATCH_MAX_TOKENS` controls the estimated
source-token budget for a combined request, while
`PROCESSING_CHUNK_BATCH_MAX_SECTIONS` limits response complexity. A section that
already exceeds the token budget remains a standalone request. Set
`PROCESSING_CHUNK_BATCH_ENABLED=false` to compare against the legacy
one-section-per-request behavior.

The model only proposes source-text boundaries. Before any chunk can reach the
embedding stage, the worker normalizes whitespace, reconstructs source spans,
and requires complete ordered coverage exactly once for every section. Chunk
titles come from the nearest validated Markdown heading, never from model
output. Unknown text, omissions, duplicate/reordered/overlapping spans, strict
JSON failures, truncation, provider errors, and timeouts all route directly to
the local deterministic Markdown splitter. There is no secondary semantic
model in this recovery path.

The deterministic splitter keeps Markdown tables and bullet items together
when they fit. Oversized tables split between rows with their header repeated;
oversized lists split between items. `PROCESSING_CHUNK_MAX_TOKENS` remains the
absolute final chunk limit, and no text is truncated to meet it.

Each OpenRouter chunking request has an explicit timeout configured through
`OPENROUTER_CHUNK_TIMEOUT_SECONDS` (60 seconds by default). SDK-level retries are
disabled by default with `OPENROUTER_CHUNK_MAX_RETRIES=0`. The deadline wraps
only the provider request; validation and deterministic fallback run locally
outside its cancellation scope. A failed batch falls back section by section in
the original source order without another provider request.

Semantic chunking defaults to the versioned `retrieval_v3` contract with
`google/gemini-3.1-flash-lite`, temperature `0`, seed `17`, and a 5,000-token
output cap. OpenRouter requests require supported parameters, ZDR routing, and
`data_collection=deny`; prompt/request bodies are never written to logs or
debug manifests. Model calls run sequentially until a later benchmark justifies
bounded concurrency. The local deterministic splitter is the only fallback.

Before manually reviewing three or four complete ingestions, compare the new
default against the former Gemini path on the six focused Dipirona/Amoxicilina
sections. This command uses the same prompt, request builder, validator,
fallback, diagnostics, parser, and configured embedding provider as the worker:

```bash
make benchmark-semantic-chunking
```

The ignored report at
`backend/tmp/semantic-chunking-benchmark/results.json` records source validity,
critical dosage/list preservation, latency, provider-reported usage/cost,
fallback rate, embedding vector count, and the generated chunks for manual
inspection. It contains no API key, provider request body, or prompt text.

### ANVISA system corpus

The system corpus uses an explicit discovery, selection, download, operator
validation, and seed workflow. The downloader runs on the host because
Playwright is a development dependency; the seed runs inside the API container.

Install the downloader dependency and its browser once:

```bash
cd backend
uv sync --dev
uv run playwright install chromium
cd ..
```

First discover the records returned by ANVISA without downloading a PDF:

```bash
make download-anvisa-bulas ARGS="--headless --discover Amoxicilina"
```

Discovery excludes the short-lived protected download tokens. It shows the
stable patient/professional source record IDs together with the ANVISA product
ID, registration, process, expedition, transaction, manufacturer, and source
timestamps. Never select a result using only an active ingredient or the newest
record from a manufacturer.

The repository contains one pinned candidate in
`backend/scripts/anvisa_targets.json` for the initial system seed. Verify its
exact product, strength, pharmaceutical form, presentation, audience, and source
record in the official Bulário before use. Use
`backend/scripts/anvisa_targets.example.json` only when adding another target.
The configured `expected_pdf_terms` must identify the product, strength, and
form in the selected PDF.

Download only the pinned targets and generate manifest schema version 2:

```bash
make download-anvisa-bulas ARGS="--headless --targets scripts/anvisa_targets.json --limit 1"
```

PDFs and the generated manifest are stored in
`backend/tmp/anvisa-bulas-v2/`, an ignored directory. The separate v2 directory
keeps legacy schema-version-1 downloads untouched and prevents them from being
resumed accidentally. Downloads are written to `.pdf.part`, parsed with the
same 10 MB limit used by uploads, checked for the configured identity terms,
and atomically moved into place. The manifest is also written atomically.

The manifest records the exact regulatory identity, canonical ANVISA query,
local filename, byte length, SHA-256 checksum, timestamps, and downloader
version. A file is reused only when its target and source identity match the
current result and its parsed bytes match the manifest. Changed sources, missing
files, checksum mismatches, partial files, corrupt PDFs, duplicate filenames,
and conflicting source identities are rejected or freshly downloaded. Schema
version 1 manifests are intentionally rejected. Legacy `review` metadata in a
schema-version-2 manifest is accepted but ignored.

Running the seed is the administrator's deliberate enqueue action. Before doing
so, the operator must inspect the selected manifest entry and PDF in the
official Bulário and confirm the product, strength, pharmaceutical form,
presentation, audience, manufacturer, registration, and source record. There is
no separate approval command or review-state edit in the local system-corpus
workflow.

With the API, worker, database, and queue running, preview one validated entry:

```bash
make seed-system-bulas ARGS="--admin-email admin@example.com --dry-run --limit 1"
```

Then execute the same operator-validated seed without `--dry-run`. The owner
must already be an active administrator. The command parses each PDF, validates
its size and checksum, creates bulas with `corpus=system`, and enqueues the
normal `ingest_bula` job. The exact ANVISA product name is stored as the bula
name and the canonical ANVISA query as its source URL.

### RAG ingestion observability

The PGQueuer ingestion worker emits structured logs for every RAG ingestion run.
Use `make logs` and filter by `run_id` or `bula_id` when multiple PDFs are being
processed at the same time.

Stable events:

- `rag_ingestion_started`: one log at the beginning of a run.
- `rag_ingestion_stage_started`: DEBUG-only marker for a stage start.
- `rag_ingestion_stage_finished`: one log per completed or failed stage.
- `rag_ingestion_finished`: final summary, emitted on success and failure.

Stable fields:

- Correlation: `log_schema_version`, `run_id`, `bula_id`, `doc_id`.
- Stage timing: `stage`, `stage_status`, `duration_ms`.
- Final summary: `ingestion_status`, `total_duration_ms`,
  `stage_durations_ms`, `slowest_stage`, `slowest_stage_duration_ms`.
- Safe counters/context: `pdf_size_bytes`, `extraction_tier`, `section_count`,
  `batch_count`, `model_call_count`, `batch_fallback_count`, `chunk_count`,
  `embedding_vector_count`, `qdrant_point_count`, `qdrant_collection`,
  `error_type`.

Example final summary:

```json
{
  "event": "rag_ingestion_finished",
  "run_id": "7b0f1c48-5c47-4bc7-845d-2b784f97b0bd",
  "bula_id": "11111111-1111-1111-1111-111111111111",
  "ingestion_status": "succeeded",
  "total_duration_ms": 5832.91,
  "stage_durations_ms": {
    "bula_lookup": 12.42,
    "mark_processing": 18.35,
    "object_metadata": 9.11,
    "pdf_download": 22.6,
    "pdf_parse_to_markdown": 741.84,
    "chunk_markdown": 3170.02,
    "write_debug_artifacts": 4.18,
    "embed_chunks": 1420.77,
    "qdrant_ensure_collection": 28.53,
    "qdrant_upsert": 381.09,
    "mark_ready": 24.0
  },
  "slowest_stage": "chunk_markdown",
  "slowest_stage_duration_ms": 3170.02
}
```

To answer "which step dominated this run?", inspect `slowest_stage` first, then
compare the ordered `stage_durations_ms` object for the full profile. The logs
intentionally do not include API keys, PDF bytes, parsed markdown, prompts, raw
model responses, or chunk text. Set `LOG_LEVEL=DEBUG` only when you need
per-section or per-batch chunking details such as `rag_section_chunked` and
`rag_chunking_batch_completed`.

Uploads are intentionally limited to 10 MB. Validation reads the PDF in chunks
and stops once the configured limit is exceeded; after validation, the current
local storage path reads the accepted file into memory. Raising this limit should
come with a DoS/memory review and a streaming object-storage strategy.

## PostgreSQL Image and Local Data

Local development and CI use the first-party PostgreSQL image
`ghcr.io/yuussuke/bula_ai_postgres:18`, which bundles pgvector, pgvectorscale,
pg_textsearch, and Portuguese full-text-search capabilities needed by the later
BM25 work.

Use `make verify-postgres` after `make up` to confirm that the running database
can create `vector`, `vectorscale`, `pg_textsearch`, and `unaccent` extensions
and execute Portuguese FTS.

When changing database image tags, prefer resetting the local database early:

```bash
make reset-db
```

This removes the Compose-managed database volume and reruns migrations. It is
destructive for local data. The Compose volume is declared as `postgres_data`;
Docker usually materializes it as `bula-ai_postgres_data`. PostgreSQL 18 mounts
this volume at `/var/lib/postgresql`, letting the image create its
major-version-specific data directory.

## Automated Dependency Updates

This repository uses Dependabot to keep dependencies up to date with controlled PR volume and clear review ownership.

- Configuration file: `.github/dependabot.yml`
- Schedule: weekly (Monday at 09:00)
- Reviewer: `Yuussuke`
- Ecosystems covered:
   - `uv` for backend Python dependencies (`/backend`)
   - `npm` for frontend dependencies (`/frontend`)
   - `docker` for backend image references (`/backend`)
   - `docker` for frontend image references (`/frontend`, pre-configured for future Dockerfile)
   - `docker` for the first-party PostgreSQL image (`/docker/bula_ai_postgres`)
   - `docker` for root Compose image references (`/`)
   - `github-actions` for workflow action versions (`/`)

Policy notes:

- Minor and patch dependency updates are grouped separately from major updates for `uv` and `npm`.
- Major Docker/runtime updates should be validated in staging before production rollout.
- The first-party PostgreSQL image tag mirrors its Dockerfile `FROM` tag and is versioned separately from application releases.
- PostgreSQL major upgrades and pgvector major upgrades require manual compatibility review.
- Security-driven updates should be prioritized, even when noise-reduction ignore rules are in place.

## Roadmap

- Improve retrieval quality and context ranking.
- Expand chat experience and conversation memory handling.
- Add broader integration coverage for critical user flows.
- Consolidate evaluation metrics for academic reporting.

## Language Note

The engineering documentation, architecture terms, and commit history follow English conventions to align with global software standards. At the same time, the product domain, source documents, and NLP evaluation context are Brazilian Portuguese, because the real-world healthcare scenario addressed by this project is Brazilian.

## Note

This README is intentionally written as a public project showcase for both thesis reviewers and professional portfolio readers. Internal coding-agent rules and development constraints are documented in AGENTS.md.
