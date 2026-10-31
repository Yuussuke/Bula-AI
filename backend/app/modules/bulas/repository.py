from datetime import datetime
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, SQLColumnExpression, and_, func, or_, select, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.bulas.models import (
    Bula,
    BulaCorpus,
    BulaStatus,
    BulaCurationEvent,
    SharedBulaSubmission,
    PublicCatalogScope,
    SystemBulaPublication,
    SystemBulaPublicationState,
)
from app.modules.bulas.schemas import (
    SystemBulaManifestEntry,
    SystemBulaSearchQuery,
    PublicCatalogSearchQuery,
)
from app.modules.storage.models import StoredObject
from app.modules.bulas.curation_repository import (
    CurationRepository,
    approved_shared_conditions,
)
from app.modules.bulas.curation_audit import shared_bula_snapshot


MAX_ERROR_MESSAGE_LENGTH = 1000


class BulaPersistenceError(Exception):
    """Raised when a bula cannot be persisted."""


class BulaRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_ready_bulas_for_indexing(
        self, *, after_id: UUID | None = None, limit: int = 100
    ) -> list[Bula]:
        """Operator-only keyset pagination; not a user catalog or access check."""
        statement = select(Bula).where(Bula.status == BulaStatus.READY)
        if after_id is not None:
            statement = statement.where(Bula.id > after_id)
        result = await self.db.execute(statement.order_by(Bula.id).limit(limit))
        return list(result.scalars().all())

    async def create_bula(
        self,
        *,
        user_id: int,
        drug_name: str,
        alias: str | None = None,
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
            alias=alias,
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

    async def list_by_user(
        self, *, user_id: int, corpus: BulaCorpus | None = None
    ) -> list[Bula]:
        statement = (
            select(Bula).where(Bula.user_id == user_id).order_by(Bula.created_at.desc())
        )
        if corpus is not None:
            statement = statement.where(Bula.corpus == corpus)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, *, bula_id: UUID) -> Bula | None:
        statement = (
            select(Bula)
            .options(
                joinedload(Bula.system_publication), joinedload(Bula.shared_submission)
            )
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
        approved_shared_access = and_(*approved_shared_conditions())
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
            .outerjoin(SharedBulaSubmission, SharedBulaSubmission.bula_id == Bula.id)
            .options(
                joinedload(Bula.system_publication), joinedload(Bula.shared_submission)
            )
            .where(
                Bula.id == bula_id,
                or_(private_access, published_system_access, approved_shared_access),
            )
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

    async def search_published_system_bulas(
        self, *, filters: SystemBulaSearchQuery
    ) -> tuple[list[Bula], int]:
        statement = self._published_system_bula_statement()
        if filters.audience != "all":
            statement = statement.where(
                SystemBulaPublication.audience == filters.audience
            )
        searchable_columns = (
            SystemBulaPublication.product_name,
            SystemBulaPublication.active_ingredient,
            SystemBulaPublication.manufacturer,
            SystemBulaPublication.strength,
            SystemBulaPublication.pharmaceutical_form,
        )
        # Filter the whole authorized catalog before counting or paginating.
        # unaccent is provided by the existing PostgreSQL ingestion migrations.
        statement = self._apply_catalog_search(
            statement, searchable_columns, filters.query
        )
        total_statement = select(func.count()).select_from(
            statement.with_only_columns(Bula.id).order_by(None).subquery()
        )
        total = int(await self.db.scalar(total_statement) or 0)
        product_order = SystemBulaPublication.product_name.asc()
        if filters.sort == "name_desc":
            product_order = SystemBulaPublication.product_name.desc()
        page_statement = (
            statement.order_by(
                product_order,
                SystemBulaPublication.manufacturer.asc(),
                Bula.id.asc(),
            )
            .limit(filters.limit)
            .offset(filters.offset)
        )
        result = await self.db.execute(page_statement)
        return list(result.unique().scalars().all()), total

    async def list_queryable_system_bulas(
        self, *, bula_ids: Sequence[UUID] | None = None
    ) -> list[Bula]:
        """Published source scope; optional IDs only narrow eligible documents."""
        statement = self._published_system_bula_statement().order_by(Bula.id)
        if bula_ids is not None:
            statement = statement.where(Bula.id.in_(bula_ids))
        result = await self.db.execute(
            statement.execution_options(populate_existing=True)
        )
        return list(result.unique().scalars().all())

    async def list_queryable_public_bulas(
        self,
        *,
        bula_ids: Sequence[UUID] | None = None,
        catalog_scope: PublicCatalogScope = PublicCatalogScope.ALL,
    ) -> list[Bula]:
        system: list[Bula] = []
        shared: list[Bula] = []
        if catalog_scope != PublicCatalogScope.SHARED:
            system = await self.list_queryable_system_bulas(bula_ids=bula_ids)
        if catalog_scope != PublicCatalogScope.SYSTEM:
            shared = await CurationRepository(self.db).list_public(bula_ids=bula_ids)
        return sorted([*system, *shared], key=lambda bula: bula.id)

    def _apply_catalog_search(
        self,
        statement: Select[tuple[Bula]],
        columns: Sequence[SQLColumnExpression[str | None]],
        query: str,
    ) -> Select[tuple[Bula]]:
        for term in query.split():
            escaped_term = term.replace("/", "//").replace("%", "/%").replace("_", "/_")
            statement = statement.where(
                or_(
                    *(
                        func.lower(func.unaccent(column)).contains(
                            func.lower(func.unaccent(escaped_term)), escape="/"
                        )
                        for column in columns
                    )
                )
            )
        return statement

    async def search_public_catalog(
        self, *, filters: PublicCatalogSearchQuery
    ) -> tuple[list[Bula], int]:
        system_ids = self._published_system_bula_statement().with_only_columns(Bula.id)
        shared_ids = (
            CurationRepository(self.db).public_statement().with_only_columns(Bula.id)
        )
        if filters.catalog_scope == PublicCatalogScope.SYSTEM:
            authorized_ids = system_ids.subquery()
        elif filters.catalog_scope == PublicCatalogScope.SHARED:
            authorized_ids = shared_ids.subquery()
        else:
            authorized_ids = system_ids.union_all(shared_ids).subquery()
        statement = (
            select(Bula)
            .join(authorized_ids, authorized_ids.c.id == Bula.id)
            .outerjoin(SystemBulaPublication, SystemBulaPublication.bula_id == Bula.id)
            .outerjoin(SharedBulaSubmission, SharedBulaSubmission.bula_id == Bula.id)
            .options(
                joinedload(Bula.system_publication), joinedload(Bula.shared_submission)
            )
        )
        is_system = Bula.corpus == BulaCorpus.SYSTEM
        name = case(
            (is_system, SystemBulaPublication.product_name), else_=Bula.drug_name
        )
        manufacturer = case(
            (is_system, SystemBulaPublication.manufacturer), else_=Bula.manufacturer
        )
        strength = case(
            (is_system, SystemBulaPublication.strength),
            else_=SharedBulaSubmission.strength,
        )
        presentation = case(
            (is_system, SystemBulaPublication.presentation),
            else_=SharedBulaSubmission.presentation,
        )
        if filters.audience != "all":
            statement = statement.where(
                is_system, SystemBulaPublication.audience == filters.audience
            )
        statement = self._apply_catalog_search(
            statement,
            [
                name,
                manufacturer,
                strength,
                presentation,
                case((is_system, SystemBulaPublication.active_ingredient)),
                case((is_system, SystemBulaPublication.pharmaceutical_form)),
            ],
            filters.query,
        )
        total = int(
            await self.db.scalar(
                select(func.count()).select_from(
                    statement.with_only_columns(Bula.id).subquery()
                )
            )
            or 0
        )
        result = await self.db.execute(
            statement.order_by(
                name.desc() if filters.sort == "name_desc" else name.asc(),
                manufacturer.asc(),
                Bula.id,
            )
            .limit(filters.limit)
            .offset(filters.offset)
        )
        return list(result.unique().scalars().all()), total

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
        before_state = None
        if bula.corpus == BulaCorpus.SHARED:
            await self.db.execute(
                select(Bula.id).where(Bula.id == bula.id).with_for_update()
            )
            current = await self.db.scalar(
                select(Bula)
                .options(joinedload(Bula.shared_submission))
                .where(Bula.id == bula.id)
                .execution_options(populate_existing=True)
            )
            if current is None:
                raise BulaPersistenceError(
                    "Shared source disappeared during ingestion."
                )
            bula = current
            before_state = shared_bula_snapshot(bula)
        bula.status = status
        bula.error_message = self._clean_error_message(error_message)

        if qdrant_collection is not None:
            bula.qdrant_collection = qdrant_collection

        if before_state is not None and bula.shared_submission is not None:
            after_state = shared_bula_snapshot(bula)
            if before_state != after_state:
                self.db.add(
                    BulaCurationEvent(
                        bula_id=bula.id,
                        actor_id=None,
                        actor_name="Sistema de ingestão",
                        actor_role="system",
                        action=f"ingestion_{status.value}",
                        reason="Transição técnica de processamento, sem decisão humana.",
                        version=bula.shared_submission.version,
                        before_state=before_state,
                        after_state=after_state,
                    )
                )
        await self.db.commit()
        await self.db.refresh(bula)
        return bula

    async def update_alias(self, *, bula: Bula, alias: str | None) -> Bula:
        bula.alias = alias
        await self.db.commit()
        await self.db.refresh(bula)
        return bula

    async def update_extracted_metadata(
        self,
        *,
        bula: Bula,
        drug_name: str,
        manufacturer: str | None,
    ) -> Bula:
        bula.drug_name = drug_name
        bula.manufacturer = manufacturer

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
