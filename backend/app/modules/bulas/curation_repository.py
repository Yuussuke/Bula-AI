from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, exists, func, select
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
import structlog

from app.modules.auth.models import User
from app.core.idempotency import IdempotencyConflictError
from app.modules.bulas.curation_audit import shared_bula_snapshot
from app.modules.bulas.curation_queue_repository import (
    CurationIngestionQueue,
    CurationQueueRepository,
)
from app.modules.bulas.curation_schemas import CurationListQuery
from app.modules.bulas.models import (
    Bula,
    BulaCorpus,
    BulaStatus,
    BulaCurationEvent,
    SharedBulaSubmission,
)
from app.modules.storage.models import StoredObject

logger = structlog.get_logger(__name__)


def approved_shared_conditions() -> tuple[ColumnElement[bool], ...]:
    # Used in both public browsing and chat eligibility, before pagination/ranking.
    return (
        Bula.corpus == BulaCorpus.SHARED,
        Bula.status == BulaStatus.READY,
        SharedBulaSubmission.review_status == "approved",
        SharedBulaSubmission.sha256_checksum == StoredObject.sha256_checksum,
        SharedBulaSubmission.content_size_bytes == StoredObject.content_size_bytes,
        exists(
            select(BulaCurationEvent.id).where(
                BulaCurationEvent.bula_id == Bula.id,
                BulaCurationEvent.action == "approved",
            )
        ),
    )


class CurationConflictError(Exception):
    """The submitted revision is stale or its transition is no longer allowed."""


class DuplicateSharedPdfError(Exception):
    """The same bytes already have a pending or approved shared submission."""


@dataclass(frozen=True)
class CurationMutationResult:
    bula: Bula
    replayed: bool


