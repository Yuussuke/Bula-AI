# app/modules/bulas/service.py
from typing import BinaryIO
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.bulas.repository import DocumentRepository
from app.modules.bulas.schemas import BulaUploadResponse


class InvalidPdfError(Exception):
    """Raised when the uploaded file cannot be parsed as a valid PDF."""

class BulaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.document_repo = DocumentRepository(db)

    def _extract_text_from_pdf(self, file: BinaryIO) -> tuple[str, int]:
        """Private method to extract text from the PDF."""
        try:
            reader = PdfReader(file)
        except PdfReadError as exc:
            raise InvalidPdfError("Arquivo PDF invalido ou corrompido.") from exc

        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text, len(reader.pages)

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        """Private method to split text into smaller chunks."""
        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap

        return chunks

    async def process_pdf(self, file: BinaryIO, filename: str | None = None) -> BulaUploadResponse:
        text, pages = self._extract_text_from_pdf(file)
        chunks = self._chunk_text(text)

        safe_name = filename or "arquivo_sem_nome.pdf"

        try:
            # Use the new repository class method!
            doc = await self.document_repo.create(safe_name)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return BulaUploadResponse(
            filename=safe_name,
            pages=pages,
            characters=len(text),
            chunks=len(chunks),
            document_id=doc.id,
        )
    