# Conferência dos PDFs baixados

Data: 2026-10-05. Pasta examinada: Downloads local do autor (caminho pessoal omitido).

Escopo: os 93 arquivos `bula_*.pdf` com data de modificação local em 2026-10-05, comparados com os 100 registros de `corpus_candidates.csv`. PDFs antigos de Downloads e arquivos de outros assuntos não foram incluídos nessa contagem. Nenhum PDF foi modificado, movido ou excluído; o CSV original também não foi alterado.

## Resumo

| Verificação | Resultado |
| --- | ---: |
| Arquivos encontrados nesta rodada | 93 |
| PDFs que abriram e tiveram todas as páginas percorridas | 93 |
| Erros de abertura/extração detectados | 0 |
| PDFs distintos por SHA-256 | 91 |
| Cópias adicionais idênticas | 2 |
| PDFs distintos com texto extraível em todas as páginas | 89 |
| PDFs distintos sem texto extraível | 2 |
| Registros candidatos associados pelo registro nos dizeres legais | 88 |
| PDF com nome esperado, mas registro divergente | 1 |
| PDFs digitalizados identificados visualmente na lista | 2 |
| Candidatas sem arquivo localizado nesta rodada | 9 |
| Arquivos com origem `consultas.anvisa.gov.br` nos metadados locais de download do Windows | 93 |

Assim, dos 100 registros esperados: **88 correspondências por registro + 1 documento com divergência cadastral + 2 digitalizados + 9 ausentes = 100**. As duas cópias repetidas explicam a diferença entre 93 arquivos e 91 PDFs únicos.

Os 89 PDFs únicos com texto incluem o documento divergente; portanto, **não devem ser chamados automaticamente de 89 bulas elegíveis**. Esta conferência não seleciona as 50 finais nem completa a caracterização documental de cada PDF.

## 1. Bulas não localizadas nesta rodada

| ID | Medicamento | Detentor cadastral | Registro e link de busca |
| --- | --- | --- | --- |
| C001 | Amoxicilina + clavulanato de potássio | EMS S/A | [102350532](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=102350532) |
| C017 | Glifage | MERCK S/A | [100890193](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100890193) |
| C040 | Bariogel | CRISTÁLIA PRODUTOS QUÍMICOS FARMACÊUTICOS LTDA. | [102980002](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=102980002) |
| C050 | Nitrop | HYPOFARMA - INSTITUTO DE HYPODERMIA E FARMÁCIA LTDA | [103870012](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=103870012) |
| C051 | Colpistar | FARMOQUÍMICA S/A | [103900059](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=103900059) |
| C054 | Loncord | DIFFUCAP - CHEMOBRÁS QUÍMICA E FARMACÊUTICA LTDA | [104300008](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=104300008) |
| C062 | JP Glicofisiológico | JP INDUSTRIA FARMACEUTICA S/A | [104910019](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=104910019) |
| C063 | Acetilcisteína | UNIÃO QUÍMICA FARMACÊUTICA NACIONAL S/A | [104970006](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=104970006) |
| C093 | HC-EsqueleRad | HOSPITAL DAS CLINICAS DA FACULDADE DE MEDICINA DA USP | [111040001](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=111040001) |

**C001 já tem uma cópia histórica no projeto**, examinada na etapa anterior, em `backend/tmp/anvisa-bulas-v2/amoxicilina-clavulanato-500mg-125mg-comprimido-ems__35934920__patient.pdf`. Ela permanece candidata a piloto. Portanto, são **8 candidatas adicionais ausentes**, se essa cópia anterior for mantida separadamente e sua versão adotada for documentada. A falta do download novo não prova que a bula esteja indisponível na ANVISA.

## 2. Downloads repetidos

| Identificação por registro | Arquivos com SHA-256 idêntico |
| --- | --- |
| C002 — Singulair | `bula_1791246623844.pdf` e `bula_1791246671591.pdf` |
| C090 — Salonpas | `bula_1791247383810.pdf` e `bula_1791247399686.pdf` |

Conservar uma cópia de cada dupla no futuro corpus. Nenhuma cópia foi excluída nesta conferência. O PDF de Salonpas contém identificação de diferentes apresentações; não se deve deduplicar ou separar suas seções apenas pelo nome da capa.

