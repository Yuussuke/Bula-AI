# Naturalness and plausibility diagnostic — effective golden set

2026-10-10. Assistant assessment only; no human decisions, source corrections or question edits.

## Scope and limits

Read all **1000 effective records / 2000 question formulations**, using the batch-10 consolidation manifest: revision 4 of phase 1 and the effective revisions of batches 01–10. Earlier versions were not counted again. Coverage and per-record canonical SHA-256 bindings are in [findings.json](findings.json).

The diagnostic considers Brazilian lay patients, families and caregivers. It screens plausibility, unnecessary source targeting, answer induction, specialized precision and technical/documentary phrasing. Suspected rewrites were compared with the **stored** expected information, literal references, qualifiers and negative absence rationales. This is not a fresh semantic validation of all 100 PDFs, proof of every negative's absence, measurement of real patient question frequency or independent human review. Hash verification proves source identity, not semantic correctness.

No retrieval rankings, generated responses, system metrics, experiments or judge results were consulted. No topic-distribution target or problem quota was used. Prior author flags were not automatically interpreted as linguistic defects.

Priorities describe linguistic suspicion: Alta = substantially source-directed/confirmatory; Média = plausible need with specificity or wording warranting review; Baixa = limited genuine improvement. These labels do not replace P0–P3 in the existing documentary-audit queue. Neither queue nor the 100-record sample was changed.

## Main interpretation

Most formulations already read like plausible patient or caregiver doubts. The residual issue is **not a generally unusable set**, and it does not justify another wholesale rewriting round. The flagged set mixes small documentary-language problems and a few needs whose plausibility cannot be improved by style alone.

There is no confirmed current cross-leaflet leak of the requested drug identity in this linguistic screen. That does **not** certify uniqueness of every target query. Existing target-identity/collision checks remain pending. Proposed cross variants retain the current medication/presentation/manufacturer identifiers; none was chosen using retrieval performance.

### Complexity retained deliberately

- **A-B015-Q07**: factor XIII, the 5–20% trough interval and specialized context are needed to identify the table condition. A laboratory-result question can be legitimate. Its technicality alone is not a linguistic defect; preserve the assay and individualization qualifiers in the response.
- **B-CB011-Q02**: a reported renal test result can naturally contain units and a threshold. Do not remove the result to make the question easier.
- **B-CB023-Q05**, **B-CB050-Q04**: age, weight/temperature where applicable and the specific inherited diagnosis distinguish the relevant dose-reference group. They are not answers inserted into the question. Table/safety review remains necessary.
- **A-B042-Q02**: HIV coinfection, genotype and prior treatment are indispensable conditions, not gratuitous specificity.
- **A-B010-Q01**: the total strength identifying Prolopa DR does not give the requested amount of each active constituent. It is not automatically leakage.
- **B-CB020-Q01**: the current cross variant no longer names the active constituents it asks for. Strength and responsible laboratory identify the presentation; the historical leak must not be attributed to the effective revision.
- **B-CB003-Q09**, **B-CB004-Q09**: asking for sodium amount can be a plausible restricted-diet need even without explaining the diet. No invented diet history or automatic rejection was added.
- **B-CB019-Q04**, **B-CB049-Q05**: a question about a known interaction or established pediatric safety/efficacy can be genuine. No rewrite solely to remove the terminology was proposed.
- **A-B038-Q07**: retain the natural uncertainty about droplets; do not assume the liquid's identity or remove the ambiguity to help scoring.
- **A-B049-Q02**: retain the natural question about the appearance of the nail. The existing note still distinguishes disappearance of lesions after 6–9 months from onset of visible improvement.
- **A-B044-Q10**, **A-B045-Q09**: acne treatment and heat with a patch are plausible negatives. A bounded documentary explanation can be adequate; missing indication or guidance is not proof of safety or clinical impossibility.

### Rewrites are not automatically equivalent

Three quantitative negatives have **no proposed replacement**: changing them to general risk/composition questions could change support and classification. Their needs may be kept after author review; lack of an everyday context is a suspicion, not proof of invalidity.

