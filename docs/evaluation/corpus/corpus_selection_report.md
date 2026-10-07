# Corpus de 50 bulas — seleção por diversidade documental

Data: 2026-10-05. Unidade de seleção: um PDF único, preservado por SHA-256. Nenhum RAG, embedding, chamada ao modelo ou avaliação de desempenho foi executado nesta seleção.

## 1. Elegibilidade e origem

O lote manual contém 93 downloads, 91 hashes distintos e 88 PDFs elegíveis. Foram retiradas duas cópias duplicadas, dois PDFs integralmente digitalizados (Forteviron e LQFEX-Cloroquina) e Alphacaine, que permanece fora por divergência entre registro impresso e cadastro. Nove candidatas da fila original não foram reconfirmadas no lote, incluindo a amoxicilina histórica C001. Restam 50 no corpus, um piloto e 37 reservas elegíveis.

Confirmação documental: arquivos baixados manualmente pelo usuário do Bulário; a informação de origem dos downloads aponta para consultas.anvisa.gov.br. Identificação do paciente, nome/registro e conteúdo foram confrontados com os PDFs e os cadastros oficiais já arquivados. Isso não representa uma nova consulta automatizada bem-sucedida ao servidor de PDFs, nem garante que estes sejam a versão mais recente em uma data futura. O bloqueio automatizado anterior não foi contornado. Os links de consulta por registro estão nos CSVs.

Todos os 88 elegíveis abrem e têm texto nativo extraível em todas as páginas. Inspeção visual complementou a leitura textual, especialmente para tabelas e glifos. Não se exigiu acerto do parser da aplicação. PDFs originais não foram modificados; as 51 cópias selecionadas/piloto foram arquivadas, com hashes conferidos, em backend/tmp/anvisa-bulas-v2/corpus-20261005/pdfs/. Essa pasta é ignorada pelo Git: fazer backup do acervo antes de limpar temporários.

## 2. Campos e limites da anotação

- Nome, formas, concentrações, embalagens, população, associações, fabricante e tabelas foram anotados a partir do PDF. Páginas de identificação/fabricação/tabelas estão nos CSVs; as restrições etárias literais estão em populacao_original_pdf.
- Fabricante não é automaticamente detentor do registro. Quando a função de fabricação não é explicitada, fabricante fica vazio e detentor_registro permanece separado. Há 5 documentos selecionados nessa situação: B016, B025, B026, B040, B047.
- Grupo terapêutico é o rótulo do cadastro oficial de medicamentos, identificado por fonte_grupo_terapeutico; é informação complementar, não uma classe inventada do PDF. C059 não tem esse campo identificado na fonte consultada. Rótulos não são uma taxonomia clínica independente.
- Associação é definida pela composição ativa, sem contar excipientes. Nimenrix é preparação vacinal multicomponente, discriminada no resumo. Um soro contra vários alvos não foi automaticamente considerado associação de fármacos.
- Uma concentração expressa por mL e por dose não é duas concentrações. Variações de embalagem contam apresentações; diferentes concentrações/formas no mesmo PDF contam múltiplas apresentações. Diluição e excedente de fabricação não foram inventados como novas versões comerciais.
- Tabelas relevantes são estruturas relacionais de orientação/composição clínica, dose, população, interação ou eventos adversos. Não contam o histórico administrativo, simples listas com pontilhado nem quadros que apenas posicionam ilustrações.
- Páginas são a extensão integral do PDF, incluindo capa, histórico e anexos. Algumas bulas reúnem formas ou marcas relacionadas no mesmo arquivo; não foram divididas para inflar a contagem. Categorias são sobrepostas.

## 3. Tamanho relativo e seleção

Os tercis foram calculados na distribuição real dos 88 elegíveis, antes da escolha do piloto e das 50: quantil com interpolação linear na posição (n−1)×p. Q1/3 = 8 páginas; Q2/3 = 12 páginas. Curtas: até 8; médias: 9–12; longas: 13 ou mais. Empates ficam juntos: o lote elegível tem 37 curtas, 24 médias e 27 longas.

A seleção é intencional de máxima variação, não probabilística nem uma otimização matemática comprovada. Primeiro preservou combinações de extensão, formas/vias/preparo, composição, população, presença/ausência e tipos de tabelas, e multiplicidade de apresentações; depois completou a cobertura de fabricantes. Grupo terapêutico foi somente desempate secundário, sem cotas clínicas. São preservadas as 44 descrições documentais de forma/via/preparo observadas no lote; essas descrições não equivalem a 44 classes farmacopéicas independentes. Nenhuma escolha usa desempenho do sistema.

