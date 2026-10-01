# Backend Setup Notes

This backend uses Alembic + SQLAlchemy async with PostgreSQL.

## 1) Environment variables

Provide the required environment variables for Docker Compose.

This project is Docker-first:

- `DATABASE_URL` is injected into the `api` container by Docker Compose.
- `SECRET_KEY` must be provided via your `.env` file (see `.env.example`).
- The local PostgreSQL service uses `ghcr.io/yuussuke/bula_ai_postgres:18`.
  If the GHCR package is private, authenticate with `docker login ghcr.io`
  before starting the stack.

## 2) Migrations (recommended flow)

Run migrations from container to avoid host/DNS mismatches:

```bash
make up
make verify-postgres
make migrate
make pgq-install

# Option A (interactive):
make makemigrations

# Option B (non-interactive):
MSG="your_message" make makemigrations
```

PGQueuer owns its own queue tables. Use `make pgq-install` on a fresh database,
`make pgq-upgrade` during deploys, and `make pgq-verify` when checking the
queue schema.

## 3) Management commands

Create administrators from inside the Docker workflow:

```bash
make create-admin ARGS="--email admin@example.com --full-name 'Admin User'"
```

The command prompts for the password securely. For non-interactive environments,
set `ADMIN_PASSWORD` before running the make target. Public self-registration
never accepts a role and always creates `user` accounts.

## 4) Common DNS error

If you get `socket.gaierror: [Errno 11001] getaddrinfo failed`,
the hostname in `DATABASE_URL` is not resolvable in the current execution context.

This usually happens when running commands outside Docker while using the Docker-only hostname `postgres`.

- Recommended fix: run migrations via `make migrate` / `make makemigrations` (inside the container).

## 5) PostgreSQL image and local reset

The project uses a first-party PostgreSQL 18 image with pgvector, pgvectorscale,
pg_textsearch, and PostgreSQL full-text-search support. Verify the running
database with:

```bash
make verify-postgres
```

When switching database image tags, use the Docker-first reset flow:

```bash
make reset-db
```

This removes the local Compose database volume and reruns migrations, so it is
destructive for local data. The volume is declared as `postgres_data` in
`docker-compose.yml` and is usually materialized by Docker as
`bula-ai_postgres_data`. PostgreSQL 18 mounts it at `/var/lib/postgresql` so the
image can create its major-version-specific data directory.

## 6) RAG evidence decisions

For every leaflet question, the chat retrieves chunks from the selected
bula and deterministically divides them into evidence units: complete prose
sentences, whole list items, and table rows with their header. The model selects
unit IDs, not quotes or a patient-facing answer. The backend resolves those IDs
against the current retrieved chunks and displays the original text with citations.
The selector also returns one of three support levels:

- `supported`: the units directly answer the question. The answer cites them
  without a generic "insufficient evidence" disclaimer.
- `partially_supported`: the units are relevant but do not establish the
  requested conclusion. The answer shows them and states the limitation.
- `insufficient`: no pertinent unit was selected. The answer abstains without
  citing unrelated chunks.

Evidence selection and validation are the default, not a route enabled by a
keyword-based medical-risk classifier. Simple identification, indication,
concentration, and storage questions use the same contract. The deterministic
allergy selector is retained as an optimization but also returns validated IDs.
There is no free-generation fallback if selection fails. Administrative history
and legal/prescription footer chunks remain excluded from answer evidence.
Adjacent excerpts from the same source share one section label; source citations
are numbered by retrieval relevance rather than the model's selection order.

These levels are **not** a medical-risk score. The pipeline checks that selected
IDs exist in the current retrieved chunk set. If the model returns
invalid JSON or an unknown ID, the answer uses a separate verification
failure message; if retrieval returns no usable chunks, it uses a no-context
message. Logs record only `retrieval`, `support`, and `verification` labels under
`rag_evidence_decision`, not the question or leaflet text.

There is one evidence-selection call and no automatic retry. Changing this
decision policy requires separate evaluation of other bulas and edge cases.

This check verifies fidelity to the *indexed chunk*, not fidelity of the chunk
to the original PDF. A malformed table or a missed section still requires
parser/retrieval validation. Before relying on new bulas, compare the source PDF,
parsed Markdown, retrieved chunks, and answers for representative questions.
### Response diagnostics

Response instrumentation does not change prompts, retrieval strategy, public
response schemas, provider calls, or patient-facing messages. It does not perform
semantic claim verification or corrective retrieval.

Structured events share a per-invocation `diagnostic_id`:

- `rag_response_stage`: `retrieval`, `context_preparation`, `evidence_selection`, and `answer_validation`,
  with elapsed milliseconds, execution status and a safe failure category.
- `rag_context_candidates`: candidate, usable-document and evidence-unit counts.
  A successful retrieval can still leave no usable documents after filtering.
- `rag_evidence_decision`: the existing support decision and a specific rejection
  or abstention reason. `claim_verification` and `generation_status` remain
  `not_implemented`: valid evidence IDs do not prove semantic entailment.