## 3. PDFs integralmente digitalizados

| Identificação visual | Arquivo | Páginas | Texto nativo |
| --- | --- | ---: | --- |
| C039 — Forteviron; registro 1.0247.0024 visível na página 2 | `bula_1791246905996.pdf` | 2 | Nenhum |
| C095 — LQFEX - Cloroquina; capa identifica cloroquina 150 mg | `bula_1791247424703.pdf` | 2 | Nenhum |

As duas páginas de cada arquivo foram renderizadas e inspecionadas. Não estão ausentes: foram baixadas, mas são documentos de imagem sem camada textual recuperável pela extração usada. Não foi executado OCR. Isso é diferente de uma falha do parser da aplicação em interpretar uma tabela.

Essas cópias **não atendem ao critério de texto extraível sem depender integralmente de OCR**. Não basta baixar novamente o mesmo arquivo. Se não houver outra versão oficial com texto nativo, registrar a inelegibilidade e substituir a candidata, sem modificar o original nem relaxar o critério após ver resultados do RAG.

## 4. Divergência no documento de Alphacaine

Arquivo: `bula_1791246883770.pdf`, 7 páginas, texto extraível em todas elas.

- Capa: `ALPHACAINE`, DFL, cloridrato de lidocaína + epinefrina; indicação de bula para o paciente.
- Registro esperado da candidata C029: `101770016`.
- Registro impresso na página 5, conferido no texto e visualmente: **`101770025`**.
- No cadastro oficial de medicamentos baixado nesta pesquisa, `101770016` corresponde a ALPHACAINE e `101770025` corresponde a ARTICAINE.

Não é uma simples ausência nem foi corrigido automaticamente pelo nome. Há uma inconsistência entre a identificação do PDF e o cadastro oficial. Não é possível atribuí-la ao usuário, ao documento publicado ou à vinculação no portal apenas por esta auditoria. **Manter pendente fora da seleção final** até conferir a vinculação oficial e/ou obter documento consistente. Não alterar o número impresso no PDF ou os metadados para fazê-los coincidir.

## 5. Método e limites

- SHA-256 calculado diretamente dos bytes originais para cada arquivo.
- Abertura e extração de todas as páginas com `pypdf`; a contagem textual deste diagnóstico é específica desse extrator, não deve ser misturada sem padronização com a contagem anterior feita por PyMuPDF.
- Correspondências pelo número de registro nos dizeres legais, admitindo a formatação com pontos e variantes usuais de `Registro`, `MS` e `nº`. Nomes da capa foram usados para revisão, não para substituir uma divergência de registro.
- Inspeção visual dos dois PDFs sem texto e da página legal de Alphacaine com PyMuPDF. Nesses casos a evidência visual prevalece sobre uma correspondência textual automática ausente/inconsistente.
- Alguns PDFs, como Petivit BC, Atrovent, Proctyl, Dodoy e Salonpas, não apresentam a expressão literal `INFORMAÇÕES AO PACIENTE` nas primeiras páginas; os títulos das perguntas de paciente foram examinados. A ausência dessa expressão isolada não foi tratada como prova de documento profissional.
- Os metadados `Zone.Identifier` dos 93 downloads apontam para o domínio oficial do Bulário. São evidência local de procedência compatível com o download manual informado pelo usuário, não uma assinatura criptográfica da ANVISA nem uma nova consulta ao servidor. Não foram publicados tokens ou URLs assinadas.
- Não foram usados o parser/chunker do RAG, embeddings, modelos ou desempenho de recuperação para decidir os resultados desta conferência.
- Não foi feita comparação exaustiva de PDFs reempacotados com hashes diferentes, nem anotação completa de forma, concentração, população e tabelas de todos os documentos. Essas verificações continuam necessárias antes de congelar o corpus final.

## Próxima etapa

O lote já é numericamente suficiente para prosseguir à caracterização e seleção intencional de 50, mais piloto disjunto, **sem obrigatoriedade de completar todos os 100 nomes iniciais**. A fila inicial era exploratória. Confirmar a elegibilidade documental, excluir as cópias repetidas da seleção, resolver/substituir as três pendências documentais e manter os registros de origem e hashes antes de preencher `corpus_final.csv`.
