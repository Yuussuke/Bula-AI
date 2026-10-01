# Comparação congelada de modelos para evidence selection

## Protocolo e integridade

Foram executadas exatamente 72 invocações: os mesmos 12 casos × dois modelos × três repetições. Cada combinação caso/modelo ocorreu três vezes. As repetições são medições dos mesmos cenários, não 72 casos independentes. O conjunto mantém quatro regressões documentais e oito fixtures sintéticos explicitamente diagnósticos. O retrieval gap histórico continua excluído.

Modelos solicitados e observados: `sabiazinho-4` (36 respostas) e `sabia-4` (36 respostas). Temperatura 0.2, mensagens, units, IDs, golds, schema e formatter congelados. A ordem das units não mudou. A ordem dos modelos alternou entre casos e entre repetições, conforme o cronograma registrado no JSON. Cada chamada usou histórico vazio.

Início: 2026-09-30T02:00:18.298160+00:00. Fim: 2026-09-30T02:01:09.267403+00:00. Datas em UTC (noite de 29/09/2026 no horário de São Paulo).

Não houve fallback, erro técnico, identidade de modelo desconhecida ou chamada de reposição. O mecanismo existente de fallback foi observado; qualquer uso seria excluído das comparações atribuídas ao modelo solicitado. Todos os valores de limitation e os tokens foram capturados. Não foram armazenadas respostas brutas, credenciais ou dados de usuários.

Apenas o executor auxiliar, seus testes e relatórios foram adicionados. Nenhum ajuste de prompt, produção, arquitetura, fixture, gold, parser ou retrieval foi feito. Não houve tuning após observar resultados.

## Comparação agregada

Os denominadores de 36 chamadas, 27 positivos e nove negativos refletem repetições de 12, nove e três cenários distintos, respectivamente.

| Métrica | sabiazinho-4 | sabia-4 |
| --- | --- | --- |
| Erros nos negativos | 3/9 (33,33%) | 0/9 (0,00%) |
| Chamadas com tangenciais | 6/36 (16,67%) | 0/36 (0,00%) |
| Casos distintos com tangenciais em alguma repetição | 2/12 | 0/12 |
| Evidências tangenciais / selecionadas | 9/42 (21,43%) | 0/36 (0,00%) |
| Positivos com pelo menos uma gold | 27/27 (100,00%) | 27/27 (100,00%) |
| False abstention | 0/27 | 0/27 |
| Falhas técnicas | 0/36 | 0/36 |
| Fallbacks | 0 | 0 |
| Precision micro / macro | 78,57% / 85,00% | 100,00% / 100,00% |
| Recall micro / macro | 78,57% / 83,33% | 85,71% / 88,89% |
| Exact set match | 24/36 (66,67%) | 30/36 (83,33%) |
| Cobertura de todas as golds nos positivos | 18/27 | 21/27 |
| Latência média por chamada | 675.1 ms | 738.4 ms |
| Tokens de entrada / saída reportados | 28917 / 858 | 28917 / 816 |
| Chamadas com contagem de tokens | 36/36 | 36/36 |

Precision e recall micro usam contagens somadas de evidências. Macro usa somente casos/chamadas com a métrica definida: precision em 30 chamadas para Sabiazinho e 27 para Sabiá; recall em 27 para ambos. Seleção vazia não recebe precision artificial de 100%. O JSON mantém denominadores, médias/faixas e todas as métricas secundárias.

## Cada repetição separadamente

| Modelo | Repetição | Erro negativo | Chamadas tangenciais | Quantidade tangencial | Cobertura positiva | False abstention | Falha técnica | Precision micro | Recall micro | Exact set | Latência média ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sabiazinho-4 | 1 | 1/3 | 2/12 | 3 | 9/9 | 0/9 | 0/12 | 78,57% | 78,57% | 8/12 | 573.7 |
| sabiazinho-4 | 2 | 1/3 | 2/12 | 3 | 9/9 | 0/9 | 0/12 | 78,57% | 78,57% | 8/12 | 730.2 |
| sabiazinho-4 | 3 | 1/3 | 2/12 | 3 | 9/9 | 0/9 | 0/12 | 78,57% | 78,57% | 8/12 | 721.4 |
| sabia-4 | 1 | 0/3 | 0/12 | 0 | 9/9 | 0/9 | 0/12 | 100,00% | 85,71% | 10/12 | 892.9 |
| sabia-4 | 2 | 0/3 | 0/12 | 0 | 9/9 | 0/9 | 0/12 | 100,00% | 85,71% | 10/12 | 651.6 |
| sabia-4 | 3 | 0/3 | 0/12 | 0 | 9/9 | 0/9 | 0/12 | 100,00% | 85,71% | 10/12 | 670.8 |