For **A-B041-Q07**, a general interaction question is more natural than “exposição”, but broader. It is explicitly a candidate requiring a directed documentary/expected-answer check, not an equivalent ready-to-apply edit. Pharmacokinetic exposure must not silently become concentration, effect, toxicity or a prohibition.

For **A-B016-Q08**, the condition-preserving candidate keeps the time window anchored to fluids/antipyretics. It asks what to do rather than eliciting a vague “yes”. Because that makes conduct explicit, reassess indispensable answer content before adoption. The author's more open alternative is also viable **as a proposal**, not approved here:

> Fiz uma aplicação de BCG na bexiga e estou com febre alta que não melhora, mesmo tomando antitérmico. Isso pode ser perigoso? O que devo fazer?

It leaves temperature, duration and the fluids condition unspecified. An adequate answer would explain the source conditionally or ask for clarification; it must not pretend those criteria were met. This would require an explicit decision about the single-turn reference and its completeness requirements. It was not applied and no conversational evaluation was introduced.

## Next decision

Review the flagged proposals first. Accept, reject or retain them individually; do not interpret this report as a mandate to replace all flagged questions. Wording-only candidates do not justify changing documentary evidence. Scope-changing candidates must pass a directed documentary check before any versioned change. Existing documentary, safety, negative-absence and target-identity audit obligations remain unchanged.

All 1000 records remain drafts. There are **zero** new human decisions, record changes, RAG/provider calls or experimental freezes. Author approval is required before applying anything.


## Quantitative summary

Counts are records, not variants or confirmed errors. All 800 positives and 200 negatives were screened.

| Priority | A positive | A negative | B positive | B negative | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Alta | 1 | 0 | 0 | 0 | 1 |
| Média | 3 | 3 | 5 | 1 | 12 |
| Baixa | 0 | 0 | 1 | 0 | 1 |

Flagged: **14 / 1000**. No linguistic issue identified: **986**; this is not documentary approval.

Input fingerprint: `96382e4c11643f0e99b7713f0cd17bb61811e35a599df03802a45e8b96520949`.

Verified 104 unique frozen/historical input files and all 100 PDF hashes. Audit-plan/sample files are separately bound in findings.json and unchanged.

## Findings

### A-B001-Q10 — SINGULAIR

Corpus **A** · **negative** · Priority **Média**.

Original scoped: Quantos miligramas de sódio elementar tem em um comprimido de mastigar de 4 mg?

Original cross-leaflet: Quantos miligramas de sódio elementar tem em um comprimido de mastigar de Singulair de 4 mg?

Issue: Jargão químico e precisão pouco contextualizada, não ausência documental por si só.

Rationale: Perguntar pela quantidade de sódio é plausível, inclusive para quem controla sua ingestão. A expressão 'sódio elementar' torna a fala mais especializada do que o necessário. Não há evidência de que o autor tenha criado a pergunta apenas para explorar uma lacuna; essa é uma suspeita, não uma conclusão sobre autoria.

Proposed scoped: Quanto sódio, em miligramas, tem no comprimido de mastigar de 4 mg?

Proposed cross-leaflet: Quanto sódio, em miligramas, tem no comprimido de mastigar de Singulair de 4 mg?

Preserve: Massa de sódio, não massa do sal montelucaste de sódio; comprimido mastigável de 4 mg; não converter quimicamente a composição.

Equivalence assessment: A proposta preserva a necessidade quantitativa e a apresentação; 'sódio' continua designando o mineral. A necessidade especializada pode ser mantida se o revisor a considerar plausível.

Potential impact: Somente linguagem: a quantidade solicitada permanece a mesma. Não adicionar automaticamente 'tem sódio?' ou uma indicação de segurança para restrição de sal, pois seriam outras proposições.

New directed documentary check before change: **not additionally required by wording alone**. A ausência registrada continua pendente da auditoria documental existente; não foi reconfirmada por uma nova leitura integral neste diagnóstico.

Binding: `docs/evaluation/golden_set/phase1/questions.revision4.draft.jsonl:20` · revision 4 · record SHA-256 `b9b9edcb6a37696b9a5c1d20eff961cf47a7b9095a4c4dd1582ec9b1547e6263`.

### B-CB002-Q02 — HIDROCLOROTIAZIDA

