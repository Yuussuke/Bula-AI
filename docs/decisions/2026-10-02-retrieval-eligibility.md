# Preserve eligible evidence and expand hybrid candidates

Date: 2026-10-02. Status: locally validated.

## Problem and decision

Administrative history could fill the retrieval top-k and be discarded only
later, leaving no answer evidence. The bounded safety-section lookup also missed
numbered source titles when its requested titles were unnumbered.

- Compare section identity without numeric prefixes, case, accents or repeated
  whitespace. Preserve original section titles, text and chunk IDs.
- Apply the existing administrative eligibility policy before filling answer
  candidates: in PostgreSQL before BM25 top-k, and inside the dense retriever's
  existing bounded point window before returning documents for fusion.
- Keep administrative sources stored and available to direct index reads and
  explicit audit retrievers. Do not classify eligibility from clinical body text.
- Request `min(3 * k, 100)` candidates per hybrid method: 12 with final `k = 4`.
  Retain the final-k range of 1–50 and the lexical limit of 100 candidates.
- Keep RRF weights/constant, authorization, identity validation, enrichment,
  prompt, model, evidence units, parser and response architecture unchanged.

## Local retrieval validation

Twelve frozen questions over four indexed leaflets, with unchanged gold IDs and
source fingerprints. Five repetitions are repeated measurements, not additional
independent scenarios. This is an auxiliary retrieval diagnostic, not the main
thesis evaluation or an evidence-selector benchmark.

| Configuration | Recall@4 macro | MRR@4 | Cases with a gold in top-4 |
| --- | --- | --- | --- |
| Historical baseline, 8 candidates | 81.25% | 0.8333 | 10/12 |
| Structural fixes, 8 candidates | 89.58% | 0.9167 | 11/12 |
| Structural fixes, 12 candidates | 93.75% | 0.9375 | 12/12 |

The 8-versus-12 comparison used identical question vectors, alternating execution
order and the same corrected code. Rankings were stable in all five repetitions;
there were no technical failures. Retrieval-only median latency was 17.68 versus
18.28 ms (P95 55.88 versus 56.75 ms), excluding embeddings, selection and generation.
Historical baseline comparisons were not paired across dates.

The cephalosporin warning moved from outside the top-4 to rank 1 after eligibility
was corrected. At depth 12, a metformin indication chunk entered the dense list
at rank 10, joined its BM25 rank 3 and reached fused rank 4. No other case lost
gold coverage. A read-only check also confirmed the existing two-chunk section
lookup finds numbered contraindication/warning headings from the real source;
that supplement was not part of the retrieval benchmark.

## Limits and rollout

The metformin indication case still retrieves only one of its two golds, and the
renal question retains three of four. Dense retrieval can still exhaust its
bounded candidate window. These results do not establish clinical safety,
selector precision, natural-answer fidelity or generalization to other leaflets.
No PDFs, indices or sessions were modified by the diagnostic.

Regression tests cover original-source preservation, numbered section lookup,
same-bula isolation, administrative crowding, audit access and candidate limits.
No migration, reindexing or PDF reprocessing is required; deploy/reload the
backend code normally. Temporary scripts, corpora and detailed JSON run outputs
are intentionally excluded from this change.
