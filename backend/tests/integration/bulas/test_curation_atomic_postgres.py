"""Real PostgreSQL/PGQueuer rollback and visibility contracts; no worker runs here."""

import asyncio
import hashlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from sqlalchemy import LargeBinary, column, delete, func, select, table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.auth.models import User, UserRole, UserRoleAssignment
from app.modules.auth.repository import UserRepository, RoleMutationResult
from app.core.idempotency import IdempotencyConflictError
from app.modules.bulas.curation_queue_repository import CurationQueueRepository
from app.modules.bulas.curation_repository import CurationRepository
from app.modules.bulas.models import (
    Bula,
    BulaCurationEvent,
    BulaStatus,
    SharedBulaSubmission,
)
from app.modules.storage.models import StoredObject
from tests.integration.bulas.test_curation_postgres import (
    disposable_database_url,
    prepare_queue,
)

QUEUE = table("pgqueuer", column("payload", LargeBinary))


@dataclass(frozen=True)
class PgCurationCase:
    sessions: async_sessionmaker[AsyncSession]
    bula_id: UUID
    reviewer_id: int
    admin_id: int
    owner_id: int


@pytest.fixture
async def pg_case() -> AsyncIterator[PgCurationCase]:
    database_url = disposable_database_url()
    await prepare_queue(database_url)
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    suffix = uuid4().hex
    address = f"curation-atomic-test/{suffix}"
    identifier = None
    try:
        async with sessions() as database:
            sender = User(
                full_name="Synthetic sender",
                email=f"sender-{suffix}@example.com",
                hashed_password="unused-test-hash",
                role=UserRole.CONTRIBUTOR,
            )
            reviewer = User(
                full_name="Synthetic reviewer",
                email=f"reviewer-{suffix}@example.com",
                hashed_password="unused-test-hash",
                role=UserRole.REVIEWER,
            )
            administrator = User(
                full_name="Synthetic administrator",
                email=f"admin-{suffix}@example.com",
                hashed_password="unused-test-hash",
                role=UserRole.ADMIN,
            )
            content = suffix.encode()
            database.add_all(
                [
                    sender,
                    reviewer,
                    administrator,
                    StoredObject(
                        object_address=address,
                        data=content,
                        sha256_checksum=hashlib.sha256(content).hexdigest(),
                        content_size_bytes=len(content),
                    ),
                ]
            )
            await database.commit()
            result = await CurationRepository(database).create(
                actor=sender,
                object_address=address,
                source_url="https://example.com/leaflet.pdf",
                source_description="Synthetic source",
                checksum=hashlib.sha256(content).hexdigest(),
                size=len(content),
                product_name="Synthetic product",
                manufacturer=None,
                operation_id=uuid4(),
                request_fingerprint="a" * 64,
            )
            identifier = result.bula.id
            reviewer_id = int(reviewer.id)
            admin_id = int(administrator.id)
            owner_id = int(sender.id)
        yield PgCurationCase(
            sessions=sessions,
            bula_id=identifier,
            reviewer_id=reviewer_id,
            admin_id=admin_id,
            owner_id=owner_id,
        )
    finally:
        async with sessions() as database:
            if identifier is not None:
                await database.execute(
                    delete(QUEUE).where(QUEUE.c.payload == str(identifier).encode())
                )
                await database.execute(delete(Bula).where(Bula.id == identifier))
            await database.execute(
                delete(StoredObject).where(StoredObject.object_address == address)
            )
            await database.execute(
                delete(User).where(
                    User.email.in_(
                        [
                            f"sender-{suffix}@example.com",
                            f"reviewer-{suffix}@example.com",
                            f"admin-{suffix}@example.com",
                        ]
                    )
                )
            )
            await database.commit()
        await engine.dispose()


@pytest.mark.anyio
async def test_interruption_after_real_enqueue_rolls_back_decision_audit_and_job(
    pg_case: PgCurationCase,
) -> None:
    class InterruptedQueue(CurationQueueRepository):
        async def enqueue(self, *, bula_id: UUID, operation_id: UUID) -> int:
            await super().enqueue(bula_id=bula_id, operation_id=operation_id)
            raise asyncio.CancelledError("Synthetic interruption before commit")

    async with pg_case.sessions() as database:
        reviewer = await database.get(User, pg_case.reviewer_id)
        repository = CurationRepository(database, queue=InterruptedQueue(database))
        document = await repository.get(pg_case.bula_id)
        assert reviewer is not None and document is not None
        with pytest.raises(asyncio.CancelledError):
            await repository.transition(
                bula=document,
                actor=reviewer,
                expected_version=1,
                expected_status="pending",
                target_status="approved",
                action="approved",
                reason="Synthetic review",
                product_name="Reviewed name",
                operation_id=uuid4(),
                request_fingerprint="b" * 64,
            )
    async with pg_case.sessions() as database:
        submission = await database.get(SharedBulaSubmission, pg_case.bula_id)
        document = await database.get(Bula, pg_case.bula_id)
        assert submission is not None and document is not None
        assert submission.review_status == "pending" and submission.version == 1
        assert (
            submission.ingestion_job_id is None
            and document.status == BulaStatus.PENDING
        )
        assert (
            await database.scalar(
                select(func.count())
                .select_from(BulaCurationEvent)
                .where(BulaCurationEvent.bula_id == pg_case.bula_id)
            )
            == 1
        )
        assert (
            await database.scalar(
                select(func.count())
                .select_from(QUEUE)
                .where(QUEUE.c.payload == str(pg_case.bula_id).encode())
            )
            == 0
        )