Corpus **B** · **positive** · Priority **Média**.

Original scoped: Quem tem comprometimento grave dos rins pode tomar esse remédio? Qual é o limite citado?

Original cross-leaflet: Quem tem comprometimento grave dos rins pode tomar hidroclorotiazida da EMS? Qual é o limite citado?

Issue: Pedido de 'limite citado' remete à leitura de um texto de prova.

Rationale: A restrição renal e seu limite numérico são necessidades legítimas. O problema é a referência implícita a algo 'citado', em vez de perguntar pelo resultado do exame que estabelece a restrição.

Proposed scoped: Quem tem problema grave nos rins pode tomar esse remédio? Há algum valor do exame que impede o uso?

Proposed cross-leaflet: Quem tem problema grave nos rins pode tomar hidroclorotiazida da EMS? Há algum valor do exame que impede o uso?

Preserve: Comprometimento renal grave; limite de depuração da creatinina abaixo de 30 mL/min na resposta; não generalizar para qualquer problema renal.

Equivalence assessment: A referência literal registra contraindicação e depuração da creatinina. A proposta não informa antecipadamente o valor nem pede interpretação de um exame individual.

Potential impact: A pergunta continua solicitando restrição e limite. A resposta precisa nomear o exame/medida correta, não qualquer exame renal. Evidências e classificação não precisam mudar pela proposta.

New directed documentary check before change: **not additionally required by wording alone**. Conferência feita contra as referências e qualificadores cadastrados, não uma nova validação clínica do PDF.

Binding: `docs/evaluation/golden_set/expansion/batch01/questions.draft.jsonl:52` · revision 1 · record SHA-256 `ce135d9d6bfbedfb65053a130b49c28224d72c6046aed99349aa4999c4d423ea`.

### B-CB006-Q09 — besilato de anlodipino

Corpus **B** · **negative** · Priority **Média**.

Original scoped: Quantos mg de cálcio tem em cada comprimido de 5 mg?

Original cross-leaflet: Quantos mg de cálcio tem em cada comprimido de besilato de anlodipino de 5 mg da Sandoz?

Issue: Pedido quantitativo de cálcio de um excipiente sem finalidade contextualizada.

Rationale: A pergunta poderia ser legítima numa situação de controle de ingestão de cálcio. Na forma atual, a quantidade exata em mg num anti-hipertensivo exige uma necessidade especializada que não está contextualizada. A justificativa de ausência menciona fosfato de cálcio e o mecanismo de canal de cálcio; nenhum deles justifica presumir que essa seja uma dúvida típica de paciente.

Proposed scoped: No equivalent rewrite proposed; retain original.

Proposed cross-leaflet: No equivalent rewrite proposed; retain original.

Preserve: Quantidade de cálcio por comprimido de anlodipino de 5 mg; não confundir 5 mg de princípio ativo com cálcio.

Equivalence assessment: Nenhuma reformulação é oferecida porque uma substituição mais ampla pode mudar a necessidade e a classificação negativa.

Potential impact: Não há substituição meramente linguística que resolva a plausibilidade. Trocar por 'tem cálcio?' pode tornar a pergunta respondível pela composição; adicionar doença ou necessidade nutricional inventaria contexto. Manter até decisão do autor.

New directed documentary check before change: **yes**. Somente se for escolhida outra necessidade: conferir novamente a ausência no PDF-alvo antes de classificar a nova pergunta. Não há erro documental demonstrado no registro atual.

Binding: `docs/evaluation/golden_set/expansion/batch01/questions.draft.jsonl:99` · revision 1 · record SHA-256 `2d6b152ed9ec7f32cf6f035eea21fd81a58e332f89bb6ce2ef4e021ee50ef0b2`.

### A-B009-Q09 — LIPOFUNDIN

Corpus **A** · **negative** · Priority **Média**.

Original scoped: Uma pessoa de 70 kg ganha quantos quilos em uma semana recebendo esse produto?

Original cross-leaflet: Uma pessoa de 70 kg ganha quantos quilos em uma semana recebendo Lipofundin MCT/LCT 20%?

Issue: Previsão individual de ganho de peso com cenário numérico muito fechado.

