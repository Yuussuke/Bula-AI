# TCC evaluation preparation

Preparation artifacts only: the pilot and main evaluation have not been run.
The evidence-selector benchmark remains an auxiliary development check.

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

Next: review ten pilot references, implement natural grounded generation and
instrument the evaluation runner. Verify cross-document access and corpus
isolation before the main evaluation.
