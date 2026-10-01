# Rodada-base isolada de evidence selection

## Escopo congelado

Uma única rodada-base, com exatamente 12 casos: quatro regressões documentais e oito fixtures sintéticos explicitamente diagnósticos. Os sintéticos não são bulas reais, orientações clínicas nem validação em novos medicamentos. O retrieval gap identificado como caso 4 na bateria histórica permanece fora desta avaliação; a numeração desta tabela é a do benchmark isolado, não a da bateria histórica.

Execução: 2026-09-29T02:45:11.988860+00:00 (UTC; 28/09/2026 no horário de São Paulo).
Modelo observado nas 12 respostas: `sabiazinho-4`. Configuração: provider `auto`, modelo Maritaca `sabiazinho-4`, fallback configurado `openai/gpt-5.4-mini`, habilitado. Não houve falha técnica registrada.

Foram enviados somente pergunta, units congeladas e histórico vazio, com o prompt, formatter, cliente/modelo e structured output existentes. Golds e anotações não foram enviados. Não houve retrieval, embeddings, banco, renderer ou pós-processamento clínico. Os IDs decodificados foram avaliados diretamente, com a verificação de pertencimento ao conjunto candidato.

Não houve tuning, mudança de golds, paráfrases, alteração de ordem ou segunda rodada. Nenhuma mudança em produção, prompt ou arquitetura nesta execução. Apenas os relatórios desta rodada foram adicionados; alterações anteriores no worktree foram preservadas.

## Métricas agregadas

| Métrica | Resultado / denominador |
| --- | --- |
| Casos tentados / válidos | 12 / 12 |
| Casos positivos / negativos válidos | 9 / 3 |
| Precision micro | 68,75% (11 evidências corretas / 16 selecionadas) |
| Recall micro | 78,57% (11 evidências corretas / 14 golds) |
| Precision macro | 70,83% (12 casos com valor definido) |
| Recall macro | 83,33% (9 casos com valor definido) |
| Exact set match | 6/12 (50%) |
| Evidências tangenciais | 5/16 selecionadas (31,25%) |
| Casos com seleção tangencial | 4/12 (33,33%) |
| False abstention | 0/9 positivos (0%) |
| Erros em negativos | 3/3 negativos (100%) |
| Falhas técnicas | 0/12 tentados (0%) |

Precision = TP/IDs selecionados. Recall = TP/gold IDs. Tangenciais = IDs selecionados fora do gold. Valores sem denominador são indefinidos (—), não 100%. Não existe nota composta.

## Métricas por caso

| Caso | Origem | Gold | Selecionados | Precision | Recall | Exact | Tangenciais: quantidade / taxa | False abstention | Erro negativo | Falha técnica |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Indicação bacteriana / virose | Regressão documental | E1, E2 | E1 | 100.0% | 50.0% | Não | 0 / 0.0% | Não | — | Não |
| 2. Idade dos comprimidos / tabelas renais | Regressão documental | E2, E6 | E6, E14 | 50.0% | 50.0% | Não | 1 / 50.0% | Não | — | Não |
| 3. Ausência de diabetes / segurança | Regressão documental | ∅ | E1, E6 | 0.0% | — | Não | 2 / 100.0% | Não | Sim | Não |
| 4. Condição expressa na gravidez | Regressão documental | E2, E6 | E2 | 100.0% | 50.0% | Não | 0 / 0.0% | Não | — | Não |
| 5. Conservação | Sintético diagnóstico | E1 | E1 | 100.0% | 100.0% | Sim | 0 / 0.0% | Não | — | Não |
| 6. Via de administração | Sintético diagnóstico | E2 | E2 | 100.0% | 100.0% | Sim | 0 / 0.0% | Não | — | Não |
| 7. Conservação + prazo após abertura | Sintético diagnóstico | E1, E2 | E1, E2 | 100.0% | 100.0% | Sim | 0 / 0.0% | Não | — | Não |
| 8. Via + refeições | Sintético diagnóstico | E1, E3 | E1, E3 | 100.0% | 100.0% | Sim | 0 / 0.0% | Não | — | Não |
| 9. Contraste de via / pele | Sintético diagnóstico | E1 | E1 | 100.0% | 100.0% | Sim | 0 / 0.0% | Não | — | Não |
| 10. Embalagem danificada | Sintético diagnóstico | E2 | E2 | 100.0% | 100.0% | Sim | 0 / 0.0% | Não | — | Não |
| 11. População não mencionada | Sintético diagnóstico | ∅ | E1 | 0.0% | — | Não | 1 / 100.0% | Não | Sim | Não |
| 12. Interação não mencionada | Sintético diagnóstico | ∅ | E1 | 0.0% | — | Não | 1 / 100.0% | Não | Sim | Não |

