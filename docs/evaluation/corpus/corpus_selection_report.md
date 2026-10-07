# Corpus A selection

Selected on 2026-10-05 for documentary diversity, without using RAG performance.
The [manifest](corpus_final.csv) contains all 50 document-level characteristics,
source links, annotation pages and SHA-256 hashes; no duplicate Markdown inventory.

## Eligibility and method

The initial batch contained 93 downloads, 91 unique hashes and 88 eligible
patient leaflets. Exclude duplicate copies, OCR-only Forteviron/LQFEX-Cloroquina
and unconfirmed Alphacaine; nine candidates were not reconfirmed in that batch.
Patient identity, registration and native text on all pages were checked against
the downloaded PDFs and official metadata. Local download provenance supports
the manual ANVISA origin, not cryptographic authenticity or latest-version status.

Select intentionally for page length, formulations/routes, single/combined
composition, declared population, clinical tables, concentrations/presentations
and manufacturers. Therapeutic group is secondary, without class quotas.
This is maximum-variation sampling, not a proven mathematical optimum.

Length bands use terciles of all 88 eligible documents: linear interpolation
at (n−1)×p, cutoffs 8 and 12 pages. Short ≤8, medium 9–12, long ≥13;
ties stay together. Count entire PDFs, including covers/history/annexes.

## Selected diversity

| Dimension | Result |
| --- | --- |
| Length | 17 short, 16 medium, 17 long; 2–50 pages |
| Form/route/preparation descriptions | 44 documentary labels, not 44 independent pharmacopoeial classes |
| Composition | 32 single; 17 non-vaccine combinations; one multicomponent vaccine |
| Population | 19 adult, one pediatric-only, 30 both |
| Clinical tables | 15 with, 35 without |
| Multiple strengths / presentations | 15 / 30 documents |
| Explicit manufacturers | 51 names in 45 PDFs; five unspecified |
| Registration holders / therapeutic labels | 50 distinct CNPJs; 49 official labels and one unspecified |

Unknown manufacturers stay blank, separate from registration holders. Clinical
tables exclude administrative history and dotted lists. Population applies to
the whole document, not automatically to every presentation. Per-mL/per-dose
expressions of the same concentration do not count as separate strengths.

[P001, PETIVIT BC](corpus_pilot.csv), is a separate nine-page syrup/combination
leaflet for adult/pediatric use, reserved before RAG testing. Its registration
and hash are outside A/B; it cannot represent all layouts on its own.
The collection spans oral, topical, inhaled, ophthalmic, otic, vaginal, rectal,
injectable and dialysis documents. This demonstrates documentary variation,
not national representativeness or clinical safety.
