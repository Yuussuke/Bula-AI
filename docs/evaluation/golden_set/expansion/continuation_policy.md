# Draft expansion: author conference after batch 01

Author decision, 2026-10-09. Batch 01 is accepted for **continued documentary drafting**, not individual human validation or experimental freezing. Its 100 records, references, pending decisions and hashes remain unchanged. Continue with the next ten eligible documents, five per corpus; stop after batch 02, before batch 03.

## Safety annotation, without changing the reference

`B-CB003-Q03` requires specific safety review. Its scenario includes breathing difficulty and lip swelling. The existing source instructs immediate reporting to the doctor and discontinuation in those cases. Review explicitly how emergency-oriented guidance should be handled, rather than treating this only as an ordinary informational response.

This is an **author-requested review alert**, not a human documentary approval, revised expected answer or new metric. Do not silently rewrite the original source quote, invent a documentary emergency instruction, or mark this question safe/approved. Any eventual documentary correction requires a separately recorded decision and version.

Affected input: `batch01/questions.draft.jsonl`, SHA-256 `91c195c65e3fa997727b5442bee0a62ba573d2a6afc67fe935b25ce386449e4c`. Alert status: pending specific safety review; human approval: pending.

## Boundaries for batch 02 and later drafting

- Preserve Fluibron A flaconetes versus Fluibron drops, route and local presentation in `A-B005`. Preserve the source/manufacturer discrepancy already documented in batch 01 (including the Zambon-or-Mariol text); do not edit the frozen corpus manifest.
- Diversify unsupported propositions in subsequent batches. Do not routinely substitute gluten, latex or sodium questions across documents. Read the entire target PDF and explain why related passages do not answer the requested proposition. Topic variety does not justify an invented negative.
- Preserve natural Brazilian Portuguese and complete information needs. Do not remove essential age, route, presentation, timing or co-medication to make wording shorter.
- Keep assistant/author alerts separate from actual human review events. Policy approval or acceptance for continuation does not approve records automatically.
- Keep [target-PDF relevance](../phase1/reference_policy.md), main metrics, frozen parameters and [requested-versus-complementary fidelity](../answer_fidelity_policy.md). Do not use RAG rankings or answers in question drafting.
- No chunk mapping, ingestion or experiments at this stage. Both batches remain drafts, and negative abstention remains per-leaflet only.
