# TCC2 — conferência técnica e próximo passo do piloto

Data: 06/10/2026. Status: inspeção estática e planejamento operacional; piloto ainda não executado.

Este relatório descreve a versão fixada abaixo, **antes da consolidação**. A PR que o publica também incorpora os commits pendentes do default `sabia-4` e a correção local de identidade do medicamento. Isso não completa as lacunas de geração/avaliação descritas aqui nem comprova a configuração dos containers.

## 1. Escopo e versão examinada

Objetivo: conferir se o projeto consegue executar o protocolo previsto no TCC1, com as duas coleções já selecionadas, sem acrescentar benchmarks, modelos concorrentes ou etapas de verificação ao produto.

- Código publicado: `Yuussuke/Bula-AI`, `main`, commit `e35e232e7f69a00f6798eac55c6e093943277753` (merge da PR #255).
- Checkout de trabalho: `fix/parser-medication-identity`, commit `d75db980d0e099ee56c526d9f750d57e56581334`, anterior à main publicada, com alterações locais de parsing. Foi preservado, sem checkout, merge, reset ou sincronização.
- Fontes locais: [decisões experimentais](experimental_design_decisions.md), manifestos A/B e piloto. A avaliação principal permanece documental, não clínica.
- O Docker não respondeu: a conexão com `dockerDesktopLinuxEngine` falhou. Não se concluiu nada sobre índices, migrations, PDFs efetivamente ingeridos, modelos em execução ou estado do banco.
- Não foram executados pytest, ingestão, RAG, judge, RAGAS ou chamadas pagas. Os testes mencionados abaixo foram inspecionados, não executados nesta conferência.

## 2. O que já existe e o que falta

| Requisito | Evidência no código publicado | Situação para o piloto |
| --- | --- | --- |
| Três estratégias sobre uma pergunta | `AskRequest.mode`, `ChatService.ask_bula_question` e `RetrieverStrategyFactory` selecionam dense/BM25/hybrid. | Base implementada; falta execução controlada e registro experimental. |
| Autorização por bula | O serviço consulta `get_queryable_by_id_for_user` antes da construção da chain. Bula privada exige titularidade; system exige ready, publicação e integridade do objeto. | Preservar. Há testes de acesso e persistência no chat. |
| Retrieval sem documento conhecido | As fábricas aceitam `bula_id=None` e escopo explícito de `BulaCorpus`; há testes de interseção de filtros. | Implementado no componente interno, não no chat geral. |
| Chat cross-bula | `ChatService.answer_question` lança `DirectAskUnavailableError`; `/direct-ask` responde 501. `RAGChainFactory.build_chain` ainda exige UUID de bula. | Lacuna funcional demonstrada. |
| Isolamento das 50 bulas de A ou B | `corpus` significa system/shared/private, não coleção experimental A/B. Não foi encontrada seleção de uma lista de 50 IDs nas interfaces examinadas. | Falta definir isolamento experimental; system sozinho não basta num índice misto. |
| Resposta natural fundamentada | A chain solicita IDs/limitation e `validate_extractive_safety_answer` monta citações extrativas. O log registra `generation_status="not_implemented"`. | Falta a geração natural prevista no artefato final. |
| IDs e ranks para Recall/MRR | Documentos internos preservam `chunk_id`/`bula_id`; híbrido registra ranks por ramo e RRF. A resposta pública conserva somente seção/texto/score. | Falta captura experimental do ranking antes das complementações e da seleção. |
| Observabilidade | `ResponseStageObserver` registra duração/falha por etapa; validação distingue erros JSON/schema/IDs de seleção vazia. | Reutilizar, mas logs não constituem uma tabela experimental completa. |
| Runner e exportação da avaliação principal | A árvore publicada contém scripts de parsing/chunking/playground, mas não foi encontrado runner do protocolo ou cálculo das métricas previstas. | Implementação de avaliação ainda necessária. |
| RAGAS e judge rubricado | Não encontrados na implementação examinada; RAGAS não consta no `pyproject.toml` publicado. | Previstos na metodologia, não implementados nessa versão. |
| Configuração fixa do seletor | A escolha é `sabia-4`, documentada na PR #250 e reafirmada pelo autor. Seus dois commits ainda não chegaram à main, que declara `sabiazinho-4`. | Decisão de modelo fechada; incorporar a alteração pendente e confirmar execução antes do congelamento. |

Ausência na versão publicada não prova ausência em branches ou scripts temporários. Estes não devem ser considerados componentes entregues sem revisão e incorporação explícitas.

### Fontes de código, fixadas ao commit examinado

- [Serviço de chat](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/chat/service.py), [router](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/chat/router.py) e [schemas](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/chat/schemas.py).
- [Chain](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/rag/chain.py), [renderer/validação extrativa](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/rag/extractive_safety_answer.py) e [diagnósticos](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/rag/response_diagnostics.py).
- [Fábrica de estratégias](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/rag/retriever_factory.py), [dependências](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/rag/dependencies.py), [fábrica híbrida](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/rag/hybrid_factory.py) e [complementação por seção](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/rag/section_evidence_retriever.py).
- [Configuração](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/core/config.py), [provedores/fallback](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/app/modules/rag/llm.py), [dependências do pacote](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/pyproject.toml), [PR #250](https://github.com/Yuussuke/Bula-AI/pull/250).
- [Testes de escopo dos retrievers](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/tests/integration/rag/test_corpus_retrieval.py) e [testes de chat](https://github.com/Yuussuke/Bula-AI/blob/e35e232e7f69a00f6798eac55c6e093943277753/backend/tests/integration/chat/test_chat.py).

## 3. Cuidados que afetam a validade do experimento

### Ranking recuperado não é a lista de fontes finais

No commit examinado, a fábrica usa `k=4`. No híbrido, cada ramo recebe até `3*k=12` candidatos e a fusão retorna até quatro resultados. Dense ainda faz seu over-fetch interno para remover candidatos inelegíveis. Isso **não significa doze fontes apresentadas ao seletor**.

Por bula, o `SectionEvidenceRetriever` pode acrescentar até duas seções de segurança, colocando-as antes do ranking original. A preparação da chain pode filtrar documentos administrativos e restringir perguntas de contraindicação. A validação seleciona/reordena as fontes citadas. Por isso:

- Calcular Recall@4/MRR@4 sobre o resultado da estratégia com sua elegibilidade definida, antes da complementação por seção e da preparação/seleção.
- Preservar separadamente ranking, contexto candidato e fontes finais, dentro da mesma execução. Não repetir retrieval para tentar reconstruir depois o ranking que gerou uma resposta.
- Registrar complementações e filtros; não creditá-los ao ranking original nem escondê-los na interpretação das diferenças entre modalidades.

No cross-bula, as dependências atuais não usam a complementação por seção quando `bula_id=None`. A comparação entre modalidades deve declarar essa diferença do pipeline, não apresentá-la como isolamento puro do efeito do filtro documental.

### Modelo escolhido não é necessariamente o modelo executado

**Decisão preservada: usar `sabia-4`, sem Thinking.** A [PR #250](https://github.com/Yuussuke/Bula-AI/pull/250), mergeada em `fix/rag-evidence-core` em 01/10/2026, registrou a mudança em configuração, `.env.example`, README do backend e testes de configuração. O autor reafirmou essa escolha; não há necessidade de repetir a comparação para decidir o modelo nesta etapa.

A justificativa registrada na PR é uma comparação auxiliar de 12 casos, com três repetições: `sabia-4` apresentou 0/9 erros nos negativos e 0/36 chamadas com evidências tangenciais, contra 3/9 e 6/36 em `sabiazinho-4`; ambos cobriram 27/27 positivos. Uma rodada posterior encontrou um caso tangencial residual em `sabia-4`, enquanto Thinking apresentou um erro em negativo e maior latência. Esses resultados motivam a escolha do seletor, mas não demonstram qualidade do pipeline completo nem validação clínica. Não transformar a investigação auxiliar em nova avaliação principal do TCC.

O blob de configuração no merge da PR #250 declara `sabia-4`; o blob da main examinada declara `sabiazinho-4`. A conferência posterior confirmou a causa: a PR #249 foi mergeada na main antes de a PR #250 ser mergeada na sua antiga branch-base `fix/rag-evidence-core`. Os commits `b000a86` (configuração/teste) e `e6136db` (documentação) permanecem fora da main. Não se trata de uma reversão demonstrada do default; a alteração não chegou à linha principal. Incorporá-los em uma PR direcionada à main, sem repetir o benchmark. O `.env` pode sobrescrever o default, portanto não foi identificado o modelo efetivamente em execução.

A pendência é de coerência técnica com a decisão já tomada, não de escolha de modelo. O modelo do judge permanece uma decisão separada; não assumir automaticamente `sabia-4` como avaliador.

O fallback está habilitado por padrão e pode trocar o provedor em falha transitória. A avaliação precisa fixar/configurar o modelo pretendido e registrar o efetivamente observado, tratando fallback separadamente ou desabilitando-o na configuração experimental. Não ler/gravar credenciais nos artefatos.

Temperatura de chat está em 0.2; não assumir automaticamente a temperatura 0.0 descrita como alvo para geração no TCC1. Seletor, futuro gerador e avaliador precisam de configuração registrada por função. Não foi encontrado limite explícito de tokens na construção atual do chat LLM. Registrar os valores reais e reconciliar o texto metodológico antes da rodada principal.

### O benchmark auxiliar não substitui a avaliação principal

O seletor e seus testes são controles de desenvolvimento. Não usar os seus 12 casos, labels ou resultados como avaliação final das respostas naturais nos corpus A/B. A auditoria humana complementar confere suporte textual, não segurança clínica.

## 4. Sequência mínima recomendada

### Passo A — estabelecer uma base reproduzível

1. Preservar alterações locais e arquivos de corpus; preparar uma branch de trabalho baseada na main atual, sem sobrescrever o checkout sujo.
2. Resolver separadamente a divergência do default `sabia-4` e confirmar configuração efetiva, sem iniciar novo tuning de modelo/prompt.
3. Restabelecer o Docker e conferir migrations/serviços. Não reingerir as cem bulas automaticamente.
4. Registrar commit, dependências, configurações não secretas e identificação do PDF piloto.

Critério de saída: saber qual código/configuração será testado e conseguir exercitar dependências locais. Não confundir integração simulada com ingestão real.

### Passo B — preparar a referência do piloto

Usar **P001, PETIVIT BC**, já separado fora das coleções A/B, conforme [manifesto do piloto](corpus/corpus_pilot.csv).

- Preparar dez necessidades: oito positivas e duas negativas verificadas documentalmente.
- Distribuir os temas conforme a fonte; não inventar evidência para cumprir quota temática. Registrar se uma categoria exigir adaptação.
- Registrar pergunta, tema, presença/ausência de evidência, seção/página, trecho esperado e condições indispensáveis.
- Elaborar rascunho com auxílio de LLM e conferir na fonte antes do congelamento. Medir separadamente esse trabalho humano e o tempo automático.
- Conferir parsing/chunks do piloto e associar os IDs à referência documental. Não definir golds pelas escolhas do retriever/seletor.
- Não gerar ainda as mil necessidades do conjunto principal.

Critério de saída: dez referências revisáveis e mapeadas, sem depender de julgamento das respostas do próprio RAG. Perguntas/golds não foram preparados nesta conferência.

### Passo C — completar somente o necessário para avaliar a resposta final

1. Acrescentar a geração natural fundamentada à base existente, mantendo o mecanismo extrativo disponível como diagnóstico e preservando autorização, seleção e validações de identidade. Não acrescentar verifier, corrective retrieval ou vários agentes.
2. Implementar um runner de avaliação reutilizando os componentes da aplicação, com captura de ranking/contexto/fontes e resultados retomáveis. Evitar copiar o pipeline para dentro do script ou aumentar a resposta pública apenas para servir à avaliação.
3. Calcular Recall@4/MRR@4, rastreabilidade, latência e FRES; conectar Faithfulness e judge rubricado no código de avaliação, não no caminho de resposta ao usuário.
4. Definir previamente modelo avaliador, rubrica, tratamento de abstenções, falhas de avaliador/provedor, retries e denominadores. Não atribuir automaticamente nota máxima a abstenção sem claims.
5. Verificar com testes sem API paga os cálculos, exportação/retomada, captura de IDs, preservação de contexto, validação e separação de erros.

Critério de saída: uma pergunta percorre ingestão → retrieval → seleção → resposta natural → avaliação → registro rastreável. A saída extrativa pode testar a infraestrutura, mas não deve ser apresentada como piloto concluído da geração final.

### Passo D — executar as 30 consultas do piloto

Dez perguntas × três modos = **30 execuções independentes de histórico**, no escopo individual. Esse número não inclui chamadas adicionais de seleção, geração e avaliadores.

- Manter as mesmas referências/configurações e alternar a execução dos modos.
- Registrar falhas, fallback, consumo/tempo quando disponíveis, métricas e resultado da auditoria piloto.
- Medir tempo ativo de preparação/conferência, execução automática e auditoria separadamente. Não estimar trabalho como revisão manual das 30 ou das futuras 6.000 respostas.
- Conferir a aplicabilidade da rubrica e corrigir problemas técnicos antes do congelamento principal, documentando ajustes do piloto.
- Usar a medição, não os minutos hipotéticos, para decidir a viabilidade do plano 8+2.

Critério de saída: resultados exportados, reprocessáveis e interpretáveis, inclusive os erros, sem selecionar perguntas/documentos pelos melhores resultados.

### Passo E — integrar e verificar cross-bula antes da rodada principal

- Conectar o chat geral aos retrievers existentes com escopo autorizado e referências contendo a identidade de cada bula. Filtro interno não substitui autorização/publicação.
- Definir um isolamento simples e verificável por coleção experimental. Uma opção a avaliar é usar um ambiente de avaliação com somente o manifesto correspondente nos dois índices; não exige criar novos tipos A/B em produção.
- Verificar tecnicamente com um conjunto pequeno fora da avaliação principal: acesso, exclusão de private/shared no protocolo, identidade das fontes e ausência de consulta a bulas fora do manifesto.
- Não usar o documento gold como filtro oculto nem filtrar somente o top-k depois da busca, pois os documentos externos já podem ter deslocado as evidências relevantes.
- Esse teste técnico não é outro corpus experimental e não cria perguntas comparativas multi-documento na bateria principal.

O piloto com uma única bula não mede competição entre documentos. O cross-bula precisa estar funcional e verificado antes de executar as doze condições principais, mas não deve bloquear a preparação documental do piloto.

## 5. Artefatos mínimos e limites

Manter somente: protocolo versionado, referência piloto, identificação/configuração da execução, resultados exportados com checkpoints e resumo/auditoria. Preferir um runner com módulos pequenos para métricas e avaliadores, não uma família de benchmarks descartáveis. A configuração de avaliação não é uma nova etapa de produção.

Ainda precisam ser fechados: distribuição temática aplicável, modelo do judge, rubrica operacional de alucinação/abstenção, tamanho/seleção da auditoria principal e política de falhas/retries. Esses itens não foram inventados nem congelados por esta conferência.

A conferência estática não executou o piloto nem alterou índices/ambiente. A consolidação posterior publica estes registros, os manifestos canônicos e as correções pendentes em commits separados; suas verificações locais constam da descrição da PR.
