import hashlib
from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.storage.client import PgObjectStoreClient
from app.modules.storage.models import StoredObject
from app.modules.storage.repository import (
    StoredObjectNotFoundError,
    StoredObjectRepository,
)
from app.modules.storage.schemas import StoredObjectRef


@pytest.fixture
def object_store_client(db_session: AsyncSession) -> PgObjectStoreClient:
    repository = StoredObjectRepository(db=db_session)
    return PgObjectStoreClient(repository=repository)


@pytest.mark.anyio
async def test_put_bytes_saves_and_reads_same_content(
    object_store_client: PgObjectStoreClient,
) -> None:
    original_content = b"leaflet pdf content"

    address = await object_store_client.put_bytes(
        data=original_content,
        filename="dipyrone-leaflet.pdf",
    )

    retrieved_content = await object_store_client.get_bytes(address)

    assert retrieved_content == original_content


@pytest.mark.anyio
async def test_put_bytes_saves_retrievable_metadata(
    object_store_client: PgObjectStoreClient,
) -> None:
    original_content = b"important metadata"
    expected_checksum = hashlib.sha256(original_content).hexdigest()

    address = await object_store_client.put_bytes(
        data=original_content,
        filename="losartan-leaflet.pdf",
    )

    retrieved_metadata = await object_store_client.get_metadata(address)

    assert isinstance(retrieved_metadata, StoredObjectRef)
    assert retrieved_metadata.object_address == address
    assert retrieved_metadata.original_filename == "losartan-leaflet.pdf"
    assert retrieved_metadata.content_type is None
    assert retrieved_metadata.content_size_bytes == len(original_content)
    assert retrieved_metadata.sha256_checksum == expected_checksum
    assert retrieved_metadata.created_at is not None
    assert retrieved_metadata.updated_at is not None


@pytest.mark.anyio
async def test_exists_returns_true_for_saved_object(
    object_store_client: PgObjectStoreClient,
) -> None:
    address = await object_store_client.put_bytes(
        data=b"existing content",
        filename="existing.pdf",
    )

    object_exists = await object_store_client.exists(address)

    assert object_exists is True


@pytest.mark.anyio
async def test_missing_object_does_not_exist(
    object_store_client: PgObjectStoreClient,
) -> None:
    missing_object_address = "stored_objects/does-not-exist"

    object_exists = await object_store_client.exists(missing_object_address)

    assert object_exists is False


@pytest.mark.anyio
async def test_identical_content_creates_distinct_object_addresses(
    object_store_client: PgObjectStoreClient,
) -> None:
    original_content = b"same content"

    first_address = await object_store_client.put_bytes(
        data=original_content,
        filename="first-leaflet.pdf",
    )
    second_address = await object_store_client.put_bytes(
        data=original_content,
        filename="second-leaflet.pdf",
    )
    first_metadata = await object_store_client.get_metadata(first_address)
    second_metadata = await object_store_client.get_metadata(second_address)

    assert first_address != second_address
    assert first_metadata.sha256_checksum == second_metadata.sha256_checksum


@pytest.mark.anyio
async def test_put_file_persists_upload_file_content(
    object_store_client: PgObjectStoreClient,
) -> None:
    content = b"pdf via upload file"
    upload = UploadFile(filename="test.pdf", file=BytesIO(content))

    address = await object_store_client.put_file(upload)
    retrieved = await object_store_client.get_bytes(address)

    assert retrieved == content


@pytest.mark.anyio
async def test_delete_removes_object(
    object_store_client: PgObjectStoreClient,
) -> None:
    address = await object_store_client.put_bytes(data=b"to delete", filename="del.pdf")

    await object_store_client.delete(address)

    assert not await object_store_client.exists(address)


@pytest.mark.anyio
async def test_get_bytes_raises_for_missing_object(
    object_store_client: PgObjectStoreClient,
) -> None:
    with pytest.raises(StoredObjectNotFoundError):
        await object_store_client.get_bytes("stored_objects/does-not-exist")


@pytest.mark.anyio
async def test_get_metadata_raises_for_missing_object(
    object_store_client: PgObjectStoreClient,
) -> None:
    with pytest.raises(StoredObjectNotFoundError):
        await object_store_client.get_metadata("stored_objects/does-not-exist")


@pytest.mark.anyio
async def test_delete_raises_for_missing_object(
    object_store_client: PgObjectStoreClient,
) -> None:
    with pytest.raises(StoredObjectNotFoundError):
        await object_store_client.delete("stored_objects/does-not-exist")


@pytest.mark.anyio
async def test_get_metadata_does_not_load_data_column(
    object_store_client: PgObjectStoreClient,
    db_session: AsyncSession,
) -> None:
    address = await object_store_client.put_bytes(
        data=b"heavy blob", filename="big.pdf"
    )
    db_session.expire_all()

    await object_store_client.get_metadata(address)
    result = await db_session.execute(
        select(StoredObject).where(StoredObject.object_address == address)
    )
    stored_object = result.scalar_one()
    state = sa_inspect(stored_object)

    assert "data" in state.unloaded, (
        "data column must remain deferred after get_metadata"
    )
