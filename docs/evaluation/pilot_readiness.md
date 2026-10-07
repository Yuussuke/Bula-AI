# Pilot readiness

Static review dated 2026-10-06, based on
[main at e35e232](https://github.com/Yuussuke/Bula-AI/tree/e35e232e7f69a00f6798eac55c6e093943277753).
The consolidation PR adds the missing `sabia-4` default and medication-identity
fix, but does not complete the evaluation pipeline.

## Implemented and missing

| Area | Status |
| --- | --- |
| Retrieval | Dense/BM25/hybrid factories exist; retain per-document authorization. |
| Cross-document components | Factories accept `bula_id=None` and system/shared/private corpus scope. |
| General chat | `/direct-ask` returns 501; the chat chain still requires a document UUID. |
| Experimental isolation | A/B are not application corpus types; isolate the corresponding manifest before retrieval. |
| Answers | Selection/validation renders diagnostic extracts; natural generation is missing. |
| Diagnostics | Stage timing and JSON/schema/ID failures are separate from empty selection. |
| Main evaluation | Runner, original-ranking export, RAGAS/judge integration and resumable results are missing. |

At the reviewed baseline, `k=4`; hybrid fetches up to 12 candidates per branch
before returning four. This is not twelve sources presented to the selector.
Per-document safety supplementation can add two sections; it is disabled for
cross-document dependencies. Record this distinction rather than treating scope
as a pure filter ablation. Internal document/chunk IDs exist, but public sources
alone cannot reconstruct the original ranking.

## Configuration checks

`sabia-4` is the chosen default, not proof of the model running in containers:
environment overrides and fallback must be recorded or disabled for evaluation.
Chat temperature is 0.2; reconcile generator settings with the TCC1 target of
0.0 instead of silently assuming equivalence. Record actual token limits.
The static review could not access Docker, so migrations, indexes and effective
runtime configuration were not verified. Publication checks are listed in the PR.

## Next steps

1. Confirm services/migrations and record the commit and non-secret configuration;
   do not automatically reingest the entire collection.
2. Review ten references for P001, PETIVIT BC (8+2), then validate parsing/chunks
   and map gold IDs without using retrieval outcomes as annotation criteria.
3. Add natural grounded generation to the existing path, retaining authorization,
   evidence selection and source identity. No new verifier/corrective retrieval.
4. Reuse application components in an evaluation runner; capture ranking,
   context and final sources, metrics, failures and resumable outputs.
5. Freeze judge/rubric/audit/error policies; run ten questions × three modes =
   30 history-isolated pilot runs, plus any model/evaluator calls.
6. Verify authorized cross-document chat and pre-retrieval corpus isolation
   before the main run; one pilot document does not test document competition.

Keep gold references, configuration, checkpoints/results and an audit summary.
The pilot has not been executed, and main questions/golds are not frozen.
