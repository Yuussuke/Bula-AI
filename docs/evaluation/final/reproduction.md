# Evaluated configuration and reproduction boundary

| Component | Execution-bound configuration |
| --- | --- |
| Corpus snapshot | 100 PDFs, 2,974 chunks; fingerprint in `provenance.json` |
| Embeddings | `intfloat/multilingual-e5-large`, 1,024 dimensions, E5 query/passage profile |
| Candidate pool | 20 eligible BM25 + 20 eligible dense; dense raw limit 60 |
| RRF-B | Equal weights, constant 60, deduplicate by chunk ID |
| BGE | `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` |
| BGE input/order | Question + existing section/text; full candidate union; descending logits, chunk-ID tie-break, final ten |
| BGE execution | CUDA FP16, batch 1, no truncation; no silent resource fallback |
| Selection/generation | Sabiá-4, temperature 0.2, frozen structured selection and natural-answer prompts; generation cap 1,024 tokens |
| Judge | `google/gemini-2.5-pro` via OpenRouter; temperature 0, output/reasoning cap 4,096, reasoning budget 1,024 |
| Attempts | No automatic retries or model/provider fallback in the recorded runs |

## Code identity is not the current checkout

The evaluated runtime comes from the isolated controlled-iteration environment
and saved evaluation adapters. Its execution plan records file-level SHA-256,
prompt/schema identities, dependencies and container image digest. A worktree
commit alone does not identify its uncommitted runtime files. The plans and
locks listed in the inventory, not this PR's commit, identify the executed code.

This publication does not enable BGE, replace production prompts, import the
experimental runtime or assert that localhost/deployment matches the experiment.
Integration requires a separate reviewed change and compatibility checks.
Citation syntax/ID validation is not semantic entailment verification. Existing
parser/table losses, cross-source attribution and contextual overreach remain
limitations, not hidden successful outcomes.

## Custodial archive

The inventory records original relative paths, byte hashes and canonical
fingerprints without rewriting any original manifest. It publishes neither
PDFs, database dumps, full questions/answers, personal reviewer exports, browser
state nor large ranking/checkpoint bundles. No public archive URL is claimed.

Full reproduction requires obtaining the author's preserved archive: original
PDFs/chunk export, input questions and qrels, generation/retrieval/BGE plans and
checkpoints, exact runtime/adapter code and locks, human event histories and
judge results. Restore its relative paths and verify each inventory file hash,
then the nested manifests' per-file hashes and canonical fingerprints. Canonical
JSON uses sorted keys, UTF-8, no ASCII escaping and comma/colon separators,
excluding the `fingerprint_sha256` field itself.

In that archive, the read-only closure check is:

```powershell
$env:PYTHONPATH = 'backend'
backend/.venv/Scripts/python.exe tmp/freeze-answer-quality-v1.py --verify
```

It requires the archived tooling and Node, not only this public clone. Original
retrieval scoring scripts and assessment modules are also archive dependencies;
do not fetch new rankings to reconstruct an old result. Review source passages
with their presentation, units and qualifiers rather than equating lexical
matching with semantic support. Future paid re-execution needs separate authority
and may vary with provider behavior; hash verification is not model replay.

One B retrieval setup failed before any Sabiá call with a PostgreSQL TOAST error.
The source was preserved; an isolated logical restore matched document/chunk,
search-text, vector and schema identities. A contexts were reused unchanged;
B retrieval was explicitly repeated in that recovered environment. Recovery and
the failed checkpoint remain in the archive; the underlying defect is not proven.
