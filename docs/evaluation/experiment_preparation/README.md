# Experimental preparation — offline only

This package prepares the accepted Golden Set v1.0.0 for two **separate** evaluations. It does not authorize or execute ingestion, embeddings, retrieval, selection, generation, judging, definitive mapping or scoring. Production and the frozen collection remain unchanged.

## Canonical implementation diagnosis

The original diagnosis compared tracked commits `d75db980d0e099ee56c526d9f750d57e56581334` and `32d3fa0ba8564470d216a21084f6252acd17d463`, then compared the original checkout's uncommitted changes with the latter worktree. At publication, PR #258 is merged into `main` at `6298d304c8523226cb6c3d474e5f5157bf821286`, which contains `32d3fa0b`. The table describes the historical comparison, not a claim that current remote `main` still uses the old pipeline.

| Component | Main checkout / local changes | Recommended candidate (`32d3fa0b`) |
| --- | --- | --- |
| Dependencies | Python >=3.14; current `pyproject.toml` and `uv.lock` | Exact same files; no dependency upgrade in this comparison |
| Deployment and persistence | Root Compose, Dockerfile, migrations, ingestion service, embedding adapter | Exact same tracked files; installed images/extensions/runtime remain unverified |
| Parser | `native_markdown_tables_v3`; local identity corrections | `native_markdown_identity_prose_v4`; identity fixes plus presentation-strength precedence, distinct-strength handling, balanced emphasis and conservative geometric prose reconciliation |
| Chunking | Existing source-copy contract, table-aware coverage validation and deterministic fallback | Same model/prompt/schema/limits; additional content roles and separate JSON/schema/provider diagnostics |
| Retrieval | K4 defaults and earlier eligibility/candidate handling | K10; dense raw 12; hybrid eligible 12 per branch / dense raw 36; equal RRF weights, constant 60; metadata/administrative eligibility before final budget; corpus scope propagation |
| LLM transport | ChatMaritalk; default `sabiazinho-4` can be overridden | OpenAI-compatible Maritaca transport supporting structured output; default `sabia-4`, temperature 0.2 |
| Answer path | Natural generation plus earlier safety branches | Structured evidence selection, ID validation and extractive rendering/abstention; **not a completed natural-answer generator** |
| Cross-leaflet | No complete general-chat path found | Retriever factories accept corpus scopes; public chat/chain factory remains leaflet-oriented |

Uncommitted main-checkout changes are preserved:

- `metadata_extractor.py` and its parser test are byte-identical to the candidate.
- The local cleaner's dosage-form rejection and cover-identity preservation are present in the candidate. Its remaining differences are the later strength/normalization changes listed above, not a demonstrated competing local implementation.
- The added cleaner tests also exist in the candidate, alongside later regressions.
- The README worker-restart notice is already present in the candidate.
- Untracked Golden Set/corpus/history files are separate assets, not obsolete material to discard or replace with the candidate's older documentation.

**Recommendation:** use current merged `main` (including `32d3fa0b`) as the ingestion/retrieval source baseline in an isolated evaluation checkout/environment. This publication does not merge branches, transplant the old generator, reset the original directory or overwrite local files. The response artifact's natural-generation path is a separate architectural decision and prerequisite for the final response evaluation, not for preparing ingestion/retrieval.

The machine-local prepared manifest records both inspected source trees and their hashes, safe static settings and allowlisted override declarations. It is not versioned: absolute checkout locations and stale worktree identities must not be presented as portable configuration. Prepare a fresh exclusive snapshot of the approved checkout before execution. These declarations are **not verified container/runtime settings**. Fallback availability must be reconciled before response runs; no environment variable was changed here. No new model or hyperparameter experiment is proposed.

## Implemented evaluation-only infrastructure

Location: `backend/evaluation/`; no `app` imports or new dependencies.

- Frozen-release reader: resolves the 11 bases and ten overrides, checks file/record/version hashes, PDF identities and per-document counts; historical draft fields do not override collection-level acceptance.
- Snapshot inspection: hashes application/migration/dependency/deployment sources and evaluation tools; records commit, local pipeline changes, static settings, override evidence and unresolved runtime requirements. Verification detects source, input, configuration or universe drift.
- Retrieval plan: 800 positives × two scenarios × three strategies = **4,800 jobs**, 400 in each of the 12 conditions. No selector/generator calls. Only scoped requests carry a document filter; cross requests do not expose the target identity to the adapter.
- Universe checks: exact A/B membership and PDF hashes; no reliance on the production `system` enum to distinguish experimental A/B.
- Runner skeleton: fixture-only retrieval adapter, ordered scores/source identities, separate empty results and technical failures, append-only checksummed checkpoints, configuration/version-bound resume, no automatic retry and no scorer.
- Mapper contracts: source snapshot and record binding, all references, original chunk text, table context, qualifiers, distributed/overlapping IDs, complete/partial/ambiguous/absent correspondence and **separate pending semantic confirmation**. There is no definitive mapper or ranking dependency.
- [Isolated dependency topology](../../../backend/evaluation/compose.yaml): separate PostgreSQL/Qdrant services and volumes for A/B; no public ports or existing application volumes. Images/password require explicit evaluation configuration. No services have been started. Image digests, initialization and canonical application mounts still need confirmation.