Exemplos de variação: Prolopa reúne formas/liberações e 50 páginas; Arnica reúne gotas, glóbulos e comprimidos; Dianeal tem tabela ampla de formulações e continuação multipágina; Dodoy possui tabela pediátrica com bordas horizontais; Sporanox possui regimes/ciclos e células mescladas; há documentos sem tabelas clínicas e exemplares de duas páginas. Casos mais redundantes em forma/tamanho/estrutura permanecem na reserva, sem julgamento de desempenho.

## 4. Resumo das 50

| Dimensão | Resultado |
| --- | --- |
| Extensão | 17 curtas; 16 médias; 17 longas; 2–50 páginas |
| Formas/vias/preparo descritos | 44; tabela de frequência abaixo |
| Composição | 18 multicomponentes: 17 associações não vacinais + 1 vacina multicomponente; 32 de princípio ativo/preparação única |
| População declarada | 19 adulto; 1 pediátrico; 30 ambos |
| Tabelas relevantes | 15 com; 35 sem |
| Concentrações | 15 com múltiplas; 35 com uma |
| Apresentações | 30 com múltiplas; 20 com uma |
| Fabricantes explicitados | 51 nomes distintos em 45 PDFs; 5 não explicitados |
| Detentores cadastrais | 50 CNPJs distintos; não equivalem automaticamente a fabricantes |
| Grupos terapêuticos | 49 rótulos oficiais distintos; 1 documento sem grupo identificado |

Há só uma bula exclusivamente pediátrica no lote elegível, Camomilina C; ela foi incluída. Não foi criado equilíbrio artificial adulto/pediátrico. A contagem ambos preserva o que o PDF declara, inclusive apresentações para crianças e outras para adultos no mesmo documento.

## 5. Tabela das 50

Concentrações de associações são lidas conjuntamente; não representam doses recomendadas. A tabela é caracterização documental, não orientação de uso. C/A = quantidade de concentrações/apresentações.

