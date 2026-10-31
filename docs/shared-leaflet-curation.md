# Shared leaflet curation

Shared PDFs require authenticated, independent review. Private uploads and the
ANVISA system catalog keep their existing behavior; no collection is automatically
approved or converted to shared.

| Role | Permissions |
| --- | --- |
| User | Read and query available shared leaflets |
| Contributor | Submit PDFs and follow their submissions |
| Curator (`reviewer`) | Inspect, approve, reject, withdraw and retry failed ingestion |
| Administrator | Designate roles, submit and perform curation |

Role designation requires an administrator and a recorded reason. Curators are
intended to be health professionals, but credentials are not verified automatically.
Documentary approval is not clinical certification. Submitters, including admins,
cannot approve or reject their own submissions; registration cannot assign roles.

## Workflow guarantees

- Submission requires a PDF up to 10 MB, declared product name, HTTPS source URL
  and description; manufacturer is optional. Other identified sources are accepted.
  URLs are references, never downloaded by the server. Submission does not enqueue ingestion.
- Review checks the stored PDF checksum/size and current version. Approval requires
  a confirmed product name; manufacturer, presentation and strength must come from
  the document. Ingestion cannot overwrite reviewed shared identification.
- Approval, audit event and PGQueuer job commit in one PostgreSQL transaction.
  Enqueue failure or interruption rolls back the action. Availability requires
  approval, its audit event, successful ingestion and matching stored-object identity.
- Stale revisions return 409. Failed ingestion requires an explicit, audited retry;
  interrupted legacy approvals without a job are recoverable when no job is active.
- Withdrawal prevents future queries without deleting history or chunks, even if
  the PDF is damaged. Rejection/withdrawal is final; resubmission creates a linked review.
- Identical PDF bytes cannot have two pending/approved shared submissions. This
  does not detect semantically equivalent documents or duplicates in other corpora.
- Shared-source eligibility restricts retrieval before ranking. Canonical chunks
  are checked and selected sources revalidated before saving. Attribution retains
  the declared source and `corpus: shared`, without labeling it as ANVISA.

Mutations require `Idempotency-Key` (UUID). Within each domain, repeating an actor's
key and request fingerprint returns current state with `replayed: true`; changed
contents return 409. Replays do not create another decision, role change or job.
Audit events retain actor/role, UTC time, operation ID, fingerprint and before/after
state, including PDF identity, version and job ID. Ingestion events are not human
approvals. Only owners/staff see review notes; role history is administrator-only.
Historical missing fields remain NULL. Audit entries have no rewrite endpoint,
but are not protected against database administrators. At-least-once worker retries
do not guarantee exactly one external provider call after a crash.

## API

- `POST /api/v1/bulas/shared`: multipart submission fields described above.
- `GET /api/v1/bulas/shared`: `view=public|mine|review`, status, search and pagination.
- `GET /api/v1/bulas/shared/{id}` and `/{id}/pdf`: authorized details and original.
- `GET /api/v1/bulas/shared/{id}/metadata-suggestions`: reviewer-only, pending
  submissions. Verifies PDF/version and runs the local parser without persisting,
  indexing or calling a model. Missing fields stay missing; approval still requires
  explicit confirmation. Approved records are not backfilled.
- `POST /api/v1/bulas/shared/{id}/{approve|reject|withdraw|retry}`:
  `expected_version`, `reason`; approval also requires `product_name` and accepts
  optional `manufacturer`, `presentation`, `strength`.
- `GET /api/v1/auth/users`, `PATCH /api/v1/auth/users/{id}/role` and
  `GET /api/v1/auth/users/{id}/role-history`: administrator-only role management.

## Activation and tests

Back up the target database, deploy matching API/worker code and run
`uv run alembic upgrade head`. Bootstrap an admin with `app.scripts.create_admin`
when needed. Actual ingestion requires the worker and configured providers.
Prompts, retrieval parameters and frozen evaluation artifacts are unchanged.

Run the regular backend checks. For real concurrency, transaction visibility,
rollback and migration tests, migrate a **disposable** database named `curation_test`,
set `CURATION_TEST_DATABASE_URL`, then run
`uv run pytest tests/integration/bulas/test_curation_postgres.py -q`.
Tests refuse other database names and run no worker or paid provider calls.
Migration rejects existing active duplicate PDFs. Downgrade refuses to discard
recorded operation keys or remove the Contributor enum while assigned; plan
rollback explicitly and preserve curation/audit data before removing its tables.