@pytest.mark.anyio
async def test_worker_cannot_observe_job_before_approval_and_audit_commit(
    pg_case: PgCurationCase,
) -> None:
    inserted = asyncio.Event()
    release_commit = asyncio.Event()

    class PausedQueue(CurationQueueRepository):
        async def enqueue(self, *, bula_id: UUID, operation_id: UUID) -> int:
            job_id = await super().enqueue(bula_id=bula_id, operation_id=operation_id)
            inserted.set()
            await release_commit.wait()
            return job_id

    async with pg_case.sessions() as database:
        reviewer = await database.get(User, pg_case.reviewer_id)
        repository = CurationRepository(database, queue=PausedQueue(database))
        document = await repository.get(pg_case.bula_id)
        assert reviewer is not None and document is not None
        operation_id = uuid4()
        task = asyncio.create_task(
            repository.transition(
                bula=document,
                actor=reviewer,
                expected_version=1,
                expected_status="pending",
                target_status="approved",
                action="approved",
                reason="Synthetic review",
                product_name="Reviewed name",
                operation_id=operation_id,
                request_fingerprint="c" * 64,
            )
        )
        try:
            await asyncio.wait_for(inserted.wait(), timeout=10)
            async with pg_case.sessions() as observer:
                submission = await observer.get(SharedBulaSubmission, pg_case.bula_id)
                assert submission is not None and submission.review_status == "pending"
                assert (
                    await observer.scalar(
                        select(func.count())
                        .select_from(QUEUE)
                        .where(QUEUE.c.payload == str(pg_case.bula_id).encode())
                    )
                    == 0
                )
                assert (
                    await observer.scalar(
                        select(func.count())
                        .select_from(BulaCurationEvent)
                        .where(BulaCurationEvent.bula_id == pg_case.bula_id)
                    )
                    == 1
                )
        finally:
            release_commit.set()
        result = await asyncio.wait_for(task, timeout=10)
        assert (
            not result.replayed
            and result.bula.shared_submission.ingestion_job_id is not None
        )
        async with pg_case.sessions() as observer:
            submission = await observer.get(SharedBulaSubmission, pg_case.bula_id)
            assert submission is not None and submission.review_status == "approved"
            assert (
                await observer.scalar(
                    select(func.count())
                    .select_from(QUEUE)
                    .where(QUEUE.c.payload == str(pg_case.bula_id).encode())
                )
                == 1
            )
            approval = await observer.scalar(
                select(BulaCurationEvent).where(
                    BulaCurationEvent.bula_id == pg_case.bula_id,
                    BulaCurationEvent.action == "approved",
                )
            )
            assert approval is not None and approval.operation_id == operation_id
            assert (
                approval.after_state
                and approval.after_state["ingestion_job_id"]
                == submission.ingestion_job_id
            )


@pytest.mark.anyio
async def test_concurrent_role_replay_preserves_original_document_author_profile(
    pg_case: PgCurationCase,
) -> None:
    operation_id = uuid4()
    async with pg_case.sessions() as first, pg_case.sessions() as second:
        first_admin = await first.get(User, pg_case.admin_id)
        second_admin = await second.get(User, pg_case.admin_id)
        assert first_admin is not None and second_admin is not None
        results = await asyncio.gather(
            UserRepository(first).assign_role(
                user_id=pg_case.owner_id,
                actor=first_admin,
                previous_role=UserRole.CONTRIBUTOR,
                assigned_role=UserRole.REVIEWER,
                reason="Synthetic administrative designation",
                operation_id=operation_id,
                request_fingerprint="e" * 64,
            ),
            UserRepository(second).assign_role(
                user_id=pg_case.owner_id,
                actor=second_admin,
                previous_role=UserRole.CONTRIBUTOR,
                assigned_role=UserRole.REVIEWER,
                reason="Synthetic administrative designation",
                operation_id=operation_id,
                request_fingerprint="e" * 64,
            ),
        )
        assert all(isinstance(result, RoleMutationResult) for result in results)
        assert sorted(result.replayed for result in results) == [False, True]
    async with pg_case.sessions() as database:
        assignment = await database.scalar(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == pg_case.owner_id
            )
        )
        assert assignment is not None and assignment.actor_role == "admin"
        assert (
            await database.scalar(
                select(func.count())
                .select_from(UserRoleAssignment)
                .where(UserRoleAssignment.user_id == pg_case.owner_id)
            )
            == 1
        )
        original = await database.scalar(
            select(BulaCurationEvent).where(
                BulaCurationEvent.bula_id == pg_case.bula_id,
                BulaCurationEvent.action == "submitted",
            )
        )
        assert original is not None and original.actor_role == "contributor"
        administrator = await database.get(User, pg_case.admin_id)
        assert administrator is not None
        with pytest.raises(IdempotencyConflictError):
            await UserRepository(database).assign_role(
                user_id=pg_case.owner_id,
                actor=administrator,
                previous_role=UserRole.REVIEWER,
                assigned_role=UserRole.USER,
                reason="Changed request using an old key",
                operation_id=operation_id,
                request_fingerprint="f" * 64,
            )
