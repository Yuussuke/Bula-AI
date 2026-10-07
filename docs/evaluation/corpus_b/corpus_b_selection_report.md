# Corpus B — 50 bulas do paciente em cinco grupos recorrentes

Análise documental: 06/10/2026. Snapshot dos cadastros ANVISA: 05/10/2026.

**Coleção fechada: 5 grupos × 10 PDFs = 50 documentos elegíveis.** Foram conferidos 47 downloads novos e reutilizados três PDFs já confirmados nas reservas anteriores (Calmador, Cipramil e Ciprolip). Tenolon e Diurit foram baixados novamente: as cópias novas substituem as anteriores apenas nesta coleção, sem dupla contagem.

Corpus A e seu piloto permanecem intactos, com hashes dos quatro arquivos de seleção previamente registrados e reconferidos. Nenhum código de produção, parser, chunker, índice, prompt ou retrieval foi alterado. Não foram geradas perguntas/golds nem executados RAG, embeddings, judge, RAGAS ou chamadas pagas.

## 1. Por que estes cinco grupos

A seleção dos grupos foi fundamentada em utilização observada, não apenas em inclusão na Rename. Não é uma amostra epidemiologicamente representativa nem o ranking dos cinco grupos mais usados em 2026. Os dados populacionais são históricos (PNAUM 2013/2014, residentes urbanos); os percentuais abaixo têm denominadores específicos e não significam percentuais de todos os brasileiros.

