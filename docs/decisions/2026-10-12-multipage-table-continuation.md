# Source-backed multipage table continuation

Date: 2026-10-12. Branch: `fix/multipage-table-continuation`, based on `4401a5c`.
Parser: `native_markdown_table_continuation_v6`.

## Cause and implementation

The previous continuation check required corresponding physical column edges
to remain within two page points. DIANEAL retains its logical column order on
pages 2–3, but shifts and resizes columns. The absolute test rejected a valid
continuation. Merely accepting an equal column count would also accept unrelated
tables and was not used as a fix.

`TableContinuationMatcher` adds two deterministic correspondence paths:

- **Reflow:** compatible relative widths/centres, identical ordered lexical
  types, source header tiers, at least two rows per fragment, shared row-label
  vocabulary and two distinct constant-column anchors. Duplicated placeholders
  cannot establish identity; moved distinctive values contradict a match.
- **Outer-frame change:** at least two interior boundaries remain absolutely
  aligned, outer-column widths remain compatible, the original header is known,
  and ordered data types agree. This does not authorize moving interior borders.

Existing page adjacency, placement, column count and reading-direction checks
remain. New preceding section context rejects propagation. Repeated marginal
text is recognized only through its source text and relative position; Markdown
emphasis is not treated as a new section. Explicit repeated grouped headers
remain separate page tables, as before.

No names, clinical quantities or document-specific phrases determine matching.
Values and units remain literal: lexical comparison does not calculate doses,
convert units or infer populations. Physical cell spans are preserved; only
proven within-page spans are expanded for comparison/rendering.

Diagnostics now retain every cell's ID, source page, bounds, raw text, spans and
text direction, plus fragment links and the originating header cells. Bounds
use rotation-normalized page points, not necessarily the unrotated PDF media
box. Markdown cannot encode rowspan or a hierarchical header graph: merged
values are repeated and both original header tiers are retained. The diagnostic
graph preserves their physical relationships. This does not establish complete
semantic preservation by a downstream chunker.

## DIANEAL validation

The frozen PDF SHA-256 is
`6af0132b12d269b8997c6085e335fbe0a183d8f0acd32d8d6076806db4001456`.
The full PDF parses offline. Original page renders 2 and 3 were inspected;
an independently transcribed matrix checks all **14 data rows and 14 columns**.
The continued fragment inherits the source header tiers without a false header
or extra separator. Calcium mass remains in column 4 under `(mg)`, ionic calcium
in column 9 under `(mEq/L)`, and volume in column 13 under `(mL)` (zero-based).
Concentration, composition and volume combinations agree with the visual source.

The integration test checks grouped/rotated headers, source spans, raw numeric
rows, continuation links and page provenance. Synthetic real-PDF tests also
cover two/three-page continuations, repeated letterhead and false matches.

## Corpus comparison: distinguish the baselines

The 100 frozen PDFs were parsed into separate local outputs with network access
blocked. This is an offline parser comparison, **not reingestion**: existing
Markdown, chunks, indices, databases, volumes and snapshots were not updated.
The reference assembly checks baseline Markdown hashes against the recorded
ingestion identities; PDF and parser fingerprints are checked around the run.

| Reference | Result against v6 |
| --- | --- |
| Actual 99 indexed PDFs (mixed v4/v5; excludes DIANEAL) | 91 byte-identical Markdown; 7 changed and accepted; 1 rejected |
| Verified offline v5, 97 accepted PDFs | All 97 remain accepted with byte-identical Markdown |
| Entire frozen corpus, 100 PDFs | 99 accepted; DIANEAL and FIBROGAMMIN repaired; CYCLOFEMINA rejected |

All 98 PDFs accepted in both the indexed reference and v6 have unchanged front
matter, including strength. The seven changed accepted documents are:

| ID | Difference inherited from the v5 layout baseline |
| --- | --- |
| A-B015 | Illustrated steps remain data rather than fabricated headers; frame continuation now accepted |
| A-B027, A-B036 | Explicit repeated grouped headers remain separate page tables |
| A-B032 | Eleven repeated history captions removed by existing furniture cleaning; known limitation |
| A-B040 | Illustrated data retained under an empty header |
| A-B048 | Duplicate flattened table occurrences removed; no unique words lost |
| A-B050 | Complete grouped headings replace split text fragments |

