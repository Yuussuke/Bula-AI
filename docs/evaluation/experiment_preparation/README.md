# Offline evaluation infrastructure

Evaluation-only tools in `backend/evaluation/`; no production changes or new
dependencies. Source baseline: merged `main`, including PR #258 / `32d3fa0b`.
The original dirty checkout and historical preparation remain preserved.

## Review order

1. `contracts.py` and `dataset.py`: snapshot-bound mapping inputs/outputs and
   exact frozen-record/PDF identities; complete/partial/ambiguous/absent
   correspondence is separate from semantic confirmation.
2. `snapshot.py`: source/dependency hashes, allowlisted configuration evidence,
   drift detection and separate A/B universes. Static settings are not verified
   runtime settings; credentials are excluded.
3. `runner.py`: 4,800 planned positive retrieval jobs, native ranks/scores,
   separate technical failures and checksummed append-only resume. Only
   synthetic offline adapters are permitted; no scorer or live adapter exists.
4. `compose.yaml`: isolated PostgreSQL/Qdrant services and volumes for A/B,
   without public ports; image digests/password require explicit configuration.

Retrieval precedes selection/generation. Cross requests have no target filter;
relevance remains restricted to the reference PDF. Recall@10 is retrieved golds
divided by all mapped golds; MRR@10 averages reciprocal first-gold rank within
ten (zero otherwise). Native tie order is retained, and negatives do not enter
these denominators. Multiple-fragment fidelity is evaluated separately.

All positives remain planned, including mapping failures. Their scoring policy
and response coverage/budget require approval; neither is implemented silently.
Negatives evaluate abstention only scoped. The current extractive answer path
does not replace the natural grounded generation required for response evaluation.

## Offline checks

From `backend/`:

```bash
uv run --offline --no-sync python -m pytest --confcutdir=tests/unit/evaluation tests/unit/evaluation -q
uv run --offline --no-sync ruff check evaluation tests/unit/evaluation
uv run --offline --no-sync mypy evaluation --follow-imports=silent --disallow-untyped-defs
docker compose -f evaluation/compose.yaml config --no-interpolate --quiet
```

The 29 tests use synthetic fixtures and prohibit sockets. No PDFs, database,
models or application conftest are required. Compose validation starts nothing.

Preparation against real data requires the exact original freeze manifest,
11 bases, ten overrides, record bindings and 100 PDF bytes, restored at the
author-controlled archive's relative paths. Full documentary reproduction also
requires original audit history/scripts. These assets are not supplied here.

```bash
uv run --offline --no-sync python -m evaluation prepare --root .. --candidate .. --output tmp/evaluation-artifacts/manifest.NEW_ID.json
uv run --offline --no-sync python -m evaluation verify tmp/evaluation-artifacts/manifest.NEW_ID.json
```

Use a new output path; creation is exclusive. Snapshots contain local locations
and remain outside Git. Before ingestion, approve runtime settings/image
digests, migrations/BM25 initialization, storage/UUID bindings, export snapshots
and paid budgets. Definitive mapping requires an approved ingestion snapshot.
No ingestion, embeddings, live queries, LLM calls, judging or metrics ran here.
