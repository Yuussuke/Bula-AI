# RRF-B and BGE: auxiliary evaluation milestone

Recorded 2026-10-15. These experiments support the artifact's controlled DSRM
iteration; they do not replace the main retrieval/response evaluation. This is a
documentation-only record: no production configuration or frozen dataset changes.

## Controlled comparison

- Same corrected snapshot: 100 PDFs, 2,974 chunks; fingerprint in [summary.json](summary.json).
- RRF-B: BM25/dense candidate depths 20/20, dense raw limit 60, equal-weight
  RRF with constant 60, final Top-10. Raw dense fetch and eligible candidates differ.
- BGE: rerank that same candidate union (up to 40), not only the RRF Top-10,
  using `BAAI/bge-reranker-v2-m3`, revision
  `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. Descending raw logits,
  chunk-ID tie-break; question plus existing section/text, no gold input.
- Same Sabiá-4, temperature 0.2, prompts, structured output, evidence preparation
  and validators. BGE used CUDA FP16, batch 1, without truncation.
- Scoped, single-turn questions; alternating arms; no automatic retries,
  fallback or LLM judge. Existing safety supplementation was not retuned.

| Measured outcome, per arm | Development: RRF-B / BGE | Final: RRF-B / BGE |
|---|---:|---:|
| Questions | 36 / 36 | 24 / 24 |
| Positive / negative needs | 24+12 / 24+12 | 16+8 / 16+8 |
| Technically valid outputs | 36 / 36 | 24 / 24 |
| Technical failures | 0 / 0 | 0 / 0 |
| Full abstentions on positives | 0 / 0 | 0 / 0 |
| Full abstentions on negatives | 10 / 8 | 6 / 6 |
| Generated explanations on negatives | 2 / 4 | 2 / 2 |

There were 72 development and 48 final executions: 60 needs, not 120 independent
questions. A generated explanation on a negative is not automatically wrong;
recognizing the documentary limitation can be useful. Technical validity and the
absence of full abstention do not establish semantic correctness or clinical safety.

## Human assessment and decision

The author previously reported both arms adequate across the 36 development
questions. On 2026-10-15, the author explicitly confirmed reviewing the 24 final
questions too, reporting better **answer quality with BGE**. These are aggregate
human reports, not reconstructed per-case rubric scores or numerical accuracy.

Decision: use **RRF-B + BGE for the thesis artifact**, accepting additional
local compute and serving complexity for the perceived qualitative benefit.
This does not claim statistically significant superiority. Integration and final
production verification remain separate work; this PR does not enable BGE.

The original final-run report still says review pending: it records the state at
execution. This later confirmation supplements it without rewriting its hashes,
checkpoints, golds or mapping approvals. Some reserved IDs had been exposed
historically; the final set was not completely unseen. No tuning followed it.

## Trade-offs and provenance

BGE consumed more input tokens in both paired runs because selected context
differed. Cached-context answer timings include API quota waits; retrieval and
reranking were timed separately. They are not live end-to-end latency, nor proof
that BGE caused the observed tail-latency difference. No exact billed cost is inferred.
Definitive final-set Recall/MRR were not calculated from unapproved mapping IDs.

The compact JSON identifies immutable custodial manifests and SHA-256 hashes.
Full bundles (plans, scripts, locked environments, rankings, checkpoints and
reports) remain outside Git, available from the author; no public archive URL is
claimed. Restore their recorded relative directory layout, verify each manifest
file's SHA-256 and its listed files/code against the bundle, then inspect the
recorded plans/environment. Re-execution requires the original PDFs, snapshot,
corrected runtime, pinned BGE assets and separately authorized API credentials.
This public summary alone is not a self-contained executable reproduction.
