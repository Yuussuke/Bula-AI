# TCC evaluation

Current milestone: [final-configuration evaluation](final/README.md), with
[retrieval/answer results](final/results.md) and [reproduction boundaries](final/reproduction.md).
The 120 needs produced 240 scoped/cross outputs; human/Gemini assessment and
the 74-case divergence review are closed, with one explicitly inconclusive case.
This is not a production integration or clinical validation claim.

[Golden Set v1.0.0](golden_set/release/README.md) remains frozen: 1,000 questions
linked to 100 PDFs. Its later 200-question derivative and previous experiments
are distinct from the final 120-need evaluation; their denominators are not pooled.
The [RRF-B/BGE milestone](reranking/README.md) remains an auxiliary comparison.

- [Corpus A](corpus/corpus_final.csv): 50 documents selected for documentary
  diversity; [selection rationale](corpus/corpus_selection_report.md).
- [Corpus B](corpus_b/corpus_b_final.csv): 50 documents in five recurring
  therapeutic groups; [selection rationale](corpus_b/corpus_b_selection_report.md).
- [Pilot](corpus/corpus_pilot.csv): P001, PETIVIT BC, outside both corpora.
- [Download audit](corpus/download_audit_report.md): historical eligibility checks.
- [Experimental decisions](experimental_design_decisions.md): historical plan.
- [Pilot readiness](pilot_readiness.md): historical implementation checklist.

The manifests contain 101 distinct PDF hashes and registration numbers. Keep
IDs, registrations, processes and CNPJ values as text. Portuguese field names
and source annotations are preserved; the CSVs are unchanged by this editorial update.
PDFs, personal absolute paths and intermediate experiment outputs are excluded.
Archive PDFs outside temporary directories before cleanup.

Next: finalize thesis reporting and separately review integration of the evaluated
runtime. No additional experiment is authorized by publication. Full reproduction
requires the hash-bound custodial archive, not only this public subset.
