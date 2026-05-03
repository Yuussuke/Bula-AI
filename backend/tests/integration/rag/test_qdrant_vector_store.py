import asyncio
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.modules.rag.qdrant_store import QdrantVectorStore, make_point_id


async def wait_for_qdrant(client: AsyncQdrantClient) -> None:
    for attempt in range(30):
        try:
            await client.get_collections()
            return
        except Exception:
            if attempt == 29:
                raise
            await asyncio.sleep(1)


@pytest.fixture
async def qdrant_test_context() -> AsyncGenerator[
    tuple[QdrantVectorStore, AsyncQdrantClient, str],
    None,
]:
    collection_name = f"test_bulaai_chunks_{uuid.uuid4().hex}"
    client = AsyncQdrantClient(
        host=os.getenv("QDRANT_HOST", "qdrant"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
        timeout=60,
    )
    await wait_for_qdrant(client)
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        vector_size=4,
    )

    try:
        yield vector_store, client, collection_name
    finally:
        collection_exists = await client.collection_exists(collection_name)
        if collection_exists:
            await client.delete_collection(collection_name)
        await client.close()


def build_test_points() -> list[PointStruct]:
    return [
        PointStruct(
            id=make_point_id(f"test-chunk-{index}"),
            vector=[float(index), 0.1, 0.2, 0.3],
            payload={
                "chunk_id": f"test-chunk-{index}",
                "chunk_text": f"Chunk {index}",
                "corpus": "private",
                "bula_id": "test-bula",
            },
        )
        for index in range(3)
    ]


@pytest.mark.anyio
async def test_ensure_collection_is_idempotent(
    qdrant_test_context: tuple[QdrantVectorStore, AsyncQdrantClient, str],
) -> None:
    vector_store, client, collection_name = qdrant_test_context

    await vector_store.ensure_collection()
    await vector_store.ensure_collection()

    collection_exists = await client.collection_exists(collection_name)
    assert collection_exists is True


@pytest.mark.anyio
async def test_upsert_points_is_idempotent_for_same_point_ids(
    qdrant_test_context: tuple[QdrantVectorStore, AsyncQdrantClient, str],
) -> None:
    vector_store, client, collection_name = qdrant_test_context
    await vector_store.ensure_collection()
    points = build_test_points()

    first_upsert_count = await vector_store.upsert_points(points)
    first_qdrant_count = await client.count(
        collection_name=collection_name,
        exact=True,
    )
    second_upsert_count = await vector_store.upsert_points(points)
    second_qdrant_count = await client.count(
        collection_name=collection_name,
        exact=True,
    )

    assert first_upsert_count == len(points)
    assert second_upsert_count == len(points)
    assert first_qdrant_count.count == len(points)
    assert second_qdrant_count.count == len(points)
