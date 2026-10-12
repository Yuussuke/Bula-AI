# Source-backed PDF table layouts (parser v5)

## Scope and provenance

Isolated branch: `fix/parser-layout-regions`, based on
`b7976cac4d44605fa3a4bfc47c2c213dd84ab1b8`. Parser version:
`native_markdown_layout_regions_v5`; Python 3.14.0, PyMuPDF/PyMuPDF4LLM 1.28.2.
Existing worktrees and their local changes were preserved.

Validation parses original PDFs offline, without semantic chunking, embeddings,
retrieval, providers, databases or index writes. Original ingestion artifacts
are not overwritten. No Golden Set questions or source PDFs were changed.
The previous parser reproduced all seven failures and all 93 successful
Markdown hashes from the original ingestion.

## Causes and intervention

| Cause | Deterministic intervention |
| --- | --- |
| Native `table` label and one-box matching excluded genuine grids | Connect geometrically overlapping nonempty native regions, including `picture` and multiple fragments. Preserve leftover physical text and validate replacement coverage. |
| Empty offsets were treated as consumed text | Validate every interval; only nonempty overlapping intervals can conflict. Nonempty unboxed gaps remain errors. |
| Thin filled/tilted rules were ignored, creating overlapping cells | Supply only actual thin source paths to strict detection. Keep unique word ownership and complete cell occupancy checks. Do not switch to permissive background detection. |
| Rotated pages/text used incompatible coordinates and reading axes | Normalize page rotation in memory and project cardinal text directions. Preserve source word order; reject mixed directions within a cell. |
| Including images in text dictionaries shifted block IDs | Match word/dictionary extraction flags before associating line directions. |
| Illustrated steps were promoted to column headers | Retain captions, blank Markdown header cells and every instruction row. No image recognition or invented labels. |
| Nearly aligned side-by-side tables changed reading order | Order grids left-to-right within the existing three-point geometric tolerance. |
| Unaligned continuation rows became false headers | Reject likely headerless continuations without proven column alignment. Explicit matching two-tier grouped headers anchor their own page. Notes between pages are not proof of a new table. |

Existing cell-span representation is retained: Markdown repeats values only
within proven physical row/column spans. No cross-page value propagation is
introduced. Public schemas, models, prompts, chunker and retrieval are unchanged.

## Seven original failures

Pages are physical PDF pages. Success refers to the complete PDF, not only the
original failing page.

| PDF | Original failure / source issue | v5 result |
| --- | --- | --- |
| A/B007 AMPLOSPEC | Picture-classified history; rotated page coordinates | Success |
| A/B018 LAFEPE BENZNIDAZOL | Picture-classified illustrated grid; missed physical borders | Success; steps 1/2, 3/4, 5/6 and 7 retain source row relationships |
| A/B038 DIANEAL PD-2 | Picture-classified composition grid and vertical labels | Original page 16 repaired; complete PDF rejected at page 3 for ambiguous continuation |
| A/B049 SPORANOX | Picture-classified calendar and merged cells | Success |
| B/CB002 HIDROCLOROTIAZIDA | One grid split into native fragments | Success; repeated grouped headers remain source-backed |
| B/CB006 anlodipino | Empty unrelated offsets and rotated reading order | Success; date, version and submission values retain their row |
| B/CB024 naproxeno | Overlapping cells from ignored filled rules | Success; neurological category, frequency and reaction remain associated |

DIANEAL pages 2/3 have 14 columns, but their physical edges change and page 3
has no repeated header. Equal column count alone does not prove correspondence.
v5 refuses to promote that first data row to a header or guess associations.
This is an unresolved conservative rejection, not a claim that the PDF is
clinically contradictory or lacks selectable text.

## Regression results and validation

The final offline sweep produced **97 successful parses and 3 rejections**.
Among the 93 previously accepted PDFs, **85 Markdowns are byte-identical**,
**6 changed and remain accepted**, and **2 are newly rejected**. These are parser
results, not ingestion or retrieval metrics.

| Previously accepted PDF | Observed change |
| --- | --- |
| A/B015 FIBROGAMMIN P | New rejection on page 14: continuation's outer border changes beyond the retained two-point alignment tolerance. Internal edges mostly match; this is a conservative limitation, not a demonstrated clinical contradiction. |
| A/B044 CYCLOFEMINA | New rejection on page 8: an internal column boundary changes without a repeated header. |
| A/B027, A/B036 | Explicit repeated grouped headers start their own Markdown table; source words are unchanged. |
| A/B032 | Grouped headers are restored, but the downstream furniture cleaner removes the repeated history title after captions become ordinary text. This title loss is an unresolved regression, not an approved omission. |
| A/B040 | Illustrated instruction rows remain data, under empty Markdown header cells. Source words are unchanged. |
| A/B048 | Previously flattened/duplicated clinical table cells become two source-backed columns. Removed occurrences are duplicated values, not missing unique words; source pages 2/3 were inspected visually. |
| A/B050 | History headings and spans are restored. Apparent lost tokens are fragments from the old split headings, not missing physical source words. |

