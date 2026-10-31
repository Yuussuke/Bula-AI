# Catalog metadata and navigation

Verified imports may preserve unknown manufacturer/acquisition fields as null.
This does not relax the downloader manifest or publication/readiness, PDF checksum,
stored-size and canonical-source checks. Missing provenance is never fabricated.
Complete strength labels use text to preserve multiple presentations. Alembic
revisions `d510a102b001` and `d510a102b002` apply these changes; downgrades reject
unresolved nulls or overlong values instead of inventing/truncating metadata.
No documents are imported or republished by these migrations.

`GET /api/v1/bulas/system/search` accepts `query`, `audience`, `sort`, `limit`
(default 20, maximum 100) and `offset`. Case/accent-insensitive terms filter the
whole authorized catalog before counting and pagination; wildcard characters are
literal. Stable A–Z/Z–A ordering includes document-ID tie-breaking. The legacy
system list remains available. `GET /api/v1/bulas/` returns owned private uploads.
These metadata requests invoke no embeddings, reranker or language model.

`PATCH /api/v1/bulas/{id}/alias` accepts `{alias: string | null}` for owned private
uploads only. Whitespace is trimmed; null/blank restores the official display name.
The official product name, sources and indexed content are unchanged.

Session listing optionally accepts `sort=updated_at`, applied before pagination;
its default remains creation order. Completed turns update session activity in
the same transaction as both messages. Ownership and scope filters are preserved.

## Client navigation

Home links to `/minhas-bulas`, `/catalogo` and `/chat`. The catalog searches after
350 ms, retains filters in the URL and offers pagination above/below its rows.
Private uploads have client-side search/status filters and 12-card pages; their
list endpoint remains unpaginated. Aliases never replace official identity.

A shared sidebar exposes independently collapsible general/medication history,
ten sessions per page ordered by activity, with more pages on demand. Each link
preserves its original scope/document; deleted-document sessions are not treated
as general conversations. Starting an individual chat requires choosing a PDF.
## Public catalog boundary

`GET /api/v1/bulas/catalog/search` reuses the search/pagination contract and adds
`catalog_scope=all|system|shared` (default `all`). It lists published/ready system
documents and approved/ready shared documents with matching stored PDF identity.
Private uploads and pending/withdrawn sources are excluded before counting and
pagination. Shared cards retain their declared origin; unknown ANVISA metadata
remains null. The audience control is shown only for the ANVISA selection.

The same small selector appears in the catalog and general-chat sidebar.
`catalogo=system|shared` persists navigation; `all` combines both public catalogs.
Search text and audience filters only affect browsing, not chat retrieval.
Only the selected catalog boundary is passed to a new conversation. See
`cross-bula-chat.md` for persistence and authorization.
