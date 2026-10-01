# Auxiliary evidence-selection paraphrase robustness

## Protocol

Completed 2026-09-30 02:20:38–02:20:56 UTC. Exactly 12 existing scenarios,
each with one original control and one reviewed paraphrase: 24 calls, **not 24
independent scenarios**. Four observed regressions and eight synthetic diagnostic
cases remain separate from the main TCC evaluation. The historical retrieval gap
remains outside this selector-only experiment.

The question pairs and pre-call semantic review are recorded in
`evidence_selection_paraphrases.json`; they were not replaced after execution.
Only the variant question was sent in paraphrase calls. Golds, review notes and
the corresponding original question were not supplied to the selector.

Model requested and observed in every call: `sabia-4`; temperature 0.2. Original
first in odd-numbered cases, paraphrase first in even-numbered cases. Units,
order, IDs, golds, prompt, formatter and structured-output schema unchanged.
Original formatted messages match the previous model-comparison hashes.
No retrieval, embeddings, database, renderer or answer post-processing.

Frozen paraphrase manifest SHA256:
`47971636c6a44da19aee4d5dfd4e7dc46a09e1f2e11dbb3475e1457e722ed77e`.
Raw provider responses, reasoning content and credentials were not saved.
Full per-call metrics, tokens, latencies and hashes are in
`evidence_selection_paraphrase_results.json`.

## Primary metrics

| Metric | Original | Paraphrase |
| --- | ---: | ---: |
| Negative-case errors | 0/3 | 0/3 |
| Cases with tangential evidence | 0/12 | 0/12 |
| Tangential units / selected units | 0/12 | 0/13 |
| Positive cases with at least one gold | 9/9 | 9/9 |
| False abstentions | 0/9 | 0/9 |
| Technical failures | 0/12 | 0/12 |
| Fallback calls | 0/12 | 0/12 |
| Observed-model mismatches | 0/12 | 0/12 |

## Secondary metrics

| Metric | Original | Paraphrase |
| --- | ---: | ---: |
| Micro precision | 100% | 100% |
| Micro recall | 12/14 (85.71%) | 13/14 (92.86%) |
| Exact set match | 10/12 | 11/12 |
| Positive cases with all golds | 7/9 | 8/9 |
| Mean latency | 778.8 ms | 672.3 ms |
| Reported input/output tokens | 9639 / 272 | 9668 / 277 |

Undefined precision for empty selection and undefined recall for negative cases
remain null, rather than being replaced with 0 or 1. Technical failures are
excluded from semantic metrics and counted separately (none in this round).
Small latency differences in one paired round do not establish a speed effect.

## Per-case comparison

IDs are local to each scenario. P/R means selection precision/recall; null is
undefined. No case selected tangential evidence or produced a false abstention.

| # | Scenario | Golds | Original IDs | Paraphrase IDs | Limitation original → paraphrase | P/R original → paraphrase | Exact original → paraphrase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | regression_indication_scope | E1,E2 | E1,E2 | E1,E2 | scope → scope | 1/1 → 1/1 | yes → yes |
| 2 | regression_age_with_renal_table | E2,E6 | E6 | E6 | null → null | 1/0.5 → 1/0.5 | no → no |
| 3 | regression_absence_not_safety | [] | [] | [] | null → null | null/null → null/null | yes → yes |
| 4 | regression_express_use_condition | E2,E6 | E2 | E2,E6 | scope → individual | 1/0.5 → 1/1 | no → yes |
| 5 | general_storage_direct | E1 | E1 | E1 | null → null | 1/1 → 1/1 | yes → yes |
| 6 | general_administration_route | E2 | E2 | E2 | null → null | 1/1 → 1/1 | yes → yes |
| 7 | general_storage_two_facts | E1,E2 | E1,E2 | E1,E2 | null → null | 1/1 → 1/1 | yes → yes |
| 8 | general_route_and_meal | E1,E3 | E1,E3 | E1,E3 | null → null | 1/1 → 1/1 | yes → yes |
| 9 | general_presentation_scope_contrast | E1 | E1 | E1 | null → null | 1/1 → 1/1 | yes → yes |
| 10 | general_explicit_package_condition | E2 | E2 | E2 | null → null | 1/1 → 1/1 | yes → yes |
| 11 | general_unmentioned_population | [] | [] | [] | null → null | null/null → null/null | yes → yes |
| 12 | general_unmentioned_interaction | [] | [] | [] | null → null | null/null → null/null | yes → yes |

## Interpretation

All 12 contemporary original controls reproduced the selected sets and
limitations of all three prior `sabia-4` repetitions. Original/paraphrase
selected sets match in 11/12 pairs. All selected IDs remain gold; negatives
remain empty. Complementary golds in the two-part questions (7 and 8) survive.

Case 4 is sensitive to wording in this execution. Original: “Estou no segundo
trimestre da gravidez. Então está liberado usar?” Paraphrase: “Minha gravidez
está no segundo trimestre. Isso significa que posso usar?” Both ask permission
under the same condition. E2 documents the specific condition and E6 adds the
general pregnancy condition. The extra E6 is useful according to the frozen
annotation, not tangential. `scope` changing to `individual` is qualifier
instability, not a loss of evidence or a false abstention. One pair cannot prove
a general causal wording effect. Its impact on a final rendered/natural answer
was not measured here.

Case 2 still omits gold E2, but retains E6, the explicit age restriction. This is
incomplete all-gold recall, not an empty or unsupported selection. Neither that
omission nor case 4's qualifier should be hidden by the perfect precision.

On this auxiliary check, recommend freezing `sabia-4` as the selector candidate
and ending prompt tuning against these 12 cases. This does not certify medical
safety or broad generalization. A separately requested `sabia-4-thinking`
comparison is a distinct controlled experiment, not a replacement paraphrase
round. After it, return to full-pipeline evaluation and natural grounded answers;
keep Recall@K/MRR, documentary fidelity, readability and operational indicators
as the main TCC evaluation.

Follow-up: the later, separately authorized Thinking comparison is documented
in `evidence_selection_thinking_results.md`. It found a tangential selection
in the original Sabiá 4 control for case 7, without changing the frozen inputs.
Thus the clean paraphrase result must not be interpreted as a guarantee of
between-round stability. The later finding is not caused by a paraphrase in
that experiment, which used original questions only.

No prompt/schema/production change or post-result tuning was made. Offline
evaluation safeguard suite: 29 tests passed; Ruff passed.