## Média e faixa entre as três repetições

| Métrica | sabiazinho-4: média [mín–máx] | sabia-4: média [mín–máx] |
| --- | --- | --- |
| negative_case_error_rate | 33,33% [33,33%–33,33%] | 0,00% [0,00%–0,00%] |
| case_tangential_rate | 16,67% [16,67%–16,67%] | 0,00% [0,00%–0,00%] |
| tangential_evidence_count | 3.00 [3.00–3.00] | 0.00 [0.00–0.00] |
| positive_coverage_rate | 100,00% [100,00%–100,00%] | 100,00% [100,00%–100,00%] |
| false_abstention_rate | 0,00% [0,00%–0,00%] | 0,00% [0,00%–0,00%] |
| technical_failure_rate | 0,00% [0,00%–0,00%] | 0,00% [0,00%–0,00%] |
| precision_micro | 78,57% [78,57%–78,57%] | 100,00% [100,00%–100,00%] |
| recall_micro | 78,57% [78,57%–78,57%] | 85,71% [85,71%–85,71%] |
| exact_set_match_rate | 66,67% [66,67%–66,67%] | 83,33% [83,33%–83,33%] |
| mean_latency_ms_all_calls | 675.12 [573.72–730.22] | 738.41 [651.59–892.88] |

As métricas semânticas ficaram iguais entre as três repetições para cada modelo. Isso não representa um intervalo de confiança nem demonstra ausência de variabilidade futura.

## IDs selecionados por caso e repetição

A numeração é a dos 12 casos do benchmark isolado. Casos 5–12 são sintéticos diagnósticos. ∅ significa seleção vazia válida.

| Caso | Modelo | Gold IDs | Repetição 1 | Repetição 2 | Repetição 3 | Conjunto idêntico nas três? |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Indicação / virose | sabiazinho-4 | E1, E2 | E1 | E1 | E1 | Sim |
| 2. Idade / tabelas renais | sabiazinho-4 | E2, E6 | E6, E12 | E6, E12 | E6, E12 | Sim |
| 3. Ausência de diabetes / segurança | sabiazinho-4 | ∅ | E1, E6 | E1, E6 | E1, E6 | Sim |
| 4. Condição na gravidez | sabiazinho-4 | E2, E6 | E2 | E2 | E2 | Sim |
| 5. Conservação | sabiazinho-4 | E1 | E1 | E1 | E1 | Sim |
| 6. Via de administração | sabiazinho-4 | E2 | E2 | E2 | E2 | Sim |
| 7. Conservação + prazo após abertura | sabiazinho-4 | E1, E2 | E1, E2 | E1, E2 | E1, E2 | Sim |
| 8. Via + refeições | sabiazinho-4 | E1, E3 | E1, E3 | E1, E3 | E1, E3 | Sim |
| 9. Contraste de via / pele | sabiazinho-4 | E1 | E1 | E1 | E1 | Sim |
| 10. Embalagem danificada | sabiazinho-4 | E2 | E2 | E2 | E2 | Sim |
| 11. População não mencionada | sabiazinho-4 | ∅ | ∅ | ∅ | ∅ | Sim |
| 12. Interação não mencionada | sabiazinho-4 | ∅ | ∅ | ∅ | ∅ | Sim |
| 1. Indicação / virose | sabia-4 | E1, E2 | E1, E2 | E1, E2 | E1, E2 | Sim |
| 2. Idade / tabelas renais | sabia-4 | E2, E6 | E6 | E6 | E6 | Sim |
| 3. Ausência de diabetes / segurança | sabia-4 | ∅ | ∅ | ∅ | ∅ | Sim |
| 4. Condição na gravidez | sabia-4 | E2, E6 | E2 | E2 | E2 | Sim |
| 5. Conservação | sabia-4 | E1 | E1 | E1 | E1 | Sim |
| 6. Via de administração | sabia-4 | E2 | E2 | E2 | E2 | Sim |
| 7. Conservação + prazo após abertura | sabia-4 | E1, E2 | E1, E2 | E1, E2 | E1, E2 | Sim |
| 8. Via + refeições | sabia-4 | E1, E3 | E1, E3 | E1, E3 | E1, E3 | Sim |
| 9. Contraste de via / pele | sabia-4 | E1 | E1 | E1 | E1 | Sim |
| 10. Embalagem danificada | sabia-4 | E2 | E2 | E2 | E2 | Sim |
| 11. População não mencionada | sabia-4 | ∅ | ∅ | ∅ | ∅ | Sim |
| 12. Interação não mencionada | sabia-4 | ∅ | ∅ | ∅ | ∅ | Sim |

