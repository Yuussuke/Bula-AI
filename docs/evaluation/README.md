# TCC evaluation preparation

The [Golden Set v1.0.0 publication](golden_set/release/README.md) documents
the completed methodological freeze: 1,000 questions linked to 100 PDFs.
[Offline infrastructure](experiment_preparation/README.md) separates retrieval
and response evaluation. The main experiments and principal metrics have not
been executed. Earlier pilots/selector checks are development diagnostics,
not the principal evaluation.

- [Corpus A](corpus/corpus_final.csv): 50 documents selected for documentary
  diversity; [selection rationale](corpus/corpus_selection_report.md).
- [Corpus B](corpus_b/corpus_b_final.csv): 50 documents in five recurring
  therapeutic groups; [selection rationale](corpus_b/corpus_b_selection_report.md).
- [Pilot](corpus/corpus_pilot.csv): P001, PETIVIT BC, outside both corpora.
- [Download audit](corpus/download_audit_report.md): historical eligibility checks.
- [Experimental decisions](experimental_design_decisions.md): design and metrics.
- [Pilot readiness](pilot_readiness.md): implementation gaps and next steps.

The manifests contain 101 distinct PDF hashes and registration numbers. Keep
IDs, registrations, processes and CNPJ values as text. Portuguese field names
and source annotations are preserved; the CSVs are unchanged by this editorial update.
PDFs, personal absolute paths and intermediate experiment outputs are excluded.
Archive PDFs outside temporary directories before cleanup.

Next: approve operational snapshots and isolated ingestion, map documentary
golds independently of rankings, then separately authorize retrieval and
response evaluation. Natural grounded generation remains a response-stage
prerequisite. Full documentary reproduction requires the external custodial
archive described in the release notes; a clone alone is not that archive.
