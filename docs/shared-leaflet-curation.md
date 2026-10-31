# Shared leaflet curation

Shared PDFs follow a separate, authenticated workflow. The ANVISA system catalog
and private uploads retain their existing behavior.

| Role | Permissions |
| --- | --- |
| User | Read available shared leaflets and query them |
| Contributor | Submit an identified PDF and follow their submissions |
| Curator (`reviewer`) | Inspect originals, approve, reject, withdraw and retry failed ingestion |
| Administrator | Designate roles, submit and perform curation |

Administrators designate Contributors and Curators with a recorded justification.
The application does not verify professional credentials automatically. Curators
are intended to be designated health professionals; documentary approval is not
clinical certification. No submitter, including an administrator, may approve or
reject their own submission. Public registration cannot assign these roles.

## Workflow and integrity

1. Submit a PDF (maximum 10 MB), its declared product name, optional manufacturer,
   HTTPS source URL and description. Non-ANVISA
   sources are accepted and identified separately. URLs are citations, never
   downloaded by the server. Uploading alone does not enqueue ingestion.
2. Inspect the stored original and record a reasoned decision against its current
   revision. Confirm/correct the product name and available manufacturer; optional
   presentation/strength fields must come from the document. The parser cannot
   later overwrite this reviewed shared identity. Private metadata extraction is unchanged.
3. Approval, its audit event and its PGQueuer job commit in **one PostgreSQL
   transaction**, using PGQueuer's public driver on the ORM-managed connection.
   Availability requires approval, its audit event, successful ingestion and
   matching stored-object checksum/size. There is no second publication step.
4. Failed ingestion remains unavailable. A Curator can explicitly retry, with a
   new version and audit event. Queue deduplication prevents duplicate active
   jobs. An enqueue failure or interruption rolls back the entire action and
   returns a technical error. Legacy approved/pending records without a recorded
   job can be explicitly recovered after checking that no job is active.
5. Withdrawal removes the document from future queries without deleting its
   history or indexed chunks. It remains possible if the original is damaged.
   Rejected/withdrawn submissions are final; a replacement requires a new upload.
   The same PDF bytes cannot have two pending/approved shared submissions, even
   with different names or URLs. After rejection/withdrawal, a new submission
   links to the previous record and requires a fresh decision. This is byte-level
   shared-PDF deduplication, not detection of equivalent texts across all corpora.

Decision updates use optimistic concurrency: only one decision for a given
revision can commit, together with its event. Stale decisions return HTTP 409.
The upload identity and source have no edit endpoint. Owners and staff can view
decision histories; other readers do not receive reviewer identities or notes.

## Idempotency and audit

Shared submissions, decisions and role assignments require a UUID in the
`Idempotency-Key` header. Within each mutation domain, an actor's repeated key
and normalized request fingerprint return `replayed: true` without another
decision, role change or job. Reusing a key with different contents returns 409.
Responses contain the **current resource state**, not a stale original snapshot.
The client retains the key for an unchanged failed request, including token
refresh, and replaces it when the operation contents change or success is confirmed.

Accepted decisions store the author's identity/role at that time, UTC timestamp,
operation ID, request hash and before/after documentary state, including PDF
checksum, source, reviewed identification, version and job ID. Ingestion status
changes are separate system events, never human approvals. Replays and rejected,
failed or cancelled attempts are distinguished in structured request logs.
Role designations have a paginated, administrator-only history in the UI/API.

Historical records remain unchanged, with unavailable keys/snapshots left NULL.
No current profile is retroactively assigned to an older event. There are no API
operations for rewriting audit entries. These are application audit guarantees,
not a cryptographically signed or database-administrator-proof ledger. Worker
retry policy remains at-least-once; idempotent dispatch does not promise exactly
one execution of every external provider call after a worker crash.

Shared documents become eligible for individual and general chat. Both restrict
retrieval before ranking and validate candidate IDs/text against canonical chunks.
Selected public sources are revalidated before saving an answer. Source attribution
retains the declared origin and `corpus: shared`; it is not labeled as ANVISA.
Existing prompts, retrieval parameters and frozen evaluation artifacts are unchanged.

## Interface and API

- `/compartilhadas`: available documents and Contributor submissions.
- `/curadoria`: Curator/administrator review queue.
- `/administracao/usuarios`: administrator role designation.
- `POST /api/v1/bulas/shared`: multipart `file`, `product_name`, `source_url`,
  `source_description`, optional `manufacturer`.
- `GET /api/v1/bulas/shared`: `view=public|mine|review`, status/search/pagination.
- `GET /api/v1/bulas/shared/{id}` and `/{id}/pdf`: authorized details and original.
- `POST /api/v1/bulas/shared/{id}/{approve|reject|withdraw|retry}`:
  `expected_version`, `reason`; approval also requires `product_name` and accepts
  optional `manufacturer`, `presentation` and `strength`.
- `GET /api/v1/auth/users` and `PATCH /api/v1/auth/users/{id}/role`:
  administrator-only; assignment requires `role`, `expected_role` and `reason`.
- `GET /api/v1/auth/users/{id}/role-history`: administrator-only, bounded pagination.

## Activation and checks

Back up the target database, deploy the matching API/worker code and run
`uv run alembic upgrade head` before opening the new UI. Bootstrap an administrator
through the existing `app.scripts.create_admin` command when necessary. Designate
the two roles in the interface; affected users reload to refresh navigation.
The existing worker and configured provider credentials are required for actual
ingestion. Functional tests use synthetic providers and do not ingest real PDFs.

Run the regular backend/frontend checks. To additionally exercise PostgreSQL
concurrency, migrate a **disposable** database named `curation_test`, set
`CURATION_TEST_DATABASE_URL` and run
`uv run pytest tests/integration/bulas/test_curation_postgres.py -q`.
The test refuses other database names. Migration stops rather than choosing
between pre-existing active duplicate PDFs. The hardening downgrade refuses to
discard recorded operation keys; preserve audit data and plan a rollback explicitly.
The original migration's downgrade refuses to remove
the Contributor enum while such accounts exist; a deliberate rollback also removes
the new curation tables, so preserve their data separately first.

This implements the curation workflow, not an empirical validation of expert
curation. No existing collection is automatically approved or converted to shared.

### Processing visibility

Shared leaflets opens the existing reviewer view for curators/administrators,
the owner's submissions for contributors and ready public documents for readers.
Staff can switch between tracking, personal submissions and available documents.
Review and ingestion statuses remain separate: approval does not mean ready.
Queued/processing rows refresh every six seconds until completion or failure;
chat stays unavailable until the API confirms public eligibility. Approval leaves
a confirmation and tracking link even when the pending-review row disappears.
This UI uses existing authorized endpoints and does not change publication rules.

### Identification suggestions

Opening a pending submission as a reviewer requests local parser suggestions for
name, manufacturer, presentation and strength. The read-only endpoint verifies
the stored PDF checksum and submission version; it never chunks, embeds,
indexes, approves or calls a model. Suggestions are cached only for that exact
version in the review UI and fill untouched fields. The reviewer must still
inspect the PDF and explicitly confirm before approving; final values use the
existing audited approval transaction. Extraction failures allow manual entry.
Approved records are not backfilled or overwritten. Unavailable fields remain
missing; source dates, registry identity and active ingredient are not inferred
from a submitted filename or a declared ANVISA URL.
