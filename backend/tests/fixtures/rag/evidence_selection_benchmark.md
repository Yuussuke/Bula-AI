# Isolated evidence selection — auxiliary development benchmark

## Scope and academic role

This benchmark checks the evidence-selection mechanism during groundedness
development. It is neither a production stage nor a replacement for the main
TCC evaluation: retrieval-mode comparison, retrieval Recall@K/MRR, documentary
answer fidelity, readability and operational indicators remain separate.

The final artifact remains a RAG assistant producing natural-language answers
grounded in retrieved evidence. The current extractive response is useful for
development/diagnosis; this benchmark does not decide that it replaces grounded
generation in the final artifact. Correct selection alone does not establish
claim entailment, answer fidelity or clinical safety.

The isolated evaluation itself uses fixtures, an opt-in live test, scripts,
offline accounting tests and this documentation. Its runs do not modify the
production prompt, schema, parser, retrieval, renderer or chat flow. Model
changes made after the experiments are documented separately in the
[progression report](evidence_selection_progression.md).

## Fixtures and golds

Each scenario contains `id`, `category`, `source_origin`, `question`, `units`,
`gold_ids` and `annotation_notes`. A frozen unit contains `id`, `source`,
`section`, `kind` and exact `text`. Tables include the already preserved local
headings/labels and column headers. Units are not rebuilt or renumbered at run
time. The application formatter renders their existing representation.

The base set has 12 scenarios, 3–15 units each:

- Four regressions: bacterial-indication scope; tablet age restriction with
  renal tables; absence of a diabetes mention; an express pregnancy condition.
- Eight clearly labelled synthetic generalist development fixtures: direct
  storage/route questions, two complementary-evidence questions, two scope or
  explicit-condition questions, and two sets containing only distractors.

Synthetic fixtures are not real leaflets, clinical instructions or validation
across additional medications. Regression candidates come from saved local
rounds. Some use documented subsets; the age and diabetes regressions preserve
their full candidate sets. This set is small and intentionally diagnostic, not
a held-out estimate of real-world quality.

A gold ID contributes directly to sustaining, contradicting or delimiting the
asked proposition. Mere topic, section or medication association does not count.
Annotate **all** contributing units, not just the preferred shortest answer.
For example, both E2 and E6 contribute to the age regression; selecting either
does not make it tangential, and selecting both is permitted. Complementary
evidence for two requested facts receives two gold IDs. Partial-but-pertinent
evidence is still relevant; support labels are not selection golds.

Missing one of two redundant gold units reduces evidence-coverage recall/exact
match, but does not necessarily make an answer incomplete. Minimize needless
redundancy in new fixtures and review per-case IDs instead of treating exact
match as the only criterion. The case-10 empty gold refers to lack of supplied
documentary support for diabetes safety, not a medical conclusion.

The previously identified case 4 is excluded: its missing indication is a
retrieval gap, not a selector benchmark failure or a newly fixed scenario.

## Isolation and leakage controls

The evaluator sends only the question and frozen units to the production
`EVIDENCE_SELECTION_PROMPT`, using `get_llm(settings=...)` and exactly
`ContextAssessment.provider_response_format()`. There is no retrieval,
embedding request, database access, deterministic allergy route, answer renderer
or clinical postprocessor. Empty history is fixed for this isolated task.
The configured provider's existing transient fallback policy remains unchanged.

Only JSON/schema decoding and candidate-ID membership checks occur before
accounting. `limitation` does not alter the selected IDs or metrics. Duplicate
returned IDs are counted once because the measurements concern sets.

Golds, source origins, case IDs/categories and annotation notes are never sent
to the model. An offline test verifies that changing golds/annotation leaves the
messages unchanged. The JSON fixtures are versioned before live execution; the
report records fixture/prompt checksums, configured provider/model information
and observed model names when the provider exposes them. No API keys, raw model
bodies or exception prose are written in the report.

Do not tune the prompt/model to maximize these cases, move golds to match a run,
or present repeated trials as independent scenarios. Annotation corrections
must have a documentary justification and a new fixture version/checksum.
There is no model-generated judge or automatic semantic reannotation.

## Metrics and denominators

For valid returned-ID set S and gold set G, TP = |S intersect G|, FP = |S minus G|
and FN = |G minus S|. Report every case, selected/gold IDs, missing/tangential IDs
and the following independent measures:

| Metric | Definition |
| --- | --- |
| Selection precision | TP / |S|; null when S is empty |
| Selection recall | TP / |G|; null when G is empty |
| Exact set match | S = G, including a correct empty negative selection |
| Tangential count/rate | FP and FP / |S|; rate null for empty selection |
| False abstention | G nonempty and S empty |
| Negative-case error | G empty and S nonempty; null for positive cases |

Aggregates include micro precision/recall (summed counts), macro averages over
defined values, exact-set count/rate, total tangential evidence and its fraction
of selected evidence, and the number/fraction of valid cases selecting a tangent.
False-abstention rate uses valid positive cases; negative-error rate uses valid
negative cases. Defined-value counts and valid/attempted case counts are explicit.
All undefined ratios serialize as null, never as an automatic 100%.

Provider errors, timeout, JSON/schema failures and unknown IDs have null metrics
and a separate technical-failure record. They are not empty documentary evidence
or false abstentions. Their rate uses all attempted cases; semantic aggregates
use valid cases. Always interpret the technical rate alongside these aggregates
to avoid hiding failed calls through denominator exclusion. Configuration or
fixture-loading errors stop the run before provider requests.

There is no composite score and no claim that these metrics equal retrieval
Recall@K/MRR or establish medical safety. Small-set deltas are diagnostic only.

## Execution

From `backend/` in the worktree/branch containing this change, with the same
environment configuration as the application:

```bash
# Offline verification; no API calls, Docker or reindexing required.
uv run pytest tests/unit/scripts/test_benchmark_evidence_selection.py -q

# Explicitly authorized live run: 12 selector invocations, no embeddings or DB.
# Existing configured provider fallback may add a call on transient failure.
uv run python -m scripts.benchmark_evidence_selection --allow-provider-requests
```

The CLI prints per-case/aggregate JSON and saves it to
`tmp/evidence-selection/results.json`. `--output PATH` chooses another report
path; use distinct paths to retain separate rounds. Running the command without
the opt-in flag fails before constructing the provider client.

Alternatively, in Git Bash:

```bash
RUN_LIVE_EVIDENCE_TESTS=1 uv run pytest tests/integration/rag/test_evidence_selection_live.py -s
```

The live pytest test executes the entire base set and prints/saves its report to
the pytest temporary directory before checking exact sets. Known differences
can make that optional test fail. Its pass/fail is not a combined quality grade
or a gate for the main TCC evaluation; use the independent reported metrics.
Ordinary CI keeps it skipped. Offline tests mock only the external model and
check accounting/errors/isolation; they do not demonstrate live selection quality.

## Stability — deferred

Paraphrases and reordered units are intentionally not implemented in this base
set. Later, run them in a separate stability report linked to the original base
scenario, preserving semantic golds and stable IDs. Do not count them as extra
independent cases or silently pool them into base-set metrics.

Historical single-source experiments and full-chain reports remain historical
artifacts; their scores are not directly comparable to this new multi-unit set.
