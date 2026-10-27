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
