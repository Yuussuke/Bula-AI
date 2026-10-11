# Golden Set v1.0.0 — published milestone

The author accepted and froze **1,000 effective documentary records**: 800
positive and 200 negative questions, linked to 100 PDFs (50 per corpus).
This is collection-level methodological acceptance, not clinical validation
or individual human approval of every question.

## Immutable collection and provenance

[Publication inventory](publication.json) identifies the exact source files,
ordered 11 bases, ten overrides, reference PDF hashes and original freeze
fingerprints. [Record bindings](../frozen/v1/record_bindings.jsonl) preserve the
effective revision and hash of every question. Historical revisions are not
additional observations; authored draft/pending flags have not been rewritten.

Git attributes disable newline conversion for this collection: byte hashes
must remain identical on Windows and Linux. Historical blank lines at EOF
are preserved rather than silently formatted.

The inventory is **not a replacement or rewritten version** of the original
freeze manifest. That manifest remains unchanged in the custodial archive:
SHA-256 `0b59a882ab360efbf7fcb51bb4c6ba1794f0d6c9d72fc2a88f88fcadb53b4fd7`.
Its canonical fingerprint is
`33ecd26d18b82925ec4c4e83b0eebf8e8edd39b432039926fd0c51f746ed7de0`.

The main audit sample contains **100 stratified records**, one per PDF,
50 per corpus, 80 positive / 20 negative, seed 20261009. Another **20 positive
records were selected by risk**, not randomly. The 120 IDs and current version
bindings remain unchanged. Human inspection covered excerpts in the original
PDF and nearby context, **not complete human reading of the PDFs**.

The 20 sampled negatives received separate AI-assisted complete-PDF checks
(237 pages), with targeted visual inspection. This does not establish absence
throughout the corpus. Original human events remain preserved externally;
the [closure index](../audit_followup/round_closure/closure.json) is derived
provenance, not a new decision ledger. No decisions were inherited or created.
The [190 authorship alerts](../audit_plan/priority_queue.json) and
[six P0 treatments](../revisions/documentary_approved_02/p0_documentary_summary.json)
remain distinct from confirmed defects or automatic human closures.

## Evaluation boundary

Recall@10 and MRR@10 evaluate only annotated evidence from the target PDF in
both scoped and cross-bula search. Cross search must not secretly filter by
that target. Negatives evaluate abstention only in the scoped scenario.
Retrieval hits do not guarantee complete multi-fragment coverage or faithful
answers. Fidelity separately distinguishes indispensable information and
qualifiers from optional context; readability and latency remain separate.

[Reference policy](../phase1/reference_policy.md),
[fidelity policy](../answer_fidelity_policy.md),
[linguistic policy](../phase1/linguistic_policy.md) and the
[original freeze report](../frozen/v1/report.md) preserve the documentary
decisions and their limitations. Old notices describe their historical stage.
No main experiment or principal metric has been executed for this milestone.

## Reproduction and external dependencies

A fresh clone can verify all published byte hashes, effective records,
bindings, document identities and counts, without APIs, PDFs or private files:

```bash
uv run --offline --project backend --no-sync python docs/evaluation/golden_set/release/verify.py
```

This check **does not revalidate PDF quotations, external audit events or
semantic support**. Full documentary reproduction requires the complete
hash-bound custodial archive. `external_history` lists omitted relative paths
and hashes; the private original decision submission is identified by hash
only. PDF inventory paths and hashes are preserved separately. Obtain these
assets from the project author, not from RAG outputs or regenerated decisions.

Restore the unchanged original manifest at
`docs/evaluation/golden_set/frozen/v1/manifest.json`, historical files at their
recorded relative locations and exact PDF bytes at the inventory locations.
Private decision provenance includes a legacy absolute source location:
retain its original bytes/location in the custodial environment for the
original full verifier. Do not edit that manifest to relocate it or claim a
fresh clone alone reproduces the complete audit. The archive also retains
the original verification scripts and generated review instruments.

PDFs, raw reviewer submissions, duplicated historical HTML/templates,
intermediate QC exports and machine-local snapshots are deliberately not
published. Their omission changes neither collection hashes nor preserved
history. No new public archive or automatic download is created by this PR.

Next stages require separate authorization: isolated ingestion, gold-to-chunk
mapping, retrieval evaluation and natural grounded-response evaluation.
