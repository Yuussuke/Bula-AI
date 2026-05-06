from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.modules.bulas.repository import BulaRepository
from app.modules.bulas.service import BulaService
from app.modules.storage.client import ObjectStoreClient
from app.modules.storage.dependencies import get_object_store_client


def get_bula_repository(db: AsyncSession = Depends(get_db)) -> BulaRepository:
    return BulaRepository(db=db)


def get_bula_service(
    repo: BulaRepository = Depends(get_bula_repository),
    object_store: ObjectStoreClient = Depends(get_object_store_client),
    settings: Settings = Depends(get_settings),
) -> BulaService:
    return BulaService(
        bula_repo=repo,
        object_store=object_store,
        max_upload_size_bytes=settings.max_bula_upload_size_bytes,
    )