Rationale: Ganho de peso durante nutrição venosa é uma preocupação plausível. O pacote '70 kg + quantos quilos + uma semana' parece um exercício de previsão quantitativa, especialmente porque a justificativa de ausência registra um exemplo de volume para 70 kg. Isso não prova intenção de explorar a lacuna e o peso poderia ser real; por isso a prioridade é média, não erro confirmado.

Proposed scoped: No equivalent rewrite proposed; retain original.

Proposed cross-leaflet: No equivalent rewrite proposed; retain original.

Preserve: Pessoa de 70 kg; previsão de ganho ponderal em uma semana; não converter calorias, volume ou dose em ganho de peso.

Equivalence assessment: Não foi encontrada uma reformulação que melhore o problema estrutural sem mudar a precisão solicitada. Uma revisão de plausibilidade deve decidir se essa necessidade será mantida.

Potential impact: Retirar peso ou período não seria só redação. 'Esse produto ajuda a ganhar peso?' perguntaria sobre finalidade/efeito geral, potencialmente respondível por outras passagens. Não substituir automaticamente.

New directed documentary check before change: **yes**. Se o autor optar por mudar a necessidade, será preciso rever classificação, ausência e informação esperada. A negativa original não foi invalidada.

Binding: `docs/evaluation/golden_set/expansion/batch02/questions.revision2.draft.jsonl:29` · revision 1 · record SHA-256 `88b957dcf62441d08f1466f563d2bdde69cd09be44ab49dd84d96e5f5b1e51cd`.

### A-B014-Q09 — Pred Fort / Pred Mild

Corpus **A** · **negative** · Priority **Média**.

Original scoped: Quanto a pressão do olho pode subir com Pred Fort, em mmHg?

Original cross-leaflet: Quanto a pressão do olho pode subir com o colírio Pred Fort da Allergan, em mmHg?

Issue: Magnitude exata de efeito adverso em mmHg sem contexto de medição.

Rationale: Um paciente que acompanha pressão ocular pode perguntar por mmHg. Não é o uso da unidade que constitui o problema. Sem esse contexto, a magnitude quantitativa parece mais especializada que a dúvida usual sobre risco e acompanhamento; deve ser avaliada, não automaticamente rejeitada.

Proposed scoped: No equivalent rewrite proposed; retain original.

Proposed cross-leaflet: No equivalent rewrite proposed; retain original.

Preserve: Pred Fort, não Pred Mild; magnitude da elevação de pressão ocular em mmHg; não confundir frequência do efeito com sua magnitude.

Equivalence assessment: Mantida sem sugestão de substituição equivalente: a dificuldade é a necessidade muito precisa, não uma expressão isolada corrigível.

Potential impact: Mudar para 'pode aumentar a pressão do olho?' mudaria a necessidade e provavelmente a classificação, pois o alerta de aumento já está documentado. Uma alteração desse tipo requer nova análise, não revisão linguística simples.

New directed documentary check before change: **yes**. Rever documentalmente somente uma eventual nova proposição. Esta suspeita não afirma que a justificativa negativa atual esteja errada.

Binding: `docs/evaluation/golden_set/expansion/batch03/questions.draft.jsonl:29` · revision 1 · record SHA-256 `1f87e1457ad06fca31659f23c3e961d37f5b7eddd8ffac7c74fcfb500c9b1302`.

### A-B016-Q08 — IMUNO  BCG

Corpus **A** · **positive** · Priority **Alta**.

Original scoped: Depois da aplicação, uma febre acima de 39 graus que não baixa em 24 a 48 horas, mesmo com líquidos e antitérmico, exige atenção especial?

Original cross-leaflet: Depois de Imuno BCG da Fundação Ataulpho de Paiva, uma febre acima de 39 graus que não baixa em 24 a 48 horas, mesmo com líquidos e antitérmico, exige atenção especial?

Issue: Critérios quase literais da fonte seguidos de uma pergunta confirmatória vaga.

Rationale: Temperatura, duração e persistência apesar das medidas são condições de segurança relevantes. Reproduzir o conjunto quase literalmente e terminar com 'exige atenção especial?' orienta para um sim pouco informativo. É possível pedir a conduta sem remover essas condições nem fornecer o desfecho esperado.

