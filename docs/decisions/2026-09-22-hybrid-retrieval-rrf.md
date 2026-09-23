# Scoped hybrid retrieval with Reciprocal Rank Fusion

Date: 2026-09-22. Status: implemented and locally validated; pending review and
consumer rollout.

## Context

Dense retrieval captures semantic similarity, while PostgreSQL BM25 preserves
exact lexical evidence such as medication names, units and section terms. Their
raw scores are not calibrated to the same scale, so adding or normalizing those
scores would make ranking depend on unrelated scoring systems.

## Decision

Use LangChain's `EnsembleRetriever` execution model with a project-specific
`HybridRetriever` that owns the safety and observability contracts:

- Run one dense and one BM25 retriever asynchronously for the same question and
  authorized `bula_id`.
- Request `2 * k` candidates from each source before fusion.
- Apply equal-weight Reciprocal Rank Fusion with `c = 60` and one-based ranks.
- Deduplicate exclusively by the logical `chunk_id`; never hash text or use the
  physical Qdrant point UUID as a fallback identity.
- Keep at most `k` fused documents with deterministic tie ordering.
- Preserve native dense and BM25 scores only as diagnostics. The public ranking
  score is the computed RRF score.
- Reject duplicate identities within one ranking and reject conflicting source
  text or non-score metadata across indexes.

The factory requires a `bula_id` and applies it to both child retrievers. Access
authorization remains the caller's responsibility; filters are defense in depth,
not an authorization decision.

The RRF formula for a document `d` is:

```text
RRF(d) = sum(1 / (60 + rank_r(d)))
```

where the sum contains only retrievers that returned the document.

## Metadata enrichment

The lexical index intentionally stores only the metadata required for search.
After fusion and final top-k selection, `EnrichingRetriever` makes one batched
Qdrant lookup for the selected logical chunk IDs. `QdrantVectorStore` maps those
IDs to deterministic physical point UUIDs and returns payloads keyed by the
original chunk ID.

Only `drug_name`, `manufacturer`, `section_title`, `bula_id`, and `corpus` may be
filled. Existing non-empty values must match. Missing Qdrant points leave the
fused result unchanged; Qdrant failures and consistency violations propagate so
the caller does not mistake infrastructure failure for absence of leaflet
evidence.

## Boundaries and rollout

- No API route, chat mode selector or frontend behavior changes in this slice.
- No database migration, backfill, re-embedding or PDF reprocessing is needed.
- The chat remains on its existing retrieval path until a separate consumer
  change selects and evaluates the hybrid strategy.
- Retrieval quality still requires a representative evaluation set; RRF makes
  score combination defensible but does not prove clinical relevance.

## Verification

Unit tests cover exact RRF scores, overlap boosting, BM25-only and dense-only
documents, deduplication, deterministic ordering, final top-k, child overfetch,
failure propagation, metadata enrichment, order preservation and consistency
failures. A Qdrant integration test verifies logical-to-physical identity lookup
and partial misses against the real service used in CI.

Primary references:

- Cormack, Clarke and Buettcher, *Reciprocal Rank Fusion outperforms Condorcet
  and individual Rank Learning Methods*:
  https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf
- LangChain `EnsembleRetriever` reference:
  https://reference.langchain.com/python/langchain-classic/retrievers/ensemble/EnsembleRetriever
- Qdrant point retrieval:
  https://qdrant.tech/documentation/manage-data/points/#retrieve-points
