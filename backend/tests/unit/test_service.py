from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, UploadFile, status
from starlette.datastructures import Headers

from app.modules.bulas.repository import BulaPersistenceError
from app.modules.bulas.service import BulaService


def build_upload_file(
    *,
    content: bytes,
    filename: str = "leaflet.pdf",
    content_type: str = "application/pdf",
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


def build_bula_service(
    *,
    repo: AsyncMock | None = None,
    object_store_client: AsyncMock | None = None,
    max_upload_size_bytes: int = 10 * 1024 * 1024,
) -> BulaService:
    bula_repo = repo or AsyncMock()
    object_store = object_store_client or AsyncMock()

    return BulaService(
        bula_repo=bula_repo,
        object_store=object_store,
        max_upload_size_bytes=max_upload_size_bytes,
    )


@pytest.mark.anyio
async def test_upload_bula_creates_bula_with_file_address() -> None:
    user_id = 123
    mock_bula = Mock(file_address="stored_objects/abc-123")
    mock_repo = AsyncMock()
    mock_repo.create_bula.return_value = mock_bula
    mock_object_store_client = AsyncMock()
    mock_object_store_client.put_file.return_value = "stored_objects/abc-123"
    upload_file = build_upload_file(content=b"%PDF-1.4\n%%EOF")
    service = build_bula_service(
        repo=mock_repo,
        object_store_client=mock_object_store_client,
    )

    result = await service.upload_bula(
        user_id=user_id,
        drug_name=" Dipirona ",
        manufacturer="Example Pharma",
        file=upload_file,
    )

    assert result is mock_bula
    assert result.file_address == "stored_objects/abc-123"
    mock_object_store_client.put_file.assert_awaited_once_with(upload_file)
    mock_repo.create_bula.assert_awaited_once_with(
        user_id=user_id,
        drug_name="Dipirona",
        manufacturer="Example Pharma",
        file_address="stored_objects/abc-123",
    )


@pytest.mark.anyio
async def test_upload_bula_deletes_file_when_bula_persistence_fails() -> None:
    mock_repo = AsyncMock()
    mock_repo.create_bula.side_effect = BulaPersistenceError()
    mock_object_store_client = AsyncMock()
    mock_object_store_client.put_file.return_value = "stored_objects/abc-123"
    upload_file = build_upload_file(content=b"%PDF-1.4\n%%EOF")
    service = build_bula_service(
        repo=mock_repo,
        object_store_client=mock_object_store_client,
    )

    with pytest.raises(BulaPersistenceError):
        await service.upload_bula(
            user_id=123,
            drug_name="Dipirona",
            manufacturer=None,
            file=upload_file,
        )

    mock_object_store_client.delete.assert_awaited_once_with("stored_objects/abc-123")


@pytest.mark.anyio
async def test_upload_bula_keeps_original_error_when_compensating_delete_fails() -> (
    None
):
    mock_repo = AsyncMock()
    mock_repo.create_bula.side_effect = BulaPersistenceError()
    mock_object_store_client = AsyncMock()
    mock_object_store_client.put_file.return_value = "stored_objects/abc-123"
    mock_object_store_client.delete.side_effect = RuntimeError("delete failed")
    upload_file = build_upload_file(content=b"%PDF-1.4\n%%EOF")
    service = build_bula_service(
        repo=mock_repo,
        object_store_client=mock_object_store_client,
    )

    with pytest.raises(BulaPersistenceError):
        await service.upload_bula(
            user_id=123,
            drug_name="Dipirona",
            manufacturer=None,
            file=upload_file,
        )

    mock_object_store_client.delete.assert_awaited_once_with("stored_objects/abc-123")


@pytest.mark.anyio
async def test_upload_bula_rejects_invalid_content_type_before_storage() -> None:
    mock_repo = AsyncMock()
    mock_object_store_client = AsyncMock()
    upload_file = build_upload_file(
        content=b"%PDF-1.4\n%%EOF",
        content_type="image/png",
    )
    service = build_bula_service(
        repo=mock_repo,
        object_store_client=mock_object_store_client,
    )

    with pytest.raises(HTTPException) as exception_info:
        await service.upload_bula(
            user_id=123,
            drug_name="Dipirona",
            manufacturer=None,
            file=upload_file,
        )

    assert exception_info.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    mock_object_store_client.put_file.assert_not_awaited()
    mock_repo.create_bula.assert_not_awaited()


@pytest.mark.anyio
async def test_upload_bula_rejects_oversized_file_before_storage() -> None:
    mock_repo = AsyncMock()
    mock_object_store_client = AsyncMock()
    upload_file = build_upload_file(content=b"%PDF-" + b"0" * 10)
    service = build_bula_service(
        repo=mock_repo,
        object_store_client=mock_object_store_client,
        max_upload_size_bytes=5,
    )

    with pytest.raises(HTTPException) as exception_info:
        await service.upload_bula(
            user_id=123,
            drug_name="Dipirona",
            manufacturer=None,
            file=upload_file,
        )

    assert exception_info.value.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    mock_object_store_client.put_file.assert_not_awaited()
    mock_repo.create_bula.assert_not_awaited()
