# Offline evidence mapping

This evaluation-only tool prepares lexical candidates, not approved golds.
It never performs retrieval, calls providers, generates answers or writes indexes.

## Bound inputs

- Frozen derived v1.0.0: 200 human-reviewed questions, 160 positives/40 negatives.
- Original Golden Set and 100 target PDFs remain unchanged.
- Current ingestion snapshot: `1466a37fdaf9ccdc05f03cdd3fd7c3d22c3f0fbac51bc00e1aabb0dd20b250c3`.
- 2,699 exported chunks: 92 documents parsed with v4, six with v5, one with v6,
  one with v8. Corpus A was reverified after its targeted reingestion; corpus B
  carries the previous verification, not a new live audit.

The reader validates hashes, frozen question approvals/revisions, PDF identity,
verification records, checkpoints and chunk exports. Totals must equal the bound
snapshot, not a hardcoded historical count. Sources are rechecked after preparation.
Live index agreement must be revalidated before future experiments.

## Discovery and review

The fixed `lexical_discovery_v1` policy compares ordered normalized tokens of the
reference quotes with all target-document chunks, independently of retrieval ranks.
NFKC/case/formatting comparison preserves numbers and unit tokens; no conversions
or semantic entailment are inferred. Partial discovery requires five contiguous
tokens and 35% quote coverage. Full adjacent windows are limited to three chunks.
Structured source-region annotations remain lossless.

Statuses describe textual correspondence only: complete (one full alternative per
reference), ambiguous (multiple alternatives), partial, or absent. Metadata-only
matches cannot establish automatic source-text completeness. Multiple overlapping
chunks may all be relevant. Every case starts with semantic review pending.

The interface displays questions scoped/cross, literal references, original PDF
page links, full chunks/neighbours, presentation context, indispensable/optional
human question annotations and qualifiers. Indexed exports lack reliable physical
chunk-page provenance; the tool does not invent it.

Current package: `gold-mapping-200-v1-r6`. All 160 positives have candidates:
139 complete, nine partial and 12 ambiguous. The 21 priority cases appear first;
139 cases offer individual quick review with quote/chunk comparison. Forty
negatives remain separate, without supporting IDs. These counts are neither
Recall@10 nor confirmed semantic coverage.

Quick approval is an explicit joint human attestation of the displayed criteria,
not separate automatically filled judgments. Loading/navigation does not create
events. Detailed review handles ambiguities, tables and exclusions of genuinely
complementary references. Existing decisions or unsaved edits disable quick approval.
No full-PDF human reading or independent clinical validation is claimed.

Events bind record/revision, mapping input, package, reviewer and timezone-aware
timestamp. Export preserves append-only history; validation rejects stale/foreign
IDs, unknown records, insufficient references and doubtful approvals. Old r3/v4
exports are not automatically imported into r6. Prior question approvals never
become mapping approvals. No migration of human decisions was performed.

## Reproduction

Restore the external original Golden Set archive, frozen derived release, source
PDFs and ingestion exports in their manifest-relative locations. Large packages,
private review histories and runtime artifacts are deliberately excluded from Git.
The collection and ingestion custody dependencies are documented in
[the milestone](../milestones/2026-10-12-pre-experiment.md).

From `backend/`, with pinned dependencies:

```sh
uv run --offline --no-sync python -m evaluation.prepare_mapping prepare \
  --root REPOSITORY_ROOT --derived-manifest FROZEN_200_MANIFEST \
  --ingestion-snapshot INGESTION_SNAPSHOT \
  --snapshot-fingerprint 1466a37fdaf9ccdc05f03cdd3fd7c3d22c3f0fbac51bc00e1aabb0dd20b250c3 \
  --output NEW_PACKAGE_DIRECTORY

uv run --offline --no-sync python -m evaluation.prepare_mapping validate-review \
  --package PACKAGE/review-package.json --decisions HUMAN_EXPORT.json
uv run --offline --no-sync python -m pytest tests/unit/evaluation --confcutdir=tests/unit/evaluation
```

Preparation blocks sockets and refuses existing output directories. Outputs include
candidate/input JSONL, negatives, coverage, review package/HTML, report and manifest;
inputs, tools/UI and output artifacts are hashed. Presentation-only refresh preserves
exact data bytes; snapshot replacement creates a new package and new review bindings.

## Remaining gates

Review and explicitly authorize freezing of the gold-to-chunk mapping before
experiments. Both scoped/cross use the same approved target-PDF IDs; cross retrieval
must still search its whole corpus without a hidden target filter. Never exclude
positives silently because of ingestion/mapping issues. Fidelity, legibility and
negative abstention remain separate from retrieval metrics.
