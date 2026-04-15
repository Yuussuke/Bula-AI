from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.modules.bulas.models import Bula, BulaStatus


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
        qdrant_collection: str | None = None,
        status: BulaStatus = BulaStatus.PENDING,
    ) -> Bula:
        bula = Bula(
            user_id=user_id,
            drug_name=drug_name,
            manufacturer=manufacturer,
            file_url=file_url,
            qdrant_collection=qdrant_collection,
            status=status,
        )

        self.db.add(bula)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise IntegrityError("Failed to create Bula due to integrity error.")

        await self.db.refresh(bula)
        return bula
