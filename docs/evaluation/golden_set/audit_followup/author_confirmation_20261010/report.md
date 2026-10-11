# Author confirmation and actual human-review scope

2026-10-10. This follow-up records an explicit author action, not an AI decision or an automatically migrated approval. The author states all records were manually reviewed, specifies review of source excerpts rather than the full PDFs, and explicitly approves the current versions of two changed records.

## Preserved evidence of review

- The supplied historical JSON contains 128 events covering 119 distinct records: 117 approved, one rejected and two pending in its record-level summary. Its structure/history was validated against the historical instrument. The file is archived unchanged in `legacy_decisions.original.json`; the original Downloads file is untouched.
- Exactly 118 of its 120 source snapshots equal current snapshots. Only `A-B016-Q08` and `B-CB021-Q04` differ. Their current author confirmations are recorded separately in `author_confirmation.json`, bound to current revisions 2 and 3, canonical record/PDF hashes, and dataset/instrument fingerprints.
- The author's general assertion that all records were manually reviewed is preserved verbatim. It is not converted into answers to `variant_equivalence` or `target_identity`, or fabricated current-format checklist events. There is no new automatic import compatibility or replacement of historical events.

## Scope clarification — no silent protocol change

Source-excerpt inspection can substantiate positive quotations and local semantic support, provided necessary context and qualifiers are retained. It does **not** establish that information is absent elsewhere in a reference PDF.

The current statement therefore cannot substantiate `full_document_checked = sim` for the 20 sampled negatives. Historical answers remain in the immutable history, alongside this later clarification; they are not silently rewritten or treated as evidence of full-PDF human inspection. The author is not required to redo all positive reviews or inspect every full PDF to record this limitation honestly.

No revised absence-verification procedure is adopted here. Any assistant-assisted full-document conference would be recorded as assisted documentary verification, not human full-PDF review. Relaxing the previous acceptance requirement would need an explicit methodological decision and disclosure, not a fabricated checklist answer or claim that the original protocol was met.

## Existing specific findings retained

- `A-B013-Q05`: latest historical decision is pending, with a population/scope comment. It has not been resolved by the present general continuation authorization.
- `B-CB011-Q02`: latest historical decision is rejected, with a specificity/plausibility comment. That explicit decision is not replaced with approval.
- `A-B021-Q10`: no individually saved event in the supplied file. The later statement that all were manually reviewed is retained, but no checklist or specific outcome is invented for it.
- All other comments, previous events and unresolved authorship alerts remain available. Approval of the two changed records does not automatically close safety alerts, validate all 1,000 records, settle every checklist field, or accept/freeze the collection.

## Next boundary

Continuation authorization is recorded, but questions, current instrument, sample IDs, priorities, corpus, RAG pipeline and frozen parameters remain unchanged. No ingestion, chunk mapping, experiments, provider calls, answer judgment or final freezing was executed.

Before final acceptance, resolve the specific pending/rejected findings and decide how the absence evidence for negatives will be substantiated or qualified under the actual review scope. No new independent semantic verifier is implemented or required by this note.
