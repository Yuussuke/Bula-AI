from typing import BinaryIO
from app.modules.bulas.repository import BulaRepository
from app.modules.bulas.helpers import PdfTextExtractor, Chunking
from app.modules.bulas.schemas import BulaUploadResponse
from fastapi.concurrency import run_in_threadpool


class BulaService:
    def __init__(
        self,
        bula_repo: BulaRepository,
        pdf_extractor: PdfTextExtractor,
        chunking: Chunking,
    ):
        self.repo = bula_repo
        self.extractor = pdf_extractor
        self.chunker = chunking

    async def process_pdf(
        self,
        *,
        user_id: int,
        drug_name: str,
        manufacturer: str | None,
        file: BinaryIO,
        filename: str | None = None,
    ) -> BulaUploadResponse:
        safe_name = filename or "arquivo_sem_nome.pdf"

        extracted = await run_in_threadpool(self.extractor.extract, file)
        text = extracted.text
        pages = extracted.pages

        chunks = self.chunker.split(text)

        bula = await self.repo.create_bula(
            user_id=user_id,
            drug_name=drug_name,
            manufacturer=manufacturer,
            file_url=safe_name,
        )

        return BulaUploadResponse(
            filename=safe_name,
            pages=pages,
            characters=len(text),
            chunks=len(chunks),
            bula_id=bula.id,
        )
