from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.modules.bulas.models import Bula, BulaCorpus, BulaStatus
from app.modules.rag import observability as observability_module
from app.modules.rag.debug_artifacts import RAGIngestionDebugArtifacts
from app.modules.rag.parsers.pdf_parser import ParseResult
from app.modules.rag.schemas import ChunkResult, ChunkingConfig, DocumentChunk
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
        self.config = build_chunking_config()

    async def chunk_markdown(self, markdown: str, doc_id: str) -> ChunkResult:
        assert markdown.startswith("## Posologia")
        assert doc_id == str(BULA_ID)
        return ChunkResult(doc_id=doc_id, chunks=self.chunks)


class FailingChunker:
    def __init__(self) -> None:
        self.config = build_chunking_config()

    async def chunk_markdown(self, markdown: str, doc_id: str) -> ChunkResult:
        _ = markdown
        _ = doc_id
        raise RuntimeError("chunking failed")


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


class FakeDebugArtifacts(RAGIngestionDebugArtifacts):
    def __init__(self) -> None:
        super().__init__(enabled=True, root_path="unused")
        self.calls: list[dict[str, object]] = []

    async def write_run_artifacts(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return None


def build_chunking_config() -> ChunkingConfig:
    return ChunkingConfig(
        target_tokens=600,
        min_tokens=200,
        max_tokens=850,
        overlap_ratio=0.12,
        max_concurrency=4,
        model="primary-model",
        fallback_model="fallback-model",
        is_llm_enabled=True,
    )


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
    chunker: FakeChunker | FailingChunker | None = None,
    embeddings: FakeEmbeddings | None = None,
    qdrant_store: FakeQdrantStore | None = None,
    debug_artifacts: RAGIngestionDebugArtifacts | None = None,
) -> RAGIngestionService:
    return RAGIngestionService(
        parser=parser or FakeParser(),
        chunker=chunker or FakeChunker([build_chunk()]),
        embeddings=embeddings or FakeEmbeddings(),  # type: ignore[arg-type]
        qdrant_store=qdrant_store or FakeQdrantStore(),  # type: ignore[arg-type]
        object_store=FakeObjectStore(),  # type: ignore[arg-type]
        bula_repo=repo,  # type: ignore[arg-type]
        debug_artifacts=debug_artifacts,
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
async def test_ingest_bula_writes_success_debug_artifacts() -> None:
    bula = build_bula()
    repo = FakeBulaRepository(bula)
    debug_artifacts = FakeDebugArtifacts()
    service = build_service(repo=repo, debug_artifacts=debug_artifacts)

    await service.ingest_bula(bula_id=BULA_ID)

    assert len(debug_artifacts.calls) == 1
    call = debug_artifacts.calls[0]
    assert isinstance(call["run_id"], str)
    assert call["doc_id"] == str(BULA_ID)
    assert call["filename"] == "leaflet.pdf"
    assert call["status"] == "success"
    assert call["markdown"] == "## Posologia\nUse conforme orientacao medica."
    assert isinstance(call["chunk_result"], ChunkResult)
    assert isinstance(call["chunking_config"], ChunkingConfig)


@pytest.mark.anyio
async def test_ingest_bula_logs_stage_timings_and_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls: list[dict[str, object]] = []
    debug_calls: list[dict[str, object]] = []

    def record_info(event: str, **kwargs: object) -> None:
        info_calls.append({"event": event, **kwargs})

    def record_debug(event: str, **kwargs: object) -> None:
        debug_calls.append({"event": event, **kwargs})

    monkeypatch.setattr(observability_module.logger, "info", record_info)
    monkeypatch.setattr(observability_module.logger, "debug", record_debug)

    bula = build_bula()
    repo = FakeBulaRepository(bula)
    service = build_service(repo=repo)

    await service.ingest_bula(bula_id=BULA_ID)

    expected_stages = [
        "bula_lookup",
        "mark_processing",
        "object_metadata",
        "pdf_download",
        "pdf_parse_to_markdown",
        "chunk_markdown",
        "write_debug_artifacts",
        "embed_chunks",
        "qdrant_ensure_collection",
        "qdrant_upsert",
        "mark_ready",
    ]
    stage_logs = [
        call
        for call in info_calls
        if call["event"] == "rag_ingestion_stage_finished"
    ]
    summary_log = next(
        call for call in info_calls if call["event"] == "rag_ingestion_finished"
    )

    assert [call["stage"] for call in stage_logs] == expected_stages
    assert [call["stage"] for call in debug_calls] == expected_stages
    assert all(call["stage_status"] == "succeeded" for call in stage_logs)
    assert all(isinstance(call["duration_ms"], float) for call in stage_logs)
    assert all(call["run_id"] == summary_log["run_id"] for call in stage_logs)
    assert all(call["bula_id"] == str(BULA_ID) for call in stage_logs)
    assert summary_log["bula_id"] == str(BULA_ID)
    assert summary_log["doc_id"] == str(BULA_ID)
    assert summary_log["ingestion_status"] == "succeeded"
    assert isinstance(summary_log["total_duration_ms"], float)
    assert list(summary_log["stage_durations_ms"].keys()) == expected_stages
    assert summary_log["slowest_stage"] in expected_stages
    assert (
        summary_log["slowest_stage_duration_ms"]
        == summary_log["stage_durations_ms"][summary_log["slowest_stage"]]
    )
    assert stage_logs[2]["pdf_size_bytes"] == 10
    assert stage_logs[4]["extraction_tier"] == "fake"
    assert stage_logs[4]["section_count"] == 1
    assert stage_logs[5]["chunk_count"] == 1
    assert stage_logs[7]["embedding_vector_count"] == 1
    assert stage_logs[9]["qdrant_point_count"] == 1
    assert stage_logs[9]["qdrant_collection"] == "bulaai_chunks"


@pytest.mark.anyio
async def test_ingest_bula_reraises_parser_error_without_marking_ready() -> None:
    bula = build_bula()
    repo = FakeBulaRepository(bula)
    debug_artifacts = FakeDebugArtifacts()
    service = build_service(
        repo=repo,
        parser=FakeParser(success=False),
        debug_artifacts=debug_artifacts,
    )

    with pytest.raises(ValueError, match="PDF parsing failed"):
        await service.ingest_bula(bula_id=BULA_ID)

    assert repo.statuses == [BulaStatus.PROCESSING]
    assert bula.status == BulaStatus.PROCESSING
    assert len(debug_artifacts.calls) == 1
    assert debug_artifacts.calls[0]["status"] == "parse_failed"
    assert debug_artifacts.calls[0]["markdown"] is None
    assert isinstance(debug_artifacts.calls[0]["error"], ValueError)


@pytest.mark.anyio
async def test_ingest_bula_logs_failed_parse_summary_without_sensitive_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls: list[dict[str, object]] = []
    debug_calls: list[dict[str, object]] = []

    def record_info(event: str, **kwargs: object) -> None:
        info_calls.append({"event": event, **kwargs})

    def record_debug(event: str, **kwargs: object) -> None:
        debug_calls.append({"event": event, **kwargs})

    monkeypatch.setattr(observability_module.logger, "info", record_info)
    monkeypatch.setattr(observability_module.logger, "debug", record_debug)

    bula = build_bula()
    repo = FakeBulaRepository(bula)
    debug_artifacts = FakeDebugArtifacts()
    service = build_service(
        repo=repo,
        parser=FakeParser(success=False),
        debug_artifacts=debug_artifacts,
    )

    with pytest.raises(ValueError, match="PDF parsing failed"):
        await service.ingest_bula(bula_id=BULA_ID)

    expected_stages = [
        "bula_lookup",
        "mark_processing",
        "object_metadata",
        "pdf_download",
        "pdf_parse_to_markdown",
        "write_debug_artifacts",
    ]
    stage_logs = [
        call
        for call in info_calls
        if call["event"] == "rag_ingestion_stage_finished"
    ]
    summary_log = next(
        call for call in info_calls if call["event"] == "rag_ingestion_finished"
    )
    parse_stage_log = next(
        call for call in stage_logs if call["stage"] == "pdf_parse_to_markdown"
    )

    assert [call["stage"] for call in stage_logs] == expected_stages
    assert list(summary_log["stage_durations_ms"].keys()) == expected_stages
    assert parse_stage_log["stage_status"] == "failed"
    assert parse_stage_log["error_type"] == "ValueError"
    assert summary_log["ingestion_status"] == "failed"
    assert summary_log["error_type"] == "ValueError"
    assert isinstance(summary_log["total_duration_ms"], float)
    assert summary_log["slowest_stage"] in expected_stages

    log_output = repr(info_calls + debug_calls)
    assert "pdf_bytes" not in log_output
    assert "%PDF-1.4" not in log_output
    assert "Use conforme orientacao medica" not in log_output
    assert "chunk_text" not in log_output
    assert "Custom chunking instruction" not in log_output
    assert "api_key" not in log_output


@pytest.mark.anyio
async def test_ingest_bula_writes_chunking_failure_debug_artifacts() -> None:
    bula = build_bula()
    repo = FakeBulaRepository(bula)
    debug_artifacts = FakeDebugArtifacts()
    service = build_service(
        repo=repo,
        chunker=FailingChunker(),
        debug_artifacts=debug_artifacts,
    )

    with pytest.raises(RuntimeError, match="chunking failed"):
        await service.ingest_bula(bula_id=BULA_ID)

    assert len(debug_artifacts.calls) == 1
    call = debug_artifacts.calls[0]
    assert call["status"] == "chunking_failed"
    assert call["markdown"] == "## Posologia\nUse conforme orientacao medica."
    assert call["chunk_result"] is None
    assert isinstance(call["error"], RuntimeError)


@pytest.mark.anyio
async def test_ingest_bula_raises_clear_error_when_no_chunks_are_generated() -> None:
    bula = build_bula()
    repo = FakeBulaRepository(bula)
    debug_artifacts = FakeDebugArtifacts()
    service = build_service(
        repo=repo,
        chunker=FakeChunker([]),
        debug_artifacts=debug_artifacts,
    )

    with pytest.raises(BulaIngestionError, match="No chunks"):
        await service.ingest_bula(bula_id=BULA_ID)

    assert repo.statuses == [BulaStatus.PROCESSING]
    assert len(debug_artifacts.calls) == 1
    assert debug_artifacts.calls[0]["status"] == "chunking_failed"
    assert isinstance(debug_artifacts.calls[0]["chunk_result"], ChunkResult)


@pytest.mark.anyio
async def test_ingest_bula_skips_ready_bula() -> None:
    bula = build_bula(status=BulaStatus.READY)
    repo = FakeBulaRepository(bula)
    service = build_service(repo=repo)

    result = await service.ingest_bula(bula_id=BULA_ID)

    assert result is bula
    assert repo.statuses == []
