from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from qdrant_client import AsyncQdrantClient

from app.modules.rag.qdrant_store import QdrantVectorStore, make_point_id


@pytest.mark.anyio
async def test_payload_retrieval_maps_logical_ids_without_vectors() -> None:
    client = AsyncMock(spec=AsyncQdrantClient)
    client.retrieve.return_value = [
        SimpleNamespace(
            id=make_point_id("second"),
            payload={"chunk_id": "second", "manufacturer": "Sanofi"},
        ),
        SimpleNamespace(
            id=make_point_id("first"),
            payload={"chunk_id": "first", "manufacturer": "EMS"},
        ),
    ]
    store = QdrantVectorStore(
        client=cast(AsyncQdrantClient, client),
        collection_name="test-chunks",
    )

    payloads = await store.retrieve_payloads_by_chunk_ids(["first", "second", "first"])

    assert payloads == {
        "second": {"chunk_id": "second", "manufacturer": "Sanofi"},
        "first": {"chunk_id": "first", "manufacturer": "EMS"},
    }
    client.retrieve.assert_awaited_once_with(
        collection_name="test-chunks",
        ids=[make_point_id("first"), make_point_id("second")],
        with_payload=True,
        with_vectors=False,
    )


@pytest.mark.anyio
async def test_payload_retrieval_skips_points_without_payload() -> None:
    client = AsyncMock(spec=AsyncQdrantClient)
    client.retrieve.return_value = [
        SimpleNamespace(id=make_point_id("missing"), payload=None)
    ]
    store = QdrantVectorStore(client=cast(AsyncQdrantClient, client))

    assert await store.retrieve_payloads_by_chunk_ids(["missing"]) == {}


@pytest.mark.anyio
async def test_payload_retrieval_does_not_call_qdrant_for_empty_input() -> None:
    client = AsyncMock(spec=AsyncQdrantClient)
    store = QdrantVectorStore(client=cast(AsyncQdrantClient, client))

    assert await store.retrieve_payloads_by_chunk_ids([]) == {}
    client.retrieve.assert_not_awaited()


@pytest.mark.anyio
async def test_payload_retrieval_rejects_blank_identity() -> None:
    client = AsyncMock(spec=AsyncQdrantClient)
    store = QdrantVectorStore(client=cast(AsyncQdrantClient, client))

    with pytest.raises(ValueError, match="must not be blank"):
        await store.retrieve_payloads_by_chunk_ids([" "])
    client.retrieve.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "record",
    [
        SimpleNamespace(
            id=make_point_id("unexpected"),
            payload={"chunk_id": "unexpected"},
        ),
        SimpleNamespace(
            id=make_point_id("expected"),
            payload={"chunk_id": "different"},
        ),
    ],
)
async def test_payload_retrieval_rejects_inconsistent_qdrant_identity(
    record: SimpleNamespace,
) -> None:
    client = AsyncMock(spec=AsyncQdrantClient)
    client.retrieve.return_value = [record]
    store = QdrantVectorStore(client=cast(AsyncQdrantClient, client))

    with pytest.raises(ValueError, match="identity|identities"):
        await store.retrieve_payloads_by_chunk_ids(["expected"])