| ID (candidata) | Medicamento | Fabricante no PDF | Forma(s) | Concentração; apresentação | Páginas / tamanho | Ativos | População | Tabelas relevantes | C/A | Grupo cadastral secundário |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B001 (C002) | SINGULAIR | Organon Pharma (UK) Ltd. | Comprimido mastigável; Comprimido revestido | 4 mg; 5 mg; 10 mg; 30 comprimidos por concentração | 9 / média | Único | ambos | Não | Múltiplas / Múltiplas | ANTIASMATICOS |
| B002 (C005) | SOLUÇÃO GLICOFISIOLÓGICA | Fresenius Kabi Brasil Ltda. | Solução injetável | Cloreto de sódio 9 mg/mL + glicose 50 mg/mL; Frascos 250/500/1000 mL | 9 / média | Associação | ambos | Não | Uma / Múltiplas | REIDRATANTES PARENTERAIS |
| B003 (C006) | CLORIDRATO DE DOXORRUBICINA | Eurofarma Laboratórios S.A. | Pó liofilizado para solução injetável | 50 mg; 1/10 frascos-ampola | 10 / média | Único | ambos | Não | Uma / Múltiplas | ANTIBIOTICOS ANTINEOPLASICOS |
| B004 (C007) | TRILAX | Sandoz do Brasil Indústria Farmacêutica Ltda. | Comprimido | Paracetamol 300 mg + carisoprodol 125 mg + diclofenaco sódico 50 mg + cafeína 30 mg; 12/30 comprimidos | 12 / média | Associação | adulto | Não | Uma / Múltiplas | ANTINFLAMATORIOS |
| B005 (C009) | Fluibron A / Fluibron | Chiesi Farmaceutici S.p.A.; Zambon Laboratórios Farmacêuticos Ltda. | Solução inalatória; Solução oral em gotas | 7,5 mg/mL; 10 flaconetes de 2 mL; frasco de 50 mL (oral ou inalatória) | 17 / longa | Único | ambos | Não | Uma / Múltiplas | EXPECTORANTES SIMPLES |
| B006 (C010) | ARNICA WELEDA | Weleda do Brasil - Laboratório e Farmácia Ltda. | Solução oral em gotas; Glóbulos; Comprimido | Arnica montana D3: gotas 1000 mg/mL; glóbulos 80 mg/g; comprimido 185 mg; Gotas: 50 mL; glóbulos: 20 g; comprimidos: 80 unidades | 17 / longa | Único | ambos | Não | Múltiplas / Múltiplas | MEDICAMENTOS DINAMIZADOS DE COMPONENTE ÚNICO |
| B007 (C011) | AMPLOSPEC | Instituto BioChimico Indústria Farmacêutica Ltda. | Pó para solução injetável | 1 g de ceftriaxona; 50 frascos-ampola | 16 / longa | Único | ambos | Sim: Reconstituição/concentração e reações adversas | Uma / Uma | CEFALOSPORINAS |
| B008 (C014) | hemitartarato de rivastigmina | Laborvida Laboratórios Farmacêuticos Ltda. | Cápsula dura | 1,5 mg; 3 mg; 4,5 mg; 6 mg de rivastigmina; 30/60/600 cápsulas | 10 / média | Único | adulto | Sim: Faixas de frequência de reações adversas | Múltiplas / Múltiplas | OUTROS PRODUTOS QUE ATUAM SOBRE O SISTEMA NERVOSO |
| B009 (C016) | LIPOFUNDIN | B. Braun Melsungen AG | Emulsão injetável | Por 100 mL: óleo de soja 10 g + triglicerídeos de cadeia média 10 g (20%); 10 frascos de 100/500 mL | 12 / média | Associação | ambos | Não | Uma / Múltiplas | NUTRIENTES PARENTERAIS |
| B010 (C018) | Prolopa DR / dispersível / BD / HBS | Skyepharma Production SAS; Delpharm Milano S.R.L.; Recipharm Leganés S.L.U.; Produtos Roche Químicos e Farmacêuticos S.A. | Comprimido de liberação modificada; Comprimido dispersível; Comprimido; Cápsula de liberação prolongada | Levodopa + benserazida: 200 mg + 50 mg (250 mg); 100 mg + 25 mg (125 mg); DR 250 mg; dispersível 125 mg; simples 250/125 mg; HBS 125 mg; 30 unidades por embalagem | 50 / longa | Associação | adulto | Não | Múltiplas / Múltiplas | ANTIPARKINSONIANOS |
| B011 (C019) | AMOXIL | Glaxo Wellcome Production | Cápsula dura; Pó para suspensão oral | Cápsula 500 mg; suspensão 50/100 mg/mL; 15/21/30 cápsulas; frasco de suspensão 150 mL + colher | 21 / longa | Único | ambos | Não | Múltiplas / Múltiplas | PENICILINA DE AMPLO ESPECTRO |
| B012 (C020) | OTO - XILODASE | Apsen Farmacêutica S.A. | Solução otológica; Pó para reconstituição | Por mL reconstituído: hialuronidase 100 UTR + lidocaína HCl 50 mg + sulfato de neomicina 5 mg; Solução 8 mL + ampola 800 UTR | 9 / média | Associação | ambos | Não | Uma / Uma | ANTINFECCIOSOS TOPICOS-ASSOCIACOES MEDICAMENTOSAS |
| B013 (C021) | MALVATRICIN | Megalabs Farmacêutica S.A. | Solução bucal; Solução bucal em spray | PPU: tirotricina 0,1 + hidroxiquinolina 1 mg/mL; concentrada: 0,3 + 10 mg/mL; spray: 0,1 + 2 + lidocaína 4 mg/mL; PPU 100/250 mL; concentrada 100 mL; spray 50 mL | 15 / longa | Associação | ambos | Não | Múltiplas / Múltiplas | DEMULCENTES E OUTROS MEDS. USO ORAL P/ TRATAM. OROFARINGE |
| B014 (C023) | Pred Fort / Pred Mild | Allergan Produtos Farmacêuticos Ltda. | Suspensão oftálmica | Pred Fort 10 mg/mL; Pred Mild 1,2 mg/mL; Fort: 5 mL; Mild: 5/10 mL | 26 / longa | Único | adulto | Não | Múltiplas / Múltiplas | GLICOCORTICOIDES TOPICO OFTALMOLOGICO SIMPLES |
| B015 (C024) | FIBROGAMMIN P | CSL Behring GmbH | Pó liofilizado para solução injetável | 250 UI; 62,5 UI/mL após reconstituição; Frasco + diluente 4 mL + dispositivo de transferência | 17 / longa | Único | ambos | Sim: Ajuste de dose segundo atividade de fator XIII | Uma / Uma | OUTROS PRODUTOS ANTI-HEMORRAGICOS |
| B016 (C026) | IMUNO  BCG | Não explicitado | Pó liofilizado para suspensão intravesical | BCG 40 mg (> 2,0 x 10^6 UFC/mg); 1/2 ampolas | 4 / curta | Único | ambos | Não | Uma / Múltiplas | IMUNOESTIMULANTES |
| B017 (C028) | CAPSFEN | Catalent Brasil Ltda. | Cápsula mole | 600 mg; 10 cápsulas | 9 / média | Único | adulto | Não | Uma / Uma | ANTINFLAMATORIOS ANTIREUMATICOS |
| B018 (C031) | LAFEPE BENZNIDAZOL | Laboratório Farmacêutico do Estado de Pernambuco S.A. - LAFEPE | Comprimido | 12,5 mg; 100 mg; 12,5 mg: 240 comprimidos + copo; 100 mg: 100 comprimidos | 5 / curta | Único | ambos | Sim: Posologia pediátrica por peso | Múltiplas / Múltiplas | ANTIPARASITARIOS |
| B019 (C032) | GENTAMISAN | Santisa Laboratório Farmacêutico S.A. | Solução injetável | 40 mg/mL; 100 ampolas de 1/2 mL | 9 / média | Único | ambos | Não | Uma / Múltiplas | AMINOGLICOSIDEOS |
| B020 (C033) | MONOFER | Wasserburger Arzneimittelwerk GmbH | Solução para infusão | 100 mg de ferro/mL; 1 frasco-ampola de 5/10 mL | 6 / curta | Único | adulto | Não | Uma / Múltiplas | ANTIANEMICOS SIMPLES |
| B021 (C034) | CAMOMILINA C | Theraskin Farmacêutica Ltda. | Cápsula | Matricaria 25 mg + Glycyrrhiza 5 mg + vitamina C 25 mg + vitamina D3 150 UI; 20 cápsulas; conteúdo aplicado por via bucal | 7 / curta | Associação | pediátrico | Não | Uma / Uma | VITAMINAS OU MINERAIS ASSOCIADOS A OUTROS FARMACOS |
| B022 (C035) | piperacilina sódica + tazobactam sódico | Qilu Tianhe Pharmaceutical Ltd. | Pó liofilizado para solução injetável | Piperacilina 4 g + tazobactam 0,5 g; 1/10 frascos-ampola | 4 / curta | Associação | ambos | Sim: Ajustes renais adulto e pediátrico | Uma / Múltiplas | PENICILINAS PENICILINASE-RESISTENTES |
| B023 (C036) | TIMEOLATE | Laboratório Tayuyna Ltda. | Solução tópica em spray | Lidocaína HCl 21 mg/mL + benzetônio 1,33 mg/mL; Frasco 30 mL com válvula | 7 / curta | Associação | ambos | Não | Uma / Uma | ANTISSEPTICO |
| B024 (C037) | NIMENRIX | Pfizer Manufacturing Belgium NV | Pó liofilizado para solução injetável | Polissacarídeos A/C/W-135/Y: 5 mcg cada por dose de 0,5 mL; Frasco + seringa de diluente 0,5 mL + 2 agulhas | 14 / longa | Associação | ambos | Sim: Calendário de imunização por faixa etária | Uma / Uma | VACINAS |
| B025 (C041) | OLINA ESSÊNCIA DE VIDA | Não explicitado | Solução oral | Gentiana lutea 4 mg/mL + Aloe ferox 0,18 mL/mL; Frascos 60/100 mL; flaconete 15 mL | 2 / curta | Associação | adulto | Não | Uma / Múltiplas | DIGESTIVOS-ASSOCIACOES MEDICAMENTOSAS |
| B026 (C042) | GLICERINA 12% | Não explicitado | Solução retal (enema) | 120 mg/mL (12%); 20/25 bolsas de 500 mL + aplicadores | 7 / curta | Único | ambos | Não | Uma / Múltiplas | ENEMAS |
| B027 (C046) | Atrovent / Atrovent N | Istituto de Angeli S.R.L.; Boehringer Ingelheim Pharma GmbH & Co. KG | Solução inalatória; Solução inalatória pressurizada | Gotas 0,25 mg/mL; Atrovent N 20 mcg/dose; Gotas 20 mL; frasco pressurizado 10 mL (200 doses) | 13 / longa | Único | ambos | Não | Múltiplas / Múltiplas | BRONCODILATADORES |
| B028 (C047) | COLPATRIN | Laboratório Teuto Brasileiro S.A. | Creme vaginal | Metronidazol 100 mg/g + nistatina 20.000 UI/g; Bisnaga 50 g + 10 aplicadores | 14 / longa | Associação | adulto | Não | Uma / Uma | PRODUTOS GINECOLOGICOS ANTIINFECCIOSOS TOPICOS ASSOCIACAO MEDICAMENTOSA |
| B029 (C056) | BIOVICERIN | Geyer Medicamentos S.A. | Suspensão oral | 1.000.000 endósporos/mL; 5.000.000 por flaconete; 2/6/12 flaconetes de 5 mL | 5 / curta | Único | ambos | Não | Uma / Múltiplas | OUTROS COADJUVANTES DO TRATAMENTO DA DIARREIA |
| B030 (C058) | HIRUDOID | Daiichi Sankyo Brasil Farmacêutica Ltda. | Gel dermatológico; Pomada dermatológica | Gel e pomada: 3 mg/g; 5 mg/g; Gel 20/40/90 g; pomada 40 g | 19 / longa | Único | ambos | Não | Múltiplas / Múltiplas | ANTIVARICOSOS TOPICOS |
| B031 (C059) | ESPINHEIRA SANTA | Vidora Farmacêutica Ltda. | Tintura (extrato fluido oral) | 0,9 g/mL; padronizado em 3,4 mg/mL de taninos; Frasco 120 mL + copo | 6 / curta | Único | ambos | Não | Uma / Uma | Não identificado |
| B032 (C066) | DEXAMETRAT | Laboratório Globo S.A. | Creme dermatológico | 1 mg/g; Bisnaga 10 g | 7 / curta | Único | ambos | Não | Uma / Uma | GLICOCORTICOIDES TOP. SIMP. EXC. USO OFTALM. |
| B033 (C069) | DRENOGRIP | Belfar Ltda. | Comprimido revestido | Amarelo: dipirona equivalente a 250 mg + clorfeniramina 2 mg; verde: dipirona equivalente a 250 mg + cafeína 30 mg; 12/120 comprimidos, metade de cada cor | 7 / curta | Associação | adulto | Não | Múltiplas / Múltiplas | PRODUTOS PARA TERAPIA SINTOMATICA DA GRIPE |
| B034 (C070) | LUR | Aché Laboratórios Farmacêuticos S.A. | Comprimido revestido; Xarope | Comprimido 5 mg; xarope 0,5 mg/mL; 10 comprimidos; xarope 60 mL + seringa | 11 / média | Único | ambos | Não | Múltiplas / Múltiplas | ANTI-HISTAMINICOS SISTEMICOS |
| B035 (C071) | IMUSSUPREX | EMS S.A.; Novamed Fabricação de Produtos Farmacêuticos Ltda. | Comprimido revestido | 50 mg; 50/200 comprimidos | 11 / média | Único | ambos | Sim: Reações adversas por órgão e frequência | Uma / Múltiplas | IMUNOMODULADOR |
| B036 (C072) | PROCTYL | Takeda Pharma Ltda. | Pomada retal; Supositório | Pomada: policresuleno 50 mg/g + cinchocaína 10 mg/g; supositório: 100 mg + 27 mg; Pomada 30 g ou 10 bisnagas de 3 g + aplicadores; 15 supositórios | 18 / longa | Associação | adulto | Não | Múltiplas / Múltiplas | ANTI-HEMORROIDARIOS TOPICOS |
| B037 (C073) | SOLUPREN | Pharma Limirio Indústria Farmacêutica Ltda. | Pó liofilizado para solução injetável | 500 mg (a composição cita excedente equivalente a 525 mg); 1 frasco-ampola + diluente 8 mL | 9 / média | Único | ambos | Não | Uma / Uma | GLICOCORTICOIDES SISTEMICOS |
| B038 (C074) | DIANEAL PD-2 | Baxter Hospitalar Ltda. | Solução para diálise peritoneal | Glicose 1,5%; 2,5%; 4,25% + eletrólitos; cálcio 2,5/3,5 mEq/L; Single Bag 2/2,5/5/6 L; Ultrabag 2/2,5 L, conforme combinação | 28 / longa | Associação | ambos | Sim: Composição/concentração iônica por formulação; 14 colunas e continuação multipágina | Múltiplas / Múltiplas | SOLUCOES PARA DIALISE PERITONIAL |
| B039 (C077) | cloridrato de dexmedetomidina | Gland Pharma Limited | Solução para diluição injetável | 100 mcg/mL de dexmedetomidina; 10 frascos-ampola de 2 mL | 11 / média | Único | adulto | Sim: Eventos adversos nos estudos | Uma / Uma | HIPNOTICOS |
| B040 (C080) | DODOY | Não explicitado | Solução oral em gotas | 500 mg/mL; Frasco 10/20 mL | 9 / média | Único | ambos | Sim: Posologia pediátrica por peso, idade, gotas e mg; bordas horizontais | Uma / Múltiplas | ANALGESICOS |
| B041 (C081) | VOMISTOP | Medquímica Indústria Farmacêutica Ltda. | Solução oral em gotas | 4 mg/mL; Frasco 10 mL | 10 / média | Único | adulto | Não | Uma / Uma | ANTIEMETICOS E ANTINAUSEANTES |
| B042 (C082) | SOVALDI | Patheon Inc. | Comprimido revestido | 400 mg; 28 comprimidos | 15 / longa | Único | adulto | Sim: Interações, regimes/duração e eventos adversos | Uma / Uma | ANTIVIROTICOS |
| B043 (C085) | CRONOBÊ | Eurofarma Laboratórios S.A. | Solução injetável | 2.000 mcg/mL (5.000 mcg/2,5 mL); 2 ampolas de 2,5 mL | 9 / média | Único | adulto | Sim: Calibre/comprimento de agulha e local de aplicação por peso | Uma / Uma | MONOVITAMINAS EXCETO VITAMINA K |
| B044 (C088) | CYCLOFEMINA | Productos Científicos S.A. de C.V. (Carnot Laboratórios) | Suspensão injetável | Por 0,5 mL: medroxiprogesterona 25 mg + estradiol 5 mg; 1 ampola 0,5 mL | 8 / curta | Associação | adulto | Não | Uma / Uma | ANTICONCEPCIONAIS |
| B045 (C090) | Air Salonpas / Salonpas Gel / Salonsip | Hisamitsu Farmacêutica do Brasil Ltda.; Hisamitsu Pharmaceutical Co., Inc. | Aerossol tópico; Gel dermatológico; Emplastro | Aerossol: salicilato de metila 30 + salicilato de etilenoglicol 19 + levomentol 38,5 + cânfora 38,5 mg/mL; gel: salicilato de metila 0,15 g/g + levomentol 0,07 g/g; emplastro: salicilato de etilenoglicol 0,175 g + levomentol 0,140 g + acetato de racealfatocoferol 0,140 g + cânfora 0,042 g; Aerossol 50 g/80 mL; gel 20/40 g; 3 emplastros de 10 x 14 cm | 15 / longa | Associação | adulto | Não | Múltiplas / Múltiplas | ANTINFLAMATORIOS E ANTIREUMATIOS-ASSOCS  MEDICAMENTOSAS |
| B046 (C092) | Fração Ácida com Cálcio 3,5 mEq/L (Farmace) | Farmace Indústria Químico-Farmacêutica Cearense Ltda. | Solução para hemodiálise | NaCl 21,07% + KCl 0,5222% + CaCl2·2H2O 0,9% + MgCl2·6H2O 0,3555% + ácido acético 0,6311%; Bombona 5 L; conteúdo eletrolítico após diluição separado da solução concentrada | 5 / curta | Associação | ambos | Não | Uma / Uma | PRODUTOS PARA HEMODIALISE |
| B047 (C096) | FUNED ÁCIDO FÓLICO | Não explicitado | Comprimido | 5 mg; Blíster de 10 comprimidos | 6 / curta | Único | adulto | Sim: Posologia e ingestão diária recomendada em adulto/gestante/lactante | Uma / Uma | ANTIANEMICOS |
| B048 (C097) | LAQFA-ISONIAZIDA | Laboratório Químico-Farmacêutico da Aeronáutica | Comprimido | 100 mg; 100/500 comprimidos | 8 / curta | Único | ambos | Sim: Indicações segundo teste de infecção latente | Uma / Múltiplas | TUBERCULOSTATICOS |
| B049 (C098) | SPORANOX | Kenvue Ltda. | Cápsula dura | 100 mg; 28 cápsulas | 19 / longa | Único | adulto | Sim: Dose/duração por infecção; ciclos de tratamento com células mescladas | Uma / Uma | ANTIMICOTICOS SISTEMICOS |
| B050 (C100) | VYVGART | Patheon Italia S.p.A. | Solução para diluição para infusão | 20 mg/mL (400 mg/20 mL); 1 frasco-ampola de 20 mL | 7 / curta | Único | adulto | Não | Uma / Uma | IMUNOSUPRESSOR |

