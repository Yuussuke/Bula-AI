from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.rag.bm25_index import PostgreSQLBM25Index
from app.modules.rag.schemas import ChunkMetadataInput


def make_chunk() -> ChunkMetadataInput:
    bula_id = uuid4()
    return ChunkMetadataInput(
        chunk_id="original-id",
        doc_id=str(bula_id),
        bula_id=bula_id,
        corpus="private",
        section_title="Uso",
        chunk_text="Texto preservado.",
    )


@pytest.mark.anyio
async def test_invalid_batch_does_not_write() -> None:
    repository = AsyncMock()
    index = PostgreSQLBM25Index(repository)
    chunk = make_chunk()
    with pytest.raises(ValueError, match="Duplicate"):
        await index.upsert_chunks([chunk, chunk])
    with pytest.raises(ValueError, match="document identity"):
        await index.upsert_chunks([chunk.model_copy(update={"doc_id": "other"})])
    with pytest.raises(ValueError, match="selected bula"):
        await index.replace_bula_chunks(bula_id=uuid4(), chunks=[chunk])
    with pytest.raises(ValueError, match="empty"):
        await index.replace_bula_chunks(bula_id=chunk.bula_id, chunks=[])
    repository.upsert_chunks.assert_not_awaited()


@pytest.mark.anyio
async def test_empty_queries_and_invalid_limits_do_not_hit_database() -> None:
    repository = AsyncMock()
    index = PostgreSQLBM25Index(repository)
    assert await index.search(" ") == []
    assert await index.search("dipirona", corpus=[]) == []
    for k in (0, -1, 101):
        with pytest.raises(ValueError, match="k must"):
            await index.search("dipirona", k=k)
    repository.search.assert_not_awaited()
    assert await index.upsert_chunks([]) == 0
    repository.upsert_chunks.assert_not_awaited()
