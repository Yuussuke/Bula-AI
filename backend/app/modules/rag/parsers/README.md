# RAG parser layers

The bula parser keeps PDF extraction concerns separate from Markdown hygiene:

1. `SectionDetector` classifies source lines as conservative section candidates.
2. `SectionDetector` also merges adjacent wrapped heading fragments when their
   typography and text shape indicate one visual title.
3. `MarkdownRenderer` emits headings and body text from the merged section model.
4. `markdown_hygiene.trim_markdown_from_legal_section` applies final Markdown
   cleanup, including truncation before legal-tail markers such as
   `DIZERES LEGAIS`, `III - DIZERES LEGAIS`, `III- DIZERES LEGAIS`, and
   `3 - DIZERES LEGAIS`.

When the legal marker is absent, Markdown hygiene leaves the document unchanged.