All 91 PDFs accepted by both versions retain identical front matter, including
`strength` when present. B/CB023's side-by-side pediatric tables and A/B042's
clinical continuation are byte-identical to baseline after intermediate ordering
and note-related regressions were corrected. No new silent clinical loss was
identified in the final diffs; this is not an independent clinical validation.
Source-page visual checks accompany the diffs; lexical counts alone are not a
semantic fidelity proof.

- 435 offline unit/integration tests passed, including all seven external PDF
  cases, four page-rotation fixtures, table spans, malformed intervals,
  fragmented/picture regions, mixed directions and side-by-side order.
- The DIANEAL regression explicitly checks both safe whole-document rejection
  and successful repair of the original page 16 region.
- Existing three bundled parser golden PDFs and the EMS table/chunking fallback
  regression passed. The latter uses a mocked provider, not a paid call.
- Ruff checks and formatting passed; mypy passed for `app` and the offline tool
  (92 source files). Dependency deprecation warnings remain (22).
- The frozen collection loader verified 1,000 effective records, version
  bindings and all 100 PDF hashes. Frozen manifest SHA-256 remains
  `0b59a882ab360efbf7fcb51bb4c6ba1794f0d6c9d72fc2a88f88fcadb53b4fd7`.

## Reproduction and artifact custody

`python -m scripts.check_parser_corpus parse --documents <A.json> <B.json>
--pdf-root <root> --output <fresh-directory>` parses only. Input JSON uses
`documents` with `corpus_id`, `document_id`, relative `path` and `sha256`.
Duplicate/unsafe identities, escaped paths, changed PDFs and changed parser
sources fail validation. Network connections are blocked during parsing.
Run the same tool with each worktree's parser on `PYTHONPATH`.

`python -m scripts.check_parser_corpus compare --before <baseline>
--after <candidate> --output <fresh-comparison>` emits diffs, text/metadata
changes and explicit success-to-rejection transitions. It does not compute
Recall@K or evaluate answers. Existing output directories are never overwritten.

External local artifacts (outside this branch's tracked files):

- Input inventories: `backend/evaluation/artifacts/ingestion-20261011/{A,B}/configuration.json`.
- Baseline and canonical candidate: `tmp/parser-layout-validation/{baseline,verified-v5}/`.
- Run source hashes/dependency versions: `verified-v5/run.json`.
- Final status, word/metadata changes and Markdown diffs:
  `tmp/parser-layout-validation/comparison-verified-v5/`.
- Integrity checks: `tmp/parser-layout-validation/provenance-v5.json`.
- Source renders: `tmp/pdfs/{seven-parser-failures,layout-regressions}/`.

Original frozen PDFs and their custodial archive are required for complete
reproduction; they are not committed. Synthetic layout tests run without them.
Set `PARSER_CORPUS_PDFS` to the external `pdfs` directory for seven-PDF tests;
set `EMS_PDF_PATH` for the separate EMS regression.

## Remaining limits and ingestion gate

Geometric acceptance does not certify every native-only/borderless table.
Raster-only information is not read; oblique or mixed within-cell directions
remain unsupported. Illustrated grids preserve selectable text, not image
meaning. Region character conservation is necessary, not semantic validation.
The existing handler boundary remains extensible for conditional OCR; OCRmyPDF
and OCR-assisted retries were not implemented.

Changed code is limited to `geometric_tables.py`, `handlers.py` and the parser
version in `pdf_parser.py`; accompanying files are the parser README, this
report, `scripts/check_parser_corpus.py`, two layout test modules and the
offline-tool unit tests. No dependency, database or application schema changed.

Geometry is checked before legal-tail trimming: an ambiguous history appendix
can still reject the entire PDF. Do not bypass it or alter original snapshots.
The A/B032 repeated-caption loss must also be addressed/reviewed before rollout;
this change does not modify the furniture cleaner to hide that regression.
Before any new ingestion, resolve/review the documented rejections, visually
approve changed clinical table relationships and approve a new parser/config
snapshot. Semantic chunking and embedding behavior then require their own
validation. This report does not authorize reingestion or reuse of old chunk IDs.
