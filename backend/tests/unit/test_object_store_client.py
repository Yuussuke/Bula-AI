import hashlib

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.storage.client import PgObjectStoreClient
from app.modules.storage.repository import StoredObjectRepository


@pytest.fixture
def object_store_client(db_session: AsyncSession) -> PgObjectStoreClient:
    repository = StoredObjectRepository(db=db_session)
    return PgObjectStoreClient(repository=repository)


@pytest.mark.anyio
async def test_put_bytes_saves_and_reads_same_content(
    object_store_client: PgObjectStoreClient,
) -> None:
    original_content = b"conteudo de uma bula em pdf"

    metadata = await object_store_client.put_bytes(
        content=original_content,
        original_filename="bula-dipirona.pdf",
        content_type="application/pdf",
    )

    retrieved_content = await object_store_client.get_bytes(metadata.object_address)

    assert retrieved_content == original_content


@pytest.mark.anyio
async def test_put_bytes_saves_retrievable_metadata(
    object_store_client: PgObjectStoreClient,
) -> None:
    original_content = b"metadados importantes"
    expected_checksum = hashlib.sha256(original_content).hexdigest()

    created_metadata = await object_store_client.put_bytes(
        content=original_content,
        original_filename="bula-losartana.pdf",
        content_type="application/pdf",
    )

    retrieved_metadata = await object_store_client.get_metadata(
        created_metadata.object_address
    )

    assert retrieved_metadata is not None
    assert retrieved_metadata.object_address == created_metadata.object_address
    assert retrieved_metadata.original_filename == "bula-losartana.pdf"
    assert retrieved_metadata.content_type == "application/pdf"
    assert retrieved_metadata.content_size_bytes == len(original_content)
    assert retrieved_metadata.sha256_checksum == expected_checksum
    assert retrieved_metadata.created_at is not None
    assert retrieved_metadata.updated_at is not None


@pytest.mark.anyio
async def test_exists_returns_true_for_saved_object(
    object_store_client: PgObjectStoreClient,
) -> None:
    metadata = await object_store_client.put_bytes(
        content=b"conteudo existente",
        original_filename=None,
        content_type=None,
    )

    object_exists = await object_store_client.exists(metadata.object_address)

    assert object_exists is True


@pytest.mark.anyio
async def test_missing_object_returns_none_and_does_not_exist(
    object_store_client: PgObjectStoreClient,
) -> None:
    missing_object_address = "stored_objects/nao-existe"

    retrieved_content = await object_store_client.get_bytes(missing_object_address)
    retrieved_metadata = await object_store_client.get_metadata(missing_object_address)
    object_exists = await object_store_client.exists(missing_object_address)

    assert retrieved_content is None
    assert retrieved_metadata is None
    assert object_exists is False


@pytest.mark.anyio
async def test_identical_content_creates_distinct_object_addresses(
    object_store_client: PgObjectStoreClient,
) -> None:
    original_content = b"mesmo conteudo"

    first_metadata = await object_store_client.put_bytes(
        content=original_content,
        original_filename="primeira-bula.pdf",
        content_type="application/pdf",
    )
    second_metadata = await object_store_client.put_bytes(
        content=original_content,
        original_filename="segunda-bula.pdf",
        content_type="application/pdf",
    )

    assert first_metadata.object_address != second_metadata.object_address
    assert first_metadata.sha256_checksum == second_metadata.sha256_checksum
