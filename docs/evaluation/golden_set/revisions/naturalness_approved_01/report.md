# Authorized controlled revision — completion report

2026-10-10. Seven new draft record versions applied under the author's explicit authorization. This is **not individual human documentary approval, a collection freeze or authorization to resume human audit**.

## Revised records

| ID | Record revision | Change | Preserved scope |
| --- | --- | --- | --- |
| B-CB002-Q02 | 1 → 2 | Linguistic; remove “limite citado”. | Severe renal restriction and the specified clearance threshold; no individual permission. |
| B-CB017-Q02 | 1 → 2 | Linguistic; ask about indication rather than “público indicado”. | Eleven-year-old child, DM2; population indication is not a clinical authorization. |
| B-CB021-Q04 | 2 → 3 | Linguistic; request the IM volume range naturally. | Four years, 20 kg, IM route and complete documentary range; no selected dose. |
| A-B040-Q08 | 1 → 2 | Linguistic; remove the table-location wording. | Six months, 7 kg, oral drops and single-dose range; not the daily maximum. |
| A-B041-Q04 | 1 → 2 | Linguistic; conversational request for guidance on other options. | Lactation contraindication and professional alternatives; no invented substitute. |
| B-CB040-Q04 | 1 → 2 | Linguistic; same two needs in everyday wording. | Lactation contraindication, professional alternatives and Globo/Zydus product identity. |
| A-B016-Q08 | 1 → 2 | Semantic; author's exact conversational scoped/cross questions, conditional expected information, qualifiers and one added citation. | Intravesical BCG, unknown warning conditions, potential seriousness and professional conduct. |

The six linguistic revisions change only `question_scoped`, `question_cross_bula` and `draft_revision`. Expected information, references, classifications and indispensable qualifiers remain identical. Scoped/cross equivalence was checked before writing each override: both variants retain the same need and conditions, with only product identification added in cross-bula. This is assistant checking, not a human audit event or proof of corpus-wide identifier uniqueness.

The ten records explicitly requested unchanged remain unchanged, as do all other non-authorized records: **993 of 1,000**. No broad rewriting was performed.

## BCG documentary confirmation

Physical pages 2–3 of the [frozen Imuno BCG PDF](../../../../../backend/tmp/anvisa-bulas-v2/corpus-20261005/pdfs/final/B016/bula_1791246837814.pdf) were reread before applying the revision. Page 2 establishes intravesical administration. Page 3 supports the conditional warning: fever above 39 °C persisting for 24–48 hours after fluids/antipyretics, and/or worsening malaise/fever, may indicate systemic infection with life-threatening risk; it also gives the professional interruption criterion until infection is excluded.

The added physical-page-3 reference uses the **actual source wording**, not the paraphrase in the earlier proposal:

> Informe a seu médico, cirurgião-dentista ou farmacêutico o aparecimento de reações indesejáveis pelo uso do medicamento.

The response requirements now distinguish:

- **Documented statements:** conditional warning criteria, possible systemic infection, seriousness, reporting adverse reactions and professional conduct.
- **Author-authorized safety guidance:** immediate contact with the treating physician given the potential seriousness. The source's fever/reporting passages do not literally specify that contact deadline; the record and qualifiers explicitly distinguish this guidance from a literal documentary claim.
- **Unknown patient facts:** measured temperature, duration and fluids received. Neither a diagnosis nor fulfillment of every criterion is assumed. A clarification can complement the answer but is not required before acknowledging danger and advising contact. The 24–48-hour condition must never become a recommendation to wait.

No antibiotic, individualized treatment, independent patient interruption, external clinical protocol or transfer of the distinct hepatitis/pneumonitis instruction was introduced.

## Versioning and effective collection

[questions.overrides.draft.jsonl](questions.overrides.draft.jsonl) contains **only the seven revised records**. [changes.json](changes.json) records original file hashes, canonical before/after record hashes, complete field differences, revision reasons and the scoped/cross assessment. All earlier files and reports remain immutable historical snapshots.

