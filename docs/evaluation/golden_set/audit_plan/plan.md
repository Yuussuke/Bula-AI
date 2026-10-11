# Documentary audit plan — proposed, not executed

2026-10-10. Draft authoring of 1,000 effective records is complete. Batch-10 continuation was accepted by the author; **final collection freezing, sampling, human decisions, chunk mapping and experiments remain unauthorized**. This proposal awaits approval.

## Preserved input and scope

Use the 11 effective question files recorded in [the conference](../expansion/batch10/collection_qc.draft.json), not every historical JSONL: 100 reference PDFs (50 A / 50 B), 1,000 records (800 positive / 200 negative). Earlier originals, revisions, ledgers, quotations, classifications, qualifiers and source manifests stay immutable. Scoped/cross variants are two formulations of one need, not independent records.

The [triage snapshot](priority_queue.json) binds every flagged record to its effective file, canonical record SHA-256 and PDF SHA-256. It verifies 112 distinct historical/conference artifact hashes, including the 11 effective inputs; this is a planning integrity snapshot, **not experimental freezing or semantic approval**. All 100 PDFs' source notes remain preserved in the conference inventory. No RAG outputs inform triage, sampling or correction.

Unchanged methodology: [target-PDF relevance](../phase1/reference_policy.md), Recall@10 and MRR on relevant target chunks in both scenarios; scoped negatives only for abstention; separate answer fidelity; [necessary versus complementary information](../answer_fidelity_policy.md). No new thematic taxonomy, redistribution, pipeline change or metric is introduced. Corpus boundaries, indices and parameters are untouched.

## Risk classification before drawing

These labels describe **review consequence and required inspection**, not proven errors. They can overlap and are separate from the existing question categories. A flag can be a useful warning, an already checked source feature or a suspected defect. Do not count flags as error prevalence.

| Priority | Criterion | Existing flagged records | Required handling |
| --- | --- | ---: | --- |
| P0 — potential blocker | A concrete unresolved source-scope conflict or explicit target-identification uncertainty could invalidate the expected conclusion or the target query | 6 | Resolve the concern documentarily; unresolved material uncertainty prevents release of affected records and final collection acceptance |
| P1 — safety | Preserving urgency, contraindication/exception, population, dose/table conditions or professional action is safety-sensitive; no error is assumed | 90 | Prioritize semantic verification and risk audit; an unsupported or doubtful indispensable safety condition escalates to P0 |
| P2 — documentary/structural | Source support/absence boundary, table association, presentation, time reference or natural ambiguity needs confirmation without an identified material safety defect | 89 | Verify local/full-document scope as applicable; escalate if a substantive error is found |
| P3 — nonblocking observation | Extraction/editorial/technical-purpose note with no identified effect on requested meaning or target identity | 5 | Retain the note; do not waive routine automatic checks or infer individual approval; escalate if impact emerges |

The [complete queue](priority_queue.md) contains all 190 original flags, verbatim, ordered by priority then ID. That ordering is an operational triage list, **not a random draw or the final additional sample**. Risk tags: potential blocker, safety, table interpretation, ambiguity, presentation difference, nonblocking observation and documentary support/absence confirmation. Overlapping counts are 6 / 104 / 16 / 22 / 20 / 5 / 48 respectively; their sum is not 190.

P0 initial concerns: `A-B017-Q05`, `A-B026-Q08`, `B-CB025-Q05`, `A-B035-Q03`, `B-CB038-Q04` (source conditions/tensions), and `B-CB021-Q01` (query uniqueness). They require an explicit resolution, not automatic rejection. A defensible source-scoped explanation can resolve a tension without changing the PDF or clinically reconciling it. If it cannot, keep the record pending and propose a separately versioned correction.

Six earlier/current author priorities are maintained separately, not inserted into the 190 source flags: `B-CB003-Q03`, `A-B032-Q07`, `A-B041-Q07`, `A-B044-Q10`, `A-B045-Q09`, `A-B049-Q02`. No source record or decision is changed.

## Document-wide watchlists and first review focus

