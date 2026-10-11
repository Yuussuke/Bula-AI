# Answer fidelity: requested information versus complementary context

Author decision, 2026-10-09, recorded before golden-set expansion and main experiments. This clarification does not change the pipeline, frozen configuration, metrics or [target-document relevance](phase1/reference_policy.md).

`expected_information` is a documentary reference, not a compulsory verbatim answer or a checklist in which every clause is equally necessary. It may include complementary context from the source.

Judge completeness against the **question actually asked**:

- Identify the information indispensable to answer that question and the conditions, exceptions and qualifiers needed to keep the answer correct.
- Distinguish those requirements from related but unrequested source context. Do not penalize a correct answer solely for omitting complementary details.
- Do penalize omissions that change scope or meaning, such as an indispensable age, presentation, dose interval, co-medication, timing condition or supervised-use exception.
- If an answer includes additional factual claims, those claims still require documentary support. An optional detail is not permission to invent or generalize.
- Do not infer permission or safety from documentary absence. Scoped negatives retain the approved abstention policy; they do not establish absence throughout the cross-leaflet corpus.

Apply this distinction consistently across retrieval modes. Do not redefine what is necessary after inspecting system outputs or rankings. Ambiguity about a requirement must be flagged during documentary review, before freezing approved records.

No judge, rubric implementation, experiment or new metric is introduced here. All existing and expanded questions remain drafts; this policy approval is not an individual human documentary decision and does not migrate earlier review events.
