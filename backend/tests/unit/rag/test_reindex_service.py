import pytest
from qdrant_client.models import PointStruct, Record

from app.modules.rag.reindex_service import (
    DenseEmbeddingReindexError,
    DenseEmbeddingReindexService,
)


class FakeEmbeddings:
    embedding_profile = "intfloat/multilingual-e5-large;input=e5-query-passage-v1"

    def __init__(self) -> None:
        self.document_batches: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_batches.append(list(texts))
        return [[float(index), 1.0] for index, _ in enumerate(texts)]


class FakeQdrantStore:
    def __init__(self, records: list[Record]) -> None:
        self.records = records
        self.requested_bula_id: str | None = None
        self.upserted_points: list[PointStruct] = []

    async def list_points_for_bula(
        self,
        *,
        bula_id: str,
        page_size: int = 100,
    ) -> list[Record]:
        _ = page_size
        self.requested_bula_id = bula_id
        return self.records

    async def upsert_points(self, points: list[PointStruct]) -> int:
        self.upserted_points = list(points)
        return len(points)


def build_record(*, point_id: str, chunk_text: str) -> Record:
    return Record(
        id=point_id,
        payload={
            "bula_id": "bula-123",
            "chunk_id": f"chunk-{point_id}",
            "chunk_text": chunk_text,
            "embedding_profile": "legacy-profile",
        },
    )


@pytest.mark.anyio
async def test_reindex_updates_vectors_and_embedding_profile() -> None:
    embeddings = FakeEmbeddings()
    qdrant_store = FakeQdrantStore(
        [
            build_record(point_id="1", chunk_text="Primeiro trecho"),
            build_record(point_id="2", chunk_text="Segundo trecho"),
        ]
    )
    service = DenseEmbeddingReindexService(
        embeddings=embeddings,  # type: ignore[arg-type]
        qdrant_store=qdrant_store,  # type: ignore[arg-type]
    )

    result = await service.reindex_bula(bula_id="bula-123")

    assert result.point_count == 2
    assert result.is_dry_run is False
    assert embeddings.document_batches == [["Primeiro trecho", "Segundo trecho"]]
    assert qdrant_store.requested_bula_id == "bula-123"
    assert [point.vector for point in qdrant_store.upserted_points] == [
        [0.0, 1.0],
        [1.0, 1.0],
    ]
    assert all(
        point.payload is not None
        and point.payload["embedding_profile"] == embeddings.embedding_profile
        for point in qdrant_store.upserted_points
    )


@pytest.mark.anyio
async def test_reindex_dry_run_has_no_embedding_or_write_side_effect() -> None:
    embeddings = FakeEmbeddings()
    qdrant_store = FakeQdrantStore(
        [build_record(point_id="1", chunk_text="Trecho valido")]
    )
    service = DenseEmbeddingReindexService(
        embeddings=embeddings,  # type: ignore[arg-type]
        qdrant_store=qdrant_store,  # type: ignore[arg-type]
    )

    result = await service.reindex_bula(
        bula_id="bula-123",
        is_dry_run=True,
    )

    assert result.point_count == 1
    assert result.is_dry_run is True
    assert embeddings.document_batches == []
    assert qdrant_store.upserted_points == []


@pytest.mark.anyio
async def test_reindex_rejects_missing_or_malformed_existing_chunks() -> None:
    embeddings = FakeEmbeddings()
    missing_store = FakeQdrantStore([])
    missing_service = DenseEmbeddingReindexService(
        embeddings=embeddings,  # type: ignore[arg-type]
        qdrant_store=missing_store,  # type: ignore[arg-type]
    )

    with pytest.raises(DenseEmbeddingReindexError, match="No existing Qdrant chunks"):
        await missing_service.reindex_bula(bula_id="bula-123")

    malformed_store = FakeQdrantStore(
        [Record(id="bad-point", payload={"chunk_text": ""})]
    )
    malformed_service = DenseEmbeddingReindexService(
        embeddings=embeddings,  # type: ignore[arg-type]
        qdrant_store=malformed_store,  # type: ignore[arg-type]
    )

    with pytest.raises(DenseEmbeddingReindexError, match="does not contain chunk_text"):
        await malformed_service.reindex_bula(bula_id="bula-123")