| Concern | Scope of the proposed check |
| --- | --- |
| Olina `A-B025` | Inspect both original pages/columns and compare its eight positive needs for substantive redundancy/support; do not manufacture eight distinct needs. This is a group concern beyond the 190 record flags |
| Fluibron `A-B005` and Atrovent `A-B027` | Keep each form, route, device and instruction bound to its local source. Retain manufacturer discrepancy as a separate provenance note; do not edit the frozen manifesto |
| Safety priorities previously requested | Preserve `B-CB003-Q03`, `A-B016-Q07/Q08`, `B-CB013-Q08` and other urgency/contraindication flags, including immediate-action conditions; do not invent emergency text as a literal reference |
| Original tables | Prioritize Nimenrix `A-B024-Q07`, stability `A-B015-Q06/Q07`, ibuprofen `B-CB023-Q05`, Imussuprex `A-B035-Q08`, dipyrone `B-CB021-Q04`, Sovaldi `A-B042-Q02` and pediatric pravastatin `B-CB050-Q04`; inspect headers/rowspans/footnotes, not reconstructed text alone |
| Bezafibrate `B-CB048` | Keep anomalous original wording on myopathy, drug-class example and schedule visible; confirm no current question's indispensable answer depends on those disputed passages. Source anomaly alone does not invalidate every question |
| Metadata/source history | Retain Fluibron manufacturer divergence, empty manufacturer fields and Vyvgart editorial/producer notes. Escalate only if identity or required answer support is affected; no silent corpus substitution |
| Natural ambiguity `A-B038-Q07` | Keep the question; check whether the conditional water-droplet/solution distinction suffices. Do not assume which liquid the user found |
| Bounded negatives | `B-CB024-Q09`, `A-B044-Q10`, `A-B045-Q09`: related advice can be explained while refusing the unsupported requested conclusion; silence is neither permission nor proof of harm |

Other source notes and corrected historical concerns remain in the inventory/revision chain; the list above is not permission to discard them. Current-version checks must not inherit an earlier human approval.

## Proposed allocation and additional-review budget

Preserve the [existing protocol](../review_demo/protocol.md) and [acceptance clarification](../expansion/human_audit_acceptance_clarification.md).

1. **Core audit: exactly 100 records**, one per PDF, 50 per corpus, 80 positive / 20 negative. Within each corpus, 40 PDFs contribute a positive and 10 a negative. This ensures document coverage, not clinical representativeness.
2. **Initial additional-risk budget: 20 distinct non-core records**, consistent with the original proposal. Prioritize unresolved P0 concerns and explicitly requested safety checks, then safety-sensitive tables/presentation scope, then other documentary structures (including multiple fragments). Group inspections, such as Olina's eight positives, are logged by affected IDs; every record actually reviewed counts toward workload. A core record may also carry risk findings but is counted once as reviewed, with dual membership disclosed.
3. **Mandatory resolution is outside any numerical cap.** All P0 concerns and any later blocking finding must be resolved, whether inside the 100/20 allocation or through additional work. The 20 are an initial work reservation, not permission to leave the remaining alerts unresolved. Required checks discovered automatically cannot be dismissed because 20 slots are used. Routine authorship warnings may be resolved by documented verification without claiming individual human review; unresolved material concerns require escalation/human adjudication.
4. If mandatory work exceeds the initial reservation, pause for an explicit workload decision, retaining the blocked status of affected questions/collection. Never silently freeze, drop difficult records, swap PDFs or reduce the planned sample. Revisions/exclusions affecting the planned 1,000-record composition require separate author approval.
5. Final non-core IDs cannot be known yet: overlap with the core and future automatic findings are unknown. No ID has been assigned sample membership. No claim that exactly 120 records will be sufficient is made. The queue is not a mandate for 190 individual approvals or 1,000 human reviews.

Approval requested: risk criteria, 20-record initial reservation, mandatory-resolution rule and escalation below. Later author approval of the method is separate from genuine individual review and eventual acceptance of the final version.

## Reproducible draw — specification only

