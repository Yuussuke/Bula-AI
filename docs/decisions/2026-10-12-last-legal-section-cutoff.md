# Last legal-section cutoff and targeted reingestion

## Decision

Following the v7 full-document diagnostic, the user authorized the last-occurrence
method and reingestion of MALVATRICIN only. Parser
`native_markdown_last_legal_section_v8` finds the last exact standalone legal title
in cleaned lines before Markdown heading deduplication. Intermediate blocks remain.
Roman/numeric labels and Markdown wrappers are accepted. Prose/table mentions do
not match; a missing title preserves all content. Exact titles are protected from
page-furniture removal and prose joining so the cutoff cannot drift to an earlier
presentation. No document-specific production rule was introduced.

This remains a heuristic: a future PDF may contain relevant material after its
last legal section. No universal regulatory/document-format guarantee is claimed.
Repeated heading deduplication and aggregated cover metadata remain unchanged.

## Validation

- 137 selected parser/layout tests passed; seven optional local-PDF tests skipped.
- Ruff and targeted mypy passed. Original parser-fixture references and BLEU/F1
  thresholds were retained; the v7 test-only clinical-prefix adapter was removed.
- MALVATRICIN offline output grew from 5,675 to 15,073 characters. The old Markdown
  remains an exact prefix. The missing age restriction occurs once in the new text.
- Reingestion used the unchanged production service and frozen chunking/embedding
  parameters in the isolated corpus A. Synthetic private ownership was preserved;
  no system publication or fictitious human approval was created.
- Target UUID remains `2138579a-78d4-4c3c-8eaf-ef186f127e98`: 12 old chunks became
  31, with three semantic chunking calls and zero fallbacks. The source restriction
  is present in chunk `2138579a-78d4-4c3c-8eaf-ef186f127e98_27_19950e7aa6f2`.
- All 50 corpus A PDFs/chunk exports were checked against live PostgreSQL and
  Qdrant before and after. The other 49 documents are unchanged. Corpus A now has
  1,330 chunks. Prior target vectors and metadata were exported before replacement.

## Provenance and remaining work

Append-only runtime artifacts: `backend/evaluation/artifacts/ingestion-reprocess-20261012-v8/`.
The composed effective snapshot contains 100 PDFs and 2,699 chunks; corpus B's
1,369 chunks carry their previous verification, not a new live audit. The additional
B-only verification launch was denied by the scope guard and was not executed.
No B index/container operation was performed by this reingestion tool.

Snapshot fingerprint: `1466a37fdaf9ccdc05f03cdd3fd7c3d22c3f0fbac51bc00e1aabb0dd20b250c3`.
Historical snapshot `ebd93e5c7f9aaa679306223307ca12835cb03af10ee9cdf7095a6e24295cdfeb`
and all prior parsing/chunk artifacts remain unchanged. Original Golden Set and
frozen derived questions are unchanged. No retrieval experiments or metrics ran.

The previous mapping instrument is bound to the old snapshot. A-B013-Q03 and
A-B013-Q06 need refreshed candidates/version links; no mapping decisions were
generated or inherited. This task does not freeze or approve a new gold mapping.