There are **no new rejection or Markdown changes among the 97 v5 successes**.
That is not equivalent to zero differences against the actual indexed corpus.

### Remaining rollout blockers and limits

- **A-B044, CYCLOFEMINA, page 8:** already rejected by v5 but accepted by the
  older indexed parser. An interior border changes, nullable protocol cells and
  variable values do not supply sufficient independent anchors. v6 still rejects
  it rather than guessing. Existing indexed data remains untouched.
- **A-B032, DEXAMETRAT:** the inherited v5 furniture cleaner removes repeated
  history captions. This is recorded as a limitation, not an approved omission.
- Reflowed all-text tables, too few rows, mixed lexical schemas, excessive drift
  or insufficient anchors remain unresolved. Lexical/date recognition is not a
  general semantic interpretation engine. Cross-page merged-cell values are not
  invented from an unproven span.
- Each-cell diagnostics increase diagnostic output size; no provider context or
  retrieval budget was changed.

Global parser adoption is **not cleared** by this report. A separately authorized
DIANEAL-only ingestion can use its verified result and versioned provenance;
reprocessing the existing 99 documents requires addressing/reviewing the inherited
differences first. No retry adapter or ingestion parameter was changed here.

## Tests and reproduction

- Relevant RAG unit/integration suite: **451 passed**, 22 existing deprecation
  warnings. The full visual DIANEAL matrix assertion was strengthened afterward
  and rerun separately: **1 passed**.
- Ruff check and format: passed for changed Python files.
- Mypy: passed for the parser package (10 source files).
- Valid and false correspondences, changed units/order, ambiguous placeholders,
  new section context, nullable cells, anchored frames and third-page header
  provenance are covered.

Use the pinned project environment and `uv run --offline --no-sync`; do not
install dependencies or connect to providers. Local run identity records Python
3.14.0, PyMuPDF 1.28.2, PyMuPDF4LLM 1.28.2 and every parser source SHA-256.
From `backend/`, example validation commands are:

```sh
uv run --offline --no-sync pytest tests/unit/rag tests/integration/rag/test_table_layout_parser.py tests/integration/rag/test_multipage_continuation_parser.py tests/integration/rag/test_geometric_table_pipeline.py -q
uv run --offline --no-sync ruff check app/modules/rag/parsers tests/unit/rag/test_table_continuation.py tests/integration/rag/test_multipage_continuation_parser.py tests/integration/rag/test_table_layout_parser.py
uv run --offline --no-sync mypy app/modules/rag/parsers --follow-imports=silent --disallow-untyped-defs
python -m scripts.check_parser_corpus parse --documents PATH_TO_A_CONFIG PATH_TO_B_CONFIG --pdf-root REPOSITORY_ROOT --output NEW_OUTPUT_DIRECTORY
python -m scripts.check_parser_corpus compare --before VERIFIED_REFERENCE_DIRECTORY --after NEW_OUTPUT_DIRECTORY --output NEW_COMPARISON_DIRECTORY
```

Real-PDF tests require `PARSER_CORPUS_PDFS` and `EMS_PDF_PATH` pointing to the
unchanged local PDFs. Check the corpus run's input paths/hashes before reuse.
Each parser run refuses an existing output directory and blocks socket calls.
Private/local inputs and outputs are deliberately not committed.

Local artifacts (relative to the primary repository):

- `tmp/parser-continuation-validation/v6-final/run.json`: inputs, dependencies and source fingerprints.
- `tmp/parser-continuation-validation/v6-final/A-B038.md` and `.json`: full DIANEAL output and cell provenance.
- `tmp/parser-continuation-validation/comparison-ingested/`: actual-index baseline comparison and diffs.
- `tmp/parser-continuation-validation/comparison-v5/`: isolated v5 comparison.
- `tmp/pdfs/layout-regressions/A-B038-2.png` and `A-B038-3.png`: original page renders.

Golden Set v1.0.0, the frozen 200-question set and the original PDF hashes remain
unchanged. No ingestion, embeddings, retrieval experiment, paid API calls or
evaluation metrics were executed. DIANEAL has **not** been reingested.
