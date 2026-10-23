# Cross-bula chat (system corpus)

Authenticated `POST /api/v1/chat/ask` accepts `{question, mode}` (default
`hybrid`). It searches all eligible system leaflets, not an inferred target PDF.
Private and shared leaflets are excluded. Shared publication remains dependent
on #44; this is a partial delivery of #46, not full shared-corpus support.

The service authorizes ready, published system documents with matching stored
object checksum/size. Their IDs constrain dense/BM25 candidates **before** ranking
and Top-K. Retrieval validates chunk identity, section and text against PostgreSQL,
then supplies canonical document labels to selection/generation. Invalid candidates
are discarded without extra retrieval; counts are logged without source text.
An empty corpus skips the provider; no selected evidence uses existing abstention.
Publication metadata is checked again before saving; a change returns HTTP 409
without saving the answer. This is request-time validation, not a distributed
transaction across publication, vector retrieval and provider execution.

Responses retain numbered `source_chunks` and add deduplicated `source_bulas`.
New general-chat sources include chunk/document IDs, drug, manufacturer,
presentation, strength and canonical source URL. Metadata identifies the source;
it is not additional clinical evidence. Historical sources lacking these fields
remain readable. Source order and original citation numbers are not changed.

Sessions have explicit `scope` (`bula` or `cross_bula`). Apply `alembic upgrade head`
before serving the new backend. Existing sessions, including orphaned sessions,
remain `bula`; only newly created general sessions use `cross_bula` with null
`bula_id`. Continue via `/chat/sessions/{id}/messages`; ownership is unchanged.
`GET /chat/sessions` accepts optional `scope` and `bula_id` filters before pagination.
Saved history is historical evidence, not a guarantee of current publication.

This change does not enable RRF-B/BGE, retune prompts or reproduce the evaluated
runtime. Citation syntax checks do not establish semantic entailment, and Top-K
retrieval is not an exhaustive survey of all drugs. No frozen datasets, indexes,
snapshots or ingestion settings change. Tests use synthetic providers; real BM25
tests require a separately migrated `BM25_TEST_DATABASE_URL` containing `test`.

## Chat admission limits

All three paid chat endpoints share an authenticated-user sliding-window budget
(`CHAT_REQUESTS_PER_MINUTE`, default 10) and concurrent-request limit
(`CHAT_MAX_CONCURRENT_PER_USER`, default 1). Rejections return 429 and
`Retry-After: 60` before calling the chat service. Slots are released on success,
exception or cancellation. Read-only history is unaffected. State is in memory
per application process; multiple workers/replicas require a shared admission
store or gateway before claiming a deployment-wide quota. This is not a monetary
budget or a substitute for provider-side spending limits.
