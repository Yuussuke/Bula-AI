from typing import BinaryIO
from app.modules.bulas.repository import DocumentRepository
from app.modules.bulas.helpers import PdfTextExtractor, Chunking
from app.modules.bulas.schemas import BulaUploadResponse

class BulaService:
    def __init__(
        self, 
        document_repo: DocumentRepository, 
        pdf_extractor: PdfTextExtractor, 
        chunking: Chunking
    ):
        self.repo = document_repo
        self.extractor = pdf_extractor
        self.chunker = chunking

    async def process_pdf(self, file: BinaryIO, filename: str | None = None) -> BulaUploadResponse:
        safe_name = filename or "arquivo_sem_nome.pdf"

        text, pages = self.extractor.extract(file)
        
        chunks = self.chunker.split(text)

        doc = await self.repo.create(safe_name)

        return BulaUploadResponse(
            filename=safe_name,
            pages=pages,
            characters=len(text),
            chunks=len(chunks),
            document_id=doc.id,
        )