# Avaliação do TCC — preparação do piloto

Esta pasta versiona os artefatos finais de preparação, não resultados de uma
avaliação já executada. A investigação isolada do seletor permanece auxiliar;
não substitui a avaliação principal do assistente RAG.

## Artefatos canônicos

- [Corpus A](corpus/corpus_final.csv): 50 PDFs selecionados por diversidade
  documental; [justificativa e características](corpus/corpus_selection_report.md).
- [Corpus B](corpus_b/corpus_b_final.csv): 50 PDFs organizados em cinco grupos
  recorrentes; [justificativa e características](corpus_b/corpus_b_selection_report.md).
- [Piloto](corpus/corpus_pilot.csv): PETIVIT BC, P001, fora dos dois corpus.
- [Auditoria de downloads](corpus/download_audit_report.md): registro histórico
  do lote inicial, anterior à seleção final.
- [Decisões experimentais](experimental_design_decisions.md): desenho-alvo,
  métricas, dimensionamento, limites e decisões ainda abertas.
- [Prontidão do piloto](pilot_readiness.md): diagnóstico técnico fixado à versão
  examinada e sequência de implementação/avaliação.

Os três manifestos têm 101 hashes e registros distintos. Importar IDs, registros,
processos e CNPJ como texto. Não usar desempenho do RAG para mudar a seleção.
PDFs, caminhos pessoais absolutos, filas exploratórias, scripts temporários e
manifestos intermediários duplicados não estão incluídos. Os PDFs precisam ser
preservados fora das pastas temporárias; um caminho de arquivo no CSV não
significa que o arquivo esteja distribuído pelo Git.

## Próximo passo

Preparar e conferir as dez necessidades do piloto (oito positivas e duas
negativas). Implementar a resposta natural fundamentada sobre a base existente,
preservando autorização e rastreabilidade; depois conectar o runner de avaliação
com ranking original, fontes finais, métricas e tratamento separado de falhas.
Cross-bula e isolamento por coleção também precisam ser verificados antes da
rodada principal. Nenhuma dessas funcionalidades é entregue por estes documentos.