[manifest.json](manifest.json) defines the current collection: load the 11 historical effective files once and replace these seven IDs. Do not append seven extra cases. The resulting collection remains **100 PDFs / 1,000 drafts / 800 positive / 200 negative**, with the same document-target relevance, Recall@10, MRR, scoped-only negative abstention and separate fidelity policy.

Current input fingerprint: `8fa88e09b50201b174d5a1a033b1ae9b739415164b6ecd1d9d4533874a8d600e`. It includes the base inputs and the override/ledger files; it does not alter the frozen corpus hashes or the RAG configuration.

## Automatic checks executed

[qc.json](qc.json) records **zero mechanical errors** from read-only checks of:

- Historical ledger/file hashes and archived audit-package integrity.
- The current collection's structure, provenance, PDF identities, reference pages and literal quotations: **1,000 fragments** (999 historical plus the new BCG citation).
- Unique IDs, document membership, per-PDF 8/2 distribution and duplicate normalized cross-bula questions.
- Exactly seven authorized changed records, six linguistic field boundaries, preserved classifications and canonical record differences/hashes.
- Draft/pending human checks, no chunk mapping and no inherited human decisions.
- Unchanged core/additional audit membership and updated hashes for the two affected additional records.

**28 offline tests passed**, including five new tests for authorized replacement without denominator inflation, refusal of unknown/duplicate/unauthorized IDs, content hashes, pending review states and the linguistic-edit boundary. The existing documentary regression suite was reused. No sampling tests or sampler were run. Pytest emitted a cache-directory warning; all assertions passed. The five new tests were also rerun with `-p no:cacheprovider`: **5 passed without warnings** (the same tests, not five additional scenarios). `git diff --check` passed. The initial default `uv` cache was inaccessible, so execution used a workspace-local cache without changing dependencies or contacting providers.

The task's pre-change hash snapshot confirmed **157 pre-existing files unchanged**, including all earlier golden-set artifacts, the audit sample, both corpus manifests and the five pre-existing README/parser/test changes. These unrelated worktree changes were not edited.

Commands executed from the repository root:

```bash
uv --cache-dir tmp/uv-cache run --offline --project backend --no-sync python docs/evaluation/golden_set/revisions/check_current.py
uv --cache-dir tmp/uv-cache run --offline --project backend --no-sync pytest docs/evaluation/golden_set/revisions/test_check_current.py docs/evaluation/golden_set/expansion/test_check_batch.py --confcutdir=docs/evaluation/golden_set -q
```

Mechanical quotation matching is **not** semantic certification, full-document negative absence approval, validation of query uniqueness or a new independent semantic verifier. Human audit remains necessary under the established sample/risk protocol.

## Audit sample status

The original seed **20261009** and the **same 100 core IDs** are retained byte-for-byte; their distribution remains A: 40 positive/10 negative and B: 40 positive/10 negative. **No core record was revised.** No draw, substitution or reassignment was executed.

The **same 20 proposed additional IDs** are also retained. Their two affected records, **A-B016-Q08** and **B-CB021-Q04**, now bind to the new record revisions/hashes in [audit_version_binding.json](audit_version_binding.json). The initial budget remains **120 unique records**, with no waiver of blocking-risk escalation. Three historical alert bindings affected by these edits are explicitly linked to current record hashes; the alerts were not automatically declared resolved.

The old `audit_sample/review.html`, decision template, automatic checks, report and instructions are **explicitly invalidated for current-version review**, but preserved as historical files with their old hashes. The original sample membership is not invalidated. [The version notice](../../audit_sample/CURRENT_VERSION.md) identifies this boundary; [CURRENT.md](../../CURRENT.md) identifies the effective collection. The old naturalness/triage/collection reports remain version-bound historical diagnostics rather than current approval records.

No human review events or approvals were created or inherited. A refreshed review instrument must bind this current collection and the same sample IDs before resumption. **Await author authorization to prepare/resume the human audit.** No RAG, ingestion, experiments, chunk mapping, response judgment or definitive freeze was performed.
