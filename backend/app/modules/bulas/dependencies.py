from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.bulas.helpers import Chunking, PdfTextExtractor
from app.modules.bulas.repository import BulaRepository
from app.modules.bulas.service import BulaService
from app.modules.storage.client import ObjectStoreClient
from app.modules.storage.dependencies import get_object_store_client


@lru_cache
def get_pdf_text_extractor() -> PdfTextExtractor:
    return PdfTextExtractor()


@lru_cache
def get_chunking() -> Chunking:
    return Chunking()


def get_bula_repository(db: AsyncSession = Depends(get_db)) -> BulaRepository:
    return BulaRepository(db=db)


def get_bula_service(
    repo: BulaRepository = Depends(get_bula_repository),
    extractor: PdfTextExtractor = Depends(get_pdf_text_extractor),
    chunking: Chunking = Depends(get_chunking),
    object_store: ObjectStoreClient = Depends(get_object_store_client),
) -> BulaService:
    return BulaService(
        bula_repo=repo,
        pdf_extractor=extractor,
        chunking=chunking,
        object_store=object_store,
    )
