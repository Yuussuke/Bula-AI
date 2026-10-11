# Controlled documentary revisions - completion

Status: authorized edits applied; **drafts, not individual human approvals or final freeze**.

## Three revisions

| Record | Revision | Authorized change |
| --- | --- | --- |
| A-B013-Q05 | 1 -> 2 | Pediatric question scope; advisory 30-minute expected information/qualifiers; literal children's-block context retained in the reference. |
| B-CB011-Q02 | 1 -> 2 | General renal-contraindication question instead of a personal TFGe scenario. Answer retains creatinine clearance below 30 mL/min **OR** TFGe below 30 mL/min/1.73 m²; no automatic permission above those thresholds. |
| B-CB025-Q05 | 1 -> 2 | Two contextual quotations added on physical p2: the contraindication introduction and the hepatic/renal-insufficiency bullet. Questions, classification, expected information and qualifiers unchanged. |

**A-B013-Q05**

Scoped: “Depois de usar essa solução na boca de uma criança, é preciso esperar para comer ou beber?”

Cross-bula: “Depois de usar Malvatricin solução para diluição da Megalabs na boca de uma criança, é preciso esperar para comer ou beber?”

**B-CB011-Q02**

Scoped: “Tem algum problema nos rins que impeça o uso desse remédio?”

Cross-bula: “Tem algum problema nos rins que impeça o uso da metformina de liberação prolongada da Merck?”

**B-CB025-Q05**

Scoped: “Quem tem problema no fígado precisa fazer exames durante o tratamento?”

Cross-bula: “Quem tem problema no fígado precisa fazer exames durante o tratamento com diclofenaco sódico injetável da Halex Istar?”

[changes.json](changes.json) contains the complete field deltas and before/after canonical hashes. [manifest.json](manifest.json) resolves the immutable prior 11 bases + seven overrides, then the three new replacements. **Exactly 997 effective records are unchanged.** Previous snapshots are not added to the denominator.

## Audit versioning and preserved decisions

Use [instrument v3](../../audit_sample_v3/review.html) and [its instructions](../../audit_sample_v3/instructions.md). [Current bindings](audit_version_binding.json) update two core-sample versions and one additional-risk version, while retaining the exact 100 + 20 IDs, order, seed and priorities. No draw or substitution occurred. The 117 other instrument snapshots are unchanged, not “117 newly approved questions.”

The original sample, instruments v1/v2, legacy decisions and separate author confirmations remain immutable history. The old instrument cannot be imported as current-v3 decisions. No old approval/rejection was transferred onto the three r2 records; they are pending current-version individual decisions. Their edit authorization is not an approval event. Historical decisions for unchanged records are not erased or relabeled as full-document reviews. Updating this instrument does **not** require repeating all 120 evaluations.

**A-B021-Q10 remains unchanged and pending a saved individual human decision**, with hash `29ad106fc7ffdc8caad70b0b58a29d71431966381b808231ebedf194a0a3c0d3`. No decision was recorded on the author's behalf.

## Six P0: documentary resolution proposals, not human closure

The [prior assisted conference](../../audit_followup/documentary_conference_20261010/report.md) remains unchanged. These interpretations are confined to that documentary evidence; the priority queue is not edited and no closure decision is recorded.

| Record / current revision | Documentary context | Bounded resolution proposal |
| --- | --- | --- |
| A-B017-Q05 / r1 | p2 stomach warning; p6 food/milk for gastrointestinal disturbances. | Retain both documentary conditions. Food/milk is not permission to use despite a stomach contraindication; no clinical reconciliation or record correction is needed from the demonstrated passages. |
| A-B026-Q08 / r1 | p2 no sensitive colic; p4 colic/diarrhea listed. | Preserve the real source tension and communicate section 8 without guaranteeing absence of colic. Current expected information already preserves the tension. |
| A-B035-Q03 / r2 | p4 timing relative to meals/milk; p6 nausea relief versus lower absorption. | Preserve the main administration timing and absorption/monitoring caveat. Do not create an independent food exception. |
| B-CB021-Q01 / r1 | p1-2 identity/presentation; both frozen manifests. | The prior conference checked product, active ingredient and responsible entity across the 100 targets: dipyrone/Santisa identifies CB021 within this corpus. Preserve the question without disclosing injection in advance; no market-wide uniqueness claim. |
| B-CB025-Q05 / r2 | p2 contraindication list; p3 severe disease; p4 monitoring. | The authorized revision now adds the p2 introduction and hepatic/renal-insufficiency bullet. Monitoring does not override either contraindication wording; question, classification, expected information and qualifiers remain unchanged. |
| B-CB038-Q04 / r1 | p6 capsule must not be split/opened/chewed; p7 individualized gradual reduction. | Dose reduction does not authorize capsule manipulation. Preserve physician-guided individualized tapering; do not add a personal schedule. |

The proposals do not equate previous approval with P0 resolution. Existing source tension remains visible. An unresolved material doubt still requires explicit handling; no quota dispenses with resolving a genuine blocker. Five records require no demonstrated material correction; diclofenac's citation-completeness revision is now applied, without declaring its alert humanly closed.

## Negative conference and methodological boundary

All 20 sampled negatives are unchanged, including their per-record version/hash bindings. The [complete-PDF assisted conference](../../audit_followup/documentary_conference_20261010/negative_conference.md) remains intact. Its AI-assisted review is not full-document human checking. The negative checklist requirement for `full_document_checked` remains unchanged, unfilled and awaiting a **separate methodological decision**. No waiver, inferred “sim” or human approval was entered.

Document-target relevance, Recall@10, MRR, scoped-only negative abstention, separate documentary fidelity and frozen pipeline parameters remain unchanged.

## Validation

[Validation report](../../audit_sample_v3/validation_report.md) and [mechanical results](../../audit_sample_v3/automatic_checks.json):

- Prior collection QC: 1,000 records / 100 PDFs / 800 positives / 200 negatives; zero automated errors; 1,000 literal reference fragments checked.
- Current layer QC: exactly three authorized deltas; seven current-record reference fragments checked against the original PDFs; zero automated errors.
- 22 Python tests, 11 ledger JavaScript tests and three DOM/interface tests passed. Ruff passed. Synthetic test decisions exist only in test memory, never in the real ledger.
- Historical artifact hashes, current bindings, blank controls, stale-version rejection and original-PDF links were checked. The CURRENT pointer was updated; its preceding contents were archived in [previous_CURRENT.md](previous_CURRENT.md).

New collection fingerprint: `820d12bc4545f2cddc0a62a1aaca8e753388e3ccc184f204fa1e07b0356d3e88`.
New instrument fingerprint: `8d5b516f3c5918f3511de7e483b1b264dc277bac18042237f96d895282d50dfb`.

No definitive freeze, RAG, ingestion, chunk mapping, experiments, provider calls or response judgment occurred. Human decisions and P0 closure remain for the author.
