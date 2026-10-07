# TCC2 — decisões sobre o desenho experimental e viabilidade

Registro: 06/10/2026. Status: planejamento pré-experimental, ainda sem geração de perguntas ou execução de avaliações.

Este documento registra as escolhas discutidas com o autor. Não substitui o texto metodológico do TCC2 nem representa um experimento executado. O projeto pertence ao autor; o backlog é direcionamento, não uma especificação obrigatória. Mudanças no protocolo não dependem de aprovação do responsável pelo backlog.

## 1. Decisões e pontos ainda abertos

| Tema | Registro |
| --- | --- |
| Método de pesquisa | Preservar pesquisa aplicada, DSRM, verificação técnica e avaliação experimental documental. Não realizar validação clínica, estudos com pacientes ou treinamento de modelos. |
| Estratégias | Comparar BM25, recuperação densa e híbrida sobre os mesmos documentos e chunks. |
| Corpus A | Preservar as 50 bulas selecionadas por máxima variação documental, sem alegar otimização matemática comprovada. |
| Corpus B | Preservar as 50 bulas organizadas em cinco grupos recorrentes, dez por grupo. Proximidade temática esperada não significa dificuldade maior já demonstrada. |
| Modalidades | Manter como desenho-alvo a comparação por bula e cross-bula em ambos os corpus. |
| Volume por bula | O autor prefere preservar o padrão do TCC1: dez necessidades, oito com evidência e duas sem evidência. Adotar 8+2 como plano preferido, condicionado à medição de esforço no piloto; 4+1 não foi adotado como redução definitiva. |
| Reutilização | Compartilhar necessidade informacional e referência documental entre modalidades, revendo a equivalência das formulações. |
| Perguntas multi-documento | Recomendação ainda a confirmar: fora das médias da avaliação principal, limitadas a demonstração técnica ou bateria complementar posterior. |
| Critérios e configuração | Congelar antes da rodada principal; versões, valores e mapeamentos ainda precisam ser registrados. Nenhum parâmetro técnico foi congelado por este documento. |
| Benchmark do seletor | Manter como validação auxiliar de groundedness durante o desenvolvimento; não substituir a contribuição principal do TCC. |
| Modelo Maritaca escolhido | Usar `sabia-4`, reafirmado pelo autor, conforme comparação auxiliar e [PR #250](https://github.com/Yuussuke/Bula-AI/pull/250). Não reabrir a comparação de modelos; reconciliar o default publicado e conferir o modelo efetivamente executado. O modelo do judge continua a definir. |
| Escopo funcional pendente | Concluir e verificar cross-bula, resposta natural fundamentada e instrumentação antes da avaliação completa. |

Manifestos documentais: [Corpus A](corpus/corpus_final.csv), [piloto disjunto](corpus/corpus_pilot.csv) e [Corpus B](corpus_b/corpus_b_final.csv). Justificativas de seleção: [relatório A](corpus/corpus_selection_report.md) e [relatório B](corpus_b/corpus_b_selection_report.md). Não alterar esses conjuntos a partir do desempenho do sistema.

## 2. Condições e limites da comparação

| Corpus | Por bula | Cross-bula |
| --- | --- | --- |
| A | Localizar evidência em documento conhecido, com variação estrutural entre documentos | Localizar documento e evidência na coleção heterogênea |
| B | Localizar evidência dentro dos documentos dos grupos recorrentes | Localizar documento e evidência com distratores tematicamente relacionados |

São duas coleções × duas modalidades × três estratégias = **12 condições experimentais**. Modalidades e corpus são condições de análise; a estratégia de recuperação permanece o foco principal. A comparação deve ser pareada dentro de cada condição.

No modo por bula, o filtro documental fornece a identidade do documento. As demais bulas não competem diretamente. Portanto, B por bula não é uma avaliação de confusão entre medicamentos semelhantes.

No cross-bula, pesquisar apenas os 50 documentos da coleção correspondente, sem passar o documento gold como filtro oculto. Não reunir A e B em uma coleção de cem durante essa comparação. Identificação do medicamento na pergunta não autoriza injetar a resposta ou a referência gold no pipeline.

Corpus A e B diferem em múltiplas características. Resultados diferentes descrevem comportamento nessas coleções, não provam efeito causal isolado de proximidade semântica, extensão ou layout. A inclusão do nome do medicamento também altera a consulta entre modalidades: não se trata de uma ablação que isola apenas o filtro.

O escopo experimental continua sendo documentos oficiais do tipo system. Private/shared e autorização devem ser verificados tecnicamente, mas não acrescidos ao conjunto experimental. Filtrar somente por system não basta se o ambiente contiver outras bulas oficiais fora dos manifestos.

## 3. Necessidades informacionais, formulações e golds

Uma necessidade representa a proposição que se quer responder para um medicamento/apresentação. Não confundir necessidade, texto de pergunta e execução.

O instrumento de referência deve preservar documento, tema, proposição, classificação documental, seção/página, evidência textual e condições que não podem ser omitidas. Associar IDs de chunks apenas após conferir e congelar a ingestão. Não definir golds pelas respostas do retriever ou do seletor.

As formulações por bula e cross-bula devem preservar população, condição, apresentação, relação perguntada e resposta esperada. Acrescentar identificação do medicamento, forma ou concentração somente quando necessário para tornar o alvo inequívoco. Não converter consulta documental em comparação de tratamentos ou autorização individual.

Reutilizar o gold quando essas condições forem satisfeitas. Se a formulação passar a exigir documentos adicionais, revisar o escopo e a anotação: não reutilizar automaticamente o mesmo gold.

### Padrão 8+2

- Oito necessidades positivas com evidência documental suficiente e duas negativas cuja insuficiência seja conferida previamente na fonte para a proposição e apresentação-alvo.
- Cobrir os temas do TCC1: posologia, contraindicações, interações, reações adversas, advertências, gravidez, conservação e composição. A correspondência exata entre oito positivas e oito temas precisa ser fechada antes de gerar o conjunto; não inventar evidência para cumprir uma quota.
- Não forçar toda bula a responder ao mesmo enunciado genérico. Os textos devem ser adequados ao documento sem mudar o objetivo da categoria.
- Negativa documental não é falha de retrieval, descarte pelo seletor, erro de parsing ou falha técnica. Informação de outro medicamento não valida a resposta para o medicamento-alvo.
- Perguntas abrangentes sobre o acervo ou genuinamente comparativas podem mudar a answerability e exigir outro gold. A inclusão desses tipos na bateria principal continua pendente.
- Conferir evidências alternativas igualmente válidas e repetições/overlap antes da rodada. O limite de até dois chunks do TCC1 deve ser reconciliado com o mapeamento real; não penalizar um trecho documental equivalente apenas por anotação incompleta. Casos incompatíveis precisam ter tratamento declarado antes da avaliação.

As variantes e as execuções da mesma necessidade são dependentes, não novas amostras independentes. Perguntas da mesma bula também compartilham documento. Preservar análise descritiva pareada, resultados por tema/bula e a limitação de generalização ao conjunto aplicado.

## 4. Recuperação, seleção e avaliação da resposta

Registrar separadamente:

1. Ranking original retornado pela estratégia, depois da fusão no caso híbrido.
2. Candidatos/contexto apresentados ao seletor, com origem de eventuais complementações.
3. Evidências selecionadas e fontes usadas na resposta final.

Quantidade de candidatos, corte da métrica e quantidade de fontes usadas são parâmetros diferentes. Se o pipeline considerar doze candidatos, ainda é possível calcular Recall@4 sobre os quatro primeiros do ranking original. Uma resposta apoiada no sexto candidato pode estar correta apesar de Recall@4 igual a zero. Não medir o retriever somente pelos source_chunks finais.

A complementação de segurança, quando usada, deve ser identificada e avaliada como parte do pipeline; não contar suas inclusões posteriores como acertos do ranking original. Não adicionar uma ablação extra apenas para aumentar o número de condições.

### Métricas mantidas

- Recall@4: fração dos chunks gold encontrados nos quatro primeiros resultados do ranking definido.
- MRR@4: média do inverso da posição do primeiro chunk gold; zero se ele não estiver no top-4. Verificar somente se algum gold aparece no top-4 não é MRR.
- Negativas sem gold: Recall/MRR não aplicáveis; fora das respectivas médias, com denominadores explícitos.
- Faithfulness via RAGAS, fidelidade documental rubricada via LLM-as-a-Judge, taxa de alucinação documental, abstenção adequada, FRES adaptado e rastreabilidade, conforme o TCC1.
- Latência P50/P95 como indicador descritivo, sem pressupor qual método será mais rápido.
- Registrar abstenções em positivas e sua causa para não premiar uma configuração que deixe de responder aos casos respondíveis.
- Separar respostas de abstenção de respostas informativas na interpretação de fidelidade e legibilidade. Resposta sem claims avaliáveis não deve receber automaticamente Faithfulness perfeita.
- Falhas técnicas e falhas do avaliador devem permanecer identificadas, com tratamento e denominadores predefinidos; não convertê-las em negativas documentais ou descartá-las silenciosamente.

Para cross-bula, acrescentar somente diagnósticos de presença da bula correta no top-4 e de atribuição de informação de outro medicamento ao alvo. São análises derivadas da rastreabilidade, não uma nota composta nem um novo framework.

A avaliação completa permanece dirigida à resposta natural fundamentada. O mecanismo extrativo auxilia desenvolvimento e diagnóstico; não substitui automaticamente a geração prevista. O modelo avaliador e a auditoria manual estratificada devem ser definidos antes da rodada, incluindo eventual viés por proximidade com o gerador.

### Divisão do trabalho: referência, avaliação e auditoria

- **Preparação do golden set:** perguntas e referências podem ser inicialmente elaboradas com auxílio de LLM. Conferir na fonte as evidências, as condições e a ausência documental antes do congelamento; não derivar golds dos resultados do RAG.
- **Avaliação das respostas:** automatizada por RAGAS/Faithfulness e LLM-as-a-Judge, além das métricas calculadas a partir dos registros. Não está prevista a pontuação manual de todas as respostas.
- **Auditoria humana:** revisão documental de uma amostra estratificada pelo autor. O TCC1 a menciona explicitamente como controle complementar quando avaliador e gerador pertencem ao mesmo provedor/família. Tamanho, seleção e tratamento de divergências ainda precisam ser fixados antes da rodada principal.

A conferência técnica e o roteiro imediato estão em [prontidão do piloto](pilot_readiness.md). Previsão metodológica não equivale a funcionalidade já implementada.

## 5. Dimensionamento: efeito de preservar 8+2

| Quantidade | TCC1 | Alternativa 4+1 discutida | Plano preferido 8+2 |
| --- | ---: | ---: | ---: |
| Documentos | 50 | 100 | 100 |
| Necessidades por documento | 10 | 5 | 10 |
| Necessidades documentais | 500 | 500 | 1.000 |
| Positivas | 400 | 400 | 800 |
| Negativas | 100 | 100 | 200 |
| Formulações/modalidades por necessidade | Uma condição de consulta por par | 2 | 2 |
| Estratégias por modalidade | 3 | 3 | 3 |
| Execuções | 1.500 | 3.000 | 6.000 |

Com 8+2, cada corpus terá 500 necessidades: 400 positivas e cem negativas. Cada corpus produzirá 3.000 execuções. Os totais das duas coleções são 1.000 necessidades, até 2.000 formulações associadas e 6.000 execuções, sem repetições adicionais. Formulações podem coincidir quando a identificação já estiver explícita.

Preservar 8+2 mantém a proporção 80/20 e a granularidade do TCC1 por documento. Não é necessário duplicar a anotação de evidência para as duas modalidades, mas é necessário conferir a equivalência. O número de chamadas de modelo não é igual ao de execuções: seleção, geração, RAGAS, judge e retries podem acrescentar chamadas.

### Esforço de anotação — cenários, não medições

Tempo médio por necessidade completa deve incluir preparação/revisão da pergunta, leitura/conferência da referência, classificação, adaptação entre modalidades e registro/mapeamento. Leitura e preparação do documento são compartilhadas, por isso dobrar perguntas não implica dobrar todo o esforço fixo. O trabalho adicional de anotação, entretanto, é significativo.

| Média por necessidade | 500 necessidades | 1.000 necessidades | Acréscimo aproximado |
| --- | ---: | ---: | ---: |
| 3 minutos | 25h | 50h | 25h |
| 5 minutos | 41,7h | 83,3h | 41,7h |
| 8 minutos | 66,7h | 133,3h | 66,7h |

Não são tempos observados nem promessa de velocidade. A proporção de tabelas, extensão, apresentação múltipla e negativas pode aumentar o tempo. Revisar evidências negativas não é necessariamente mais rápido que anotar positivas.

Esses cenários referem-se à preparação/conferência das necessidades e referências, **não à revisão humana de cada resposta produzida**. Não usar esses números hipotéticos para decidir antecipadamente entre 8+2 e 4+1. Medir no piloto o esforço com auxílio de LLM e conferência documental, separadamente da execução automática e da auditoria amostral.

### Tempo automático — estimativas condicionais

| Duração por execução | 3.000 execuções sequenciais | 6.000 execuções sequenciais |
| --- | ---: | ---: |
| 10 segundos | 8,3h | 16,7h |
| 30 segundos | 25h | 50h |

Esses cenários não incluem chamadas adicionais de avaliadores, filas, retries ou indisponibilidade. Paralelismo pode reduzir tempo de parede, condicionado aos limites reais do provedor. O operador não precisa acompanhar todas as chamadas, mas precisa de checkpoint, retomada e registro para evitar repetir toda a bateria. Automatização não elimina a necessidade de conferência documental.

## 6. Prazo e critério de viabilidade

Disponibilidade informada: três horas por noite de segunda a sexta; fins de semana com disponibilidade maior ainda não quantificada. Em quatro semanas, dias úteis fornecem aproximadamente 60h. Se forem seis a dez horas totais por fim de semana, o orçamento fica em 84–100h; essa parcela é hipótese, não disponibilidade confirmada.

Entrega escrita informada: 23/11/2026. Metas de planejamento: implementação e avaliações até 01/11; texto revisado até 20/11; margem de entrega de 21 a 23/11. A redação final está fora do mês destinado à implementação/avaliação, mas registros mínimos precisam ser produzidos durante o experimento.

A janela concreta de 07/10 a 01/11 tem 18 dias de segunda a sexta (54h) e quatro fins de semana. Com a hipótese de seis a dez horas por fim de semana, a capacidade seria **78–94h**, menor que quatro semanas completas. Não foram presumidas horas adicionais em feriados.

Reservando como hipótese 30–40h para implementação, integração, instrumentação, auditoria e imprevistos, restariam 38–64h para anotação nessa janela. Para mil necessidades, a média teria de ficar aproximadamente em **2,3–3,8 minutos por necessidade completa**. Esse intervalo é um cálculo de capacidade, não recomendação de apressar a revisão.

Se a média real for cinco minutos, a anotação sozinha consumirá cerca de 83h e o trabalho total ficará em aproximadamente 113–123h sob essas hipóteses. Manter 8+2 seria então apertado para o período estimado, exigindo mais horas ou revisão de escopo antes da rodada principal.

### Marco de decisão após o piloto

1. Usar o piloto disjunto para exercitar fluxo completo, registro, anotação, ingestão, métricas e avaliação da resposta.
2. Medir tempo ativo de anotação e revisão; registrar também preparação/leitura por documento para não esconder esforço fixo.
3. Projetar horas restantes de implementação, anotação e auditoria com margem. Uma única bula piloto não garante o mesmo tempo em documentos longos ou com tabelas.
4. Preservar 8+2 se a projeção couber com margem, sem reduzir rigor. Caso contrário, discutir explicitamente volume ou condições antes da rodada principal; não reduzir automaticamente.
5. Não decidir quais documentos/perguntas retirar pelos resultados dos retrievers. Reduzir apenas chamadas de geração não resolve um gargalo de mil anotações.

## 7. Caminho de entrega e congelamento

| Meta | Critério de saída |
| --- | --- |
| Até 11/10 | Protocolo operacional mínimo e piloto que permita medir esforço; validar ou rever volume previsto. |
| Até 18/10 | Cross-bula, resposta natural e registro funcionando; condições de ingestão prontas para congelamento. Se houver bloqueio, rever cronograma/escopo. |
| Até 25/10 | Referências documentais revisadas, PDFs/ingestão conferidos, golds associados e configuração congelada. |
| 26/10–01/11 | Rodada principal, tratamento registrado de falhas, auditoria e resultados consolidados. |
| 02/11–13/11 | Atualização da metodologia/implementação e redação dos resultados e discussão. |
| 14/11–20/11 | Revisão de coerência, limitações, referências, formatação e PDF final. |
| 21/11–23/11 | Margem e entrega; não reservar funcionalidades novas para esse período. |

As datas são metas, não resultados concluídos. Referências em nível PDF podem ser anotadas antes da ingestão definitiva; IDs dependem do congelamento. Correções técnicas exigem registro de versão e das execuções afetadas. Não fazer tuning de prompt, modelo ou parâmetros com base nas notas da rodada principal.

## 8. Pendências a fechar antes de gerar perguntas

- Confirmar quais tipos entram na bateria principal: recomendação de necessidades com documento-alvo único, sem comparações genuinamente multi-bula.
- Confirmar distribuição das oito positivas pelos temas e política para temas sem evidência aplicável.
- Validar viabilidade de 8+2 pelo piloto; confirmar disponibilidade total dos fins de semana.
- Fixar commit, parser/chunker, modelo de embeddings, IDs, configuração do gerador/seletor e prompts.
- Distinguir quantidade de candidatos, corte @4, orçamento de contexto e complementação de segurança; não congelar valores apenas por terem aparecido como exemplos na discussão.
- Definir avaliador, versões, rubrica, tamanho/seleção da auditoria, política de falhas, retries e fallback.
- Manter nos roteiros de avaliação a definição correta de MRR e o dimensionamento. Não exigir resultados diferentes ou rankings sempre não vazios: empate e ausência de evidência são resultados válidos.
- Demonstração multi-bula e verificações shared/private não precisam virar fatores experimentais; adequar referências antigas ao armazenamento atual sem ampliar o protocolo.

Nenhum código de produção, corpus, configuração, índice ou documento do TCC foi modificado por este registro. Nenhuma pergunta/gold foi gerada, nenhum RAG/avaliador foi executado e nenhuma chamada paga foi realizada.
