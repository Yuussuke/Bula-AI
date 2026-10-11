# Main evaluation: target-document relevance

Decision confirmed by the author on 2026-10-09, before main experiments. This supersedes revision 2's cross-document equivalence policy. It does not change the RAG pipeline, frozen parameters or the main metrics.

## Retrieval gold and search scope

For each positive question, the target is the reference PDF identified by `corpus_id`, `document_id` and `document_sha256` in the golden set. Map its approved documentary references to relevant chunks only after the ingestion snapshot is frozen. Annotate all relevant target-document chunks for the requested proposition, including overlapping/repeated evidence; do not choose golds using system rankings or generated answers.

| Scenario | Search space | Relevant chunks for retrieval metrics |
| --- | --- | --- |
| Per-leaflet | The selected reference PDF | Relevant chunks from that PDF only |
| Cross-leaflet | The corresponding authorized, frozen corpus, without a hidden target-document filter | The same relevant chunks from the reference PDF only |

The cross-leaflet evaluation measures recovery of **specific reference-PDF evidence under document competition**. It does not measure the general ability to find any equivalent evidence in the corpus. Query variants must identify the medication and, when needed, manufacturer, form or presentation without leaking the expected answer. Review ambiguity before approval; a reference identifier must never be secretly supplied as a retrieval filter in the cross-leaflet scenario.

Equivalent evidence in another PDF does not enter the retrieval gold, numerator or denominator. It may be recorded separately for interpretation of answer fidelity and provenance, but cannot repair a target-document retrieval miss. Finding it is neither a target-document retrieval success nor, automatically, an incorrect answer. No exhaustive equivalence annotation across the corpus is required for the main evaluation.

## Recall@10, MRR and multiple references

For positive question `q`, let `G(q)` be the approved relevant chunk IDs in the target PDF and `R10(q)` the first ten chunks of the strategy's recorded retrieval ranking (after fusion for hybrid, before selection or later supplementation).

`Recall@10(q) = |G(q) intersect R10(q)| / |G(q)|`.

MRR retains the frozen protocol's ranking/cutoff convention: take the reciprocal rank of the **first relevant target-document chunk**, or zero if no such chunk is found within that evaluation ranking. Average over positive questions with approved, nonempty target golds. This decision changes neither the MRR cutoff nor its aggregation convention; it fixes which chunks count as relevant. Record the already-frozen cutoff in the experiment manifest, rather than silently switching between truncated and untruncated MRR.

Do not compress non-target hits out of the cross-leaflet ranking: their positions represent document competition. Do not compute either retrieval metric from the renderer's final citations or selected evidence units. Negative questions with no gold have undefined Recall/MRR, not zero; exclude them from those means with explicit denominators. An approved positive whose evidence was lost during ingestion must be logged as an ingestion/mapping defect, not relabeled negative or silently dropped.

**Recall@10 and MRR do not guarantee a complete answer to a multi-fragment question.** MRR considers only the first relevant hit; Recall@10 may be nonzero with required fragments still missing. Even Recall@10 = 1 only establishes recovery of all *annotated chunks*, not correct interpretation, qualifier preservation or annotation completeness. A reference fragment is not necessarily one chunk, and several fragments may map to one chunk. Documentary fidelity and adequacy of the natural-language response remain separate main evaluations. No new coverage metric or OR-group scoring is introduced here.

## Negative questions

`answerable=false` means insufficient documentary support for the requested proposition in the **reference PDF**. It does not mean that the combination is medically safe, unsafe or unsupported everywhere.

- Use the ten scoped negative questions for per-leaflet abstention evaluation only, after documentary approval.
- Do not score their cross-leaflet variants as requiring abstention. They are outside the main negative-abstention denominator; no full-corpus absence has been established.
- Retain cross-leaflet wording for traceability, not as an approved negative gold. A supported answer from another document must not be penalized merely for being informative.
- A separate cross-leaflet unsupported-question evaluation would require its own complete-corpus absence review and explicit authorization. It is not a prerequisite for the current main target-document design and is not being implemented now.

## Approval and history

The author accepted the revision-3 conference report on 2026-10-09 ("Está aprovada"). This confirms acceptance of the documented decision and review findings, not an assertion of independent source rereading or authorization to expand/run experiments.

All 50 records remain drafts, with human documentary approval pending and `expected_chunk_ids=[]`. Positive cross-leaflet query identification still needs review against the corresponding corpus; alternatives do not need to be exhaustively annotated. Frozen corpus boundaries, target gold mapping and question approval must precede the main runs.

Revision-3 record metadata uses `pending_target_query_review` for positives and `not_evaluated_for_abstention` for negatives. The empty `alternative_document_references` field is retained as legacy annotation metadata, not an active main-evaluation requirement.

History: [revision-2 changes](revision_2_changes.json), [superseded reference policy](revision_history.md), [revision-3 changes](revision_3_changes.json). Documentary findings are in [the review report](documentary_review_revision3.md). No experiment, expansion or pipeline modification is authorized by these documents.