## 6. Piloto separado

P001 (C004) — **PETIVIT BC**, fabricante Brasterapica Pharmaceutica Ltda.; xarope, Por mL: ciproeptadina 0,8 mg + tiamina 0,12 mg + riboflavina 0,15 mg + piridoxina 0,134 mg + nicotinamida 1,334 mg + ácido ascórbico 4,334 mg; Frasco 240 mL + copo-medida; 9 páginas (média); associação; população ambos; sem tabela clínica; uma concentração/apresentação. SHA-256 e arquivo em corpus_pilot.csv.

Foi reservado antes da análise do RAG por reunir identificação, associação, população adulta/pediátrica e forma líquida em um documento de extensão intermediária. Serve para ensaiar o protocolo, não cobre sozinho todas as estruturas do corpus. Não é nenhuma das 50 nem duplicata por hash. A antiga candidata C001 não foi usada como piloto definitivo porque sua versão atual não foi reconfirmada neste lote.

## 7. Formas e grupos presentes

Uma bula pode aparecer em várias formas; as frequências não somam 50.

| Descrição documental de forma/via/preparo | PDFs |
| --- | ---: |
| Aerossol tópico | 1 |
| Comprimido | 6 |
| Comprimido de liberação modificada | 1 |
| Comprimido dispersível | 1 |
| Comprimido mastigável | 1 |
| Comprimido revestido | 5 |
| Creme dermatológico | 1 |
| Creme vaginal | 1 |
| Cápsula | 1 |
| Cápsula de liberação prolongada | 1 |
| Cápsula dura | 3 |
| Cápsula mole | 1 |
| Emplastro | 1 |
| Emulsão injetável | 1 |
| Gel dermatológico | 2 |
| Glóbulos | 1 |
| Pomada dermatológica | 1 |
| Pomada retal | 1 |
| Pó liofilizado para solução injetável | 5 |
| Pó liofilizado para suspensão intravesical | 1 |
| Pó para reconstituição | 1 |
| Pó para solução injetável | 1 |
| Pó para suspensão oral | 1 |
| Solução bucal | 1 |
| Solução bucal em spray | 1 |
| Solução inalatória | 2 |
| Solução inalatória pressurizada | 1 |
| Solução injetável | 3 |
| Solução oral | 1 |
| Solução oral em gotas | 4 |
| Solução otológica | 1 |
| Solução para diluição injetável | 1 |
| Solução para diluição para infusão | 1 |
| Solução para diálise peritoneal | 1 |
| Solução para hemodiálise | 1 |
| Solução para infusão | 1 |
| Solução retal (enema) | 1 |
| Solução tópica em spray | 1 |
| Supositório | 1 |
| Suspensão injetável | 1 |
| Suspensão oftálmica | 1 |
| Suspensão oral | 1 |
| Tintura (extrato fluido oral) | 1 |
| Xarope | 1 |

