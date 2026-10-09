# Retrieval eligibility and semantic diagnostics

Document identification is not answer evidence. Front-matter-only chunks remain stored and searchable for discovery, but cannot consume the answer retriever's final K slots.

- Chunk artifacts and new Qdrant payloads record a structural `content_role`: `document_metadata` or `evidence`. The latter denotes eligible source content, not semantic support for a particular question.
- Dense retrieval excludes tagged metadata in its query filter and checks source structure for older untagged points before filling K. Its raw budget is independent of the final cut.
- BM25 filters metadata envelopes before ranking/truncation. This role is computed from source structure without a database migration or rewriting stored text.
- Internal discovery can explicitly enable `include_document_metadata`. Authorization is still required before constructing/searching a scope.
- Mixed front matter/prose remains eligible; evidence preparation strips only the envelope. Headings or medicine names do not determine the role.

Existing indices need no re-ingestion for eligibility to apply. Re-ingestion adds payload tags; it is not required solely for this fix. Neither document discovery nor a future cross-bula chat is implemented here.

Semantic chunking keeps its existing request contract, model, prompt, limits and deterministic fallback. Diagnostics now distinguish malformed JSON (`invalid_json`) from strict-schema validation (`invalid_schema`), separately from timeout, truncation and provider failures. Each request records affected section indices, observed model/provider and finish reason when available, plus bounded validation types/locations. Input values, raw responses, exception strings and arbitrary field names are not logged.

A failed batch can cause several section fallbacks; request failure counts and affected-section counts are not interchangeable. Reported provider usage is not proof of billing completeness.

## Controlled Top-K pilot (2026-10-09)

The PETIVIT pilot used eight positive and two negative draft questions, unchanged references and 16 frozen indexed chunks. Parser, chunking, embeddings, selector model (`sabia-4`, temperature 0.2), prompt, schema and equal-weight RRF stayed fixed. K is the final evidence-retrieval cut, not the number of selected units or intermediate candidates.

| Method | Recall@4 | Recall@6 | Recall@8 | Recall@10 | MRR@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dense | 0.75 | 0.75 | 0.875 | 1.00 | 0.7192 |
| BM25 | 0.75 | 0.75 | 1.00 | 1.00 | 0.7835 |
| Hybrid | 0.75 | 0.75 | 1.00 | 1.00 | 0.7813 |

Q02/Q06 first gold ranks were 9/7 (dense), 7/8 (BM25) and 8/8 (hybrid). MRR uses the same rank cutoff across K values; non-gold candidates are not automatically irrelevant.

The controlled pools were dense raw=12, BM25 common cutoff=10, and hybrid=12 candidates per branch (dense raw=36). Every K4 ranking matched the preceding eligibility-fix baseline. No metadata-only chunk consumed an evidence slot. Simply passing K10 to the stock factories also enlarges their derived pools and does **not** reproduce this single-variable experiment.

### Answer impact and trade-offs

- K4/K8/K10 produced 90 accepted outcomes across the three modes. All available positive gold chunks were selected: K4 covered 18/24 positive runs, K8 23/24, and K10 24/24. The two negative questions abstained in every mode and configuration (18/18).
- The first execution had 61 provider rate-limit failures. Only those combinations were retried with spacing; all completed. Preserve those failures separately rather than reporting a technically flawless initial run. Accepted outcomes had valid IDs and no JSON/schema failure.
- K10 supplied more context and used roughly twice K4's input tokens, or 25% more than K8. Provider caching mitigated observed cost, but future cache hits and failed-call billing cannot be assumed. Exact monetary amounts and raw experimental outputs are intentionally omitted.
- K10 warm-pipeline P50 was about 1.37–1.57 seconds across modes; P95 was 1.83–3.45 seconds. These small, mixed execution windows exclude query embeddings, retry spacing and HTTP/UI overhead; they are not production latency guarantees.
- More context adds distractors and can saturate the unchanged six-unit selection limit. Q05 still lost the local vitamin qualifier and included broader interaction text; this existed at K4. Gold coverage is not a documentary-fidelity or natural-answer quality score.

**Decision:** adopt K10 for the main evaluation and standard retrieval defaults after user approval. This is a pragmatic pilot-based choice, not a statistically optimal value. Stop hyperparameter tuning here. The pilot covers one leaflet only and does not establish a cross-bula allocation policy. Keep fidelity, legibility and operational evaluation separate from retrieval metrics.

**Rollout:** final K defaults to 10 for dense, BM25 and hybrid. Preserve the tested pools: dense raw=12, BM25 final=10, hybrid=12 eligible per branch with dense raw=36. Factories no longer multiply the hybrid branch pool by final K; explicit larger cuts still require a pool at least as large as K. Dense supports an explicit raw `candidate_limit`; setting it to null opts into the existing multiplier mode. The safety supplement and six-unit selector cap remain unchanged. No prompts, references, query rewriting or ingestion settings were changed. No migration or re-ingestion is required; restart the API after updating its code. One non-indexing semantic reproduction succeeded, but did not establish the cause or resolution of the earlier invalid responses.
