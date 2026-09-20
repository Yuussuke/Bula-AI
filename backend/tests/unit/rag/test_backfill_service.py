from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from qdrant_client.models import Record

from app.modules.bulas.models import Bula, BulaCorpus, BulaStatus
from app.modules.rag.backfill_service import (
    ChunkBackfillError,
    ChunkMetadataBackfillService,
)
from app.modules.rag.qdrant_store import make_point_id


def build_bula() -> Bula:
    return Bula(
        id=uuid4(),
        user_id=1,
        drug_name="Nome real",
        corpus=BulaCorpus.SYSTEM,
        status=BulaStatus.READY,
    )


def build_record(bula: Bula, chunk_id: str = "original-chunk-id") -> Record:
    return Record(
        id=make_point_id(chunk_id),
        payload={
            "bula_id": str(bula.id),
            "chunk_id": chunk_id,
            "chunk_text": "## Uso\nConteúdo original.\n",
            "section_title": "Uso",
            "corpus": "private",
            "drug_name": "Stale name",
        },
    )


def build_service(bula: Bula, records: list[Record]) -> ChunkMetadataBackfillService:
    return ChunkMetadataBackfillService(
        bula_repository=AsyncMock(get_by_id=AsyncMock(return_value=bula)),
        qdrant_store=AsyncMock(list_points_for_bula=AsyncMock(return_value=records)),
        bm25_index=AsyncMock(),
    )


@pytest.mark.anyio
async def test_backfill_preserves_source_ids_and_uses_current_bula_metadata() -> None:
    bula = build_bula()
    record = build_record(bula)
    service = build_service(bula, [record])
    result = await service.backfill(bula_id=bula.id)
    chunk = service.bm25_index.replace_bula_chunks.call_args.kwargs["chunks"][0]
    assert result.chunk_count == 1
    assert result.bula_count == 1
    assert chunk.chunk_id == "original-chunk-id"
    assert chunk.chunk_id != record.id
    assert chunk.doc_id == str(bula.id)
    assert chunk.chunk_text == record.payload["chunk_text"]
    assert chunk.corpus == BulaCorpus.SYSTEM
    assert chunk.drug_name == "Nome real"
    assert bula.status == BulaStatus.READY


@pytest.mark.anyio
async def test_dry_run_validates_without_writing() -> None:
    bula = build_bula()
    service = build_service(bula, [build_record(bula)])
    result = await service.backfill(bula_id=bula.id, is_dry_run=True)
    assert result.chunk_count == 1
    assert result.is_dry_run
    service.bm25_index.replace_bula_chunks.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "field,value",
    [
        ("chunk_text", " "),
        ("chunk_text", 123),
        ("chunk_id", ""),
        ("bula_id", str(uuid4())),
        ("doc_id", "another-document"),
        ("section_title", None),
        ("chunk_id", "does-not-match-point"),
    ],
)
async def test_bad_source_rejects_entire_bula_before_write(
    field: str, value: object
) -> None:
    bula = build_bula()
    bad_record = build_record(bula, "bad")
    bad_record.payload[field] = value
    service = build_service(bula, [build_record(bula), bad_record])
    with pytest.raises(ChunkBackfillError):
        await service.backfill(bula_id=bula.id)
    service.bm25_index.replace_bula_chunks.assert_not_awaited()


@pytest.mark.anyio
async def test_missing_chunks_and_duplicate_identity_are_rejected() -> None:
    bula = build_bula()
    record = build_record(bula)
    for records in ([], [record, record]):
        service = build_service(bula, records)
        with pytest.raises(ChunkBackfillError):
            await service.backfill(bula_id=bula.id)
        service.bm25_index.replace_bula_chunks.assert_not_awaited()


@pytest.mark.anyio
async def test_nonready_bula_is_not_copied() -> None:
    bula = build_bula()
    bula.status = BulaStatus.PROCESSING
    service = build_service(bula, [])
    with pytest.raises(ChunkBackfillError, match="ready"):
        await service.backfill(bula_id=bula.id)
    service.qdrant_store.list_points_for_bula.assert_not_awaited()


@pytest.mark.anyio
async def test_all_bulas_uses_keyset_pages_and_can_be_resumed() -> None:
    first_bula, second_bula = build_bula(), build_bula()
    bulas = sorted([first_bula, second_bula], key=lambda bula: bula.id)
    service = build_service(bulas[0], [])
    service.bula_repository.list_ready_bulas_for_indexing.side_effect = [
        [bulas[0]],
        [bulas[1]],
        [],
    ]

    async def list_points(*, bula_id: str, page_size: int) -> list[Record]:
        assert page_size == 1
        selected = next(bula for bula in bulas if bula.id == UUID(bula_id))
        return [build_record(selected, str(selected.id))]

    service.qdrant_store.list_points_for_bula.side_effect = list_points
    result = await service.backfill(batch_size=1)
    assert result.bula_count == 2
    assert result.chunk_count == 2
    calls = service.bula_repository.list_ready_bulas_for_indexing.call_args_list
    assert calls[1].kwargs["after_id"] == bulas[0].id
    assert calls[2].kwargs["after_id"] == bulas[1].id
