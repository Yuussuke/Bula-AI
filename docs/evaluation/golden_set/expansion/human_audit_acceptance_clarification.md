# Collection acceptance and individual human review

Author clarification, 2026-10-10, before batch 07. This clarifies the existing [audit protocol](../review_demo/protocol.md); it does not replace or expand it.

The planned final process combines automatic verification of **100% of records** with a **stratified human sample** and additional risk-priority audit. The protocol specifies a core of 100 questions, one per document, with seed `20261009`; its separate risk audit and escalation rules remain unchanged. No sample is drawn or reviewed in this drafting stage. The proposed additional risk budget still requires the author confirmation already specified in that protocol.

## Two different decisions

- **Acceptance of a collection/version:** an explicit methodological decision after the required automatic verification, planned sample audit, risk-issue resolution and other freeze prerequisites. It is not a claim that each question was individually human-reviewed.
- **Individual human review/approval:** a genuine reviewer action attached to an exact record/version hash, stored separately. A reviewed question can remain pending, have doubts, or be rejected. Acceptance of a batch for continued drafting never creates individual approvals.

An unaudited record remains `human_review_status=pending` and must not be described as human-approved. That status alone does not create a new requirement to individually audit all 1,000 questions before collection acceptance. Unresolved blocking alerts are not waived by sampling; retain the protocol's risk audit and escalation procedure.

Earlier reports and revision metadata remain immutable. Where they say every record must receive independent individual documentary approval before entering metrics, read that wording as superseded by this distinction: **the accepted/frozen collection must satisfy the agreed verification and audit protocol**, not universal individual human review. Genuine individual decisions remain separate and are never inferred, migrated or fabricated.

## Current status and unchanged boundaries

All expanded records are still documentary drafts. Continuation authorization is not final collection acceptance. Current offline checks establish structure, source integrity, literal quotation location and coverage bookkeeping; they do not claim completion of the planned independent semantic verification or human audit. Assistant full-PDF reading and authorship alerts are not human review events.

Preserve reference-PDF relevance in both search scenarios, Recall@10 and MRR, per-leaflet-only negative abstention, separate response fidelity, and the distinction between indispensable answer information and complementary context. No RAG, ingestion, chunk mapping, experiment, judge, audit-tool implementation or change to frozen pipeline parameters is authorized by this clarification.