## Frequências por caso

Cada denominador é três chamadas válidas comparáveis. Os IDs não listados na coluna de frequência tiveram frequência 0/3; o JSON enumera explicitamente todos os IDs, inclusive zeros. “—” significa não aplicável: false abstention é avaliada nos positivos e negative-case error nos negativos.

| Caso | Modelo | Frequência de IDs selecionados | Seleção vazia | Chamada com tangencial | False abstention | Erro negativo | Falha técnica |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Indicação / virose | sabiazinho-4 | E1: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 2. Idade / tabelas renais | sabiazinho-4 | E6: 3/3; E12: 3/3 | 0/3 | 3/3 | 0/3 | — | 0/3 |
| 3. Ausência de diabetes / segurança | sabiazinho-4 | E1: 3/3; E6: 3/3 | 0/3 | 3/3 | — | 3/3 | 0/3 |
| 4. Condição na gravidez | sabiazinho-4 | E2: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 5. Conservação | sabiazinho-4 | E1: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 6. Via de administração | sabiazinho-4 | E2: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 7. Conservação + prazo após abertura | sabiazinho-4 | E1: 3/3; E2: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 8. Via + refeições | sabiazinho-4 | E1: 3/3; E3: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 9. Contraste de via / pele | sabiazinho-4 | E1: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 10. Embalagem danificada | sabiazinho-4 | E2: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 11. População não mencionada | sabiazinho-4 | Todos: 0/3 | 3/3 | 0/3 | — | 0/3 | 0/3 |
| 12. Interação não mencionada | sabiazinho-4 | Todos: 0/3 | 3/3 | 0/3 | — | 0/3 | 0/3 |
| 1. Indicação / virose | sabia-4 | E1: 3/3; E2: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 2. Idade / tabelas renais | sabia-4 | E6: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 3. Ausência de diabetes / segurança | sabia-4 | Todos: 0/3 | 3/3 | 0/3 | — | 0/3 | 0/3 |
| 4. Condição na gravidez | sabia-4 | E2: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 5. Conservação | sabia-4 | E1: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 6. Via de administração | sabia-4 | E2: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 7. Conservação + prazo após abertura | sabia-4 | E1: 3/3; E2: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 8. Via + refeições | sabia-4 | E1: 3/3; E3: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 9. Contraste de via / pele | sabia-4 | E1: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 10. Embalagem danificada | sabia-4 | E2: 3/3 | 0/3 | 0/3 | 0/3 | — | 0/3 |
| 11. População não mencionada | sabia-4 | Todos: 0/3 | 3/3 | 0/3 | — | 0/3 | 0/3 |
| 12. Interação não mencionada | sabia-4 | Todos: 0/3 | 3/3 | 0/3 | — | 0/3 | 0/3 |

## Estabilidade e limitation

Os conjuntos de IDs foram idênticos em 3/3 execuções para todos os 12 casos de cada modelo. Não houve instabilidade de seleção dentro desta rodada. Historicamente, os casos 11/12 do Sabiazinho e a unit tangencial do caso 2 já variaram; três repetições consecutivas estáveis não anulam essa observação anterior.

- Sabiazinho: no caso 3, selecionou E1/E6 em todas as execuções, com limitation `scope`, `scope`, `missing`. Portanto, o campo limitation variou em um dos 12 casos, embora os IDs permanecessem iguais.
- Sabiazinho: nos casos 11 e 12, retornou IDs vazios com limitation `scope` e `missing`, respectivamente, nas três execuções. Isso contraria a instrução textual de usar null quando não há IDs, mas é aceito pelo schema atual; não foi reclassificado como falha técnica nem altera as métricas de seleção.
- Sabiá: limitation foi `scope` em 3/3 execuções dos casos 1 e 4 e null em todos os demais. O campo ficou estável nos 12 casos.
- Nos casos 1 e 4, a seleção do Sabiá é pertinente, mas a ressalva merece revisão qualitativa frente à definição anterior de limitation. A fonte delimita a indicação ou explicita a condição necessária. Este benchmark não avaliou o texto final nem o efeito dessa ressalva no renderer; não se conclui que todo o comportamento final esteja resolvido.

