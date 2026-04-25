from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bulas.models import Bula, BulaStatus


class BulaPersistenceError(Exception):
    """Raised when a bula cannot be persisted."""


class BulaRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_bula(
        self,
        *,
        user_id: int,
        drug_name: str,
        file_url: str,
        manufacturer: str | None = None,
        file_address: str | None = None,
        qdrant_collection: str | None = None,
        status: BulaStatus = BulaStatus.PENDING,
    ) -> Bula:
        bula = Bula(
            user_id=user_id,
            drug_name=drug_name,
            manufacturer=manufacturer,
            file_url=file_url,
            file_address=file_address,
            qdrant_collection=qdrant_collection,
            status=status,
        )

        self.db.add(bula)

        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise BulaPersistenceError() from exc

        await self.db.refresh(bula)
        return bula