Proposed scoped: Depois da aplicação, a febre está acima de 39 graus e não baixou nem 24 a 48 horas depois de eu receber líquidos e antitérmico. O que devo fazer?

Proposed cross-leaflet: Depois da aplicação de Imuno BCG da Fundação Ataulpho de Paiva, a febre está acima de 39 graus e não baixou nem 24 a 48 horas depois de eu receber líquidos e antitérmico. O que devo fazer?

Preserve: Febre acima de 39 graus persistente apesar de líquidos e antitérmico e janela de 24–48 horas; aplicação de Imuno BCG; possibilidade de infecção sistêmica, não diagnóstico; risco de vida e conduta profissional expressos na fonte.

Equivalence assessment: Equivalência condicionada à conferência temporal: a proposta é um rascunho, não aprovada. A pergunta original indaga gravidade; a conduta presente na resposta esperada passaria a ser explicitamente solicitada. Não transportar o critério de completude sem revisão.

Potential impact: Mantém as condições documentais, mas torna explícito o pedido de conduta, já contido em expected_information. O período continua contado após receber líquidos/antipiréticos, não simplesmente desde a aplicação. A alternativa aberta sugerida pelo autor, sem temperatura e duração, exigiria resposta condicional e reavaliação do que é obrigatório, nunca presumir critérios preenchidos.

New directed documentary check before change: **yes**. Verificação dirigida de escopo/tempo e requisitos da resposta necessária antes de aplicar. Não acrescentar tratamento, diagnóstico ou orientação de emergência como se fossem citações literais desta passagem.

Binding: `docs/evaluation/golden_set/expansion/batch03/questions.draft.jsonl:48` · revision 1 · record SHA-256 `98adb0f599f9c89ab81722d4204566343b097c1eaf3b6a559e8ba3fd4fa14620`.

### B-CB016-Q03 — dapagliflozina

Corpus **B** · **positive** · Priority **Média**.

Original scoped: Com quanto tempo de tratamento foi observada queda do açúcar em jejum?

Original cross-leaflet: Com quanto tempo de tratamento com dapagliflozina de 10 mg da Aché foi observada queda do açúcar em jejum?

Issue: Voz de relato de estudo ('foi observada') em vez de dúvida sobre tempo de resposta.

Rationale: A informação de tempo é plausível para o paciente. A voz passiva replica o enquadramento documental. A natureza observacional da fonte deve ser preservada na resposta e nos qualificadores, sem exigir que o usuário já fale como um pesquisador.

Proposed scoped: Quanto tempo pode levar para esse remédio baixar o açúcar no sangue em jejum?

Proposed cross-leaflet: Quanto tempo pode levar para dapagliflozina de 10 mg da Aché baixar o açúcar no sangue em jejum?

Preserve: Açúcar no sangue em jejum; redução observada após uma semana, não garantia individual nem tempo até pico em horas.

Equivalence assessment: Proposta compatível com o tempo de redução documentado, com ressalva de modalidade: 'pode levar' não significa prazo garantido. Nenhuma evidência adicional foi inventada.

Potential impact: A necessidade temporal permanece. A pergunta deixa de exigir explicitamente um relato retrospectivo; a resposta deve qualificar o achado como observado, não prometer resposta individual. Conferir essa equivalência antes de adotar.

New directed documentary check before change: **not additionally required by wording alone**. A verificação linguístico-semântica utilizou a referência cadastrada. Não altera o resultado observado da fonte.

Binding: `docs/evaluation/golden_set/expansion/batch03/questions.draft.jsonl:93` · revision 1 · record SHA-256 `1d9abc2da06a1dc74822b20dc91c3b5231dfcc320cfd21c9fd533e1239a199e5`.

### B-CB017-Q02 — empagliflozina

Corpus **B** · **positive** · Priority **Baixa**.

Original scoped: Uma criança de onze anos com diabetes tipo 2 está no público indicado?

Original cross-leaflet: Uma criança de onze anos com diabetes tipo 2 está no público indicado para empagliflozina da Germed?

Issue: Expressão 'está no público indicado' é uma categoria de avaliação, pouco conversacional.