Reserved seed **20261009**, not used in this operation. Preserve the established stable SHA-256 ordering: UTF-8 JSON array `[seed, purpose, corpus_id, document_id, question_id]`, without spaces; lexicographic ID breaks ties.

- Validate 100 PDFs / 1,000 effective records / per-PDF 8+2 and record input hashes before drawing.
- For each corpus, rank its documents with purpose `negative-documents` and empty question ID; first ten contribute negatives, other 40 positives.
- Within each PDF, rank eligible records of the assigned type with purpose `question-choice`; take first. Never reroll based on topics or outcomes.
- Additional-risk priority derives from source/annotation concerns, not RAG performance. Mandatory concerns are not randomized away. Use the existing `risk-choice` purpose only to break equal-priority optional-risk ties; publish rule/version and chosen IDs after authorization.
- Record the exact input snapshot and selected IDs before review; preserve the initial core through corrections. Describe structural/category coverage without changing wording or creating a new topic taxonomy. Report core and targeted additional findings separately; do not pool them as an unbiased overall error rate.

No sampler is implemented or executed by this proposal.

## Executable workflow after authorization

| Step | Operation and output | Stop/gate |
| --- | --- | --- |
| 1 | Approve this plan; establish reviewer identity, ledger/version convention and working hours | No inferred individual decisions |
| 2 | Recheck hashes/composition and run the agreed automatic documentary verification on all 1,000, with positive/negative checks and complete page coverage for negatives | The independent semantic verifier remains unimplemented/unexecuted. Configuration/execution require their own approval; existing literal QC is not a substitute |
| 3 | Log findings, incomplete coverage and technical failures separately; update triage in a new artifact, not in source records | Unresolved blockers never become automatic passes |
| 4 | Draw the approved 100-record core using the reserved algorithm; register input fingerprint and sample | No reroll/replacement; keep current records immutable |
| 5 | Assemble the separate initial risk worklist using core overlap, mandatory issues and approved ranking; disclose any excess mandatory work | Author approves extra workload, not waiver of blockers |
| 6 | Human reads original PDFs and saves explicit checklists/decisions for the core and additional risk records | Doubts remain pending; log time and issue IDs, not fabricated approvals |
| 7 | Escalate affected groups, propose/version only demonstrated corrections, rerun affected checks and record the resolution | Original sample IDs and pre-correction findings remain visible |
| 8 | Produce audit closure: core/risk/expanded-wave denominators; actual reviewed, approved, rejected, pending/doubts; unresolved issues and exclusions/corrections | Request final collection acceptance separately. No chunk mapping or experiment is authorized by audit closure |

This is an ordered plan, not authorization to run the future verifier, expand the interface or start step 2 now. Provider calls and any tool implementation are separate from the current documentation task.

## Human documentary checklist and acceptance

For **every actually audited record**, examine both question variants and the exact effective reference PDF:

- Same requested proposition, population, substance, presentation, route, time and conditions in scoped/cross variants; natural wording need not be artificially complete beyond indispensable qualifiers.
- Cross query uniquely identifies the reference PDF within the corresponding frozen corpus, without leaking the requested answer or relying on a hidden ID filter. A necessary presentation identifier is not automatically leakage.
- Positives: literal references are located correctly **and semantically support the requested answer**, alone or jointly. Check full local paragraphs, headings, captions, table cells/rowspans/footnotes and mandatory exceptions.
- Expected information: identify indispensable answer content versus optional context before system output is seen. Optional omission is not infidelity; any volunteered factual claim still needs support.
- Negatives: read the full target PDF, including relevant tables, other presentations and history distinctions; check indirect/conditional support too. Mark `full_document_checked` and `insufficient_support_confirmed` explicitly. A topical mention does not necessarily answer; a newly found sufficient passage requires reclassification/correction, not dismissal as a retrieval issue.
- Negative cross variants retain traceability/identity review but **do not certify corpus-wide absence or require cross-bula abstention**.

Use the existing instrument's positive fields `clarity/source/support/qualifiers` and negative fields `clarity/full_document_checked/insufficient_support_confirmed/qualifiers`; store equivalence, target identity and structural findings as review notes/issues, not silently passed extra fields or a changed schema. No production schema is altered.