Grupos são rótulos literais da fonte oficial, somente critério secundário. Nomes diferentes não garantem independência clínica.

| Grupo terapêutico cadastral | PDFs |
| --- | ---: |
| AMINOGLICOSIDEOS | 1 |
| ANALGESICOS | 1 |
| ANTI-HEMORROIDARIOS TOPICOS | 1 |
| ANTI-HISTAMINICOS SISTEMICOS | 1 |
| ANTIANEMICOS | 1 |
| ANTIANEMICOS SIMPLES | 1 |
| ANTIASMATICOS | 1 |
| ANTIBIOTICOS ANTINEOPLASICOS | 1 |
| ANTICONCEPCIONAIS | 1 |
| ANTIEMETICOS E ANTINAUSEANTES | 1 |
| ANTIMICOTICOS SISTEMICOS | 1 |
| ANTINFECCIOSOS TOPICOS-ASSOCIACOES MEDICAMENTOSAS | 1 |
| ANTINFLAMATORIOS | 1 |
| ANTINFLAMATORIOS ANTIREUMATICOS | 1 |
| ANTINFLAMATORIOS E ANTIREUMATIOS-ASSOCS  MEDICAMENTOSAS | 1 |
| ANTIPARASITARIOS | 1 |
| ANTIPARKINSONIANOS | 1 |
| ANTISSEPTICO | 1 |
| ANTIVARICOSOS TOPICOS | 1 |
| ANTIVIROTICOS | 1 |
| BRONCODILATADORES | 1 |
| CEFALOSPORINAS | 1 |
| DEMULCENTES E OUTROS MEDS. USO ORAL P/ TRATAM. OROFARINGE | 1 |
| DIGESTIVOS-ASSOCIACOES MEDICAMENTOSAS | 1 |
| ENEMAS | 1 |
| EXPECTORANTES SIMPLES | 1 |
| GLICOCORTICOIDES SISTEMICOS | 1 |
| GLICOCORTICOIDES TOP. SIMP. EXC. USO OFTALM. | 1 |
| GLICOCORTICOIDES TOPICO OFTALMOLOGICO SIMPLES | 1 |
| HIPNOTICOS | 1 |
| IMUNOESTIMULANTES | 1 |
| IMUNOMODULADOR | 1 |
| IMUNOSUPRESSOR | 1 |
| MEDICAMENTOS DINAMIZADOS DE COMPONENTE ÚNICO | 1 |
| MONOVITAMINAS EXCETO VITAMINA K | 1 |
| NUTRIENTES PARENTERAIS | 1 |
| Não identificado no cadastro consultado | 1 |
| OUTROS COADJUVANTES DO TRATAMENTO DA DIARREIA | 1 |
| OUTROS PRODUTOS ANTI-HEMORRAGICOS | 1 |
| OUTROS PRODUTOS QUE ATUAM SOBRE O SISTEMA NERVOSO | 1 |
| PENICILINA DE AMPLO ESPECTRO | 1 |
| PENICILINAS PENICILINASE-RESISTENTES | 1 |
| PRODUTOS GINECOLOGICOS ANTIINFECCIOSOS TOPICOS ASSOCIACAO MEDICAMENTOSA | 1 |
| PRODUTOS PARA HEMODIALISE | 1 |
| PRODUTOS PARA TERAPIA SINTOMATICA DA GRIPE | 1 |
| REIDRATANTES PARENTERAIS | 1 |
| SOLUCOES PARA DIALISE PERITONIAL | 1 |
| TUBERCULOSTATICOS | 1 |
| VACINAS | 1 |
| VITAMINAS OU MINERAIS ASSOCIADOS A OUTROS FARMACOS | 1 |

