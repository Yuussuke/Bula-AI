# Initial download audit

Historical review: 2026-10-05, before the final corpus selection.
The final [selection report](corpus_selection_report.md) and manifests supersede
this initial acquisition status.

| Check | Result |
| --- | ---: |
| Downloads opened and reviewed | 93 |
| Unique SHA-256 hashes / duplicate copies | 91 / 2 |
| Unique PDFs with native text | 89 |
| Registration-matched eligible candidates | 88 |
| Registration mismatch / OCR-only PDFs / missing candidates | 1 / 2 / 9 |

The 89 text-bearing PDFs include the mismatched document; they are not 89
eligible leaflets. Hash-identical duplicates were Singulair and Salonpas.
Forteviron and LQFEX-Cloroquina contained image-only pages; no OCR was performed.
Alphacaine remains excluded: expected registration 101770016, but the PDF's
legal page displays 101770025, associated with ARTICAINE in the consulted registry.
Do not change source identity to force a match.

Checks used original-byte hashes, pypdf extraction of every page, registration
matching and visual inspection of ambiguous cases. Local Zone.Identifier
metadata pointed to the official Bulário; this is provenance evidence, not a
cryptographic signature or a new automated PDF-server verification.
No PDF was modified/deleted, and no RAG/parser performance informed eligibility.