A reviewer must genuinely save the checklist and separately choose approval. `human_reviewed` is not `approved`; a complete review with doubts can remain pending. Missing/changed sources, proposed corrections or unresolved indispensable support prevent approval of the affected version. Decisions are append-only and version/hash-bound, with reviewer/date; corrections stay separate until an explicitly approved new revision is applied. Unaudited records remain human-pending, not human-approved.

**Collection acceptance gate:** required automatic verification complete with technical failures resolved; approved core/risk audit executed; blocking issues resolved and revisions checked; unresolved doubts that affect classification, indispensable support, qualifiers or target identity adjudicated; explicit author acceptance of the effective collection/version. Harmless source/editorial observations may remain disclosed. This is not universal individual approval or clinical validation.

## Escalation rules — predeclared, no tuning

| Finding | Action before acceptance |
| --- | --- |
| One severe error: false documentary negative, wrong dose/age/route/strength, swapped table cell, lost urgent/prohibitive condition | Quarantine affected record/version; inspect all records sharing the affected table, presentation or source paragraph. Expand to analogous documentary structures across PDFs if the mechanism can recur; log a bounded issue-driven wave |
| Two confirmed instances of the same non-severe defect mechanism in distinct records | Review the affected document/structure/template group; log rationale and all IDs. This makes the existing "repeated problem" trigger explicit, not a new metric |
| Source/manifest hash mismatch, missing PDF or incomplete required verification | Technical blocker; stop affected processing, resolve integrity/coverage, never relabel as documentary absence |
| Query cannot uniquely identify the target or variants change the proposition | Block that record for the relevant scenario; propose a separately versioned, documentary-equivalent fix without leaking the answer |
| Natural ambiguity answerable conditionally, or complementary detail omitted | Retain natural wording; document acceptable conditional scope/optional content. Do not invent an error or require unnecessary clarification |
| Source tension cannot be resolved documentarily for the necessary answer | Keep pending; seek documentary adjudication, not clinical reconciliation. Present alternatives to the author before changing/excluding the record |

Escalation is issue-driven, not a fixed extra-sample quota. Log each wave's reason, parent finding, affected IDs/versions, denominator, reviewer action and before/after hashes. Finding one error does not imply all neighboring records are erroneous, but shared causes must be checked. Keep failures in the original core results; do not replace them with easier records. No quantitative threshold can waive a blocking finding.

## Effort estimate — assumptions, not measured durations

| Work | Assumption | Human effort |
| --- | --- | ---: |
| 80 core positives | 6–10 min each, including both variants and local original-source check | 8–13.3 h |
| 20 core negatives | 15–25 min each for whole-PDF absence check; long/complex PDFs may exceed this | 5–8.3 h |
| 20 initial additional-risk records | 12–20 min each; complex tables/contradictions may exceed this | 4–6.7 h |
| Setup, version-bound notes and closure | Working estimate | 3–5 h |
| Initial total | Before extra mandatory resolution/escalation; not a completion guarantee | **20–33.3 h** |

At three hours per session, this is roughly **7–12 sessions**, excluding automated-verifier implementation/runtime, correction cycles and additional blocking work. Human full-PDF reading is the main uncertainty, not model-call time. Calibrate these assumptions from the first ten genuinely reviewed records without rerolling the sample or changing acceptance criteria. Keep separate time for severe findings; every ten extra complex checks at 12–20 min add about 2–3.3 h. Report actual workload after the draw, not an exact pre-draw finish date.

## Specific fidelity note and current stop

See [A-B049-Q02 author note](sporanox_q02_author_note.md): 6–9 months concerns **disappearance of nail lesions after treatment**, not necessarily onset of visible improvement. The natural question and reference remain unchanged; complementary details are not mandatory merely because they appear in `expected_information`.

Current operation: organize 190 existing flags, retain six supplemental author priorities, propose sampling/risk/escalation/effort rules and verify preservation. **No draw, human event, independent semantic verification, RAG, ingestion, chunk mapping, judgment, experiment or final freeze. Await author approval.**
