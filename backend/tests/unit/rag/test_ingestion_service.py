from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.modules.bulas.models import Bula, BulaCorpus, BulaStatus
from app.modules.rag.parsers.pdf_parser import ParseResult
from app.modules.rag.schemas import ChunkResult, DocumentChunk
from app.modules.rag.service import BulaIngestionError, RAGIngestionService
from app.modules.storage.schemas import StoredObjectRef


BULA_ID = UUID("11111111-1111-1111-1111-111111111111")


class FakeBulaRepository:
    def __init__(self, bula: Bula | None) -> None:
        self.bula = bula
        self.statuses: list[BulaStatus] = []

    async def get_by_id(self, *, bula_id: UUID) -> Bula | None:
        assert bula_id == BULA_ID
        return self.bula

    async def update_ingestion_status(
        self,
        *,
        bula: Bula,
        status: BulaStatus,
        error_message: str | None = None,
        qdrant_collection: str | None = None,
    ) -> Bula:
        bula.status = status
        bula.error_message = error_message
        if qdrant_collection is not None:
            bula.qdrant_collection = qdrant_collection
        self.statuses.append(status)
        return bula


class FakeObjectStore:
    async def get_metadata(self, address: str) -> StoredObjectRef:
        assert address == "stored_objects/pdf-123"
        now = datetime.now(timezone.utc)
        return StoredObjectRef(
            object_address=address,
            original_filename="leaflet.pdf",
            content_type="application/pdf",
            content_size_bytes=10,
            sha256_checksum="abc123",
            created_at=now,
            updated_at=now,
        )

    async def get_bytes(self, address: str) -> bytes:
        assert address == "stored_objects/pdf-123"
        return b"%PDF-1.4\n%%EOF"


class FakeParser:
    def __init__(self, *, success: bool = True) -> None:
        self.success = success

    async def parse(self, pdf_bytes: bytes, filename: str) -> ParseResult:
        assert pdf_bytes == b"%PDF-1.4\n%%EOF"
        assert filename == "leaflet.pdf"
        return ParseResult(
            markdown="## Posologia\nUse conforme orientacao medica.",
            metadata={},
            sections=["Posologia"],
            extraction_tier="fake",
            success=self.success,
            error=None if self.success else "PDF parsing failed.",
        )


class FakeChunker:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = chunks

    async def chunk_markdown(self, markdown: str, doc_id: str) -> ChunkResult:
        assert markdown.startswith("## Posologia")
        assert doc_id == str(BULA_ID)
        return ChunkResult(doc_id=doc_id, chunks=self.chunks)


class FakeEmbeddings:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.texts = texts
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeQdrantStore:
    collection_name = "bulaai_chunks"

    def __init__(self) -> None:
        self.did_ensure_collection = False
        self.upserted_payloads: list[dict[str, object]] = []

    async def ensure_collection(self) -> None:
        self.did_ensure_collection = True

    async def upsert_points(self, points: list[object]) -> int:
        self.upserted_payloads = [
            point.payload for point in points if isinstance(point.payload, dict)
        ]
        return len(points)


def build_bula(status: BulaStatus = BulaStatus.PENDING) -> Bula:
    return Bula(
        id=BULA_ID,
        user_id=1,
        drug_name="Dipirona",
        manufacturer="Example Pharma",
        file_address="stored_objects/pdf-123",
        status=status,
        corpus=BulaCorpus.PRIVATE,
    )


def build_chunk() -> DocumentChunk:
    return DocumentChunk(
        chunk_id="chunk-1",
        doc_id=str(BULA_ID),
        index=0,
        text="Use conforme orientacao medica.",
        chunk_title="Posologia",
        section_title="Posologia",
        token_estimate=8,
        method="heuristic",
    )


def build_service(
    *,
    repo: FakeBulaRepository,
    parser: FakeParser | None = None,
    chunker: FakeChunker | None = None,
    embeddings: FakeEmbeddings | None = None,
    qdrant_store: FakeQdrantStore | None = None,
) -> RAGIngestionService:
    return RAGIngestionService(
        parser=parser or FakeParser(),
        chunker=chunker or FakeChunker([build_chunk()]),
        embeddings=embeddings or FakeEmbeddings(),  # type: ignore[arg-type]
        qdrant_store=qdrant_store or FakeQdrantStore(),  # type: ignore[arg-type]
        object_store=FakeObjectStore(),  # type: ignore[arg-type]
        bula_repo=repo,  # type: ignore[arg-type]
    )


@pytest.mark.anyio
async def test_ingest_bula_moves_pending_to_processing_then_ready() -> None:
    bula = build_bula()
    repo = FakeBulaRepository(bula)
    qdrant_store = FakeQdrantStore()
    embeddings = FakeEmbeddings()
    service = build_service(
        repo=repo,
        embeddings=embeddings,
        qdrant_store=qdrant_store,
    )

    result = await service.ingest_bula(bula_id=BULA_ID)

    assert result.status == BulaStatus.READY
    assert result.error_message is None
    assert result.qdrant_collection == "bulaai_chunks"
    assert repo.statuses == [BulaStatus.PROCESSING, BulaStatus.READY]
    assert embeddings.texts == ["Use conforme orientacao medica."]
    assert qdrant_store.did_ensure_collection is True
    assert qdrant_store.upserted_payloads[0]["bula_id"] == str(BULA_ID)


@pytest.mark.anyio
async def test_ingest_bula_reraises_parser_error_without_marking_ready() -> None:
    bula = build_bula()
    repo = FakeBulaRepository(bula)
    service = build_service(repo=repo, parser=FakeParser(success=False))

    with pytest.raises(ValueError, match="PDF parsing failed"):
        await service.ingest_bula(bula_id=BULA_ID)

    assert repo.statuses == [BulaStatus.PROCESSING]
    assert bula.status == BulaStatus.PROCESSING


@pytest.mark.anyio
async def test_ingest_bula_raises_clear_error_when_no_chunks_are_generated() -> None:
    bula = build_bula()
    repo = FakeBulaRepository(bula)
    service = build_service(repo=repo, chunker=FakeChunker([]))

    with pytest.raises(BulaIngestionError, match="No chunks"):
        await service.ingest_bula(bula_id=BULA_ID)

    assert repo.statuses == [BulaStatus.PROCESSING]


@pytest.mark.anyio
async def test_ingest_bula_skips_ready_bula() -> None:
    bula = build_bula(status=BulaStatus.READY)
    repo = FakeBulaRepository(bula)
    service = build_service(repo=repo)

    result = await service.ingest_bula(bula_id=BULA_ID)

    assert result is bula
    assert repo.statuses == []