Rationale: Idade e diabetes tipo 2 são indispensáveis e naturais. Há uma oportunidade pequena e específica de substituir a expressão classificatória por uma dúvida de uso, sem eliminar essas condições.

Proposed scoped: Uma criança de onze anos com diabetes tipo 2 pode usar esse remédio?

Proposed cross-leaflet: Uma criança de onze anos com diabetes tipo 2 pode usar empagliflozina da Germed?

Preserve: Onze anos e diabetes tipo 2; indicação glicêmica associada a dieta e exercícios; não transferir indicações adultas cardíacas/renais nem escolher dose.

Equivalence assessment: A referência contém indicação no DM2 a partir de dez anos. A idade não antecipa esse limite; é condição do cenário.

Potential impact: Solicita a indicação documental para esse grupo, não decisão individual irrestrita. Evidência e classificação positiva permanecem compatíveis.

New directed documentary check before change: **not additionally required by wording alone**. Manter a distinção entre indicação e autorização clínica individual na futura resposta.

Binding: `docs/evaluation/golden_set/expansion/batch04/questions.revision2.draft.jsonl:52` · revision 1 · record SHA-256 `bbea522a3fa8d472a8b1f2a3bde9732c2464206ec22268471e68c6a027390fb1`.

### B-CB021-Q04 — dipirona

Corpus **B** · **positive** · Priority **Média**.

Original scoped: Para uma criança de quatro anos e vinte quilos, que faixa de volume aparece para aplicação no músculo?

Original cross-leaflet: Para uma criança de quatro anos e vinte quilos, que faixa de volume aparece para dipirona injetável da Santisa no músculo?

Issue: 'Que faixa de volume aparece' parece uma instrução para localizar célula.

Rationale: Idade, peso, via e intervalo de volume são indispensáveis para a pergunta. O verbo 'aparece' evoca inspeção de tabela, não a dúvida de um cuidador. Pedir a faixa não autoriza selecionar uma dose individual.

Proposed scoped: Para uma criança de quatro anos e vinte quilos, qual é a faixa de volume da injeção no músculo?

Proposed cross-leaflet: Para uma criança de quatro anos e vinte quilos, qual é a faixa de volume da dipirona injetável da Santisa no músculo?

Preserve: Quatro anos, vinte quilos, via IM e faixa completa em mL; não escolher ponto do intervalo, calcular dose nova ou usar referência oral.

Equivalence assessment: As referências cadastradas associam 16–23 kg a 0,3–0,8 mL e remetem a decisão médica de dose/via. A proposta não antecipa os valores da célula.

Potential impact: Mesma faixa documental e associação de coluna. A restrição de não individualizar pertence à avaliação, não deve ser inserida artificialmente na fala do paciente.

New directed documentary check before change: **not additionally required by wording alone**. A auditoria visual de tabela já prevista continua pendente; este diagnóstico não a substitui.

Binding: `docs/evaluation/golden_set/expansion/batch04/questions.revision2.draft.jsonl:94` · revision 2 · record SHA-256 `d841f1854c9865bcd1c5d850a75c85fd9e6d0fecf5f6511e44d6dff740487cdf`.

### A-B040-Q08 — DODOY

Corpus **A** · **positive** · Priority **Média**.

Original scoped: Para um bebê de 6 meses e 7 kg, o que a tabela indica como dose única dessas gotas?

Original cross-leaflet: Para um bebê de 6 meses e 7 kg, o que a tabela do Dodoy gotas da Jarrell indica como dose única?

Issue: Referência explícita à tabela transforma a dúvida de dose em tarefa de transcrição.

Rationale: Perguntar a dose de um bebê é plausível, e idade/peso são necessários. A pergunta não precisa exigir que o usuário saiba que existe uma tabela nem pedir a leitura dela.

Proposed scoped: Para um bebê de 6 meses e 7 kg, qual é a faixa de gotas para uma dose só?

Proposed cross-leaflet: Para um bebê de 6 meses e 7 kg, qual é a faixa de gotas de Dodoy da Jarrell para uma dose só?

Preserve: Idade de 6 meses, peso de 7 kg, gotas orais e dose única; não confundir com máximo diário nem selecionar valor individual.

