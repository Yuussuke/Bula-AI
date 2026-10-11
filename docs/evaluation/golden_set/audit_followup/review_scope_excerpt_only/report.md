# Human audit scope correction

The author explicitly states that no PDF was read in full: human inspection opened the original PDFs near the reference passages to check inconsistencies. The full-document option is removed from the current instrument. This is a disclosed methodological amendment, not evidence that the former full-document requirement was met.

The submitted v3 export passed its original validator: current record snapshots, versions, collection/instrument fingerprints, event checklists and summary are consistent. It contains four explicit approvals: A-B013-Q05 r2, B-CB011-Q02 r2, B-CB025-Q05 r2 and A-B021-Q10 r1. Its four events (including their original snapshots) are archived unchanged in [submitted_events.original.json](submitted_events.original.json), with the source export's path and SHA-256. The full original export in Downloads is untouched; the extract is not an importable ledger.

All four decisions and earlier human histories are preserved. The author clarification supersedes any interpretation of historical `full_document_checked = sim` as actual human full-document inspection, including A-B021-Q10. No event is rewritten and no new approval is fabricated. The 116 pending entries in this export are not revocations of previous reviews.

For negative records, human approval now concerns the record and supplied rationale under **excerpt-only review**, not independently established absence across the full PDF. Existing full-document authorship/assisted checks remain separately attributed. This limits confidence in negative labels and must be disclosed in the TCC; absence of support is not authorization or proof of safety.

The [v4 instrument](../../audit_sample_v4/review.html) uses the same 120 IDs and current snapshots. Its blank ledger contains no transferred decisions. No Golden Set record, corpus, priority, pipeline parameter or metric is changed; there is no freeze, experiment, ingestion or chunk mapping.
