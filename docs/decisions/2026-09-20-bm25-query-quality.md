# BM25 query accents and evidence eligibility

## Evidence and scope

A manual BM25 check found that `contraindicacoes` missed prose containing
`contraindicada`, although accented `contraindicação`/`contraindicações` matched.
Heading-only chunks also occupied top-k slots for `amoxicilina` and `500`.
This is a follow-up to the v2 normalization decision, not replacement of it.
The chat remains dense-only; this change affects the standalone BM25 path.

## Decision

`PostgreSQLBM25Index` applies `BM25QueryNormalizer` before repository search.
It restores accents only in complete words from this closed vocabulary, case
insensitively: advertencia(s), composicao/composicoes,
contraindicacao/contraindicacoes, indicacao/indicacoes,
informacao/informacoes, interacao/interacoes, precaucao/precaucoes,
reacao/reacoes. Already accented and unknown words are untouched.

Restoration occurs before PostgreSQL's Portuguese stemming. The existing folded
stream still handles the same unaccented spelling in stored text. There is no
query expansion, LLM call, medication-name correction, suffix guessing, or fuzzy
matching. Numbers, units, negation and punctuation are not rewritten. Original
question/history, source chunks, IDs and metadata are not modified.

The repository uses a parameterized SQLAlchemy regexp expression to exclude
chunks whose only non-whitespace content is Markdown ATX headings (levels 1–6).
The eligibility predicate is inside the materialized candidate scope, before
scoring and limiting. Unlike filtering an already limited response, it can fill
k slots even when many heading-only matches would otherwise rank first. Lists,
tables, plain text and headings with body text remain eligible. Returned source
text is exact; stored heading-only rows are retained for audit/backfill.

## Boundaries and alternatives

- This is bounded domain-vocabulary restoration, not general accent-insensitive
  lemmatization. Unlisted words and Snowball's other inflection limitations
  remain; each vocabulary extension needs examples and tests.
- Avoid approximate matching of drug names: the known typo `amoxicilinna` still
  yields no match. This change is not a general remedy for poor retrieval.
- No forced minimum source length: short but useful doses/lists must survive.
  Heading detection is structural, not semantic; it does not judge clinical
  usefulness, detect Setext headings, or repair bad PDF extraction.
- The regex runs over scoped candidates. The existing materialization/scoring
  scan and global index statistics remain; heading rows still contribute to
  those statistics. Large-corpus performance requires separate measurement.
- Bula/corpus filters, positive-score ordering and deterministic tie-breaking
  are unchanged. Callers must still authorize ownership/publication separately.

## Rollout and validation

No schema/index change, new dependency, backfill or Qdrant reindex is needed on
revision `f6c8d2a91b40`. Load updated backend code (restart long-running processes
or rebuild if not bind-mounted); rollback is an application-code rollback.

Unit tests exercise exact restoration, whole-word boundaries, idempotence, drug
typos, negation, doses and formatting. Real isolated PostgreSQL tests cover
`contraindicacoes` → `contraindicada`, case variation, preserved originals,
cross-bula/corpus isolation, heading-only CRLF/multiline cases, more misleading
headings than k, retained tables/lists, ranking and the LangChain adapter.
Existing normalization and populated migration round-trip tests remain enabled.

Local validation: 429 backend tests passed with no skips or expected failures,
87.88% application coverage, and 98 dependency deprecation warnings. Ruff lint
and formatting and mypy passed. PostgreSQL and Qdrant ran in disposable containers
with no application volumes; the application's stored bulas were not modified.

Manual check: rerun the standalone search with the same bula and k. Expect
`contraindicacoes` to retrieve the contraindication prose, no heading-only
results, unchanged dose/table text, and no match for `amoxicilinna` or blank
input. Do not expect this branch to change the dense chat's responses.

## References

- [PostgreSQL dictionaries](https://www.postgresql.org/docs/18/textsearch-dictionaries.html)
  describes domain-specific normalization before general stemmers.
- [Snowball Portuguese algorithm](https://snowballstem.org/algorithms/portuguese/stemmer.html)
  documents the accent-sensitive suffix rules motivating conservative restoration.
