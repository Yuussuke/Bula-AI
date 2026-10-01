# Auxiliary selector comparison: Sabiá 4 versus Sabiá 4 Thinking

## Frozen experiment

Executed 2026-09-30 23:04:39–23:07:57 UTC. Exactly 72 calls: the same 12 original
questions × two models × three repetitions. These are **12 scenarios, not 72
independent observations of generalization**. Four observed regressions and
eight synthetic diagnostic scenarios; no new medical cases. The historical
retrieval gap remains excluded. Paraphrases were not used in this comparison.

Requested/observed identities: `sabia-4` in all 36 control calls and
`sabia-4-thinking` in all 36 experimental calls. No fallback, unknown identity,
technical failure or extra retry. Temperature 0.2; same prompt, structured
output, formatter, unit order, IDs, golds and provider configuration. The only
request-setting difference is the model identifier. Models alternate within
case/repetition pairs; the first model changes with case and repetition parity.
Provider timeout 60 seconds, unchanged outer benchmark timeout 30 seconds.

The [official Maritaca integration documentation](https://docs.maritaca.ai/pt/examples/langchain)
identifies `sabia-4-thinking` as usable by changing the model name in the same
integration. No prompt instruction to reason or new production stage was added.

Preflight verified every original formatted message and the schema against the
earlier model comparison. Frozen fixture SHA256:
`c32832b346e86c649d360e34e3a8d77313df7ee6d6c27b50175971e87300fe16`.
Production file hashes remained unchanged before/after. No retrieval,
embeddings, database, renderer or answer post-processing participates here.

`evidence_selection_thinking_results.json` contains all call records, per-case
ID frequencies (including zeros), per-repetition metrics, means/ranges, observed
models, limitations, latencies and reported token usage. No raw provider answer,
internal reasoning or credentials were saved. Model aliases are observed API
identifiers, not a guarantee of a pinned internal provider revision.

## Main results

Denominators below count repeated calls, not distinct scenarios. Both models
covered all nine positive scenarios in every repetition.

| Metric | sabia-4 | sabia-4-thinking |
| --- | ---: | ---: |
| Negative-case errors | 0/9 (0%) | 1/9 (11.11%) |
| Calls with tangential evidence | 3/36 (8.33%) | 2/36 (5.56%) |
| Distinct scenarios with tangential evidence | 1/12 | 2/12 |
| Tangential units / selected units | 3/40 (7.50%) | 2/42 (4.76%) |
| Positive calls with at least one gold | 27/27 | 27/27 |
| False abstentions | 0/27 | 0/27 |
| Technical failures | 0/36 | 0/36 |
| Fallback / identity exclusions | 0 / 0 | 0 / 0 |
| Mean latency | 899.3 ms | 4602.4 ms |
| Reported input tokens | 28917 | 28917 |
| Reported output tokens | 834 | 11091 |

Thinking was about 5.12× slower in this round. Output-token usage reported by
the provider was about 13.30× greater; no separate reasoning-token breakdown
was captured and this is not a monetary cost estimate.

Secondary aggregate metrics:

| Metric | sabia-4 | sabia-4-thinking |
| --- | ---: | ---: |
| Micro precision | 37/40 (92.50%) | 40/42 (95.24%) |
| Micro recall | 37/42 (88.10%) | 40/42 (95.24%) |
| Exact set match | 28/36 (77.78%) | 32/36 (88.89%) |
| Positive calls containing all golds | 22/27 | 25/27 |
| Scenarios with identical ID sets across all three repetitions | 11/12 | 9/12 |

No composite score. Empty-selection precision and negative-case recall remain
undefined, not coerced to zero/one. Technical failures would be excluded from
semantic denominators and counted separately.

## Repetitions

Each row has 12 scenarios: nine positive and three negative. Positive any-gold
coverage is 9/9 in every row; false abstentions and technical failures are zero
in every row. Counts of tangential calls equal counts of tangential units here.

| Model | Rep | Negative errors | Tangential calls | Micro P | Micro R | Exact | All golds in positives | Mean ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sabia-4 | 1 | 0/3 | 1/12 | 92.31% | 85.71% | 9/12 | 7/9 | 874.2 |
| sabia-4 | 2 | 0/3 | 1/12 | 92.86% | 92.86% | 10/12 | 8/9 | 917.1 |
| sabia-4 | 3 | 0/3 | 1/12 | 92.31% | 85.71% | 9/12 | 7/9 | 906.5 |
| sabia-4-thinking | 1 | 1/3 | 1/12 | 93.33% | 100% | 11/12 | 9/9 | 4410.0 |
| sabia-4-thinking | 2 | 0/3 | 1/12 | 92.86% | 92.86% | 10/12 | 8/9 | 4909.6 |
| sabia-4-thinking | 3 | 0/3 | 0/12 | 100% | 92.86% | 11/12 | 8/9 | 4487.7 |

Means and ranges across the three repetitions, distinct from pooled ratios:

| Metric | sabia-4 mean [min–max] | Thinking mean [min–max] |
| --- | --- | --- |
| Negative errors per repetition | 0 [0–0] | 0.33 [0–1] |
| Tangential calls per repetition | 1 [1–1] | 0.67 [0–1] |
| Positive any-gold coverage | 100% [100–100] | 100% [100–100] |
| Micro precision | 92.49% [92.31–92.86] | 95.40% [92.86–100] |
| Micro recall | 88.10% [85.71–92.86] | 95.24% [92.86–100] |
| Exact matches per repetition | 9.33 [9–10] | 10.67 [10–11] |
| Mean latency ms | 899.3 [874.2–917.1] | 4602.4 [4410.0–4909.6] |

## Selected IDs per scenario

Cells list repetition 1 / 2 / 3, preserving returned ID order. Asterisk marks a
non-gold selected ID. IDs are local to each scenario.

| # | Case ID | Golds | sabia-4 R1 / R2 / R3 | Thinking R1 / R2 / R3 |
| --- | --- | --- | --- | --- |
| 1 | regression_indication_scope | E1,E2 | [E1,E2] / [E1,E2] / [E1,E2] | [E1,E2] / [E1,E2] / [E1,E2] |
| 2 | regression_age_with_renal_table | E2,E6 | [E6] / [E6] / [E6] | [E6,E2] / [E6] / [E6] |
| 3 | regression_absence_not_safety | [] | [] / [] / [] | [E1*] / [] / [] |
| 4 | regression_express_use_condition | E2,E6 | [E2] / [E2,E6] / [E2] | [E2,E6] / [E2,E6] / [E2,E6] |
| 5 | general_storage_direct | E1 | [E1] / [E1] / [E1] | [E1] / [E1] / [E1] |
| 6 | general_administration_route | E2 | [E2] / [E2] / [E2] | [E2] / [E2] / [E2] |
| 7 | general_storage_two_facts | E1,E2 | [E1,E2,E3*] / [E1,E2,E3*] / [E1,E2,E3*] | [E1,E2] / [E1,E2,E3*] / [E1,E2] |
| 8 | general_route_and_meal | E1,E3 | [E1,E3] / [E1,E3] / [E1,E3] | [E1,E3] / [E1,E3] / [E1,E3] |
| 9 | general_presentation_scope_contrast | E1 | [E1] / [E1] / [E1] | [E1] / [E1] / [E1] |
| 10 | general_explicit_package_condition | E2 | [E2] / [E2] / [E2] | [E2] / [E2] / [E2] |
| 11 | general_unmentioned_population | [] | [] / [] / [] | [] / [] / [] |
| 12 | general_unmentioned_interaction | [] | [] / [] / [] | [] / [] / [] |

Nonzero ID frequencies out of three executions; every unlisted ID has frequency
zero (the JSON also lists those zeros):

| # | sabia-4 | Thinking | Empty selections S4 / Thinking | Tangential calls S4 / Thinking |
| --- | --- | --- | --- | --- |
| 1 | E1:3, E2:3 | E1:3, E2:3 | 0/3 / 0/3 | 0/3 / 0/3 |
| 2 | E6:3 | E2:1, E6:3 | 0/3 / 0/3 | 0/3 / 0/3 |
| 3 | none | E1:1 | 3/3 / 2/3 | 0/3 / 1/3 |
| 4 | E2:3, E6:1 | E2:3, E6:3 | 0/3 / 0/3 | 0/3 / 0/3 |
| 5 | E1:3 | E1:3 | 0/3 / 0/3 | 0/3 / 0/3 |
| 6 | E2:3 | E2:3 | 0/3 / 0/3 | 0/3 / 0/3 |
| 7 | E1:3, E2:3, E3:3 | E1:3, E2:3, E3:1 | 0/3 / 0/3 | 3/3 / 1/3 |
| 8 | E1:3, E3:3 | E1:3, E3:3 | 0/3 / 0/3 | 0/3 / 0/3 |
| 9 | E1:3 | E1:3 | 0/3 / 0/3 | 0/3 / 0/3 |
| 10 | E2:3 | E2:3 | 0/3 / 0/3 | 0/3 / 0/3 |
| 11 | none | none | 3/3 / 3/3 | 0/3 / 0/3 |
| 12 | none | none | 3/3 / 3/3 | 0/3 / 0/3 |

All positive-case false-abstention frequencies are 0/3 for both models. Negative
errors are 0/3 in cases 3, 11 and 12 for Sabiá 4; Thinking has 1/3 in case 3 and
0/3 in 11 and 12. Technical-failure frequencies are zero in every case/model.
Selected sets vary only in case 4 for Sabiá 4, and cases 2, 3 and 7 for Thinking.

## Limitation and semantic diagnosis

Non-null or varying limitations (all others are null in all repetitions):

| Case | sabia-4 R1 / R2 / R3 | Thinking R1 / R2 / R3 |
| --- | --- | --- |
| 1: indication contrast | scope / null / scope | null / null / null |
| 3: absence implies safety | null / null / null | missing / null / missing |
| 4: express use condition | null / individual / scope | null / null / null |

1. **Case 7, shared residual error:** E1 gives storage conditions and E2 gives
   use time after opening. E3 only says that the expiry of the closed package
   is printed on the label. Selecting E3 conflates related expiry information
   with the particular post-opening condition. Under the unchanged golds this
   is tangential, not additional necessary support. It persists in all three
   Sabiá 4 calls but only one Thinking call. Both retain the two correct golds.
2. **Case 3, Thinking negative error:** E1 lists contraindications involving
   other conditions, not evidence about the diabetes proposition. Its selection
   once with `missing` does not become correct merely because a limitation was
   supplied. In another repetition Thinking returned [] with `missing`, further
   illustrating that labels alone do not measure selection quality. No final
   medical answer was generated, so this is not evidence that the pipeline
   explicitly authorized use; it is a selector false positive.
3. **Case 2, incomplete gold coverage:** Sabiá 4 omits E2 in all repetitions;
   Thinking includes it once. Both retain the explicit restriction E6 every
   time. This reduces all-gold recall but does not create a false abstention.
4. **Case 4, evidence and qualifier stability:** Thinking retains both golds
   consistently and uses null limitation; Sabiá 4 retains the directly relevant
   E2 throughout, adds E6 once and varies across all three limitation values.
   Given the strict meaning of limitation, source-expressed conditions should
   not automatically be counted as missing evidence. However this benchmark
   has gold IDs, not independent gold limitation labels; qualifier differences
   are descriptive and their impact on natural answers remains unmeasured.

## Relation to the paraphrase check and earlier runs

The earlier original/paraphrase round completed at 02:20 UTC; this comparison
ran at 23:04 UTC on the same UTC date. In that earlier round Sabiá 4 selected no
tangents, and question variants differed only in case 4, without losing golds.
Here the **original** case 7 selects E3 in all three control repetitions despite
unchanged recorded inputs/configuration. Do not reinterpret that as a paraphrase
effect: no paraphrases were used here. The observations show between-round
variability as well as within-round behavior. Sampling and unobserved provider
factors are possibilities, not established causes; no seed or internal revision
control was added after seeing results.

Thinking reduces total tangential calls from three to two and improves secondary
recall/exact matching, but introduces a negative error, has fewer scenarios with
identical selected sets, and costs substantially more latency. Its tangential
call count is lower only in repetition 3 (ties in repetitions 1 and 2), not a
consistent primary-metric improvement across all repetitions. Therefore this is
**not sufficient evidence to replace Sabiá 4 with Thinking for this selector**.

## Recommendation and limits

Keep `sabia-4` as the fixed candidate/baseline for the next full-pipeline phase,
not as a claim that selection is solved or medically validated. Preserve case 7
as an unresolved precision regression and cases 1/4 as qualifier-stability
observations. End tuning on these 12 known scenarios; do not add special rules,
new prompts or another model search to chase this sample.

Next evaluate the full pipeline and natural grounded responses, explicitly
checking whether these observed selection/qualifier issues affect factual
content or user understanding. This auxiliary benchmark does not measure
generation, claim support of final answers, retrieval recall, readability or
clinical safety. Recall@K/MRR, documentary fidelity, readability and operational
indicators remain the main TCC evaluation. No production configuration was
changed to either model in this task.

Implementation changes are evaluation-only: the existing comparison runner now
accepts the requested model pair; the paraphrase runner, frozen manifest,
reports and offline safeguards are separate from application code. Thirty
offline tests passed; Ruff passed. No tuning or corrective implementation
followed the results.
