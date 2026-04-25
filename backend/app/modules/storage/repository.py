from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.modules.storage.models import StoredObject


class StoredObjectPersistenceError(Exception):
    """Raised when a stored object cannot be persisted."""


class StoredObjectNotFoundError(Exception):
    """Raised when a stored object address cannot be found."""


class StoredObjectRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_stored_object(
        self,
        *,
        object_address: str,
        original_filename: str | None,
        content_type: str | None,
        content_size_bytes: int,
        sha256_checksum: str,
        data: bytes,
    ) -> StoredObject:
        stored_object = StoredObject(
            object_address=object_address,
            original_filename=original_filename,
            content_type=content_type,
            content_size_bytes=content_size_bytes,
            sha256_checksum=sha256_checksum,
            data=data,
        )

        self.db.add(stored_object)

        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise StoredObjectPersistenceError() from exc

        await self.db.refresh(stored_object)
        return stored_object

    async def get_by_object_address(
        self,
        object_address: str,
    ) -> StoredObject | None:
        statement = select(StoredObject).where(
            StoredObject.object_address == object_address
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_object_address_with_data(
        self,
        object_address: str,
    ) -> StoredObject | None:
        statement = (
            select(StoredObject)
            .options(undefer(StoredObject.data))
            .where(StoredObject.object_address == object_address)
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def object_exists(self, object_address: str) -> bool:
        statement = select(StoredObject.id).where(
            StoredObject.object_address == object_address
        )
        result = await self.db.execute(statement)
        stored_object_id = result.scalar_one_or_none()
        return stored_object_id is not None

    async def delete_by_address(self, object_address: str) -> None:
        statement = delete(StoredObject).where(
            StoredObject.object_address == object_address
        )
        result = await self.db.execute(statement)

        if result.rowcount == 0:
            await self.db.rollback()
            raise StoredObjectNotFoundError(object_address)

        await self.db.commit()