## Erros persistentes e diferenças

### Caso 2 — idade e tabelas renais

Sabiazinho selecionou E6, que responde à restrição etária, e E12, uma tabela de insuficiência renal explicitamente rotulada “Adultos”, nas três repetições. A tabela tangencial foi selecionada apesar do contexto estrutural preservado. Sabiá selecionou apenas E6 nas três execuções.

Ambos omitiram E2, outra gold referente à faixa etária da apresentação. A cobertura de todas as golds/exact set diminui, mas a restrição explícita em E6 permanece disponível. Não é falsa abstenção nem perda de toda evidência necessária.

### Caso 3 — ausência de diabetes e segurança

Sabiazinho selecionou E1 (contraindicações para outras condições) e E6 (indicação bacteriana) em 3/3 execuções. Sabiá retornou zero IDs em 3/3. Nenhuma unit gold existe nesse conjunto. Esta diferença persistiu nas três repetições e é diretamente favorável ao Sabiá no critério principal.

### Casos 11 e 12 — grupo Y e medicamento B

Ambos retornaram zero IDs em todas as repetições. Os erros históricos do Sabiazinho não reapareceram nesta rodada. Não atribuir essa mudança a uma alteração de código/prompt nem usar a rodada-base antiga como se fosse o controle contemporâneo desta comparação.

### Casos 1 e 4 — cobertura de golds pertinentes

No caso 1, Sabiá selecionou E1/E2; Sabiazinho selecionou apenas E1. No caso 4, ambos selecionaram E2 e omitiram E6. São diferenças de cobertura de evidências adicionais pertinentes, não seleções tangenciais. Nos demais casos, as seleções dos dois modelos coincidiram.

## Interpretação e próximo passo

A evidência desta rodada favorece Sabiá 4: nas três repetições reduziu erros nos negativos de 1/3 para 0/3 e chamadas tangenciais de 2/12 para 0/12, preservando cobertura dos nove positivos e zero false abstentions/falhas técnicas. O ganho não apareceu apenas em uma repetição.

A hipótese de limitação do Sabiazinho ganhou força para esta tarefa/configuração, principalmente pelos casos 2 e 3. A comparação demonstra dependência do modelo, não isola tamanho, arquitetura interna, dados de treinamento ou alinhamento como causa. A melhora histórica do Sabiazinho nos casos 11/12 e as limitações ainda retornadas pelo Sabiá impedem conclusões universais.

A latência média foi 675,1 ms versus 738,4 ms nesta rodada. Essas medições incluem execução do seletor e variam por repetição; não constituem um benchmark geral de desempenho dos provedores.

Próximo experimento mínimo recomendado, não executado: manter Sabiá 4 e toda a configuração congelados e avaliar estabilidade com uma paráfrase previamente revisada de cada uma das 12 perguntas, preservando units e golds. Tratar as paráfrases como variantes dos mesmos cenários, incluindo observação de limitation nos casos 1/4. Isso verifica sensibilidade à formulação antes de qualquer ajuste de prompt ou promoção do modelo para produção. Validação futura com outras bulas continua necessária na avaliação já prevista do TCC.

Não há nota composta nem inferência de generalização a partir das 36 execuções por modelo. Esta é uma verificação auxiliar de groundedness; seleção correta não substitui avaliação de fidelidade documental das respostas naturais.

## Artefatos e verificações

- [Resumo estruturado dos dois experimentos finais](evidence_selection_model_summary.json).
- Executor: `backend/scripts/compare_evidence_selection_models.py`.
- Testes: `backend/tests/unit/scripts/test_compare_evidence_selection_models.py`.
- 25 testes offline passaram (19 do benchmark-base e seis do executor/contabilidade/observação). Ruff e git diff --check passaram.
- Contagens, tangenciais, cobertura e exact set foram recalculados independentemente a partir dos IDs registrados e conferidos com os agregados.
- Hashes de fixture, prompt, schema, formatter e configuração de modelo permaneceram iguais antes/depois.

Fixture SHA-256: `c32832b346e86c649d360e34e3a8d77313df7ee6d6c27b50175971e87300fe16`.
Prompt SHA-256: `60041f2820b2dd80d6dbe4ca554862039544c00f0a0b87ab85897ca643238850`.
Structured output SHA-256: `2d764ffb05bda932361cba39c04e3ffe87f530b1de7a7774841956e1ff04f2af`.

Os registros completos por chamada foram mantidos fora da PR para reduzir o diff.