Selection rejection reasons distinguish `invalid_json`,
`invalid_selection_schema`, `unknown_evidence_id`, and
`allergy_target_mismatch`. Valid model-declared insufficiency is
`insufficient_context`; zero usable documents is `no_usable_documents`.
Timeouts, provider failures and internal exceptions are logged by the failing
stage and re-raised unchanged, never converted into insufficient context.

No question, leaflet text, model response, exception message, credentials or
provider request body is emitted by this instrumentation. Use the request's
correlation context and diagnostic ID to inspect one invocation in API logs.

For a manual regression, repeat the virose question in Swagger and inspect the
events for that invocation. A rejected selection now reports why it failed;
historical failures without these events cannot be reconstructed precisely.
Automated contract tests use controlled model/retriever doubles and do not measure
real-model answer quality or retrieval Recall@K. Continue manual tests for virose,
cephalosporin allergy, diabetes, explicit AAS restrictions and pediatric tables.

`tests/fixtures/rag/evidence_selection_cases.json` contains 12 auxiliary
development scenarios with frozen multiple evidence units and gold ID sets.
The isolated benchmark evaluates raw model-selected IDs, not the clinical
postprocessor or renderer. It is not a new application stage or the main TCC
evaluation. See [isolated selection benchmark](tests/fixtures/rag/evidence_selection_benchmark.md)
for annotation, metric denominators, limitations and execution commands.
`tests/integration/rag/test_evidence_selection_live.py` remains skipped by
default. Set `RUN_LIVE_EVIDENCE_TESTS=1` only when explicitly authorizing fixture
transmission to the configured LLM provider and API consumption.
Run it with `uv run pytest tests/integration/rag/test_evidence_selection_live.py -s`.
`LLM_PROVIDER=auto` selects Maritaca as primary and may use OpenRouter as fallback;
an OpenRouter chat-model setting alone does not select OpenRouter as primary.
The opt-in test reports all cases before checking exact ID sets, so known
selection differences may fail it. Do not enable it in ordinary CI. It isolates
selection, not retrieval or full generation.
The [evidence-selection progression](tests/fixtures/rag/evidence_selection_progression.md)
records the frozen baseline, model comparison, paraphrase check and Thinking
comparison. These are development diagnostics, not a clinical validation.

## Consolidated evidence selection

Both the model and the existing deterministic allergy path now emit one contract:
`unit_ids` (at most six source IDs in total) and `limitation` (required, either
null, `scope`, `individual`, or `missing`). No summaries or lists of hypothetical
gaps are requested. No automatic legacy-contract decoding remains.

Empty IDs mean insufficient evidence, regardless of the limitation field: there
is no selected source to qualify. Decision logs omit an inapplicable limitation.
Otherwise null means the source answers
the actual question. A limitation means evidence answers part of the question,
but a necessary conclusion remains without documentary support. It is not a
generic clinical caveat: an explicit condition of use or a source-delimited
purpose contrast can fully answer the documentary question without deciding
individual treatment. An explicit presentation/group restriction does not require
unsolicited individual data. A caution must not become permission or prohibition.
Selected units must support, contradict or bound the asked proposition; shared
topic, section or medication alone is not evidence. See
[isolated selection benchmark](tests/fixtures/rag/evidence_selection_benchmark.md)
for the reviewed golds and primary evidence metrics. This remains extractive selection, not generation or
semantic verification. No new retrieval strategy, additional model stage, ingestion
changes, or migrations are introduced.

Front matter is excluded from evidence units without changing indexed documents.
Only source-body units can be selected. A complete JSON/unlabelled Markdown fence
is accepted without extra prose; JSON repair and fragment extraction are not.

Original JSON and schema exceptions are retained by the validator. Safe logs
include JSON line/column or schema issue types and known field locations; input,
exception prose and unknown field names are not emitted. Decision logs retain
stage statuses and reasons, with `selected_unit_count` and `limitation`.

Restart only the experimental API process after editing the mounted worktree,
then test its Swagger on port 8001. This change does not require reindexing.
Parser-version audits must compare index text with matching ingestion artifacts;
the running parser version does not prove which version produced stored chunks.

### Provider-side JSON contract

Evidence selection sends a strict `response_format` JSON Schema derived from
`ContextAssessment`, through the existing LCEL chain. The Maritaca adapter now
uses `ChatOpenAI` with `https://chat.maritaca.ai/api`, as described in the
[official LangChain integration](https://docs.maritaca.ai/pt/examples/langchain).
OpenRouter routing requires support for requested parameters. The same schema
is forwarded to the transient fallback, not silently replaced with free text.

The provider schema omits `maxItems`, unsupported by Maritaca's documented
[schema subset](https://docs.maritaca.ai/pt/structured-outputs); the six-ID bound
is still enforced locally. JSON syntax, field types, extra-field rejection,
source-ID ownership and authorization remain enforced. There is no JSON repair,
legacy schema conversion, semantic verifier, or model-answer revision.

Structured output addresses format, not correctness of evidence selection.
The default Maritaca chat model is `sabia-4`; `MARITACA_MODEL` can override it.
This setting supplies the chat LLM used by the RAG chain, including evidence
selection. The isolated model comparison supported this default on its frozen
12-case development set; it did not evaluate the entire chat pipeline or
additional medications. See the
[progression report](tests/fixtures/rag/evidence_selection_progression.md).
