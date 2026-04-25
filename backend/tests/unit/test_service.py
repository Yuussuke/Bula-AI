import pytest
import uuid
from io import BytesIO
from unittest.mock import Mock, AsyncMock
from app.modules.bulas.service import BulaService
from app.modules.bulas.helpers import ExtractedBula, InvalidPdfError


@pytest.mark.anyio
async def test_bula_service_success():
    # --- ARRANGE ---
    fake_file = BytesIO(b"fake pdf content")
    fake_filename = "my_leaflet.pdf"
    user_id = 123
    drug_name = "Dipyrone"
    manufacturer = "Example Pharma"

    mock_extractor = Mock()
    mock_extractor.extract.return_value = ExtractedBula(text="Fake text", pages=2)

    mock_chunker = Mock()
    mock_chunker.split.return_value = ["Chunk 1", "Chunk 2", "Chunk 3"]

    mock_repo = AsyncMock()
    mock_object_store_client = AsyncMock()
    mock_object_store_client.put_bytes.return_value = "stored_objects/abc-123"

    bula_id = uuid.uuid4()
    mock_bula = Mock(id=bula_id)
    mock_repo.create_bula.return_value = mock_bula

    service = BulaService(
        bula_repo=mock_repo,
        pdf_extractor=mock_extractor,
        chunking=mock_chunker,
        object_store=mock_object_store_client,
    )

    # --- ACT ---
    result = await service.process_pdf(
        user_id=user_id,
        drug_name=drug_name,
        manufacturer=manufacturer,
        file=fake_file,
        filename=fake_filename,
    )

    # --- ASSERT ---
    assert result.characters == len("Fake text")
    assert result.filename == fake_filename
    assert result.pages == 2
    assert result.chunks == 3
    assert result.bula_id == bula_id

    extractor_file = mock_extractor.extract.call_args.args[0]
    assert extractor_file is not fake_file
    assert extractor_file.read() == b"fake pdf content"
    mock_chunker.split.assert_called_once_with("Fake text")

    mock_repo.create_bula.assert_awaited_once_with(
        user_id=user_id,
        drug_name=drug_name,
        manufacturer=manufacturer,
        file_url=fake_filename,
        file_address="stored_objects/abc-123",
    )
    mock_object_store_client.put_bytes.assert_awaited_once_with(
        data=b"fake pdf content",
        filename=fake_filename,
    )


@pytest.mark.anyio
async def test_bula_service_invalid_pdf():
    # --- ARRANGE ---
    fake_file = BytesIO(b"corrupted image or file data")
    fake_filename = "foto.png"
    user_id = 123
    drug_name = "Dipyrone"
    manufacturer = None

    mock_extractor = Mock()

    mock_extractor.extract.side_effect = InvalidPdfError("Invalid or corrupted PDF.")

    mock_chunker = Mock()
    mock_repo = AsyncMock()
    mock_object_store_client = AsyncMock()

    service = BulaService(
        bula_repo=mock_repo,
        pdf_extractor=mock_extractor,
        chunking=mock_chunker,
        object_store=mock_object_store_client,
    )

    # --- ACT & ASSERT ---

    with pytest.raises(InvalidPdfError, match="Invalid or corrupted PDF."):
        await service.process_pdf(
            user_id=user_id,
            drug_name=drug_name,
            manufacturer=manufacturer,
            file=fake_file,
            filename=fake_filename,
        )

    extractor_file = mock_extractor.extract.call_args.args[0]
    assert extractor_file is not fake_file
    assert extractor_file.read() == b"corrupted image or file data"

    mock_chunker.split.assert_not_called()
    mock_repo.create_bula.assert_not_awaited()
    mock_object_store_client.put_bytes.assert_not_awaited()


@pytest.mark.anyio
async def test_bula_service_stores_file_via_object_store() -> None:
    import inspect

    import app.modules.bulas.service as svc

    fake_file = BytesIO(b"file content")
    fake_filename = "leaflet.pdf"
    mock_extractor = Mock()
    mock_extractor.extract.return_value = ExtractedBula(text="Text", pages=1)
    mock_chunker = Mock()
    mock_chunker.split.return_value = ["Chunk"]
    mock_repo = AsyncMock()
    mock_object_store_client = AsyncMock()
    mock_object_store_client.put_bytes.return_value = "stored_objects/abc-123"

    bula_id = uuid.uuid4()
    mock_bula = Mock(id=bula_id, file_address="stored_objects/abc-123")
    mock_repo.create_bula.return_value = mock_bula
    service = BulaService(
        bula_repo=mock_repo,
        pdf_extractor=mock_extractor,
        chunking=mock_chunker,
        object_store=mock_object_store_client,
    )

    await service.process_pdf(
        user_id=123,
        drug_name="Dipyrone",
        manufacturer="Example Pharma",
        file=fake_file,
        filename=fake_filename,
    )

    mock_object_store_client.put_bytes.assert_awaited_once_with(
        data=b"file content",
        filename=fake_filename,
    )
    mock_repo.create_bula.assert_awaited_once_with(
        user_id=123,
        drug_name="Dipyrone",
        manufacturer="Example Pharma",
        file_url=fake_filename,
        file_address="stored_objects/abc-123",
    )

    source = inspect.getsource(svc)
    assert "StoredObject" not in source
    assert "LargeBinary" not in source
