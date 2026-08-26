from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bulas.models import Bula, BulaCorpus, BulaStatus


MAX_ERROR_MESSAGE_LENGTH = 1000


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
        corpus: BulaCorpus = BulaCorpus.PRIVATE,
    ) -> Bula:
        bula = Bula(
            user_id=user_id,
            drug_name=drug_name,
            manufacturer=manufacturer,
            file_url=file_url,
            file_address=file_address,
            qdrant_collection=qdrant_collection,
            status=status,
            corpus=corpus,
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
            select(Bula).where(Bula.user_id == user_id).order_by(Bula.created_at.desc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, *, bula_id: UUID) -> Bula | None:
        statement = select(Bula).where(Bula.id == bula_id)
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self,
        *,
        bula_id: UUID,
        user_id: int,
    ) -> Bula | None:
        statement = select(Bula).where(Bula.id == bula_id, Bula.user_id == user_id)
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_file_address_and_corpus(
        self,
        *,
        file_address: str,
        corpus: BulaCorpus,
    ) -> Bula | None:
        statement = select(Bula).where(
            Bula.file_address == file_address,
            Bula.corpus == corpus,
        )
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def update_ingestion_status(
        self,
        *,
        bula: Bula,
        status: BulaStatus,
        error_message: str | None = None,
        qdrant_collection: str | None = None,
    ) -> Bula:
        bula.status = status
        bula.error_message = self._clean_error_message(error_message)

        if qdrant_collection is not None:
            bula.qdrant_collection = qdrant_collection

        await self.db.commit()
        await self.db.refresh(bula)
        return bula

    async def delete_bula(self, bula: Bula) -> None:
        await self.db.delete(bula)
        await self.db.commit()

    def _clean_error_message(self, error_message: str | None) -> str | None:
        if error_message is None:
            return None

        clean_error_message = error_message.strip()
        if not clean_error_message:
            return None

        return clean_error_message[:MAX_ERROR_MESSAGE_LENGTH]