Equivalence assessment: A linha de 5–8 kg/3–11 meses contém a faixa de dose única em gotas. A proposta pede essa mesma faixa sem anunciar a estrutura da fonte.

Potential impact: A faixa de gotas continua obrigatória; a equivalência em mg pode ser contexto complementar, não critério obrigatório se não solicitada. Conservar evidência e classificações, com a revisão visual existente.

New directed documentary check before change: **not additionally required by wording alone**. Não foi refeita a inspeção visual: continua sendo parte da auditoria de risco da referência.

Binding: `docs/evaluation/golden_set/expansion/batch08/questions.revision2.draft.jsonl:18` · revision 1 · record SHA-256 `2788b887c846bcb9fb972fe8ce3b3a5e15bd2f358b57499883380de1097d716a`.

### A-B041-Q04 — VOMISTOP

Corpus **A** · **positive** · Priority **Média**.

Original scoped: Estou amamentando. Posso usar essas gotas? O profissional precisa orientar alguma alternativa?

Original cross-leaflet: Estou amamentando. Posso usar Vomistop gotas da Medquímica? O profissional precisa orientar alguma alternativa?

Issue: Segunda pergunta soa como cobrança de obrigação normativa do 'profissional'.

Rationale: A preocupação com amamentação e alternativas é legítima. 'O profissional precisa orientar alguma alternativa?' aproxima a fala da redação regulatória. Não há problema de suporte: a referência cadastrada expressa essa obrigação.

Proposed scoped: Estou amamentando. Posso usar essas gotas? Preciso receber orientação sobre outras opções?

Proposed cross-leaflet: Estou amamentando. Posso usar Vomistop gotas da Medquímica? Preciso receber orientação sobre outras opções?

Preserve: Aleitamento; contraindicação expressa; orientação profissional sobre alternativas de tratamento ou alimentação do bebê; não inventar substituto.

Equivalence assessment: A citação menciona contraindicação e apresentação de alternativas pelo médico ou dentista. Nenhuma alternativa específica é revelada nem solicitada.

Potential impact: Preserva as duas necessidades: uso no aleitamento e orientação de alternativas. Não transformar a segunda pergunta em 'qual remédio tomo no lugar?', que precisaria de outros documentos.

New directed documentary check before change: **not additionally required by wording alone**. Suspeita linguística, não a divergência de evidência anteriormente resolvida em outro registro.

Binding: `docs/evaluation/golden_set/expansion/batch08/questions.revision2.draft.jsonl:24` · revision 1 · record SHA-256 `6a76c66b385b2a07c27957b3f92502db4c58f1ab30b052c699b96d771dbeb4e1`.

### A-B041-Q07 — VOMISTOP

Corpus **A** · **positive** · Priority **Média**.

Original scoped: Tomo fluoxetina. Ela pode mudar a exposição a esse remédio?

Original cross-leaflet: Tomo fluoxetina. Ela pode mudar a exposição ao Vomistop gotas da Medquímica?

Issue: 'Mudar a exposição' usa conceito farmacocinético sem significado cotidiano claro.

Rationale: A combinação com fluoxetina é uma dúvida plausível. 'Exposição' isolada exige conhecimento técnico e pode ser entendida como contato externo. Trocar por 'efeito' ou 'quantidade no sangue' não garante equivalência farmacocinética; uma pergunta geral de interação é mais natural, mas mais ampla.

Proposed scoped: Tomo fluoxetina. Tem alguma interação com essas gotas?

Proposed cross-leaflet: Tomo fluoxetina. Tem alguma interação com Vomistop gotas da Medquímica?

Preserve: Fluoxetina e metoclopramida/Vomistop gotas; é a exposição à metoclopramida que aumenta, não o inverso; não inferir proibição ou decisão individual.

Equivalence assessment: Equivalência estrita não confirmada. Há uma relação de interação sustentada nas referências, porém a pergunta geral pode abranger outros efeitos/qualificações. Manter original até autorização e conferência dirigida.

