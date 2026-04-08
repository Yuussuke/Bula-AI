import pytest
from unittest.mock import Mock, AsyncMock # <-- A mágica mora aqui
from app.modules.bulas.service import BulaService
from app.modules.bulas.helpers import ExtractedBula, InvalidPdfError

@pytest.mark.asyncio
async def test_bula_service_success():
    # --- ARRANGE ---
    fake_file = b"fake pdf content"
    fake_filename = "minha_bula.pdf"

    mock_extractor = Mock()
    mock_extractor.extract.return_value = ExtractedBula(text="Texto falso", pages=2)

    mock_chunker = Mock()
    mock_chunker.split.return_value = ["Chunk 1", "Chunk 2", "Chunk 3"]

    mock_repo = AsyncMock() 

    mock_document = Mock(id=999) 
    mock_repo.create.return_value = mock_document 


    service = BulaService(
        document_repo=mock_repo,
        pdf_extractor=mock_extractor,
        chunking=mock_chunker
    )

    # --- ACT ---
    result = await service.process_pdf(file=fake_file, filename=fake_filename)

    # --- ASSERT ---
    assert result.characters == len("Texto falso")
    assert result.filename == fake_filename 
    assert result.pages == 2
    assert result.chunks == 3
    assert result.document_id == 999

    mock_extractor.extract.assert_called_once_with(fake_file)
    mock_chunker.split.assert_called_once_with("Texto falso")

    mock_repo.create.assert_awaited_once_with(fake_filename)

@pytest.mark.asyncio
async def test_bula_service_invalid_pdf():
    # --- ARRANGE ---
    fake_file = b"dados de uma imagem ou arquivo corrompido"
    fake_filename = "foto.png"


    mock_extractor = Mock()

    mock_extractor.extract.side_effect = InvalidPdfError("Arquivo PDF invalido ou corrompido.")


    mock_chunker = Mock()
    mock_repo = AsyncMock()

    service = BulaService(
        document_repo=mock_repo,
        pdf_extractor=mock_extractor,
        chunking=mock_chunker
    )

    # --- ACT & ASSERT ---
    
    with pytest.raises(InvalidPdfError, match="Arquivo PDF invalido ou corrompido."):
        await service.process_pdf(file=fake_file, filename=fake_filename)
    
    mock_extractor.extract.assert_called_once_with(fake_file)

    mock_chunker.split.assert_not_called()
    mock_repo.create.assert_not_awaited()