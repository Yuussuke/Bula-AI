import asyncio
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from qdrant_client import AsyncQdrantClient

from app.modules.rag.qdrant_store import QdrantVectorStore


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
        try:
            if is_qdrant_available:
                collection_exists = await client.collection_exists(collection_name)
                if collection_exists:
                    await client.delete_collection(collection_name)
        except Exception:
            pass
        finally:
            await client.close()