## 8. Por que o conjunto é documentalmente diversificado

Combina as três faixas relativas de extensão com formas sólidas, líquidas, tópicas, inalatórias, oftálmicas, otológicas, vaginais, retais, injetáveis e soluções de diálise. Inclui composições únicas e associadas, uso adulto e pediátrico, arquivos com uma ou várias apresentações, e tabelas de diferentes larguras/continuações e objetivos, além de prosa sem tabelas clínicas. Essa é diversidade de documentos observáveis, não uma alegação de representatividade estatística das bulas brasileiras ou segurança clínica demonstrada.

## 9. Arquivos e auditoria

- A fila exploratória de 100 candidatos (88 elegíveis) permanece no arquivo local `corpus_candidates.csv`; não é outro corpus nem um artefato publicado nesta consolidação.
- corpus_final.csv: exatamente 50 IDs B001–B050, com características, fonte por registro, páginas e SHA-256.
- corpus_pilot.csv: P001, disjunto das 50 e com hash diferente.
- download_audit_report.md: auditoria anterior do recebimento do lote, preservada como registro histórico.
- Os CSVs são UTF-8 com BOM; importar registro/processo/CNPJ/IDs como texto para preservar zeros. Contagens e ausência de duplicatas foram verificadas; todos os 51 PDFs arquivados mantêm o hash original. Código de produção e índices não foram alterados nesta tarefa.


### Publicação dos manifestos

Os manifestos publicados omitem somente `caminho_pdf_original`, que continha caminhos pessoais absolutos. Nomes dos PDFs, IDs, hashes, registros, fontes e demais características permanecem inalterados. `caminho_pdf_arquivado` é a referência relativa ao arquivo local, não uma promessa de PDF incluído no repositório. PDFs, candidatos exploratórios e arquivos temporários não são versionados nesta entrega.