## Interpretação, sem ajuste

- Todos os nove casos positivos receberam ao menos uma unit gold; não houve falsa abstenção.
- No caso 2, E6 sustenta a restrição etária, mas E14 trata de uma tabela renal pediátrica e é tangencial à pergunta. E2, também relevante à faixa etária da apresentação, ficou de fora.
- No caso 3, E1 (outras contraindicações) e E6 (indicação bacteriana) não sustentam a conclusão de segurança para diabetes. Ambos foram selecionados indevidamente.
- Nos sintéticos diagnósticos 11 e 12, o modelo selecionou respectivamente uma orientação para outra população e uma interação com outro medicamento. Associação temática não resolve a proposição perguntada.
- Nos casos 1 e 4, a unit selecionada é pertinente. A omissão de uma segunda unit gold reduz cobertura/exact match, mas não demonstra, por si só, impossibilidade de responder: há evidência redundante ou complementar no gold.
- Os três negativos exigiam zero IDs, mas nenhum retornou esse conjunto. Esse resultado expõe a dificuldade residual de rejeitar distratores, separada da boa cobertura nos positivos e da estabilidade técnica.
- A avaliação mede seleção documental, não a segurança ou fidelidade de respostas finais. Não permite concluir que o renderer autorizaria uso, nem substitui a avaliação principal do TCC.

## Rastreabilidade

Fixture SHA-256: `c32832b346e86c649d360e34e3a8d77313df7ee6d6c27b50175971e87300fe16`.
Prompt renderizado sem entradas SHA-256: `60041f2820b2dd80d6dbe4ca554862039544c00f0a0b87ab85897ca643238850`.

Hashes de arquivos protegidos conferidos após a rodada e iguais aos valores anteriores:

| Arquivo | SHA-256 |
| --- | --- |
| chain.py | D59803855DA6DDCDACA72CF105384C5279F34C55AE7C951148AA37FC8754EB19 |
| context_assessment.py | A0FC80829A0CD958DB2C4AEA58AF711CA1EDCB9E6CD6ACC18DE1EC47D386605A |
| evidence_units.py | C8A1BBCF7D368A465E01ED6E3883CC8B9EFBD317B99A0173AE56FEF33469659C |
| llm.py | 4AF2B1B70327C98373D4BCAEE452CA6EA7FA67D9A62FEEC6B3E09857D2A02D2F |
| retriever_factory.py | 3823B59D2970243220953D7AAE1E249EC9C79043AD87394206C2D007F0405454 |
| extractive_safety_answer.py | E5DF9C413B519A9977AC7B9BDD32EDF12738BB851A987F03D52C76AB1BABC2A5 |

Os 19 testes offline do avaliador passaram. `git diff --check` passou. As advertências de compatibilidade/depreciação das bibliotecas não produziram falha nesta rodada.

Os detalhes estruturados, IDs ausentes/tangenciais, tempos e metadados por caso estão em [evidence_selection_base_results.json](evidence_selection_base_results.json). Nenhuma chave, resposta bruta do modelo ou sessão foi armazenada.
