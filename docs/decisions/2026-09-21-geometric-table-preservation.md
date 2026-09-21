# Coordinate-backed table preservation

## Evidence

The EMS amoxicillin/clavulanate PDF (SHA256
`ffd3780e4895c67b9bf1986127e4a205265245f865b6b0123843400582689d41`)
has three ruled tables on page 4. Historical pdfplumber output flattened their
columns and promoted their headers to section titles. The current native layout
converter still merged age/presentation columns and adult/child table regions.
Copying historical Qdrant chunks into PostgreSQL cannot repair either problem.

## Decision and scope

Keep PyMuPDF4LLM as the default converter, with a geometric complement using the
already installed PyMuPDF. No new model, dependency, OCR or schema migration.
This refines #72/#76; it does not change retrieval modes or the BM25 patch.

`GeometricTableExtractor` reads arbitrary ruled grids with
`strategy="lines_strict", use_layout=False`. Disabling learned layout here is
essential: after native conversion, layout-aware table detection can reuse the
same merged regions we are trying to correct. Grid dimensions come from actual
cell edges, not medicine names, coordinates specific to EMS, or a fixed width.

Internal typed cells retain bounds, text and row/column spans. A bordered empty
cell stays empty; a missing grid slot is not guessed to be a merged cell. Proven
merged spans expand their own source value in a rectangular Markdown view;
leading full-width captions appear once above the grid. This is deterministic
source-derived context, not generated medical content.

`GeometricTableIntegrator` matches physical tables to native page-box coordinates
and character offsets. A native box may contain multiple physical tables. An
overlap threshold of 75% of the smaller area allows layout boxes fitted to text
to match ruled grids including padding. Caption/text boxes inside those grids
are consumed together; unrelated intervening blocks, overlapping replacements
and ambiguous matches reject conversion. Outside text is retained in page order.
No string-based replacement of medication names is used.

Word centers must have exactly one physical cell owner, grid slots must have
exactly one owner, and normalized character counts must reconcile the region
with cells plus surrounding text. These checks detect loss/duplication; they
do NOT constitute a semantic proof of correct column recognition. Cell-level
regression expectations and visual validation are necessary too.

Known structure failures fail parsing and cannot delegate to the plain-text
fallback. Diagnostics include bounded page/bounds/dimension/merge summaries,
parser version `native_markdown_tables_v2`, and safe failure reasons. The normal
ingestion error path handles failure before embeddings/index writes/ready.

## Chunking contract

Shared source-block ranges attach a short adjacent caption and explicit
asterisk footnotes to a table. Semantic proposals that split those ranges are
rejected even when every source token is present. Existing strict ordered source
coverage remains enabled; deterministic fallback handles the source block.

Oversized tables split only between complete rows. Source captions, headers and
explicit footnotes repeat as necessary and resulting chunk metadata records
`table_context.repeated_from_source`. A row plus required context exceeding the
existing token cap is a quality error, not an invitation to split that row as
prose. No values are truncated to satisfy the cap.

## Deliberate boundaries

- Borderless tables retain native output. Inconsistent Markdown column counts
  reject parsing; structurally consistent output is not necessarily correct.
  `native_only_table_count` reports this unverified-by-geometry path.
- No automatic cross-page joining. Equal widths are insufficient evidence of
  continuation; separate page tables stay separate. Headerless continuation and
  complex multi-level headers still require explicit future validation work.
- Footnote association currently covers explicit adjacent `*`/`**` markers,
  not every semantic qualification elsewhere in a document.
- Geometry does not guarantee that every table is detected. Decorative boxes,
  absent borders and ambiguous reading order remain limits. This is not a claim
  of general lossless PDF conversion or complete clinical validation.

## Validation and rollout

Synthetic PDFs exercise variable row/column counts, actual empty cells, merged
caption cells, page isolation, non-table boxes and coordinate replacement. Other
tests cover safe failures, preserved context, oversized rows and semantic cuts.
The optional local EMS integration test checks exact cell relationships through
PDF → Markdown → model-timeout fallback → chunks → sanitized debug manifest.
Its PDF is not versioned; CI runs the synthetic tests and existing real goldens.

Run the five-document comparison without databases or providers:

```bash
cd backend
uv run python -m scripts.benchmark_pdf_markdown --table-comparison \
  --output tmp/parser-benchmark/geometric-tables.json \
  tmp/anvisa-bulas/Amoxicilina__EMS.pdf \
  tests/fixtures/rag/bulas/dipirona_sanofi_medley_solucao_oral.pdf \
  tests/fixtures/rag/bulas/amoxicilina_cimed_suspensao_oral.pdf \
  tests/fixtures/rag/bulas/nesina_met_cosmed_comprimido_revestido.pdf \
  tmp/parser-benchmark/metronidazol-cimed-patient-benchmark__10709560__patient.pdf
```

Local sequential comparison (five PDFs, same installed converter): controller
wall time 26.90 → 30.48 s, peak process-tree RSS 324.56 → 330.73 MiB, mean lexical
recall 0.807279 → 0.810025. Critical dosage-signal recall remained 0.989474;
the pre-existing Cimed result is below 1.0 in both variants. Legal-section removal
also affects whole-PDF lexical recall. These metrics do not replace cell-level
assertions; no conclusion of universal accuracy follows from them.

Final local checks: 428 backend tests passed with no skips/expected failures,
88.17% application coverage, and 98 dependency deprecation warnings. Ruff lint,
formatting and mypy passed. PostgreSQL and Qdrant integration tests used separate
disposable containers, not the application's database or vector collection.

The operator reported a successful local visual check after following the manual
test instructions. This is evidence for the tested leaflet, not validation of
every table layout. A pre-publication rerun passed 197 focused RAG, benchmark and
parser regression tests; Ruff lint/formatting and mypy also passed again.

This change does not automatically reingest or republish existing bulas. Before
corpus-wide rollout, visually review the remaining corpus, then explicitly run
the controlled reingestion workflow. PostgreSQL BM25 backfill alone is insufficient:
corrected chunks require re-parsing/chunking, embeddings and both indexes. Preserve
old artifacts for comparison; apply system publication review policy again.

## Sources

- [PyMuPDF table extraction](https://pymupdf.readthedocs.io/en/latest/page.html#Page.find_tables)
- [PyMuPDF4LLM conversion API](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html)