Snapshot/checkpoint layout is declared in the manifest. Runtime/ingestion/index snapshots are intentionally absent: inventing those identities would misrepresent readiness. Exclusive manifest creation prevents replacing existing artifacts; a new execution must use a new path/ID. The runner is serial/single-writer; future external adapters and operational execution policy are not implemented in this preparation.

## Retrieval protocol

Let `G(q)` contain all annotated relevant chunks of the reference PDF, including relevant repeated/overlapping evidence. Let `R10(q)` be the strategy's first ten eligible chunks, after hybrid fusion when applicable, **before safety supplements, context preparation, selection or generation**.

- `Recall@10(q) = |G(q) ∩ R10(q)| / |G(q)|`.
- `RR@10(q) = 1/r` for the first target-gold rank `r <= 10`; otherwise zero. MRR@10 averages these values, matching the recent pilot's cutoff convention.
- Intended denominators remain all 400 positives per corpus/scenario/strategy. Negatives are not assigned zero Recall/MRR or included in those averages.
- Cross searches only the corresponding 50-PDF universe. Other-PDF results retain their positions; equivalent evidence is not a target-retrieval hit.
- Preserve native tie order: BM25 distance then chunk ID; RRF score, best branch rank, first-seen and chunk ID; Qdrant returned order for dense. No gold-aware reordering or deduplication by text.
- Scoring does not invoke an LLM. Actual future dense/hybrid retrieval needs query embeddings, which must be budgeted separately; this is not a cost-free retrieval claim.
- Multi-fragment coverage and answer fidelity are distinct. A first-gold hit does not establish a complete response.

### Unresolved positives — policy awaiting approval

No positive is deleted, relabeled negative or silently omitted from the 4,800-job plan. Mapping gaps remain explicit, classified as source extraction, chunking, correspondence ambiguity or missing semantic confirmation.

**Recommended default:** block principal scoring until every positive has a defensible mapping, resolving issues with authorization and preserving the frozen questions. If a material ingestion loss cannot be resolved, request an explicit author decision before scoring: one alternative is a documented zero-credit convention for unmappable positives in the fixed denominator, separately reporting those losses. That convention is not mathematically Recall on an empty gold set and must not be introduced silently. A successful-mapping-only mean would be a conditional diagnostic, not a replacement for the principal denominator.

No metric implementation encodes either policy yet. Technical retrieval failures also require a declared reporting/denominator policy, rather than being silently removed or confused with documentary insufficiency.

## Response coverage alternatives — none selected

Retrieval coverage stays 4,800 in every alternative. Response coverage is independent; do not infer 5,400 LLM evaluations from the retrieval plan.

| Alternative | Positive response needs | Positive pipeline runs | All scoped negative runs | Total possible response runs | Trade-off |
| --- | ---: | ---: | ---: | ---: | --- |
| Full established coverage | 800 | 4,800 | 600 | **5,400** | No reduction of the main response scope; highest execution/judging volume |
| Two positives per PDF | 200 | 1,200 | 600 | **1,800** | One third of response volume; stratify before observing rankings; reduced thematic/multi-evidence coverage |
| One positive per PDF | 100 | 600 | 600 | **1,200** | Lowest volume while covering every PDF; substantially narrower response claims |

All options preserve the 200 scoped negative needs across three strategies and compare the same selected positive IDs across strategies/scenarios. No response sample has been drawn. A smaller option is an **explicit scope amendment**, requiring approval and justification against TCC1; not an automatic optimization. The existing 100+20 documentary audit is not silently reused as an unbiased response sample.

Approximate selector-only input exposure using the PETIVIT K10 historical guide of about 5,500 tokens/run: full ~29.7M, two/PDF ~9.9M, one/PDF ~6.6M. This is a planning extrapolation from one leaflet, not a monetary quote, new measurement or a cross-leaflet guarantee. Some paths do not call a selector, and abstention can skip generation. Judge and RAGAS call counts must be measured/configured separately, not assumed equal to response count.

Monetary budget: sum, for each stage, `(input_tokens * input_rate + output_tokens * output_rate) / 1,000,000`, plus embeddings, billed retries and hosting. Rates, final generator and judge are not fixed here; no credible total can yet be approved. Do not assume cache discounts. Present stage budgets and a cap before paid execution. Standalone metric calculation needs no selector/generator; future retrieval may issue up to 3,200 dense/hybrid query-embedding operations without reuse. Any reuse policy must be explicit and must not disguise uncached end-to-end latency.

