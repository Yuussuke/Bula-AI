from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.storage.client import ObjectStoreClient, PgObjectStoreClient
from app.modules.storage.repository import StoredObjectRepository


def get_stored_object_repository(
    db: AsyncSession = Depends(get_db),
) -> StoredObjectRepository:
    return StoredObjectRepository(db=db)


def get_object_store_client(
    repository: StoredObjectRepository = Depends(get_stored_object_repository),
) -> ObjectStoreClient:
    return PgObjectStoreClient(repository=repository)
