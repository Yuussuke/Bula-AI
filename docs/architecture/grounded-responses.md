# Grounded chat responses

The chat factory now composes retrieval, existing evidence selection/validation,
and natural-language generation. The generator receives only selected evidence
units, their source numbers, the documented limitation and the question/history.
Unselected sentences are not added to the generation prompt. Public API schemas,
source ordering and authorization are unchanged.

`build_rag_chain` remains the extractive diagnostic entry point;
`RAGChainFactory` uses `build_grounded_rag_chain`. Empty valid selection skips
generation and abstains. Invalid selection is recorded as a technical failure,
not insufficient context. Generation failures propagate to the existing safe
exception boundary, without substituting a successful abstention.

The archived `grounded_patient_answer_v1` prompt and 1,024-token generation cap
are reused without tuning. Responses must be nonempty, complete and reference
existing numbered sources. Citation checks validate syntax/identity, **not
semantic entailment**. No verifier, revision, new retrieval or model is added.
`numeric_source_citations_v2` accepts `[1]`, `[1][2]` and `[1,2]` without
rewriting answers. Unknown IDs and malformed numeric markers remain failures,
even when another citation is valid; bracketed prose is not a source marker.
Provider calls, cost and latency can increase by one generation call after a
supported selection; tests use synthetic providers, not paid API calls.

This is a bounded runtime integration, not a claim that the deployed application
already reproduces the [final evaluation](../evaluation/final/reproduction.md).
BGE/RRF-B serving, later evidence-preparation/selection changes, cross-bula
API/UI and frontend synchronization remain separate integration work. Frozen
questions, mappings, snapshots, prompts and experimental results are untouched.
