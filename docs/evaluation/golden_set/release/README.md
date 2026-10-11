# Golden Set v1.0.0

Accepted and frozen: **1,000 records, 800 positives / 200 negatives, 100 PDFs**,
50 PDFs per corpus and eight positives/two negatives per PDF.

[Publication inventory](publication.json) retains only the 11 effective bases,
ten overrides, original record bindings, PDF identities, audit IDs and release
fingerprints. Inputs are copied byte-for-byte; no questions or decisions were
rewritten. Historical draft/pending flags are not collection-level rejection.
Git attributes prevent newline conversion of these hash-bound files.

This inventory is a packaging index, **not the original freeze manifest**.
That manifest remains unchanged externally (SHA-256
`0b59a882ab360efbf7fcb51bb4c6ba1794f0d6c9d72fc2a88f88fcadb53b4fd7`;
canonical fingerprint
`33ecd26d18b82925ec4c4e83b0eebf8e8edd39b432039926fd0c51f746ed7de0`).

## Audit and evaluation scope

- Main sample: 100 stratified records, seed 20261009, one per PDF,
  50 per corpus, 80 positives/20 negatives. Another 20 positives were selected
  by risk, not randomly; all 120 IDs and existing decisions are preserved.
- Human review covered original PDF excerpts and nearby context, not complete
  PDF reading. The 20 sampled negatives received separate AI-assisted
  complete-PDF checks (237 pages), with targeted visual inspection.
- The 190 authorship alerts and six documentary P0 treatments remain archived;
  they are not automatically confirmed errors or human closure events.
  No independent clinical validation or individual approval of all records
  is claimed, nor absence of support throughout the corpus.
- Recall@10/MRR@10 use only target-PDF evidence, even in cross search without
  a hidden target filter. Negatives assess abstention only scoped. Retrieval
  hits do not guarantee multi-fragment coverage or faithful answers; fidelity,
  readability and latency remain separate. Optional context is not mandatory
  answer content, while indispensable qualifiers must be preserved.

## Verification and external archive

From the repository root, with the locked environment installed:

```bash
uv run --offline --project backend --no-sync python docs/evaluation/golden_set/release/verify.py
uv run --offline --project backend --no-sync python -m unittest discover -s docs/evaluation/golden_set/release -p test_verify.py
```

A clone verifies published byte hashes, effective record fingerprints,
bindings, document identities and counts. It does **not** revalidate PDF
quotations, semantic support or external audit decisions.

Full reproduction requires the author's complete hash-bound custodial archive:
original manifest, all revisions/audit events/scripts and 100 exact PDFs.
Restore recorded relative paths; obtain original bytes rather than regenerate
decisions. The original manifest binds a legacy private absolute decision-file
location: retain that location in the custodial environment for its full
verifier, without editing the manifest. No hosted archive is provisioned here.

The former combined PR #262 retains the broader public packaging history;
private originals remain in the custody of the author. This smaller publication
does not discard them. No RAG change, principal experiment, chunk mapping or
metric calculation is included. Those activities require separate authorization.
