# Hybrid runtime: RRF-B + BGE

Hybrid chat retrieves 20 eligible BM25 and 20 eligible dense candidates (dense
raw limit 60), deduplicates by chunk ID and retains the complete RRF union,
up to 40 chunks. RRF remains equal-weight, constant 60. BGE then sorts all
authorized candidates by descending raw logit, breaking ties by chunk ID,
and returns 10. It does not blend logits with RRF scores or impose a threshold.
The original RRF score remains in metadata; the source score becomes the BGE
logit, not a probability. Dense and BM25 modes keep their existing budgets.

Cross-bula canonical validation precedes BGE and its final cut. The allowlist
still applies inside PostgreSQL/Qdrant before ranking. The existing safety
supplement is applied after retrieval only in individual chat; it can add up
to two chunks beyond the ranked Top-10. Selection, generation, prompts, storage
and frozen experimental artifacts are unchanged. This integration does not
assert full parity with the experimental evidence-preparation code.

## Local setup

Python 3.14 uses the optional `reranker` extra: PyTorch 2.9.1/CUDA 12.8 and
Transformers 4.57.1. The evaluated runtime used Python 3.12/PyTorch 2.8;
these environments are distinct. Native 3.14/CUDA inference was smoke-tested
with synthetic non-medical text, without rerunning the thesis benchmark.
PyTorch publishes [compatible wheels](https://download.pytorch.org/whl/cu128/torch/).

From `backend`, install with `uv sync --extra reranker`. Obtain the public
`BAAI/bge-reranker-v2-m3` assets at revision
`953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` into
`models/bge-reranker-v2-m3`. For example:

```bash
uv run --extra reranker python -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-reranker-v2-m3', revision='953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e', local_dir='models/bge-reranker-v2-m3', allow_patterns=['config.json', 'model.safetensors', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json', 'sentencepiece.bpe.model'])"
uv run --extra reranker python run.py
```

Assets are external, ignored by Git and verified against `bge_assets.json`
before loading. The application never downloads weights or executes remote
model code. Existing verified assets may be reused via `RERANKER_MODEL_PATH`.
Run one API worker on the evaluated 4 GiB GPU. Each process owns its own model.

For Docker with NVIDIA GPU support and assets already provisioned, the optional
`docker-compose.bge.yml` override installs the extra, requests the GPU and
mounts weights read-only. It does not modify database/index configuration.
Native `uv run` must include `--extra reranker`; otherwise uv may remove the
optional dependencies. The Docker override uses the prebuilt environment and
`--no-sync` to avoid that issue.

## Limits and failures

One model is loaded at API startup, before query deadlines begin. Inference
uses one thread, CUDA FP16, deterministic settings, batch size 1 and the original
formatter `Seção: {section_title}\n\n{chunk_text}`. Empty titles omit the prefix.
Pairs over 8192 tokens are rejected, never truncated. The default outstanding
capacity is 16, including running work, with a 15-second queue/inference deadline.
A timed-out CUDA operation retains its slot until it actually finishes.

Missing assets, CUDA/dependencies, overload, timeout and invalid inference are
technical errors (HTTP 503), not abstentions. Initialization failure leaves
dense/BM25 and other routes available; queries requiring BGE fail until restart
after correcting configuration. There is no automatic CPU or RRF fallback.
`RERANKER_ENABLED=false` explicitly restores the legacy hybrid configuration
(12 candidates per branch); it is not an equivalent experimental arm.

Logs identify model/revision/runtime on load and candidate count/latency per
inference, without recording questions or source text. Warmup contributes to
startup time, not steady-state request latency. Larger model dependencies,
GPU memory and serialized inference are operational costs; deployment remains
outside this change.

## Verification

Behavioral tests use synthetic scorers, real source validation/persistence and
no providers. The opt-in GPU smoke test is
`tests/integration/rag/test_bge_runtime.py`; set `BGE_TEST_MODEL_PATH` to verified
local weights and run it with `uv run --extra reranker pytest`. No corpus,
ingestion or paid call is needed.
