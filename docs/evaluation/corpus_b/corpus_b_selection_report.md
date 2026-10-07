# Corpus B selection

Document review: 2026-10-06; official metadata snapshot: 2026-10-05.
The [manifest](corpus_b_final.csv) is the sole 50-document inventory, preserving
identity, registration, provenance, annotation pages and PDF/text hashes.

## Selection and provenance

Select ten eligible patient PDFs in each group below. Thematic membership is
primary; internal variation is secondary. Historical Brazilian usage studies
motivate the groups, not a claim that these are today's ten most-used medicines.

| Group | Usage rationale |
| --- | --- |
| G1: Antihypertensives | [PNAUM/Mengue et al., table 3](https://www.scielo.br/j/rsp/a/Q8rkJR7H3ZJXRSjqW4WfRLD/?lang=pt) |
| G2: Oral antidiabetics | [PNAUM, table 7, printed p. 24](https://bvsms.saude.gov.br/bvs/publicacoes/componente_populacional_resultados_pnaum_caderno3.pdf) |
| G3: Non-opioid analgesics/antipyretics and systemic NSAIDs | [PNAUM/Arrais et al., table 4](https://www.scielo.br/j/rsp/a/PNCVwkVMbZYwHvKN9b4ZxRh/?lang=pt) |
| G4: Antidepressants | [PNAUM, table 16, printed pp. 30–31](https://bvsms.saude.gov.br/bvs/publicacoes/componente_populacional_resultados_pnaum_caderno3.pdf) |
| G5: Lipid-lowering medicines | [PNAUM, table 10, printed p. 26](https://bvsms.saude.gov.br/bvs/publicacoes/componente_populacional_resultados_pnaum_caderno3.pdf) |

PNAUM refers to urban residents in 2013/2014 with source-specific denominators.
[CMED 2024, table 9](https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/medicamentos/cmed/anuario-estatistico-do-mercado-farmaceutico-2024.pdf/@@download/file)
provides complementary package-volume evidence, not user prevalence.

Verify manual ANVISA download provenance, patient/drug identity, registration
against official records, all-page native text, intact PDFs and hashes.
Forty-seven new downloads plus three eligible reserve PDFs form the collection.
Ten unconfirmed registry reserves are not additional eligible leaflets.
No RAG results, embeddings or application-parser success influenced selection.

## Documentary summary

| Dimension | Result |
| --- | --- |
| Documents / groups | 50 / five, ten documents each |
| Pages | 515 total; 6–17 per PDF |
| Length | 20 short, 15 medium, 15 long |
| Composition | Three combinations, 47 single-active documents |
| Population | 33 adult, 17 both; none pediatric-only |
| Clinical tables | Five with, 45 without |
| Multiple strengths / presentations | 24 / 37 documents |
| Form/release descriptions | 11 documentary labels; predominantly oral |
| Explicit manufacturers / holders | 33 manufacturer names; 27 holder CNPJs |
| Unspecified manufacturer | CB022 and CB025; not inferred from the holder |
| Overlap with A/pilot | None by registration or PDF hash |

Length terciles use these 50 documents, interpolation at (n−1)×p:
short ≤9 pages, medium 10–11, long ≥12; ties remain together. These relative
bands differ from corpus A. Entire PDFs count once, including multiple internal
presentations; do not generalize a population statement to every strength.

Manufacturing, registration metadata and PDF annotations remain distinct.
Text extraction does not guarantee perfect reading order/table parsing.
Origin checks do not establish the latest available version. This intentional,
thematically concentrated collection is not nationally representative, and
greater retrieval difficulty is a hypothesis, not an observed selection result.

Official snapshot sources: [Bulário products](https://dados.anvisa.gov.br/dados/CONSULTAS/DOCUMENTOS/TA_CONSULTA_BULA_PRODUTO.CSV),
[medicines](https://dados.anvisa.gov.br/dados/DADOS_ABERTOS_MEDICAMENTOS.csv) and
[presentations](https://dados.anvisa.gov.br/dados/CONSULTAS/PRODUTOS/TA_CONSULTA_MEDICAMENTOS.CSV).
