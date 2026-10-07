# Experimental design decisions

Recorded on 2026-10-06. Pre-experimental plan, not completed evaluation results
or a replacement for the thesis methodology.

## Design

- Preserve applied research/DSRM and documentary evaluation, not clinical
  validation, patient studies or model training.
- Compare BM25, dense and hybrid retrieval on identical documents/chunks.
- Use [corpus A](corpus/corpus_final.csv) for documentary variation and
  [corpus B](corpus_b/corpus_b_final.csv) for thematic concentration.
- Compare known-document and cross-document retrieval separately in each corpus:
  two corpora × two scopes × three strategies = 12 experimental conditions.
- Prefer ten information needs per document: eight supported and two unsupported.
  Confirm feasibility in the disjoint [pilot](corpus/corpus_pilot.csv); 4+1 remains
  a discussed alternative, not an adopted reduction.
- This yields 1,000 needs (800 positive, 200 negative), up to 2,000 equivalent
  question formulations and 6,000 pipeline runs. Model/evaluator calls and retries
  are additional; repeated formulations are not independent samples.
- Use `sabia-4` without Thinking, following the auxiliary selector comparison
  documented in the [backend guide](../../backend/README.md#6-rag-evidence-selector-model).
  The judge model is a separate, unresolved choice.

Cross-document runs must search only the corresponding 50-document corpus,
without supplying the gold document as a hidden filter or filtering only after
top-k retrieval. Known-document runs do not test inter-document competition.
Keep private/shared access checks outside the experimental factors. Corpora
differ in several dimensions; differences do not isolate a causal effect of
thematic similarity. Multi-document comparative questions remain outside the
recommended main battery, subject to confirmation.

## References and freeze

Draft questions/golds with LLM assistance, then review against the source.
Record target document/presentation, proposition, topic, section/page, excerpts
and indispensable conditions; map chunk IDs after validating/fixing ingestion.
Do not derive golds from retriever/selector outputs or select documents by RAG performance.
Preserve equivalent propositions across scopes; include all valid alternative
evidence. Reconcile the TCC1 two-chunk annotation limit with actual chunking.

Cover dosage, contraindications, interactions, adverse reactions, warnings,
pregnancy, storage and composition where applicable. Do not invent evidence to
meet topic quotas. Negative cases require documented absence for the target
proposition, not a parsing/retrieval/selection failure.

Before the main run, freeze commit, manifests/PDF hashes, ingestion, embeddings,
prompts, model settings, candidate/context budgets, evaluator rubric, manual
audit sampling and retry/fallback/error policies. No tuning on main-run scores.

## Measurement

Capture original ranked retrieval, supplemented candidate context and selected
sources separately within each execution. Evaluate retrieval before safety
supplementation or evidence selection; do not reconstruct it with another search.

- Recall@4: fraction of gold chunks in the original top four.
- MRR@4: mean reciprocal rank of the first gold chunk; zero when absent.
- Negative cases without golds: exclude from Recall/MRR with explicit denominators.
- Answers: RAGAS Faithfulness, rubric-based LLM-as-a-Judge, documentary hallucination,
  appropriate abstention, adapted FRES, traceability and descriptive P50/P95 latency.
- Report false abstentions, technical/evaluator failures and fallback separately.
  Claim-free abstention is not automatically perfect Faithfulness.
- Cross-document diagnostics: target-document presence in top four and wrong-drug attribution.

Assess the final natural grounded answers, not the auxiliary selector benchmark
or diagnostic extractive output. Automated scoring is supplemented by a
stratified human documentary audit, not manual scoring of every answer. Audit
size and evaluator/abstention policies remain to be fixed.

## Feasibility and milestones

Measure active reference preparation, automatic execution and sample audit
separately in the pilot. Do not use hypothetical minutes as measured workload;
one pilot cannot represent every long/table-heavy document.
Availability is three weekday hours plus unquantified weekend time. Preferred
targets: pilot by October 11, integration by October 18, freeze by October 25,
main evaluation October 26–November 1, written submission November 23, 2026.
These are planning targets, not completed milestones; revise scope explicitly
if pilot measurements show that 8+2 cannot fit without reducing rigor.

See [pilot readiness](pilot_readiness.md) for the immediate implementation path.
