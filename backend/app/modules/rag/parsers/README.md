# RAG parser layers

The default parser converts selectable-text PDFs with PyMuPDF4LLM's modern
layout engine. It requests page chunks, disables OCR explicitly, processes one
document at a time, and records the converter version and `native_text`
decision. It does not instantiate the legacy `IdentifyHeaders` helper. The
plain PyMuPDF handler remains a sparse/error fallback; OCR belongs to its own
later ingestion phase.

The bula parser keeps extraction concerns separate from Markdown hygiene:

1. `PyMuPDF4LLMHandler` converts each page to Markdown while retaining its
   one-based page number.
2. `BulaDocumentCleaner` removes repeated page furniture, page-number text,
   omitted-picture markers, and soft hyphens before section detection. It joins
   ordinary wrapped prose but leaves lists, paragraph boundaries, units,
   decimal commas, ranges, and Markdown table rows unchanged.
3. `BulaDocumentCleaner` moves the cover identity block into YAML front matter
   and repairs the known cross-page pediatric dosage-table header/weight rows.
4. `SectionDetector` classifies conservative section candidates and normalizes
   core clinical sections to level 2 and internal topics to level 3.
5. `SectionDetector` also merges adjacent wrapped heading fragments when their
   typography and text shape indicate one visual title.
6. `MarkdownRenderer` emits headings and body text from the merged section model.
7. `markdown_hygiene.trim_markdown_from_legal_section` applies final Markdown
   cleanup, including truncation before legal-tail markers such as
   `DIZERES LEGAIS`, `III - DIZERES LEGAIS`, `III- DIZERES LEGAIS`, and
   `3 - DIZERES LEGAIS`.

When the legal marker is absent, Markdown hygiene leaves the document unchanged.

The converter API and page-chunk contract are documented in the
[official PyMuPDF4LLM API](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html).

## Five-document benchmark

`scripts/benchmark_pdf_markdown.py` runs the legacy and native variants in
separate child processes, strictly sequentially. It records SHA-256 identity,
page count, lexical token recall against the selectable text layer, Markdown
heading count, unique critical dosage-signal recall, wall time, standalone page
numbers, and peak process-tree RSS. The report contains metrics only; PDFs and
generated JSON stay under ignored `backend/tmp/parser-benchmark/`.

Run it with exactly five distinct PDFs:

```bash
make benchmark-pdf-markdown ARGS="tests/fixtures/rag/bulas/dipirona_sanofi_medley_solucao_oral.pdf tests/fixtures/rag/bulas/amoxicilina_cimed_suspensao_oral.pdf tests/fixtures/rag/bulas/nesina_met_cosmed_comprimido_revestido.pdf tmp/parser-benchmark/metronidazol-cimed-patient-benchmark__10709560__patient.pdf tmp/parser-benchmark/sinvastatina-ems-patient-benchmark__29377928__patient.pdf --output tmp/parser-benchmark/results.json"
```

The 2026-08-28 Windows run used PyMuPDF4LLM 1.28.2 and covered 85 pages
across Dipirona Sanofi, Amoxicilina Cimed, Nesina Met Cosmed, Metronidazol
Cimed, and Sinvastatina EMS:

| Metric | Legacy | Native |
|---|---:|---:|
| Mean lexical token recall | 0.664 | 0.717 |
| Mean unique critical dosage-signal recall | 0.856 | 0.967 |
| Standalone page numbers | 19 | 0 |
| Markdown headings | 167 | 126 |
| Total wall time | 12.9 s | 25.4 s |
| Peak process-tree RSS | 253 MB | 342 MB |

These measurements are a comparison snapshot, not a hardware-independent
performance gate. The Dipirona regression separately asserts its front matter,
manufacturer, core clinical sections, natural prose, page-number removal, page
provenance, decimal/range preservation, and pediatric dosage relationships.

## License decision

The lockfile uses PyMuPDF, PyMuPDF4LLM, and PyMuPDF Layout 1.28.2. Their
published terms are dual GNU AGPL v3 or an Artifex commercial license. The
upgrade from 1.27.2.3 is intentional: that older layout wheel still declared
PolyForm Noncommercial/commercial terms.

The repository is public but currently has no declared project license. Local
academic development can continue, but a production/public-service release
must first choose AGPL-compatible project terms or obtain the applicable
commercial license. This README records the dependency decision; it is not
legal advice.
