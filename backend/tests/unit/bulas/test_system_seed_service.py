import hashlib
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.modules.auth.models import UserRole
from app.modules.bulas.models import BulaCorpus
from app.modules.bulas.schemas import (
    SystemBulaManifestEntry,
    SystemBulaSeedCandidate,
)
from app.modules.bulas.service import (
    SystemBulaSeedConfigurationError,
    SystemBulaSeedService,
)
from app.modules.storage.schemas import StoredObjectRef


PDF_CONTENT = b"%PDF-1.4\nexample leaflet\n%%EOF"


def build_candidate(*, content: bytes = PDF_CONTENT) -> SystemBulaSeedCandidate:
    return SystemBulaSeedCandidate(
        manifest_entry=SystemBulaManifestEntry(
            drug_name="Dipirona",
            manufacturer="Example Pharma",
            source_url="https://consultas.anvisa.gov.br/documento.pdf",
            filename="dipirona.pdf",
            sha256_checksum=hashlib.sha256(content).hexdigest(),
            content_size_bytes=len(content),
        ),
        content=content,
    )


def build_seed_service(
    *,
    user_repository: AsyncMock | None = None,
    bula_repository: AsyncMock | None = None,
    object_store: AsyncMock | None = None,
    ingestion_queue: AsyncMock | None = None,
) -> tuple[
    SystemBulaSeedService,
    AsyncMock,
    AsyncMock,
    AsyncMock,
    AsyncMock,
]:
    users = user_repository or AsyncMock()
    bulas = bula_repository or AsyncMock()
    storage = object_store or AsyncMock()
    queue = ingestion_queue or AsyncMock()
    users.get_user_by_email.return_value = Mock(
        id=42,
        role=UserRole.ADMIN,
        is_active=True,
    )
    storage.find_by_sha256_checksum.return_value = None

    service = SystemBulaSeedService(
        user_repository=users,
        bula_repository=bulas,
        object_store=storage,
        ingestion_queue=queue,
        max_upload_size_bytes=10 * 1024 * 1024,
    )
    return service, users, bulas, storage, queue


@pytest.mark.anyio
async def test_seed_creates_system_bula_and_enqueues_ingestion() -> None:
    bula_id = UUID("11111111-1111-1111-1111-111111111111")
    service, _, bulas, storage, queue = build_seed_service()
    storage.put_bytes.return_value = "stored_objects/dipirona"
    bulas.create_bula.return_value = Mock(
        id=bula_id,
        file_address="stored_objects/dipirona",
    )

    summary = await service.seed_documents(
        admin_email=" ADMIN@example.com ",
        candidates=[build_candidate()],
        is_dry_run=False,
    )

    assert summary.planned == 1
    assert summary.inserted == 1
    assert summary.queued == 1
    assert summary.skipped == 0
    assert summary.failed == 0
    bulas.create_bula.assert_awaited_once_with(
        user_id=42,
        drug_name="Dipirona",
        manufacturer="Example Pharma",
        file_address="stored_objects/dipirona",
        file_url="https://consultas.anvisa.gov.br/documento.pdf",
        corpus=BulaCorpus.SYSTEM,
    )
    queue.enqueue_bula_ingestion.assert_awaited_once_with(bula_id=bula_id)


@pytest.mark.anyio
async def test_seed_skips_existing_system_bula_with_same_checksum() -> None:
    service, _, bulas, storage, queue = build_seed_service()
    storage.find_by_sha256_checksum.return_value = Mock(
        spec=StoredObjectRef,
        object_address="stored_objects/existing",
    )
    bulas.get_by_file_address_and_corpus.return_value = Mock()

    summary = await service.seed_documents(
        admin_email="admin@example.com",
        candidates=[build_candidate()],
        is_dry_run=False,
    )

    assert summary.skipped == 1
    assert summary.planned == 0
    assert summary.inserted == 0
    storage.put_bytes.assert_not_awaited()
    bulas.create_bula.assert_not_awaited()
    queue.enqueue_bula_ingestion.assert_not_awaited()


@pytest.mark.anyio
async def test_seed_dry_run_validates_without_writing_or_queueing() -> None:
    service, _, bulas, storage, queue = build_seed_service()

    summary = await service.seed_documents(
        admin_email="admin@example.com",
        candidates=[build_candidate()],
        is_dry_run=True,
    )

    assert summary.planned == 1
    assert summary.inserted == 0
    assert summary.queued == 0
    storage.put_bytes.assert_not_awaited()
    bulas.create_bula.assert_not_awaited()
    queue.enqueue_bula_ingestion.assert_not_awaited()


@pytest.mark.anyio
async def test_seed_reuses_stored_object_without_duplicate_upload() -> None:
    bula_id = UUID("22222222-2222-2222-2222-222222222222")
    service, _, bulas, storage, queue = build_seed_service()
    storage.find_by_sha256_checksum.return_value = Mock(
        spec=StoredObjectRef,
        object_address="stored_objects/reused",
    )
    bulas.get_by_file_address_and_corpus.return_value = None
    bulas.create_bula.return_value = Mock(
        id=bula_id,
        file_address="stored_objects/reused",
    )

    summary = await service.seed_documents(
        admin_email="admin@example.com",
        candidates=[build_candidate()],
        is_dry_run=False,
    )

    assert summary.inserted == 1
    storage.put_bytes.assert_not_awaited()
    queue.enqueue_bula_ingestion.assert_awaited_once_with(bula_id=bula_id)


@pytest.mark.anyio
async def test_seed_reports_invalid_checksum_and_continues() -> None:
    candidate = build_candidate()
    candidate.manifest_entry.sha256_checksum = "0" * 64
    service, _, bulas, storage, queue = build_seed_service()

    summary = await service.seed_documents(
        admin_email="admin@example.com",
        candidates=[candidate],
        is_dry_run=False,
    )

    assert summary.failed == 1
    assert summary.failures[0].filename == "dipirona.pdf"
    assert "checksum" in summary.failures[0].reason.lower()
    storage.find_by_sha256_checksum.assert_not_awaited()
    bulas.create_bula.assert_not_awaited()
    queue.enqueue_bula_ingestion.assert_not_awaited()


@pytest.mark.anyio
async def test_seed_cleans_up_new_bula_and_object_when_queue_fails() -> None:
    bula = Mock(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        file_address="stored_objects/new",
    )
    service, _, bulas, storage, queue = build_seed_service()
    storage.put_bytes.return_value = "stored_objects/new"
    bulas.create_bula.return_value = bula
    queue.enqueue_bula_ingestion.side_effect = RuntimeError("queue unavailable")

    summary = await service.seed_documents(
        admin_email="admin@example.com",
        candidates=[build_candidate()],
        is_dry_run=False,
    )

    assert summary.failed == 1
    assert summary.inserted == 0
    bulas.delete_bula.assert_awaited_once_with(bula)
    storage.delete.assert_awaited_once_with("stored_objects/new")


@pytest.mark.anyio
async def test_seed_rejects_non_admin_owner_before_processing() -> None:
    service, users, bulas, storage, queue = build_seed_service()
    users.get_user_by_email.return_value = Mock(
        id=42,
        role=UserRole.USER,
        is_active=True,
    )

    with pytest.raises(SystemBulaSeedConfigurationError, match="admin role"):
        await service.seed_documents(
            admin_email="user@example.com",
            candidates=[build_candidate()],
            is_dry_run=False,
        )

    storage.find_by_sha256_checksum.assert_not_awaited()
    bulas.create_bula.assert_not_awaited()
    queue.enqueue_bula_ingestion.assert_not_awaited()
