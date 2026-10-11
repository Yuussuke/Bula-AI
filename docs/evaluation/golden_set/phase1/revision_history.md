# Reference-policy history

## Revision 2 - superseded on 2026-10-09

The following policy is preserved verbatim from revision 2 for audit purposes. It is **not the current main-evaluation policy**. The author subsequently confirmed target-document-only retrieval golds and scoped-only negative-abstention evaluation; see [the current decision](reference_policy.md).

### Archived text: Reference policy: scoped versus cross-bula

**Scoped chat:** the selected, hashed PDF defines the documentary reference. Evidence from another PDF does not repair a missing reference in this mode.

**Cross-bula:** the target is valid documentary evidence within the authorized, frozen corpus, not necessarily recovery of the origin PDF. Another PDF can count only after documentary annotation establishes that its literal evidence supports the same requested proposition and all necessary qualifiers. Sharing an active substance, section title or topic is not enough.

Before experimental execution, an alternative must record its corpus/document ID, SHA-256, exact fragments, sections/physical pages, conditions, an equivalence rationale and reviewer/date. `alternative_document_references=[]` is reserved for these annotations; it does not assert that no alternative exists. All positive cross-bula records are `pending_reference_equivalence_review`. **No alternative documents were searched or approved in this revision.**

Preserve the named medication/product, form, strength, population, route, timing and exceptions whenever they affect the question. Product-specific excipients, packaging or device materials cannot be transferred to another manufacturer merely because the active substance matches. A named brand is not automatically interchangeable with a generic or another brand for evaluation purposes. A different strength can only be considered if the question is genuinely strength-independent and that equivalence is documented, never assumed.

Necessary fragments can be supported together; redundant but genuinely supporting evidence is not an error. A generic instruction to consult a professional is not equivalent to evidence establishing the requested specific fact. If compatible-looking documents disagree, flag the ambiguity and resolve the reference/query scope before freezing; do not pick a convenient version after seeing results.

Negative `answerable=false` labels apply only to the source document. Cross-bula absence requires full authorized-corpus review. If an alternative contains sufficient support, the scoped question remains negative but its cross-bula variant cannot be evaluated as an unsupported negative. Exclude that variant from cross-bula scoring until it is separately annotated/reclassified; do not silently reuse the scoped label or invent an answer.

Do not compute cross-bula Recall@10 or MRR against origin-only chunk IDs while claiming to accept equivalent documents. The later mapping must incorporate all pre-approved alternatives and state the unit of relevance explicitly. Standard chunk Recall measures retrieved relevant chunks divided by annotated relevant chunks; recovery of one sufficient alternative does not imply retrieval of all equivalent chunks. If the intended score instead treats alternative realizations of a necessary evidence fragment as an OR-group (and jointly necessary fragments as AND requirements), report it explicitly as evidence-requirement coverage, not silently as standard chunk Recall. This revision defines reference eligibility, **not a new metric, evaluator or change to the principal TCC protocol**. Final mapping/scoring remains a documented prerequisite before experiments.

Freeze the approved questions, corpus snapshot, references and scoring rules together. Do not add golds based on one method's rankings or model answers. A later annotation error must be logged and corrected consistently across all compared methods, without selecting only favorable corrections. No model is trained or tuned using this batch.

## Revision 3 - current decision

Confirmed by the author on 2026-10-09. Only reference-PDF chunks are retrieval golds in both scenarios; equivalent PDFs are not main retrieval golds. Negative-abstention scoring applies only to per-leaflet questions. No question, expected information, qualifier, literal citation, page, rectangle, source hash or documentary label was changed during the revision-3 conference. Record metadata and documentation were aligned to the decision; records remain unapproved drafts.

The existing [revision-2 audit](revision_2_changes.json) is unchanged, including the correction of A-B024-Q05 from section 4 to section 3. [Revision 3](revision_3_changes.json) records the new policy and metadata transitions. No prior experimental result is rewritten.

### Author's acceptance, 2026-10-09

Conversation confirmation: "Está aprovada". Recorded as acceptance of the revision-3 conference report and methodological decision. No assertion of independent source rereading or clinical validation is added. Individual records remain drafts, pending the remaining validation/disambiguation and frozen chunk mapping. This acceptance does not authorize the 950-record expansion, experiments, commits or publication. Prior audit files and question annotations remain unchanged.

## Revision 4 - linguistic draft, pending author approval

2026-10-09. The author approved proceeding from the 15 presented linguistic proposals to all 50 records. This authorizes preparation, not automatic human approval of the resulting questions. [Revision 4](questions.revision4.draft.jsonl) is a separate artifact; `questions.draft.jsonl` remains the immutable revision-3 source. [The change log](revision_4_changes.json) records revised variants and case-specific semantic assessments; [the comparison report](linguistic_review_revision4.md) shows both old and new wording.

Only question wording and the draft revision number change. Documentary references, expected information, qualifiers, classifications, review states and source identities remain unchanged. Revision 3 remains the governing reference policy. No RAG outputs or rankings inform the linguistic choices, and no questions for the other 95 leaflets are generated. A [possible conversational complement](linguistic_policy.md) is documented only, not implemented.

### Subsequent policy approval and bounded expansion, 2026-10-09

The author approved revision 4's linguistic policy for expansion and clarified that omitted unrequested complementary details in `expected_information` are not fidelity errors when the necessary answer and qualifiers are preserved. See [the recorded fidelity rule](../answer_fidelity_policy.md). The historical revision-4 records, audit and QC remain unchanged and pending individual documentary approval. The author now authorizes preparation of the remaining documents in batches of ten, with a mandatory stop after the first batch; no main experiments or RAG/configuration changes are authorized.
