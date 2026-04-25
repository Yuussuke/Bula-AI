from io import BytesIO
from typing import BinaryIO

from fastapi.concurrency import run_in_threadpool

from app.modules.bulas.helpers import Chunking, PdfTextExtractor
from app.modules.bulas.repository import BulaRepository
from app.modules.bulas.schemas import BulaUploadResponse
from app.modules.storage.client import ObjectStoreClient


class BulaService:
    def __init__(
        self,
        bula_repo: BulaRepository,
        pdf_extractor: PdfTextExtractor,
        chunking: Chunking,
        object_store: ObjectStoreClient,
    ) -> None:
        self.repo = bula_repo
        self.extractor = pdf_extractor
        self.chunker = chunking
        self.object_store = object_store

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

        file.seek(0)
        file_content = file.read()
        extraction_file = BytesIO(file_content)

        extracted = await run_in_threadpool(self.extractor.extract, extraction_file)
        text = extracted.text
        pages = extracted.pages

        chunks = self.chunker.split(text)
        file_address = await self.object_store.put_bytes(
            data=file_content,
            filename=safe_name,
        )

        bula = await self.repo.create_bula(
            user_id=user_id,
            drug_name=drug_name,
            manufacturer=manufacturer,
            file_url=safe_name,
            file_address=file_address,
        )

        return BulaUploadResponse(
            filename=safe_name,
            pages=pages,
            characters=len(text),
            chunks=len(chunks),
            bula_id=bula.id,
        )
