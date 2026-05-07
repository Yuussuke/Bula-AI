import asyncio
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.modules.rag.qdrant_store import QdrantVectorStore, make_point_id


QDRANT_TEST_HOST = os.getenv("QDRANT_TEST_HOST", os.getenv("QDRANT_HOST", "localhost"))
QDRANT_TEST_PORT = int(os.getenv("QDRANT_TEST_PORT", os.getenv("QDRANT_PORT", "6333")))
QDRANT_TEST_TIMEOUT_SECONDS = 2
QDRANT_WAIT_ATTEMPTS = 5
QDRANT_WAIT_SLEEP_SECONDS = 0.2


async def wait_for_qdrant(client: AsyncQdrantClient) -> None:
    last_error: Exception | None = None
    for _attempt_index in range(QDRANT_WAIT_ATTEMPTS):
        try:
            await client.get_collections()
            return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(QDRANT_WAIT_SLEEP_SECONDS)

    pytest.skip(f"Qdrant is not available for integration tests: {last_error}")


@pytest.fixture
async def qdrant_test_context() -> AsyncGenerator[
    tuple[QdrantVectorStore, AsyncQdrantClient, str],
    None,
]:
    collection_name = f"test_bulaai_chunks_{uuid.uuid4().hex}"
    client = AsyncQdrantClient(
        host=QDRANT_TEST_HOST,
        port=QDRANT_TEST_PORT,
        timeout=QDRANT_TEST_TIMEOUT_SECONDS,
    )
    is_qdrant_available = False

    try:
        await wait_for_qdrant(client)
        is_qdrant_available = True
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            vector_size=4,
        )
        yield vector_store, client, collection_name
    finally:
        if is_qdrant_available:
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


@pytest.mark.anyio
async def test_search_similar_returns_relevant_chunk(
    qdrant_test_context: tuple[QdrantVectorStore, AsyncQdrantClient, str],
) -> None:
    vector_store, _, _ = qdrant_test_context
    await vector_store.ensure_collection()
    await vector_store.upsert_points(build_test_points())

    search_result = await vector_store.search_similar(
        vector=[2.0, 0.1, 0.2, 0.3],
        limit=1,
    )

    assert search_result.points[0].payload["chunk_id"] == "test-chunk-2"