| Grupo | Justificativa para a coleção | Evidência brasileira e fonte |
| --- | --- | --- |
| G1 — Anti-hipertensivos | Tratamento crônico recorrente; compartilhar indicações/precauções sem repetir a mesma molécula dez vezes. | Hidroclorotiazida 23,9% e losartana 20,1% dos fármacos anti-hipertensivos relatados; [Mengue et al., PNAUM, tabela 3](https://www.scielo.br/j/rsp/a/Q8rkJR7H3ZJXRSjqW4WfRLD/?lang=pt). |
| G2 — Antidiabéticos | Tratamento metabólico recorrente; incluir diferentes substâncias e uma associação. | Metformina 60,2% dos fármacos orais referidos por pessoas diabéticas com indicação de terapia; [Ministério da Saúde, PNAUM, tabela 7, página impressa 24](https://bvsms.saude.gov.br/bvs/publicacoes/componente_populacional_resultados_pnaum_caderno3.pdf). |
| G3 — Analgésicos/antitérmicos e AINEs sistêmicos | Uso sintomático recorrente; proximidade temática de dor/febre, sem reunir todos os anti-inflamatórios indiscriminadamente. | Analgésicos 33,4% e anti-inflamatórios/antirreumáticos 11,7% dos medicamentos de automedicação relatados; [Arrais et al., PNAUM, tabela 4](https://www.scielo.br/j/rsp/a/PNCVwkVMbZYwHvKN9b4ZxRh/?lang=pt). Isso não é prevalência de uso de AINEs na população inteira. |
| G4 — Antidepressivos | Grupo de tratamento crônico com sobreposição temática entre documentos. | Fluoxetina 19,2% e amitriptilina 12,9% dos fármacos referidos por pessoas com depressão e indicação de terapia; [Ministério da Saúde, PNAUM, tabela 16, páginas impressas 30–31](https://bvsms.saude.gov.br/bvs/publicacoes/componente_populacional_resultados_pnaum_caderno3.pdf). A tabela também contém outras classes: elas não foram automaticamente classificadas como antidepressivos. |
| G5 — Hipolipemiantes | Tratamento cardiometabólico recorrente; diferentes princípios ativos relacionados à redução de lipídios. | Sinvastatina 78,4% dos fármacos referidos para hipercolesterolemia com indicação de terapia; [Ministério da Saúde, PNAUM, tabela 10, página impressa 26](https://bvsms.saude.gov.br/bvs/publicacoes/componente_populacional_resultados_pnaum_caderno3.pdf). |

Como atualização complementar, a tabela 9 do [Anuário CMED 2024](https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/medicamentos/cmed/anuario-estatistico-do-mercado-farmaceutico-2024.pdf/@@download/file) inclui dipirona, losartana, metformina, ibuprofeno e sinvastatina entre as maiores quantidades comercializadas de embalagens. Volume industrial não equivale a prevalência de usuários. A [nota oficial de publicação](https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/cmed/informes/cmed-publica-o-anuario-estatistico-do-mercado-farmaceutico-2024) identifica o ano-base e a origem do levantamento.

As fontes justificam a recorrência dos **grupos**, não afirmam que todos os 50 alvos são igualmente frequentes nem os dez mais utilizados atualmente. Princípios ativos adicionais são alternativas cadastrais para compor a coleção temática.


## 2. Critérios e confirmação documental

A seleção preserva os cinco grupos e os 50 alvos da pré-seleção, sem consultar desempenho do sistema. G1 abrange anti-hipertensivos; G2 antidiabéticos orais; G3 analgésicos não opioides/antitérmicos e AINEs sistêmicos, incluindo apresentações injetáveis; G4 somente antidepressivos; G5 hipolipemiantes. A diversidade interna é secundária à pertença ao grupo, não uma nova otimização de heterogeneidade máxima.

Foram pesquisados 12 alvos cadastrais por grupo. Agora há dez PDFs elegíveis por grupo. As duas reservas adicionais de cada grupo continuam **candidatos cadastrais sem PDF confirmado**, não dez bulas elegíveis extras. A seleção foi intencional, não aleatória; não se alega que sejam os dez medicamentos mais usados de cada grupo.

A confirmação local combina: origem oficial do download manual preservada em Zone.Identifier (HostUrl de consultas.anvisa.gov.br); identificação de paciente e medicamento/apresentação no PDF; registro lido no documento e confrontado com produto, processo e detentor nos cadastros oficiais; abertura de todas as páginas; presença de texto nativo; SHA-256 e cópia íntegra arquivada. Não foram usados sites externos como confirmação final, nem contornados bloqueios. O link por registro é a consulta oficial reprodutível, não um endereço direto do PDF.

Todos os 50 PDFs abrem, contêm texto nativo em todas as páginas e são do paciente. Há 50 registros, 50 hashes de arquivo e 50 hashes de texto normalizado distintos. Nenhum coincide por registro ou hash com as 50 bulas do Corpus A ou seu piloto. As bulas não foram divididas, recortadas ou convertidas para compor o corpus.

Dois alertas automáticos foram resolvidos por inspeção documental: CB020 usa “INFORMAÇÃO AO PACIENTE” no singular; CB038 apresenta “Registro: – 1.0497.1526”. Não eram PDFs inelegíveis. O reconhecedor auxiliar não foi tratado como confirmação suficiente nem como parser de produção.

Nome e composição foram conferidos na identificação/composição. A coluna de princípio ativo no PDF usa denominação canônica para leitura, não transcrição quantitativa integral; o campo cadastral literal permanece separado no CSV. Sal/base equivalentes não foram contados como associação. Fabricante significa fabricação/produção explicitada, não importador, embalador ou detentor presumido. Em CB022 e CB025 essa função não está explícita: o fabricante fica vazio e o detentor oficial continua registrado. Quando o PDF admite fábricas alternativas, todas as explicitadas foram preservadas.

Tabelas relevantes são relações clínicas de posologia, administração ou reações adversas, não histórico de alterações nem caixas de prosa. A conferência combina estrutura geométrica, texto e inspeção visual das tabelas identificadas. Há cinco PDFs com tabelas clínicas. “Não” significa nenhuma tabela clínica identificada nessa revisão; não é medição do desempenho de reconhecimento de tabelas pelo RAG.

Limites: esta é confirmação documental dos arquivos baixados, **não uma nova consulta automatizada ao servidor de PDFs nem garantia de versão mais recente**. Texto extraível não assegura extração perfeita de ordem de leitura/tabelas. As páginas incluem capas, históricos e anexos. CB031 reúne, em um PDF intacto, duas bulas do paciente de fluoxetina (10/20 mg), contado uma vez; o número de arquivos e de folhas internas de apresentação não são conceitos equivalentes.

## 3. As 50 bulas selecionadas

A tabela abaixo e corpus_b_final.csv contêm as 50 selecionadas. Registros são links de consulta no Bulário; nomes de arquivo e hashes permitem identificar a cópia efetivamente conferida. Os CSVs também guardam páginas da identificação/fabricante/tabelas, população original, observações e caminho da cópia arquivada.

| ID | Grupo | Medicamento | Princípio ativo | Fabricante no PDF | Detentor do registro | Forma | Concentração; apresentação | População | Páginas | Associação | Tabela clínica | Registro / confirmação | PDF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| CB001 | G1 | losartana potássica | losartana | Eurofarma Laboratórios S.A. | EUROFARMA LABORATORIOS S.A. | Comprimido revestido | 50 mg; 30 ou 60 comprimidos | adulto | 10 | nao | nao | [100430911](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100430911) | bula_1791329435703.pdf |
| CB002 | G1 | HIDROCLOROTIAZIDA | hidroclorotiazida | EMS S/A; Novamed Fabricação de Produtos Farmacêuticos Ltda. | EMS S/A | Comprimido | 25 mg; 50 mg; 10, 20, 30, 40, 60 ou 500 comprimidos | ambos | 15 | nao | nao | [102350792](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=102350792) | bula_1791329439872.pdf |
| CB003 | G1 | CAPTOPRIL | captopril | Brasterapica Pharmaceutica Ltda. | BRASTERAPICA PHARMACEUTICA LTDA. | Comprimido | 25 mg; 30 comprimidos | adulto | 9 | nao | nao | [100380098](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100380098) | bula_1791329442902.pdf |
| CB004 | G1 | maleato de enalapril | enalapril | Laboratório Teuto Brasileiro S/A | LABORATÓRIO TEUTO BRASILEIRO S/A | Comprimido | 10 mg; 20 mg; 30 comprimidos | adulto | 11 | nao | nao | [103700442](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=103700442) | bula_1791329445649.pdf |
| CB005 | G1 | TENOLON | atenolol | Vitamedic Ind. Farmacêutica Ltda. | VITAMEDIC INDUSTRIA FARMACEUTICA LTDA | Comprimido | 25 mg; 50 mg; 100 mg; 25/50 mg: 28, 30, 280, 495 ou 504 comprimidos; 100 mg: 28, 30, 280 ou 495 comprimidos | adulto | 14 | nao | nao | [103920045](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=103920045) | bula_1791329448696.pdf |
| CB006 | G1 | besilato de anlodipino | anlodipino | Sandoz do Brasil Indústria Farmacêutica Ltda. | SANDOZ DO BRASIL INDÚSTRIA FARMACÊUTICA LTDA | Comprimido | 5 mg; 10 mg; 30 ou 60 comprimidos | adulto | 11 | nao | nao | [100470557](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100470557) | bula_1791329451238.pdf |
| CB007 | G1 | cloridrato de propranolol | propranolol | União Química Farmacêutica Nacional S/A; Anovis Industrial Farmacêutica Ltda. | UNIÃO QUÍMICA FARMACÊUTICA NACIONAL S/A | Comprimido | 40 mg; 30 comprimidos | ambos | 9 | nao | sim | [104971314](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=104971314) | bula_1791329461722.pdf |
| CB008 | G1 | DIURIT | furosemida | Cimed Indústria de Medicamentos Ltda. | 1FARMA INDUSTRIA FARMACEUTICA LTDA | Comprimido | 40 mg; 20 ou 500 comprimidos | ambos | 11 | nao | nao | [104810051](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=104810051) | bula_1791329499197.pdf |
| CB009 | G1 | NIFEDIPRESS | nifedipino | Medquímica Indústria Farmacêutica Ltda. | MEDQUIMICA INDUSTRIA FARMACEUTICA LTDA. | Comprimido revestido retard | 20 mg; 30 comprimidos | adulto | 7 | nao | nao | [109170034](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=109170034) | bula_1791329502750.pdf |
| CB010 | G1 | clortalidona | clortalidona | EMS S/A; Novamed Fabricação de Produtos Farmacêuticos Ltda. | GERMED FARMACEUTICA LTDA | Comprimido | 12,5 mg; 25 mg; 50 mg; 12,5/25 mg: 60, 75, 90 ou 500 comprimidos; 50 mg: 30, 60, 75, 90 ou 500 comprimidos | ambos | 11 | nao | nao | [105830801](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105830801) | bula_1791329506273.pdf |
| CB011 | G2 | CLORIDRATO DE METFORMINA | metformina | Merck S.A.; Merck Santé S.A.S | MERCK S/A | Comprimido de liberação prolongada | 500 mg; 750 mg; 1 g; 30 comprimidos | adulto | 15 | nao | nao | [100890379](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100890379) | bula_1791329509872.pdf |
| CB012 | G2 | Glibenclamida | glibenclamida | EMS S/A; Novamed Fabricação de Produtos Farmacêuticos Ltda. | EMS S/A | Comprimido | 5 mg; 30, 60 ou 450 comprimidos | adulto | 12 | nao | nao | [102350661](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=102350661) | bula_1791329513517.pdf |
| CB013 | G2 | gliclazida | gliclazida | Torrent Pharmaceuticals Ltd. | TORRENT DO BRASIL LTDA | Comprimido de liberação prolongada | 30 mg; 30 ou 60 comprimidos | adulto | 11 | nao | nao | [105250069](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105250069) | bula_1791329516988.pdf |
| CB014 | G2 | GLIMEPIRIDA | glimepirida | Eurofarma Argentina S.A.; Eurofarma Laboratórios S.A. | EUROFARMA LABORATORIOS S.A. | Comprimido | 2 mg; 4 mg; 30 comprimidos | adulto | 11 | nao | nao | [100431143](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100431143) | bula_1791329519793.pdf |
| CB015 | G2 | cloridrato de pioglitazona | pioglitazona | Aurobindo Pharma Limited | LABORATÓRIO TEUTO BRASILEIRO S/A | Comprimido | 15 mg; 30 mg; 15 mg: 30 comprimidos; 30 mg: 15 ou 30 comprimidos | adulto | 9 | nao | nao | [103700782](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=103700782) | bula_1791329522882.pdf |
| CB016 | G2 | dapagliflozina | dapagliflozina | Aché Laboratórios Farmacêuticos S.A. | ACHÉ LABORATÓRIOS FARMACÊUTICOS S.A | Comprimido revestido | 10 mg; 30 comprimidos | adulto | 10 | nao | nao | [105730186](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105730186) | bula_1791329525463.pdf |
| CB017 | G2 | empagliflozina | empagliflozina | EMS S/A; Novamed Fabricação de Produtos Farmacêuticos Ltda. | GERMED FARMACEUTICA LTDA | Comprimido revestido | 10 mg; 25 mg; 10 comprimidos | ambos | 9 | nao | nao | [105831024](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105831024) | bula_1791329528383.pdf |
| CB018 | G2 | fosfato de sitagliptina | sitagliptina | Sandoz Private Limited | SANDOZ DO BRASIL INDÚSTRIA FARMACÊUTICA LTDA | Comprimido revestido | 25 mg; 50 mg; 100 mg; 25 mg: 30 comprimidos; 50/100 mg: 30 ou 60 comprimidos | adulto | 6 | nao | nao | [100470660](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100470660) | bula_1791329531264.pdf |
| CB019 | G2 | vildagliptina | vildagliptina | Sun Pharmaceutical Industries Limited | RANBAXY FARMACÊUTICA LTDA | Comprimido | 50 mg; 30 ou 60 comprimidos | adulto | 10 | nao | nao | [123520293](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=123520293) | bula_1791329586213.pdf |
| CB020 | G2 | fosfato de sitagliptina + cloridrato de metformina | sitagliptina + metformina | Annora Pharma Private Limited | LABORATÓRIO GLOBO SA | Comprimido revestido | 50 mg + 1000 mg; 7, 14, 28 ou 56 comprimidos | adulto | 10 | sim | nao | [105350254](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105350254) | bula_1791329589987.pdf |
| CB021 | G3 | dipirona | dipirona monoidratada | Santisa Laboratório Farmacêutico S/A | SANTISA LABORATÓRIO FARMACÊUTICO S/A | Solução injetável | 500 mg/mL; 100 ampolas de 2 mL | ambos | 11 | nao | sim | [101860036](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=101860036) | bula_1791329599897.pdf |
| CB022 | G3 | PARACETAMOL | paracetamol | Não explicitado | EMS S/A | Pó para preparação extemporânea | 500 mg por sachê de 5 g; 1, 5, 10, 16, 20, 24, 25, 50, 80, 100 ou 120 sachês de 5 g | ambos | 6 | nao | nao | [102350764](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=102350764) | bula_1791329605125.pdf |
| CB023 | G3 | ibuprofeno | ibuprofeno | Laboratório Teuto Brasileiro S/A | LABORATÓRIO TEUTO BRASILEIRO S/A | Suspensão oral em gotas | 50 mg/mL; 1 frasco de 30 mL | ambos | 9 | nao | sim | [103700539](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=103700539) | bula_1791329608990.pdf |
| CB024 | G3 | naproxeno sodico | naproxeno | Eurofarma Laboratórios S.A. | EUROFARMA LABORATORIOS S.A. | Comprimido revestido | 550 mg; 10 ou 20 comprimidos | adulto | 8 | nao | sim | [100431565](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100431565) | bula_1791329613221.pdf |
| CB025 | G3 | DICLOFENACO SÓDICO | diclofenaco | Não explicitado | HALEX ISTAR INDÚSTRIA FARMACÊUTICA SA | Solução injetável | 25 mg/mL; 100 ampolas de 3 mL | adulto | 9 | nao | nao | [103110142](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=103110142) | bula_1791329617813.pdf |
| CB026 | G3 | NIMESULIDA | nimesulida | Vitamedic Ind. Farmacêutica Ltda. | VITAMEDIC INDUSTRIA FARMACEUTICA LTDA | Comprimido | 100 mg; 12, 492 ou 504 comprimidos | ambos | 10 | nao | nao | [103920174](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=103920174) | bula_1791329621948.pdf |
| CB027 | G3 | meloxicam | meloxicam | Cellera Farmacêutica S.A. | CELLERA FARMACEUTICA S.A. | Comprimido | 15 mg; 10 comprimidos | ambos | 10 | nao | nao | [104400213](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=104400213) | bula_1791329625718.pdf |
| CB028 | G3 | CETOPROFENO | cetoprofeno | Cristália Produtos Químicos Farmacêuticos Ltda. | CRISTÁLIA PRODUTOS QUÍMICOS FARMACÊUTICOS LTDA. | Solução injetável | 50 mg/mL; 6 ou 25 ampolas de 2 mL | adulto | 17 | nao | nao | [102980276](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=102980276) | bula_1791329629038.pdf |
| CB029 | G3 | trometamol cetorolaco | cetorolaco | União Química Farmacêutica Nacional S/A | UNIÃO QUÍMICA FARMACÊUTICA NACIONAL S/A | Comprimido sublingual | 10 mg; 10 ou 20 comprimidos | adulto | 10 | nao | sim | [104971520](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=104971520) | bula_1791329632161.pdf |
| CB030 | G3 | CALMADOR | ácido acetilsalicílico + cafeína | Laboratório Saúde Ltda. | LABORATÓRIO SAÚDE LTDA | Comprimido | Ácido acetilsalicílico 500 mg + cafeína 30 mg; 25 envelopes de 4 comprimidos | adulto | 10 | sim | nao | [100490106](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100490106) | bula_1791246726579.pdf |
| CB031 | G4 | cloridrato de fluoxetina | fluoxetina | Eurofarma Laboratórios S.A. | EUROFARMA LABORATORIOS S.A. | Cápsula dura | 10 mg; 20 mg; 10 mg: 28 cápsulas; 20 mg: 28, 30 ou 60 cápsulas | adulto | 16 | nao | nao | [100431159](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100431159) | bula_1791329635147.pdf |
| CB032 | G4 | cloridrato de amitriptilina | amitriptilina | Cristália Produtos Químicos Farmacêuticos Ltda. | INSTITUTO BIOCHIMICO INDÚSTRIA FARMACÊUTICA LTDA | Comprimido revestido | 25 mg; 75 mg; 30 comprimidos | ambos | 8 | nao | nao | [100630267](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100630267) | bula_1791329638185.pdf |
| CB033 | G4 | CLORIDRATO DE SERTRALINA | sertralina | EMS S/A; Novamed Fabricação de Produtos Farmacêuticos Ltda. | EMS S/A | Comprimido revestido | 50 mg; 100 mg; 50 mg: 10, 14, 20, 28, 30, 40, 60, 450 ou 500 comprimidos; 100 mg: 10, 14, 20, 28, 30, 40, 60 ou 500 comprimidos | ambos | 12 | nao | nao | [102350700](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=102350700) | bula_1791329641140.pdf |
| CB034 | G4 | CIPRAMIL | bromidrato de citalopram | H. Lundbeck A/S | LUNDBECK BRASIL LTDA | Comprimido revestido | 20 mg de citalopram; 28 comprimidos | adulto | 13 | nao | nao | [104750043](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=104750043) | bula_1791247042757.pdf |
| CB035 | G4 | CLORIDRATO DE PAROXETINA | paroxetina | Laboratório Teuto Brasileiro S/A | LABORATÓRIO TEUTO BRASILEIRO S/A | Comprimido revestido | 20 mg; 30 comprimidos | adulto | 12 | nao | nao | [103700704](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=103700704) | bula_1791329644445.pdf |
| CB036 | G4 | cloridrato de venlafaxina | venlafaxina | Torrent Pharmaceuticals Ltd. | TORRENT DO BRASIL LTDA | Cápsula dura de liberação prolongada | 37,5 mg; 75 mg; 150 mg; 30 cápsulas | adulto | 13 | nao | nao | [105250068](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105250068) | bula_1791329687037.pdf |
| CB037 | G4 | oxalato de escitalopram | escitalopram | Sandoz Private Limited; Salutas Pharma GmbH | SANDOZ DO BRASIL INDÚSTRIA FARMACÊUTICA LTDA | Comprimido revestido | 10 mg; 15 mg; 20 mg; 10/20 mg: 30 ou 60 comprimidos; 15 mg: 30 comprimidos | adulto | 13 | nao | nao | [100470574](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100470574) | bula_1791329690930.pdf |
| CB038 | G4 | cloridrato de duloxetina | duloxetina | Anovis Industrial Farmacêutica Ltda. | UNIÃO QUÍMICA FARMACÊUTICA NACIONAL S/A | Cápsula dura de liberação retardada | 30 mg; 60 mg; 30 ou 60 cápsulas | adulto | 13 | nao | nao | [104971526](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=104971526) | bula_1791329694894.pdf |
| CB039 | G4 | mirtazapina | mirtazapina | Sandoz do Brasil Indústria Farmacêutica Ltda. | NOVARTIS BIOCIENCIAS S.A | Comprimido revestido | 30 mg; 45 mg; 30 comprimidos | adulto | 8 | nao | nao | [100681146](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100681146) | bula_1791329698726.pdf |
| CB040 | G4 | cloridrato de trazodona | trazodona | Zydus Lifesciences Limited | LABORATÓRIO GLOBO SA | Comprimido | 50 mg; 100 mg; 50 mg: 60 comprimidos; 100 mg: 30 comprimidos | adulto | 13 | nao | nao | [105350238](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105350238) | bula_1791329702857.pdf |
| CB041 | G5 | SINVASTATINA | sinvastatina | Sandoz do Brasil Indústria Farmacêutica Ltda. | SANDOZ DO BRASIL INDÚSTRIA FARMACÊUTICA LTDA | Comprimido revestido | 10 mg; 20 mg; 40 mg; 10/40 mg: 30 comprimidos; 20 mg: 30 ou 150 comprimidos | adulto | 6 | nao | nao | [100470472](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100470472) | bula_1791329706258.pdf |
| CB042 | G5 | ATORVASTATINA CÁLCICA | atorvastatina | Eurofarma Laboratórios S.A. | EUROFARMA LABORATORIOS S.A. | Comprimido revestido | 10 mg; 20 mg; 40 mg; 30 comprimidos | ambos | 7 | nao | nao | [100431137](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100431137) | bula_1791329709865.pdf |
| CB043 | G5 | rosuvastatina cálcica | rosuvastatina | Novartis Pharmaceutical Manufacturing LLC; Lek S.A. | NOVARTIS BIOCIENCIAS S.A | Comprimido revestido | 10 mg; 20 mg; 30 comprimidos | ambos | 9 | nao | nao | [100681144](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=100681144) | bula_1791329713235.pdf |
| CB044 | G5 | CIPROLIP | ciprofibrato | UCI-Farma Indústria Farmacêutica Ltda. | UCI - FARMA INDÚSTRIA FARMACÊUTICA LTDA | Comprimido | 100 mg; 30 comprimidos | adulto | 7 | nao | nao | [105500172](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105500172) | bula_1791247123073.pdf |
| CB045 | G5 | ezetimiba + sinvastatina | ezetimiba + sinvastatina | EMS S/A; Novamed Fabricação de Produtos Farmacêuticos Ltda. | EMS S/A | Comprimido | 10 mg + 10 mg; 10 mg + 20 mg; 10 mg + 40 mg; 10, 15, 20, 30, 60, 100, 200 ou 500 comprimidos | ambos | 12 | sim | nao | [102351139](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=102351139) | bula_1791329715920.pdf |
| CB046 | G5 | fenofibrato | fenofibrato | Torrent Pharmaceuticals Ltd. | TORRENT DO BRASIL LTDA | Comprimido revestido | 160 mg; 30 comprimidos | adulto | 8 | nao | nao | [105250112](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105250112) | bula_1791329719056.pdf |
| CB047 | G5 | EZETIMIBA | ezetimiba | Watson Pharma Private Limited | BIOLAB SANUS FARMACÊUTICA LTDA | Comprimido | 10 mg; 30 ou 60 comprimidos | ambos | 6 | nao | nao | [109740297](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=109740297) | bula_1791329721812.pdf |
| CB048 | G5 | bezafibrato | bezafibrato | EMS S/A; Novamed Fabricação de Produtos Farmacêuticos Ltda. | GERMED FARMACEUTICA LTDA | Comprimido revestido | 200 mg; 10, 20, 30, 60, 90, 450 ou 500 comprimidos | adulto | 7 | nao | nao | [105830883](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=105830883) | bula_1791329724624.pdf |
| CB049 | G5 | genfibrozila | genfibrozila | CPM Concessionária Paulista de Medicamentos S/A | FUNDAÇÃO PARA O REMÉDIO POPULAR - FURP | Comprimido revestido | 600 mg; 900 mg; 600 mg: 24 comprimidos; 900 mg: 12 comprimidos | adulto | 6 | nao | nao | [110390189](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=110390189) | bula_1791329727134.pdf |
| CB050 | G5 | Pravastatina Sódica | pravastatina | Intas Pharmaceuticals Ltd. | ACCORD FARMACÊUTICA LTDA | Comprimido | 10 mg; 20 mg; 40 mg; 10 ou 30 comprimidos | ambos | 15 | nao | nao | [155370006](https://consultas.anvisa.gov.br/#/bulario/q/?numeroRegistro=155370006) | bula_1791329730305.pdf |

### Listas por grupo

### G1 — Anti-hipertensivos

CB001: Losartana; CB002: Hidroclorotiazida; CB003: Captopril; CB004: Enalapril; CB005: Atenolol; CB006: Anlodipino; CB007: Propranolol; CB008: Furosemida; CB009: Nifedipino; CB010: Clortalidona.

Detentores: 10; páginas: 7–15; adulto/ambos: 6/4; tabelas clínicas: 1.

### G2 — Antidiabéticos

CB011: Metformina; CB012: Glibenclamida; CB013: Gliclazida; CB014: Glimepirida; CB015: Pioglitazona; CB016: Dapagliflozina; CB017: Empagliflozina; CB018: Sitagliptina; CB019: Vildagliptina; CB020: Sitagliptina + metformina.

Detentores: 10; páginas: 6–15; adulto/ambos: 9/1; tabelas clínicas: 0.

### G3 — Analgésicos/antitérmicos e AINEs sistêmicos

CB021: Dipirona; CB022: Paracetamol; CB023: Ibuprofeno; CB024: Naproxeno; CB025: Diclofenaco; CB026: Nimesulida; CB027: Meloxicam; CB028: Cetoprofeno; CB029: Cetorolaco; CB030: Ácido acetilsalicílico + cafeína.

Detentores: 10; páginas: 6–17; adulto/ambos: 5/5; tabelas clínicas: 4.

### G4 — Antidepressivos

CB031: Fluoxetina; CB032: Amitriptilina; CB033: Sertralina; CB034: Citalopram; CB035: Paroxetina; CB036: Venlafaxina; CB037: Escitalopram; CB038: Duloxetina; CB039: Mirtazapina; CB040: Trazodona.

Detentores: 10; páginas: 8–16; adulto/ambos: 8/2; tabelas clínicas: 0.

### G5 — Hipolipemiantes

CB041: Sinvastatina; CB042: Atorvastatina; CB043: Rosuvastatina; CB044: Ciprofibrato; CB045: Ezetimiba + sinvastatina; CB046: Fenofibrato; CB047: Ezetimiba; CB048: Bezafibrato; CB049: Genfibrozila; CB050: Pravastatina.

Detentores: 10; páginas: 6–15; adulto/ambos: 5/5; tabelas clínicas: 0.

## 4. Diversidade documental obtida

| Indicador | Resultado |
| --- | ---: |
| Documentos / grupos / documentos por grupo | 50 / 5 / 10 |
| Páginas totais / mínimo / máximo | 515 / 6 / 17 |
| Associações de princípios ativos | 3 |
| Princípio ativo único | 47 |
| Com tabelas clínicas | 5 |
| Sem tabela clínica identificada | 45 |
| Múltiplas concentrações no mesmo PDF | 24 |
| Múltiplas concentrações e/ou apresentações | 37 |
| Denominações de forma/liberação documentadas | 11 |
| Fabricantes distintos explicitados | 33 |
| PDFs sem função de fabricação explicitada | 2 |
| Detentores distintos (CNPJ) | 27 |
| Sobreposição de registro/hash com Corpus A e piloto | 0 |

### Tamanho relativo das bulas

Calculado apenas sobre estas 50 bulas: quantis de 1/3 e 2/3 por interpolação linear na série ordenada, posição (n−1)×p. Os limites são **9 e 11 páginas**: curta ≤ 9; média > 9 e ≤ 11; longa > 11. Empates permanecem juntos, por isso não se forçam três grupos com contagens iguais. São categorias relativas a B, não pontos de corte clínicos nem os limites do Corpus A.

| Tamanho | Bulas |
| --- | ---: |
| média | 15 |
| longa | 15 |
| curta | 20 |

### População

| População | Bulas |
| --- | ---: |
| adulto | 33 |
| ambos | 17 |

Não há documento exclusivamente pediátrico. “Ambos” considera o documento completo: algumas concentrações podem ser adultas e outras pediátricas. Isso não autoriza generalizar a população de uma concentração a todas as outras. As linhas originais de uso estão preservadas no CSV.

### Formas farmacêuticas

| Denominação documental de forma/liberação | Bulas |
| --- | ---: |
| Comprimido revestido | 18 |
| Comprimido | 20 |
| Comprimido revestido retard | 1 |
| Comprimido de liberação prolongada | 2 |
| Solução injetável | 3 |
| Pó para preparação extemporânea | 1 |
| Suspensão oral em gotas | 1 |
| Comprimido sublingual | 1 |
| Cápsula dura | 1 |
| Cápsula dura de liberação prolongada | 1 |
| Cápsula dura de liberação retardada | 1 |

Essas denominações distinguem liberação prolongada/retardada e via/apresentação quando a fonte distingue; não se afirma que sejam 11 classes terapêuticas ou formas básicas independentes. A predominância oral foi aceita porque o critério primário é temático.

### Fabricantes

1. Aché Laboratórios Farmacêuticos S.A.
2. Annora Pharma Private Limited
3. Anovis Industrial Farmacêutica Ltda.
4. Aurobindo Pharma Limited
5. Brasterapica Pharmaceutica Ltda.
6. CPM Concessionária Paulista de Medicamentos S/A
7. Cellera Farmacêutica S.A.
8. Cimed Indústria de Medicamentos Ltda.
9. Cristália Produtos Químicos Farmacêuticos Ltda.
10. EMS S/A
11. Eurofarma Argentina S.A.
12. Eurofarma Laboratórios S.A.
13. H. Lundbeck A/S
14. Intas Pharmaceuticals Ltd.
15. Laboratório Saúde Ltda.
16. Laboratório Teuto Brasileiro S/A
17. Lek S.A.
18. Medquímica Indústria Farmacêutica Ltda.
19. Merck S.A.
20. Merck Santé S.A.S
21. Novamed Fabricação de Produtos Farmacêuticos Ltda.
22. Novartis Pharmaceutical Manufacturing LLC
23. Salutas Pharma GmbH
24. Sandoz Private Limited
25. Sandoz do Brasil Indústria Farmacêutica Ltda.
26. Santisa Laboratório Farmacêutico S/A
27. Sun Pharmaceutical Industries Limited
28. Torrent Pharmaceuticals Ltd.
29. UCI-Farma Indústria Farmacêutica Ltda.
30. União Química Farmacêutica Nacional S/A
31. Vitamedic Ind. Farmacêutica Ltda.
32. Watson Pharma Private Limited
33. Zydus Lifesciences Limited

Fabricantes são contados individualmente quando há alternativas explícitas; detentores pelo CNPJ. Um mesmo PDF pode contribuir com mais de uma fábrica. Ausência do campo não foi preenchida a partir do cadastro. Não confundir 33 fabricantes explicitados com 27 detentores.

## 5. Justificativa metodológica e limites

Corpus A privilegia diversidade documental. Corpus B privilegia concentração intencional em cinco grupos de uso recorrente, com dez substâncias/composições por grupo e alguma variação de fabricante, extensão, concentração, população e estrutura. São coleções complementares, não intercambiáveis nem amostras nacionais de consumo.

Bulário e composição documental fundamentam elegibilidade/identidade; estudos brasileiros justificam a escolha dos grupos. As fontes não tornam todos os 50 produtos igualmente comuns. A proximidade semântica é uma hipótese operacionalizada pela pertença temática, não medida por embeddings nesta tarefa.

Vários medicamentos relacionados podem compartilhar indicações, precauções e termos de administração, exigindo distinguir evidência entre documentos. Isso pode tornar a recuperação mais desafiadora, mas não foi demonstrado aqui. O desenho permite comparar BM25, dense e híbrido em dois cenários sem selecionar documentos pelo desempenho. Se a avaliação recuperar apenas dentro de uma bula por pergunta, a dificuldade interdocumental não será automaticamente avaliada e essa delimitação deverá constar do protocolo.

## 6. Arquivos e preservação

- corpus_b_final.csv: **manifesto canônico das 50 selecionadas**, com caracterização, confirmação e rastreabilidade.
- `corpus_b_candidates.csv`, `corpus_b_preselection.csv` e `corpus_b_eligible.csv` permanecem como registros locais de preparação. Os dois últimos duplicam a coleção final nesta etapa e não são publicados; a fila de 60 candidatos tampouco é outro corpus.

Os CSVs são UTF-8 com BOM. Importar IDs, registro, processo e CNPJ **como texto**. Célula vazia de fabricante significa função não explicitada, não nome inferido; campos documentais vazios nas dez reservas significam não examinados.

Cópias intactas estão em backend/tmp/anvisa-bulas-v2/corpus-20261005/pdfs/corpus-b/CBxxx/. Essa pasta é temporária/ignorada pelo Git: **fazer backup fora de tmp antes de limpar o ambiente**. Downloads originais não foram removidos. A origem ANVISA e as datas são descritas no manifesto; hashes identificam as versões preservadas.

Fontes oficiais de metadados: [produtos do Bulário](https://dados.anvisa.gov.br/dados/CONSULTAS/DOCUMENTOS/TA_CONSULTA_BULA_PRODUTO.CSV), [medicamentos](https://dados.anvisa.gov.br/dados/DADOS_ABERTOS_MEDICAMENTOS.csv) e [apresentações](https://dados.anvisa.gov.br/dados/CONSULTAS/PRODUTOS/TA_CONSULTA_MEDICAMENTOS.CSV), snapshot de 05/10/2026. Metadados de cadastro e características do PDF permanecem separados.

A etapa para aqui: **nenhuma avaliação ou ingestão do RAG foi iniciada**.


Na cópia publicada, somente a coluna `caminho_pdf_original` foi omitida para não versionar caminhos pessoais absolutos. Identidades, nomes de arquivo, SHA-256 e todas as demais anotações foram preservados. A referência relativa `caminho_pdf_arquivado` identifica um arquivo local, não um PDF versionado no Git.
