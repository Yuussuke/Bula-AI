# Parser identity and prose continuity

Local validation against `origin/main` at `253bcd1`; parser version
`native_markdown_identity_prose_v4`. No model calls, index writes, retrieval,
chunker changes or changes to pilot questions.

## Causes and changes

- Removing an outer bold wrapper before recognizing independent inline runs
  left markers inside product names. Balanced runs are now removed without
  stripping literal single underscores, footnote stars or trademark symbols.
- The first cover strength could be less specific than the presentation.
  Explicit presentation strengths now take precedence. Standalone mL package
  volumes are excluded; written ratios with the same units are compared exactly.
  Output remains a literal source value, not a computed dose. Distinct strengths
  omit the scalar field rather than silently choosing one presentation.
- Converter blank lines were accepted as paragraph boundaries even between
  consecutive PDF lines. Reconciliation now requires complete visible-text
  matches, consecutive physical lines in one block, similar heights, close
  spacing and aligned starts, plus an unfinished sentence and lowercase
  continuation. Structural boundaries and missing geometry prevent joining.

## Before/after checks

| Document | Observation |
| --- | --- |
| PETIVIT BC | `PETIVIT**® **BC` becomes `PETIVIT® BC`; `0,8 mg` becomes the presentation's `0,8 mg/mL`; pregnancy sentence remains one paragraph. |
| Dipirona, Sanofi Medley fixture | Product and `50 mg/mL` preserved; existing dosage-table assertions pass. |
| Amoxicilina, Cimed fixture | `50 mg/mL` and `250 mg/5 mL` correctly reconcile; output uses literal `50 mg/mL`. |
| Nesina Met, Cosmed fixture | Product markers removed; scalar strength omitted because `12,5mg + 850mg` and `12,5mg + 1000mg` are distinct. Both remain in the presentation. |

All four parsed successfully. Body word sequences and detected section titles
were identical before/after (excluding front matter); this is a lexical check,
not proof of correctness for all PDF layouts. The Cimed fixture's missing product
and overbroad dosage-form value already existed in the baseline and were not
addressed by this change.

PETIVIT's deterministic preview still has 16 chunks. All 13 draft quotation
fragments remain present in parsed text and chunks; two are related passages
for negative cases, not supporting gold. Semantic chunking and live indexed
state were not evaluated.

Validation: 380 tests passed (`tests/unit/rag` plus parser golden integration
tests). The full local suite passed with 677 tests, 63 skips and approximately
88% coverage; skips cover unavailable integration services and an optional PDF.
Backend-wide Ruff checks/formatting and mypy on all 89 application files passed.
Pytest required execution outside restricted temporary-directory permissions.
Existing dependency deprecation warnings remain.

## Trade-offs and limits

Conservative reconciliation may retain artificial breaks with uncertain layout,
different blocks or capitalized continuation. Multiple strengths remain in the
presentation rather than a new schema. Equivalence does not convert between
different unit names; unsupported units and mass-based packaging still require
review. This is not a universal pharmaceutical-expression parser. Four PDFs are
regression samples, not a validation of the complete TCC corpus. Timing was not
a controlled performance experiment.

Existing indexed documents are unchanged. Adopt through explicit reprocessing
and inspect final chunks before freezing their IDs; BM25 backfill alone cannot
repair parsed source text. Preview artifacts remain local and unversioned.
