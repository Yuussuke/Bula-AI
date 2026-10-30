# Local thesis demonstration

## Scope and source identity

The demonstration uses the existing authorized catalog of 100 ANVISA leaflets
(50 from corpus A and 50 from B), with 2,974 previously prepared chunks/vectors.
They remain in the separate demonstration PostgreSQL, Qdrant and PDF storage;
checking out or merging source code does not populate a new database.
Preserve these services and their volumes. Do not reimport or reingest them to
update the interface.

Every imported document has a canonical ANVISA registration link. The source
inventories are [corpus A](../evaluation/corpus/corpus_final.csv) and
[corpus B](../evaluation/corpus_b/corpus_b_final.csv). These links identify the
official source; they are not necessarily direct PDF downloads. Local PDF hashes
identify the exact imported versions. A later ANVISA publication may differ.
Unknown acquisition/manufacturer fields remain unknown. Catalog availability
does not imply new human review or clinical certification.

General chat searches all 100 authorized sources. This demonstration scope must
not be described as identical to the separate A/B experimental universes.
The frozen evaluation and its results remain unchanged.

## Prerequisites and startup

- Use a checkout containing the merged runtime, catalog and chat changes
  (baseline `2f26e4da201df66c98f284575a24bb8d36633567` or a descendant).
- Start Docker Desktop and the existing demonstration data services. Use the
  prepared private environment/launcher when available; it is machine-specific
  and is not included in Git. Verify its code paths before starting it: an older
  worktree is not automatically updated by a merge to `main`.
- Point the API at those existing services and stored PDFs. Apply required
  Alembic migrations only to the intended demonstration database after checking
  its current revision and backup. Never redirect it at frozen evaluation data.
- Reuse verified BGE weights and the CUDA environment described in
  [the runtime setup](rrfb-bge-runtime.md). Hybrid requires a successfully loaded
  reranker; there is no automatic CPU/RRF fallback. Keep one API worker.
- Configure provider credentials privately and allow the exact frontend origin.
  The prepared local origins are `http://127.0.0.1:3100` (frontend) and
  `http://127.0.0.1:8100` (API). Do not mix these with the older `localhost:3000`
  environment. For native frontend startup, set `VITE_API_BASE_URL` to
  `http://127.0.0.1:8100` (without `/api/v1`) and run `npm ci`, then
  `npm run dev -- --host 127.0.0.1 --port 3100 --strictPort`.

Do not publish environment files, accounts, tokens, database dumps, local launchers
or model weights. Source links alone cannot reconstruct the existing indexed
environment; full reproduction also requires its private data/configuration bundle.

## Final rehearsal checklist

1. Confirm the running checkout and database migration revision. `/health` must
   return 200, but that alone does not establish BGE/provider readiness; also
   inspect successful reranker startup and the selected configuration.
2. Sign in with the existing demonstration account. Open **Catálogo ANVISA**:
   confirm 100 documents, 20-item pages, dynamic search outside the first page
   and an official source link in each document's details. Keep **Minhas bulas**
   separate from system documents.
3. Open one document-scoped conversation and **Chat geral**. Confirm the three
   search-mode options, hybrid default, visible notice and source-panel access.
   Reopen existing saved answers and check citation numbers/document identities.
4. Confirm recent conversations reopen in their original scope, including after
   signing in again. Check the sidebar/mobile drawer and keyboard navigation.
5. Before presenting, manually submit one ordinary document question and one
   general-chat question; inspect the answer and sources, then reopen the saved
   conversation. These are live provider calls, distinct from offline UI checks.
   Check connectivity, available credits and startup time on the actual notebook.

Keep a small set of saved conversations available if network/provider access is
unavailable. Identify them as saved examples rather than a live generation.

## Verification record and remaining gate

The merged baseline passed backend/frontend CI. The branding release passed
102 frontend tests, formatting, zero-warning ESLint and TypeScript/Vite build;
synthetic browser checks covered desktop/mobile and light/dark favicon themes.
One initial asynchronous-render test timed out while build and tests ran
concurrently; the complete rerun without concurrent build passed unchanged.

On 2026-10-30, the import report matched both corpus manifests: 50+50 documents
and 100 canonical ANVISA links. After Docker started, read-only live checks
verified all 100 stored PDF hashes and authorized document accesses, 2,974
matching PostgreSQL/Qdrant chunk payloads, and migration head `d510a102b002`.
Browser checks passed five catalog pages, source links, the three search modes,
saved history/source-panel reopening and mobile navigation, with no page errors.
The API loaded the pinned BGE on the local CUDA GPU. Data counts were unchanged.

Authentication used an ephemeral signed token, not an interactive login test.
External ANVISA availability and new provider generations were not tested.
No ingestion, new embeddings, paid calls or experimental metrics were performed.
The remaining presentation-day checks are interactive login, connectivity and
the two manual live questions in step 5; this is not a new answer-quality study.
