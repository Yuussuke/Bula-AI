# Portuguese BM25 normalization — issue #55

Date: 2026-09-20. Status: implemented and locally validated; pending PR review.
The operator reported completing the local migration steps; that environment
was not independently inspected as part of this validation.

## Problem and evidence

The #55 regression requires `contraindicação` and `contraindicações` to match.
In #32, unaccent ran before Portuguese Snowball, producing different stems:
`contraindicaca` and `contraindicaco`. Native Portuguese stemming produces
`contraindic` for both. Simply removing unaccent would regress accent-insensitive
search. Simply reversing dictionary order does not compose two transformations:
Snowball recognizes a token and terminates dictionary lookup.

`ts_debug` is suitable here for the native configuration with its single stemmer,
but its reported lexemes do not compose an unaccent filtering dictionary and the
next stemmer. The implementation therefore explicitly calls `ts_lexize` for the
folded path rather than treating that diagnostic output as a full filter chain.

References:

- [PostgreSQL dictionaries](https://www.postgresql.org/docs/18/textsearch-dictionaries.html)
- [Portuguese Snowball](https://snowballstem.org/algorithms/portuguese/stemmer.html)
- [pg_textsearch v1.1.0](https://github.com/timescale/pg_textsearch/tree/v1.1.0)

## Decision

Use two complementary term streams in one internal search representation:

1. `p`: native Portuguese lexemes, then accent folding.
2. `f`: accent folding before Portuguese stemming, preserving the prior path
   for words entered with missing accents.

Tokenization and dictionary selection use the built-in Portuguese configuration.
The folded stream explicitly applies unaccent + Portuguese stemming to tokens
assigned to that stemmer; numeric/other tokens retain their parser dictionary.
Each lexeme is encoded as a stream prefix plus UTF-8 hex, making it one token
under the BM25 index's `simple` configuration. This avoids another parser pass
splitting decimal lexemes or re-stemming already-normalized words. Encoded tokens
are internal indexing artifacts, never citations or model context.

The SQL function is shared by writes and queries, versioned, `STABLE`, and not
misrepresented as immutable. Keep every token occurrence (including more than
256 repeats); a unique lexeme array or tsvector positions would lose frequency.
No hard-coded medication word replacements, synonym generation, or fuzzy search.

## Storage and architecture

- `chunk_text` remains exact source text. `search_text` is derived internal data.
- Migration `f6c8d2a91b40` backfills from existing relational chunks, adds a
  trigger, and rebuilds the BM25 index on `search_text` with `simple` parsing.
- The trigger covers inserts and updates of source/derived text, including direct
  database writes; a caller cannot persist inconsistent supplied search terms.
- The repository applies the same function to the parameterized query and scores
  only scoped candidates. It explicitly selects original source fields, never
  returning the encoded representation.
- The LangChain adapter, DI, authorization requirements, and dense chat are unchanged.
- Static function/trigger DDL is the documented raw-SQL exception; application
  queries continue to use SQLAlchemy. No new package or PostgreSQL extension.

## Rollout and reversibility

Pause ingestion and concurrent writes. Apply the new Alembic migration; the #32
migration is not edited. Table locks and index rebuilding are expected. Existing
relational chunks are sufficient: no Qdrant backfill, PDF reprocessing, embeddings,
or provider calls. PostgreSQL transactional DDL provides atomic rollout. The
downgrade restores the old index/configuration and drops only derived structures;
source rows survive. Application version and schema must be deployed/rolled back
together. Test containers are separate from the operator's application database.

## Tradeoffs and boundaries

- Two streams increase index/storage size and normalization CPU. Index/query
  statistics now describe this representation; scores are not comparable to v1
  or dense cosine scores. Hybrid fusion should use ranks, not add raw scores.
- Both streams can contribute to a match. This is lexical normalization, not the
  dense/BM25 hybrid retriever planned for #56. Retrieval evaluation remains needed.
- Standard stemming is not complete Portuguese lemmatization. For example native
  Snowball still differs for `reação`/`reações`; combining a missing accent with a
  different inflection can also differ (`contraindicacao`/`contraindicações`).
  The fix guarantees the tested card examples, not every grammatical variant.
- PostgreSQL tokenization still splits decimal-comma text and ranges into its
  own tokens. Exact clinical values are preserved in source text; lexical matches
  alone must never be interpreted as dosage equivalence.
- Existing candidate materialization, global corpus statistics, and authorization
  limitations from #32 still apply. No change to user-facing retrieval modes.

## Validation contract

Real PostgreSQL tests cover the previously failing example in both directions,
same-spelling accent variants, information/warning inflections, no-match queries,
scoped top-k/order, term repetition, numeric distinctions, unchanged source text,
derived-field updates, and downgrade/upgrade with populated rows. The previous
expected-failure marker is removed, not suppressed or weakened.

Local results: 410 backend tests passed, no skips or expected failures, 87.85%
application coverage. The PostgreSQL module has 33 passing cases, including the
populated-schema downgrade/upgrade test. Ruff lint/format, mypy, and migration
sequence validation passed. The 98 warnings are dependency deprecations.
`alembic check` reports only the pre-existing `chat_messages.source_chunks`
server-default mismatch recorded in #32; no drift was reported for `chunk_meta`.
These results used disposable PostgreSQL/Qdrant instances, not application data.
