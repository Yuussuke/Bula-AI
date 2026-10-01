# Progression of the auxiliary evidence selector

The 12 frozen scenarios test whether selected source units support, contradict
or delimit the question. Four scenarios came from observed regressions; eight
are synthetic diagnostics. All runs used the same candidate units, gold IDs and
order. Golds and annotation notes were never sent to the model. This is a
development check of selection, separate from retrieval Recall@K/MRR, the
fidelity and readability of final answers, and operational evaluation for the
TCC. A historical retrieval gap remains outside this benchmark.

| Completed check | Requested model and calls | Negative errors | Calls with tangential evidence | Positive coverage | False abstentions | Technical failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| [Frozen baseline](evidence_selection_base_results.md) | Sabiazinho 4; 12 cases once | 3/3 | 4/12 | 9/9 | 0/9 | 0/12 |
| [Paired model comparison](evidence_selection_model_comparison_results.md) | Sabiazinho 4; 12 × 3 | 3/9 | 6/36 | 27/27 | 0/27 | 0/36 |
| Same paired comparison | Sabiá 4; 12 × 3 | 0/9 | 0/36 | 27/27 | 0/27 | 0/36 |
| [Original/paraphrase pairs](evidence_selection_paraphrase_results.md) | Sabiá 4; 12 + 12 | 0/3 each | 0/12 each | 9/9 each | 0/9 each | 0/12 each |
| [Sabiá 4/Thinking comparison](evidence_selection_thinking_results.md) | Sabiá 4; 12 × 3 | 0/9 | 3/36 | 27/27 | 0/27 | 0/36 |
| Same Thinking comparison | Sabiá 4 Thinking; 12 × 3 | 1/9 | 2/36 | 27/27 | 0/27 | 0/36 |

The initial Sabiazinho 4 run selected five tangential IDs across four cases,
including distractors in every negative. In the controlled three-repetition
model comparison, Sabiá 4 selected no distractor on any negative and no
tangential unit while retaining at least one gold in all positive calls. That
is the substantive reason for choosing Sabiá 4 as the application default.

The paraphrase check preserved an adequate selection in all 12 paired cases;
11 pairs returned the same ID sets. In the pregnancy-condition case, the
paraphrase added a second relevant gold and changed `limitation`. The later
Thinking comparison used original questions only and exposed between-round
variability: Sabiá 4 selected a closed-package expiry unit for a question about
the deadline *after opening* in all three repetitions. Thinking did so once,
but selected an unrelated contraindication in one diabetes negative. Thinking
improved secondary precision/recall in that round, yet introduced a negative
error and averaged 4.60 seconds versus 0.90 seconds for Sabiá 4.

The default change sets `MARITACA_MODEL` to `sabia-4` when there is no explicit
environment override. This is the **chat LLM setting**, so it is not isolated to
the selector. The isolated benchmark temporarily overrode the model in its
own calls; it did not prove that the full chat pipeline had switched. Existing
environments that explicitly set `MARITACA_MODEL` retain their configured
value until changed by the operator.

These rounds show progress on the same small fixture set, not generalization to
other leaflets or proof of clinical safety. The final answer still needs
full-pipeline testing for source fidelity, natural language quality and the
remaining tangential-selection case. The benchmark is an auxiliary groundedness
check, not a new production stage or the TCC's primary evaluation. We did not
change the prompt or golds in response to these final runs.

Sanitized per-call data and hashes for reproducibility are in the matching JSON
reports: [baseline](evidence_selection_base_results.json),
[paired models](evidence_selection_model_comparison_results.json),
[paraphrases](evidence_selection_paraphrase_results.json) and
[Thinking](evidence_selection_thinking_results.json). The
[frozen cases](evidence_selection_cases.json) and
[reviewed paraphrases](evidence_selection_paraphrases.json) are versioned.
No credentials, raw provider answers or user sessions are stored in these
reports. Earlier exploratory tuning runs were not included in this release.