Illustrative unattended response time at 5–15 seconds/run, before independent judges: full 7.5–22.5 hours; two/PDF 2.5–7.5 hours; one/PDF 1.7–5 hours. These are arithmetic planning assumptions, not SLA or measurements. No automatic full-battery repetitions are proposed.

Fidelity must distinguish required information/qualifiers from optional context. Documentary negatives may receive a bounded explanation rather than only generic abstention. Readability and declared-path latency remain separate from retrieval. Judge model/rubric, natural response path, actual model/fallback, concurrency, retries and coverage need author approval before paid response runs. No clinical validation is claimed.

## Offline reproduction

From `backend/`, using the existing locked environment:

```bash
uv --cache-dir tmp/evaluation-cache run --offline --no-sync python -m evaluation prepare --root .. --candidate .. --output tmp/evaluation-artifacts/manifest.prepared.NEW_ID.json
uv --cache-dir tmp/evaluation-cache run --offline --no-sync python -m evaluation verify tmp/evaluation-artifacts/manifest.prepared.NEW_ID.json
uv --cache-dir tmp/evaluation-cache run --offline --no-sync python -m pytest --confcutdir=tests/unit/evaluation tests/unit/evaluation -q --basetemp=tmp/evaluation-tests-NEW_ID
uv --cache-dir tmp/evaluation-cache run --offline --no-sync ruff check evaluation tests/unit/evaluation
uv --cache-dir tmp/evaluation-cache run --offline --no-sync mypy evaluation --follow-imports=silent --disallow-untyped-defs
```

Restore the external immutable freeze manifest and original PDFs first, following the [release notes](../golden_set/release/README.md). Preparation verifies actual PDF bytes and cannot run from the public subset alone. Offline unit tests use synthetic fixtures and need no external archive. Use a new pytest temporary directory; Windows sandbox restrictions may require approval. Tests prohibit sockets and do not load the application's parent conftest. The CLI provides only `prepare` and `verify`, no execution command. Each preparation creates a new snapshot exclusively; it does not grant permissions or supersede approval.

Compose topology validation only, from the repository root:

```bash
docker compose -f backend/evaluation/compose.yaml config --no-interpolate --quiet
```

This does not pull images, start services or verify installed versions.

## Ingestion authorization checklist

- [ ] Author confirms canonical ingestion/retrieval commit; no automatic merge of the old generator.
- [ ] Preserve the original dirty checkout, corpus files, frozen histories and audit decisions; use a separate application checkout/mount.
- [ ] Verify the prepared manifest and the existing full frozen-release verifier with no material divergences.
- [ ] Record actual non-secret settings, parser/chunker prompts/schema/tokenizer and provider routing; retain approved parameters without tuning.
- [ ] Pin image digests; initialize isolated A/B databases via existing migrations and verify BM25 extension/normalization/index configuration.
- [ ] Bind persistent experimental document UUIDs to the frozen PDF hashes; choose isolated artifact/object-storage locations.
- [ ] Enable complete ingestion exports and checkpoints; verify both indices before marking a snapshot ready; preserve failures/fallbacks.
- [ ] Author explicitly authorizes corpus ingestion and its paid chunking/embedding budget.

Response sampling/judge decisions and final mapping are not prerequisites for **ingestion authorization**. They remain prerequisites for their respective later activities. No definitive mapping begins until ingestion snapshots are approved; no principal scoring begins until the unresolved-positive policy is approved.

## Validation completed in this preparation

- 29 offline infrastructure tests passed, with network prohibited. Windows temporary-directory permissions required approved execution outside the sandbox.
- Four publication regressions also passed. A dedicated CI job verifies the public collection and offline infrastructure without PostgreSQL, Qdrant or model calls; full PDF/audit reproduction still requires external assets.
- Ruff checks and formatting passed; mypy passed for all seven evaluation Python files.
- The isolated Compose topology passed `config --no-interpolate --quiet`; no containers were started.
- The existing frozen-release verifier passed with zero material divergences: 1,000 records (800/200), 100 PDFs / 1,109 pages, 1,002 literal references, 120 version-bound audit IDs and 190 preserved alerts. No questions, decisions or frozen files were changed.
- The preparation CLI verified both source trees, input/PDF hashes, the A/B universes and the 4,800-job plan; no queries or metrics were executed. The evaluation source and topology identities are included in the final preparation manifest.

This establishes **offline infrastructure readiness**, not ingestion/runtime or experimental readiness. No cross-bula production endpoint, natural generator, external runner adapter, definitive mapper or metric scorer was added.
