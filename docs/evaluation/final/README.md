# Final-configuration evaluation

Completed 17–18 October 2026; assessment closure authorized by the author.
This is a documentary publication of archived results, not a new experiment,
production release or clinical validation.

## Executed design

- 120 simulated information needs for 30 purposively selected target PDFs:
  ten from corpus A and 20 from B. There are 45 needs from A and 75 from B.
- Two paired formulations per need: scoped (primary) and cross-bula
  (supplementary), producing 240 outputs, not 240 independent questions.
- Scoped retrieval selects the target PDF. Cross retrieval searches all 50
  PDFs of the corresponding A/B corpus, not only the 30 selected targets.
- The unchanged snapshot contains 100 PDFs and 2,974 chunks. Four archived
  ranking arms are compared: BM25, dense, RRF-B and RRF-B + BGE, at K=10.
- Final answers use only RRF-B + BGE and Sabiá-4, temperature 0.2. Answer
  quality is not a four-generator comparison. There are no automatic retries
  or model fallbacks; technical rejection is retained, not replaced by a draft.

The external drafting chat received a neutral medication list, not PDFs or
previous system answers; documentary references were added separately. This
does not make the questions patient-authored, population-representative or a
document holdout. They are a separate evaluation set, not a subset silently
substituted into the frozen 200-question release.

## Measurement

Retrieval is scored before safety supplementation, evidence selection or answer
generation. Gold relevance is restricted to the reference PDF in both scenarios.
Recall@10 is mean per-question chunk recall; MRR@10 uses the first gold rank
within ten, otherwise zero. Stored tie order and cross-document competitors are
preserved. Coverage of every equivalent chunk is not required for a correct answer.

Report 85 full-support needs as primary, 19 partial-support needs separately,
one source conflict separately and 15 unsupported needs with N/A retrieval metrics.
`Q039` retains zero in the primary denominator for an unindexed raster instruction.
Qrels were finalized after response execution, independently of ranking files;
this is not pre-execution freezing or independent blinded gold annotation.

All 240 outputs have an initial author assessment and a complementary Gemini
2.5 Pro judgment. The five 1–4 dimensions are documentary fidelity, indispensable
information, relevance, clarity and safety; N/A, issue flags and abstention
adequacy are separate. Unsolicited complementary detail is not obligatory.
Full abstention and a grounded explanation of limitations are not automatically
incorrect. Absence in the target PDF alone cannot establish cross-corpus absence.

The author initially reviewed without judge grades, then adjudicated the 74
registered disagreements with both assessments visible. No original grade was
replaced. This is same-author adjudication, not independent expert validation.

## Relation to earlier milestones

The [1,000-question Golden Set](../golden_set/release/README.md), its later
200-question derivative, pilots, 600-output run and controlled 36/24-question
[reranking comparison](../reranking/README.md) remain historical development
and evaluation evidence. They are not pooled into this round's denominators.
The [2026-10-06 plan](../experimental_design_decisions.md) records intentions,
not the final executed design. The implementation remains the DSRM artifact;
these evaluations document its development and limitations, not clinical safety.

See [results](results.md), [configuration/custody](reproduction.md) and the
[compact provenance inventory](provenance.json). No tuning or new execution is
performed by this publication. Runtime integration and deployment verification
remain separate from this documentation-only PR.
