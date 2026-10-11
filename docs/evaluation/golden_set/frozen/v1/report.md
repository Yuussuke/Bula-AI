# Golden Set v1.0.0 — definitive documentary freeze

The author explicitly authorized methodological acceptance and freezing after the audit round closed. This release preserves the effective collection unchanged: **1,000 records, 800 positive / 200 negative, 100 reference PDFs**, with 50 PDFs and 500 records in each corpus. There are eight positives and two negatives per PDF.

[The definitive manifest](manifest.json) is the collection-level authority. Resolve its 11 ordered bases, then the seven linguistic/semantic overrides and three documentary overrides. Historical files are not additional records. [Per-record bindings](record_bindings.jsonl) record every effective ID, revision, canonical hash and source file; they contain no rewritten questions.

## Final checks

[Reproducible validation](validation.json) found **zero material divergences**:

- 100 original PDFs / 1,109 physical pages: identity, exact-byte SHA-256, frozen manifest rows and record provenance checked.
- 1,002 effective literal reference fragments: page ranges and whitespace-normalized native-text matches checked, respecting recorded source regions.
- 1,000 unique record IDs; exactly 8/2 per PDF; 50/50 corpus documents and 500/500 corpus records.
- No duplicate PDF hashes or normalized cross-leaflet queries. Repeated scoped wording across different documents is not automatically a defect; semantic duplicates are not exhaustively machine-certified.
- All revision deltas/hashes and 120 current audit version bindings checked. The existing main 100 IDs and additional 20 IDs, their ordering and priorities were not redrawn.
- All 190 authorship alerts and six current P0 documentary treatments retained.
- All 230 pre-existing collection/history/protocol files were unchanged before sealing. Only CURRENT.md and AUDIT_INSTRUMENT.md are superseded entry notices; their exact prior bytes are archived here. The submitted complete original decision file remains unchanged at its hash-bound original location.
- 33 tests passed: 18 Python integrity/version/audit tests, 12 ledger tests and 3 interface compatibility tests. Ruff and git diff --check passed.

Mechanical quote matches do not independently establish semantic entailment, table-cell association or clinical correctness. The previously documented visual conferences and audit findings remain distinct evidence.

## Acceptance and audit scope

The main sample is **100 seeded stratified records**: one per PDF, 50 per corpus, 80 positive and 20 negative; seed **20261009**. The other **20 are risk-directed additions**, all positive (12 corpus A / 8 B), not a second random sample. Their union is 120 distinct IDs. One P0 is in the main sample and five are in the additions; all eight positive Olina needs remain covered across these groups.

Human inspection covered **original PDF excerpts and nearby context**, not complete human reading of every PDF. The separate assisted conference examined full native text of the **20 sampled negative target PDFs / 237 pages**, with targeted visual inspection. This is AI-assisted documentary work, not full-document reading by the human evaluator or proof of absence throughout the corpus.

The closure index preserves 114 compatible historical approval events, two explicit current-version confirmations and four submitted current-version events. It is a derived provenance index, not a new decision ledger. No human decision was created, migrated or inferred from collection acceptance. The other 880 records are **not individually human-approved**, and completion of a uniform new checklist is not claimed.

The author accepts the six documentary P0 treatments as part of this methodological freeze. Their original reports, tensions and safeguards remain unchanged; no automatic human closure event is created. The 190 alerts (6 P0 / 90 P1 / 89 P2 / 5 P3) and their referrals remain available, not automatically confirmed defects or unresolved blockers.

Authored records retain their historical draft/pending fields and empty chunk mappings. This manifest separately records collection-level acceptance; it does not falsify individual review metadata. Historical notices saying “not frozen” remain valid descriptions of their time and are superseded by this release.

## Preserved evaluation protocol

- Recall@10 and MRR use only relevant chunks of the identified reference PDF, in both scoped and cross-leaflet search. Cross-leaflet competition retains other-document ranking positions, without a hidden target filter.
- MRR retains the existing ranking/cutoff convention; this release does not redefine it. Record the inherited convention explicitly in the later experiment manifest.
- The 200 negative needs assess abstention only per leaflet. Cross-leaflet variants do not establish absence across the corpus; documentary absence is not authorization or a safety claim.
- Recall@10 and MRR do not guarantee complete multi-fragment evidence or correct interpretation. Documentary answer fidelity is evaluated separately, distinguishing indispensable requested information/qualifiers from optional complementary context.
- The main retrieval comparison, response fidelity, readability and operational indicators remain unchanged. No independent clinical validation is claimed.

[Target-document policy](../../phase1/reference_policy.md), [fidelity policy](../../answer_fidelity_policy.md) and [linguistic revision 4](../../phase1/linguistic_policy.md) remain preserved. Their earlier draft-status paragraphs are historical, not current rejection of collection acceptance. Questions were not selected or rewritten using RAG outcomes in this task.

## Reproduction and next-stage boundary

From the repository root:

```bash
uv run --offline --project backend --no-sync python docs/evaluation/golden_set/frozen/v1/verify.py --manifest docs/evaluation/golden_set/frozen/v1/manifest.json
```

The verifier is evaluation-only and read-only. It checks both the preserved source chain and this sealed release; a material mismatch exits nonzero instead of repairing data. Original PDFs, the original submitted decision file and the recorded historical paths must remain available; copy the complete hash-bound source tree when backing up this release, not only the manifest.

The documentary collection is ready for the **next separately authorized stage**, not for immediate metrics: no ingestion snapshot or chunk golds are created here. Freezing does **not** authorize ingestion, retrieval, model calls, chunk mapping, response judging, metric calculation or experiments. Production code, RAG parameters, corpus contents and indices were not changed.
