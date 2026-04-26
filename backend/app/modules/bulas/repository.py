from sqlalchemy import select
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
        manufacturer: str | None = None,
        file_address: str | None = None,
        file_url: str | None = None,
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

    async def list_by_user(self, *, user_id: int) -> list[Bula]:
        statement = (
            select(Bula)
            .where(Bula.user_id == user_id)
            .order_by(Bula.created_at.desc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())
