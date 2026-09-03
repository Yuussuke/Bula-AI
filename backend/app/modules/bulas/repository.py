from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.bulas.models import (
    Bula,
    BulaCorpus,
    BulaStatus,
    SystemBulaPublication,
    SystemBulaPublicationState,
)
from app.modules.bulas.schemas import SystemBulaManifestEntry
from app.modules.storage.models import StoredObject


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
        statement = (
            select(Bula)
            .options(joinedload(Bula.system_publication))
            .where(Bula.id == bula_id)
        )
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

    async def get_queryable_by_id_for_user(
        self,
        *,
        bula_id: UUID,
        user_id: int,
    ) -> Bula | None:
        private_access = and_(
            Bula.corpus == BulaCorpus.PRIVATE,
            Bula.user_id == user_id,
            Bula.status == BulaStatus.READY,
        )
        published_system_access = and_(
            Bula.corpus == BulaCorpus.SYSTEM,
            Bula.status == BulaStatus.READY,
            SystemBulaPublication.state == SystemBulaPublicationState.PUBLISHED,
            StoredObject.sha256_checksum == SystemBulaPublication.sha256_checksum,
            StoredObject.content_size_bytes == SystemBulaPublication.content_size_bytes,
        )
        statement = (
            select(Bula)
            .outerjoin(
                SystemBulaPublication,
                SystemBulaPublication.bula_id == Bula.id,
            )
            .outerjoin(
                StoredObject,
                StoredObject.object_address == Bula.file_address,
            )
            .options(joinedload(Bula.system_publication))
            .where(Bula.id == bula_id, or_(private_access, published_system_access))
        )
        result = await self.db.execute(statement)
        return result.unique().scalar_one_or_none()

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

    async def create_system_publication(
        self,
        *,
        bula: Bula,
        manifest_entry: SystemBulaManifestEntry,
        supersedes_bula_id: UUID | None = None,
    ) -> SystemBulaPublication:
        publication = SystemBulaPublication(
            bula_id=bula.id,
            state=SystemBulaPublicationState.STAGED,
            target_id=manifest_entry.target_id,
            active_ingredient=manifest_entry.active_ingredient,
            product_name=manifest_entry.product_name,
            strength=manifest_entry.strength,
            pharmaceutical_form=manifest_entry.pharmaceutical_form,
            presentation=manifest_entry.presentation,
            audience=manifest_entry.audience,
            manufacturer=manifest_entry.manufacturer,
            company_tax_id=manifest_entry.company_tax_id,
            anvisa_product_id=manifest_entry.anvisa_product_id,
            registration_number=manifest_entry.registration_number,
            process_number=manifest_entry.process_number,
            expedition_number=manifest_entry.expedition_number,
            transaction_number=manifest_entry.transaction_number,
            source_record_id=manifest_entry.source_record_id,
            canonical_source_url=str(manifest_entry.canonical_source_url),
            source_published_at=manifest_entry.source_published_at,
            source_updated_at=manifest_entry.source_updated_at,
            search_query=manifest_entry.search_query,
            downloader_version=manifest_entry.downloader_version,
            downloaded_at=manifest_entry.downloaded_at,
            filename=manifest_entry.filename,
            sha256_checksum=manifest_entry.sha256_checksum,
            content_size_bytes=manifest_entry.content_size_bytes,
            supersedes_bula_id=supersedes_bula_id,
        )
        self.db.add(publication)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise BulaPersistenceError() from exc

        await self.db.refresh(publication)
        return publication

    async def get_system_publication(
        self,
        *,
        bula_id: UUID,
    ) -> SystemBulaPublication | None:
        statement = select(SystemBulaPublication).where(
            SystemBulaPublication.bula_id == bula_id
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_system_publication_by_source_identity(
        self,
        *,
        source_record_id: str,
        audience: str,
    ) -> SystemBulaPublication | None:
        statement = (
            select(SystemBulaPublication)
            .options(joinedload(SystemBulaPublication.bula))
            .where(
                SystemBulaPublication.source_record_id == source_record_id,
                SystemBulaPublication.audience == audience,
            )
            .order_by(SystemBulaPublication.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def update_system_publication_state(
        self,
        *,
        publication: SystemBulaPublication,
        state: SystemBulaPublicationState,
        reviewed_by_user_id: int | None = None,
        reviewed_by_name: str | None = None,
        reviewed_at: datetime | None = None,
        review_notes: str | None = None,
        published_by_user_id: int | None = None,
        published_by_name: str | None = None,
        published_at: datetime | None = None,
        withdrawal_reason: str | None = None,
    ) -> SystemBulaPublication:
        publication.state = state
        if reviewed_by_user_id is not None:
            publication.reviewed_by_user_id = reviewed_by_user_id
            publication.reviewed_by_name = reviewed_by_name
            publication.reviewed_at = reviewed_at
            publication.review_notes = review_notes
        if published_by_user_id is not None:
            publication.published_by_user_id = published_by_user_id
            publication.published_by_name = published_by_name
            publication.published_at = published_at
        publication.withdrawal_reason = withdrawal_reason

        await self.db.commit()
        await self.db.refresh(publication)
        return publication

    async def reset_system_publication_for_reingestion(
        self,
        *,
        publication: SystemBulaPublication,
    ) -> SystemBulaPublication:
        publication.state = SystemBulaPublicationState.STAGED
        publication.reviewed_by_user_id = None
        publication.reviewed_by_name = None
        publication.reviewed_at = None
        publication.review_notes = None
        publication.published_by_user_id = None
        publication.published_by_name = None
        publication.published_at = None
        publication.withdrawal_reason = "Document requires ingestion and review again."
        await self.db.commit()
        await self.db.refresh(publication)
        return publication

    async def list_published_system_bulas(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Bula]:
        statement = (
            self._published_system_bula_statement()
            .order_by(
                SystemBulaPublication.product_name.asc(),
                SystemBulaPublication.manufacturer.asc(),
                Bula.id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(statement)
        return list(result.unique().scalars().all())

    async def get_published_system_bula(self, *, bula_id: UUID) -> Bula | None:
        statement = self._published_system_bula_statement().where(Bula.id == bula_id)
        result = await self.db.execute(statement)
        return result.unique().scalar_one_or_none()

    def _published_system_bula_statement(self) -> Select[tuple[Bula]]:
        return (
            select(Bula)
            .join(
                SystemBulaPublication,
                SystemBulaPublication.bula_id == Bula.id,
            )
            .join(
                StoredObject,
                StoredObject.object_address == Bula.file_address,
            )
            .options(joinedload(Bula.system_publication))
            .where(
                Bula.corpus == BulaCorpus.SYSTEM,
                Bula.status == BulaStatus.READY,
                SystemBulaPublication.state == SystemBulaPublicationState.PUBLISHED,
                StoredObject.sha256_checksum == SystemBulaPublication.sha256_checksum,
                StoredObject.content_size_bytes
                == SystemBulaPublication.content_size_bytes,
            )
        )

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