Potential impact: A proposta amplia de um parâmetro farmacocinético para interação em geral. Não é correção equivalente automática: revisar a passagem inteira e a completude necessária antes de adotá-la. A classificação positiva parece compatível com a relação explícita, mas não está revalidada nesta proposta.

New directed documentary check before change: **yes**. Rever escopo e exigências da resposta; não substituir 'exposição' por concentração, efeito clínico ou toxicidade sem suporte.

Binding: `docs/evaluation/golden_set/expansion/batch08/questions.revision2.draft.jsonl:27` · revision 2 · record SHA-256 `e8066a49c3bbd96c5f4b0436ad42ddd45a5230d17d2a219660bbdbae945326e8`.

### B-CB040-Q04 — cloridrato de trazodona

Corpus **B** · **positive** · Priority **Média**.

Original scoped: Quem amamenta pode usar? O profissional deve oferecer alternativas?

Original cross-leaflet: Quem amamenta pode usar cloridrato de trazodona da Globo, produzido pela Zydus? O profissional deve oferecer alternativas?

Issue: Pergunta de dever profissional construída em registro regulatório.

Rationale: Uso no aleitamento e orientação sobre alternativas são necessidades plausíveis. A formulação 'O profissional deve oferecer alternativas?' replica uma obrigação da fonte, embora a citação a sustente.

Proposed scoped: Quem está amamentando pode tomar esse remédio? Precisa receber orientação sobre outras opções?

Proposed cross-leaflet: Quem está amamentando pode tomar cloridrato de trazodona da Globo, produzido pela Zydus? Precisa receber orientação sobre outras opções?

Preserve: Aleitamento; contraindicação; orientação profissional de alternativas para tratamento ou alimentação do bebê; não sugerir substituto nem interromper leite por conta própria.

Equivalence assessment: Referência literal contém ambas as orientações. A proposta não determina qual tratamento ou alimentação deve substituir os atuais.

Potential impact: Mesmas duas necessidades e mesmo identificador do produto. Não reduzir automaticamente à primeira pergunta e depois exigir alternativas como detalhe obrigatório não solicitado.

New directed documentary check before change: **not additionally required by wording alone**. Manter responsáveis Globo/Zydus como na variante vigente; identificação do PDF não é provada pela naturalidade da redação.

Binding: `docs/evaluation/golden_set/expansion/batch08/questions.revision2.draft.jsonl:74` · revision 1 · record SHA-256 `2b396918d97709be9954f53303f2eb0a97f9a19d9403ef4241a1ffca38dd7649`.

### B-CB049-Q01 — genfibrozila

Corpus **B** · **positive** · Priority **Média**.

Original scoped: Depois de começar, quando os estudos mostram redução do colesterol?

Original cross-leaflet: Depois de começar genfibrozila da FURP, quando os estudos mostram redução do colesterol?

Issue: Usuário fala diretamente da conclusão dos estudos, não de sua dúvida sobre tempo.

Rationale: Saber quando o colesterol pode baixar é uma necessidade plausível. A referência a 'quando os estudos mostram' aproxima a pergunta de uma avaliação acadêmica. A informação deve continuar sendo apresentada como resultado observado, sem garantia individual.

Proposed scoped: Depois de começar, em quanto tempo pode aparecer uma redução do colesterol?

Proposed cross-leaflet: Depois de começar genfibrozila da FURP, em quanto tempo pode aparecer uma redução do colesterol?

Preserve: Redução do colesterol a partir da oitava semana nos estudos; não confundir com pico no sangue em uma a duas horas nem prometer resposta individual.

Equivalence assessment: A referência distingue pico de concentração e redução do colesterol nos estudos. A proposta pede a segunda informação sem revelar o prazo.

Potential impact: Mesma necessidade temporal com modalidade mais cotidiana. A resposta deve preservar a origem observacional; não exigir promessa clínica de prazo.

New directed documentary check before change: **not additionally required by wording alone**. Conferência feita contra a citação vigente. Nenhum dado de desempenho do sistema foi utilizado.

Binding: `docs/evaluation/golden_set/expansion/batch10/questions.draft.jsonl:31` · revision 1 · record SHA-256 `b1065341b3ea1f7dac33de5bdc1e0a2e16b68b50e0f6e1aaa042ab6ece6e75d0`.

