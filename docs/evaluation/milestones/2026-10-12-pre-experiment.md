# Pre-experiment milestone — 12 October 2026

Since merged PRs #263/#264, work progressed from the original Golden Set freeze
to a smaller individually reviewed evaluation release, repaired ingestion and
offline documentary mapping. This note records completed work, not experimental
results or a new clinical validation claim.

## Question sets and protocol

Golden Set v1.0.0 remains immutable: 1,000 questions/100 PDFs, 800 positives and
200 negatives. A separately frozen derived v1.0.0 contains 200 questions: two per
PDF, 160 positives/40 negatives, balanced as 80/20 per corpus. The author reviewed
each current question; original human events remain privately preserved.

Review concerned original-PDF passages and context, not full human reading of
every PDF or independent clinical certification. Natural-language variations
preserve intent and essential qualifiers. Required information is distinguished
from optional context; omission of unsolicited detail is not automatically an error.

The implementation remains the DSRM artefact. Retrieval comparison retains BM25,
dense and hybrid, Recall@10/MRR@10 before selection/generation, relevance restricted
to the target PDF and separate scoped/cross universes. Negative abstention applies
only scoped. Response fidelity, completeness, relevance, legibility and latency
are separate; human review and a complementary external LLM judge are planned,
not completed. External participant recruitment/ethics checks remain future work.

## Ingestion and parser repairs

- Initial ingestion accepted 93 PDFs. Source-backed region/table repairs v5
  permitted six targeted retries; multipage correspondence v6 resolved DIANEAL.
- Those 100 PDFs produced 2,680 verified chunks in the isolated A/B stores.
- Offline mapping exposed missing MALVATRICIN spray content: the parser truncated
  the entire PDF at the first legal block, before later presentations.
- Authorized v8 reingestion cuts at the last standalone legal title before heading
  deduplication. MALVATRICIN changed from 12 to 31 chunks; the source restriction
  was preserved with zero chunking fallbacks. No other document was reingested.
- Corpus A's 49 other documents were verified unchanged before/after. Its current
  total is 1,330; corpus B's prior verified 1,369 were carried without a new live
  audit. The composed export snapshot therefore contains 2,699 chunks.

The final legal-tail rule is a heuristic, not a guarantee about future PDF layouts.
Repeated heading deduplication and cover identity aggregation remain limitations.
Original PDFs, old snapshots and all question histories were preserved.

## Mapping checkpoint

Offline mapping uses only frozen references and indexed exports, never retrieval
rankings. All 160 positives now have candidates: 139 complete textual matches,
nine partial and 12 ambiguous. These are not human-approved evidence sets or
retrieval metrics. The review UI prioritizes 21 cases, with quick individual review
for the remaining 139; all mapping decisions start pending. Negatives are separate.
Only A-B013-Q03/Q06 changed candidate sets after the snapshot update. Old package
exports are not inherited into the new version.

## Custody and identities

| Artefact | Fingerprint |
| --- | --- |
| Frozen derived release | `d2bd1ef17094b26f90012f94ea419d93cb8582c49ff1bb4ec080506295312589` |
| Previous ingestion snapshot | `ebd93e5c7f9aaa679306223307ca12835cb03af10ee9cdf7095a6e24295cdfeb` |
| Current composed snapshot | `1466a37fdaf9ccdc05f03cdd3fd7c3d22c3f0fbac51bc00e1aabb0dd20b250c3` |
| Current mapping package | `4305cc0f57b829bf2feb2219ad9181c1b317141fb05151911f4eec723dae7b35` |

PDFs, private human exports/name bindings, full frozen derived inputs and generated
packages remain in the external custodial archive. Preserve the ingestion artifact
directories and four isolated database/vector volumes. Never delete volumes or
rebuild a frozen release from rankings. Restore manifest-relative files and verify
hashes before reproduction. Publication does not pretend these private dependencies
are recoverable from Git alone. Intermediate launch/retry scripts and the separate
derived-set authoring tooling are not included in the mapping PR.

## Next authorized stage

Finish independent human mapping review, resolve documentary doubts, then request
explicit mapping-freeze/experimental authorization. No principal retrieval metrics,
answer generation, response judging or main evaluation experiments have run.