class CurationRepository:
    def __init__(
        self, db: AsyncSession, queue: CurationIngestionQueue | None = None
    ) -> None:
        self.db = db
        self.queue = queue if queue is not None else CurationQueueRepository(db)

    def public_statement(self) -> Select[tuple[Bula]]:
        return (
            select(Bula)
            .join(SharedBulaSubmission, SharedBulaSubmission.bula_id == Bula.id)
            .join(StoredObject, StoredObject.object_address == Bula.file_address)
            .options(joinedload(Bula.shared_submission))
            .where(and_(*approved_shared_conditions()))
        )

    async def list_public(
        self, *, bula_ids: Sequence[UUID] | None = None
    ) -> list[Bula]:
        statement = self.public_statement()
        if bula_ids is not None:
            statement = statement.where(Bula.id.in_(bula_ids))
        result = await self.db.execute(
            statement.execution_options(populate_existing=True)
        )
        return list(result.unique().scalars().all())

    async def list_page(
        self, *, filters: CurationListQuery, owner_id: int | None
    ) -> tuple[list[Bula], int]:
        statement = (
            self.public_statement()
            if filters.view == "public"
            else (
                select(Bula)
                .join(SharedBulaSubmission, SharedBulaSubmission.bula_id == Bula.id)
                .options(joinedload(Bula.shared_submission))
                .where(Bula.corpus == BulaCorpus.SHARED)
            )
        )
        if owner_id is not None:
            statement = statement.where(Bula.user_id == owner_id)
        if filters.status is not None:
            statement = statement.where(
                SharedBulaSubmission.review_status == filters.status.value
            )
        for term in filters.query.split():
            statement = statement.where(
                func.lower(Bula.drug_name).contains(term.lower(), autoescape=True)
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
            statement.order_by(Bula.created_at.desc(), Bula.id)
            .limit(filters.limit)
            .offset(filters.offset)
        )
        return list(result.unique().scalars().all()), total

    async def get(self, bula_id: UUID, *, lock: bool = False) -> Bula | None:
        if lock:
            # Read child review state only AFTER acquiring the parent lock.
            # A joined SELECT can retain an older child-row snapshot while it waits.
            await self.db.execute(
                select(Bula.id).where(Bula.id == bula_id).with_for_update()
            )
        statement = (
            select(Bula)
            .join(SharedBulaSubmission, SharedBulaSubmission.bula_id == Bula.id)
            .options(joinedload(Bula.shared_submission))
            .where(Bula.id == bula_id, Bula.corpus == BulaCorpus.SHARED)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def replay(
        self, *, actor_id: int, operation_id: UUID, request_fingerprint: str
    ) -> CurationMutationResult | None:
        event = await self.db.scalar(
            select(BulaCurationEvent).where(
                BulaCurationEvent.actor_id == actor_id,
                BulaCurationEvent.operation_id == operation_id,
            )
        )
        if event is None:
            return None
        if event.request_fingerprint != request_fingerprint:
            logger.warning(
                "curation_operation_key_conflict",
                actor_id=actor_id,
                operation_id=str(operation_id),
                requested_fingerprint=request_fingerprint,
                recorded_fingerprint=event.request_fingerprint,
            )
            raise IdempotencyConflictError()
        bula = await self.get(event.bula_id)
        if bula is None:
            raise CurationConflictError("Recorded operation lost its document.")
        await self.db.commit()
        return CurationMutationResult(bula=bula, replayed=True)

    async def has_active_pdf(self, checksum: str) -> bool:
        return bool(
            await self.db.scalar(
                select(
                    exists().where(
                        SharedBulaSubmission.sha256_checksum == checksum,
                        SharedBulaSubmission.review_status.in_(["pending", "approved"]),
                    )
                )
            )
        )

    async def is_object_referenced(self, address: str) -> bool:
        return bool(
            await self.db.scalar(select(exists().where(Bula.file_address == address)))
        )

    async def create(
        self,
        *,
        actor: User,
        object_address: str,
        source_url: str,
        source_description: str,
        checksum: str,
        size: int,
        product_name: str,
        manufacturer: str | None,
        operation_id: UUID,
        request_fingerprint: str,
    ) -> CurationMutationResult:
        actor_id = int(actor.id)
        replay = await self.replay(
            actor_id=actor_id,
            operation_id=operation_id,
            request_fingerprint=request_fingerprint,
        )
        if replay is not None:
            return replay
        if await self.has_active_pdf(checksum):
            raise DuplicateSharedPdfError()
        previous = await self.db.scalar(
            select(SharedBulaSubmission.bula_id)
            .where(
                SharedBulaSubmission.sha256_checksum == checksum,
                SharedBulaSubmission.review_status.in_(["rejected", "withdrawn"]),
            )
            .order_by(
                SharedBulaSubmission.created_at.desc(), SharedBulaSubmission.bula_id
            )
            .limit(1)
        )
        bula = Bula(
            user_id=actor_id,
            drug_name=product_name,
            manufacturer=manufacturer,
            file_address=object_address,
            corpus=BulaCorpus.SHARED,
            status=BulaStatus.PENDING,
        )
        submission = SharedBulaSubmission(
            bula=bula,
            source_url=source_url,
            source_description=source_description,
            sha256_checksum=checksum,
            content_size_bytes=size,
            supersedes_bula_id=previous,
        )
        self.db.add_all([bula, submission])
        try:
            await self.db.flush()
            self._add_event(
                bula_id=bula.id,
                actor=actor,
                action="submitted",
                reason=source_description,
                version=1,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
                before_state=None,
                after_state=shared_bula_snapshot(bula),
            )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            replay = await self.replay(
                actor_id=actor_id,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                return replay
            if await self.has_active_pdf(checksum):
                raise DuplicateSharedPdfError() from None
            raise
        except BaseException:
            await self.db.rollback()
            raise
        result = await self.get(bula.id)
        assert result is not None
        return CurationMutationResult(bula=result, replayed=False)

    async def transition(
        self,
        *,
        bula: Bula,
        actor: User,
        expected_version: int,
        expected_status: str,
        target_status: str,
        action: str,
        reason: str,
        operation_id: UUID,
        request_fingerprint: str,
        product_name: str | None = None,
        manufacturer: str | None = None,
        presentation: str | None = None,
        strength: str | None = None,
        retry_ingestion: bool = False,
    ) -> CurationMutationResult:
        actor_id = int(actor.id)
        bula_id = bula.id
        try:
            replay = await self.replay(
                actor_id=actor_id,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                return replay
            current = await self.get(bula_id, lock=True)
            # A concurrent identical request may have committed while we waited.
            replay = await self.replay(
                actor_id=actor_id,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                return replay
            if current is None or current.shared_submission is None:
                raise CurationConflictError()
            submission = current.shared_submission
            if (
                submission.version != expected_version
                or submission.review_status != expected_status
            ):
                raise CurationConflictError()
            if retry_ingestion:
                is_failed = current.status in {BulaStatus.FAILED, BulaStatus.ERROR}
                is_legacy_pending = (
                    current.status == BulaStatus.PENDING
                    and submission.ingestion_job_id is None
                )
                if not (
                    is_failed or is_legacy_pending
                ) or await self.queue.has_active_job(bula_id=bula_id):
                    raise CurationConflictError()
            before_state = shared_bula_snapshot(current)
            if action == "approved":
                if product_name is None:
                    raise CurationConflictError(
                        "Approval requires reviewed identification."
                    )
                current.drug_name = product_name
                current.manufacturer = manufacturer
                submission.presentation = presentation
                submission.strength = strength
            submission.review_status = target_status
            submission.version = expected_version + 1
            submission.updated_at = datetime.now(UTC)
            if action == "approved" or retry_ingestion:
                current.status = BulaStatus.PENDING
                current.error_message = None
                submission.ingestion_operation_id = operation_id
                await self.db.flush()
                submission.ingestion_job_id = await self.queue.enqueue(
                    bula_id=bula_id, operation_id=operation_id
                )
            self._add_event(
                bula_id=bula_id,
                actor=actor,
                action=action,
                reason=reason,
                version=expected_version + 1,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
                before_state=before_state,
                after_state=shared_bula_snapshot(current),
            )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            replay = await self.replay(
                actor_id=actor_id,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                return replay
            raise
        except BaseException:
            await self.db.rollback()
            raise
        refreshed = await self.get(bula_id)
        assert refreshed is not None
        return CurationMutationResult(bula=refreshed, replayed=False)

    async def events(self, bula_id: UUID) -> list[BulaCurationEvent]:
        result = await self.db.execute(
            select(BulaCurationEvent)
            .where(BulaCurationEvent.bula_id == bula_id)
            .order_by(BulaCurationEvent.created_at, BulaCurationEvent.id)
        )
        return list(result.scalars().all())

    def _add_event(
        self,
        *,
        bula_id: UUID,
        actor: User,
        action: str,
        reason: str,
        version: int,
        operation_id: UUID,
        request_fingerprint: str,
        before_state: dict[str, object] | None,
        after_state: dict[str, object],
    ) -> None:
        self.db.add(
            BulaCurationEvent(
                bula_id=bula_id,
                actor_id=actor.id,
                actor_name=actor.full_name,
                actor_role=actor.role.value,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
                before_state=before_state,
                after_state=after_state,
                action=action,
                reason=reason,
                version=version,
            )
        )
