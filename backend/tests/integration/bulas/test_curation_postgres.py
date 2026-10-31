"""Optional concurrency contract against an explicitly migrated disposable database."""

import asyncio
import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy import delete, func, select
from sqlalchemy import table, column, LargeBinary
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.auth.models import User, UserRole
from app.modules.bulas.curation_repository import (
    CurationConflictError,
    CurationRepository,
    CurationMutationResult,
)
from app.core.pgqueuer import create_pgq_queries
from app.modules.bulas.models import Bula, BulaCurationEvent, SharedBulaSubmission
from app.modules.storage.models import StoredObject


def disposable_database_url() -> str:
    database_url = os.getenv("CURATION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set CURATION_TEST_DATABASE_URL to a migrated disposable database.")
    if not database_url.endswith("/curation_test"):
        pytest.fail("This test only accepts the disposable curation_test database.")
    return database_url


async def prepare_queue(database_url: str) -> None:
    pool, queries = await create_pgq_queries(database_url)
    try:
        if not await queries.has_table("pgqueuer"):
            await queries.install()
    finally:
        await pool.close()


@pytest.mark.anyio
@pytest.mark.parametrize("same_operation", [False, True])
async def test_postgres_concurrent_review_commits_one_decision_and_event(
    same_operation: bool,
) -> None:
    database_url = disposable_database_url()
    await prepare_queue(database_url)
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    suffix = uuid4().hex
    object_address = f"curation-test/{suffix}"
    identifier = None
    try:
        async with sessions() as database:
            contributor = User(
                full_name="Contributor test",
                email=f"sender-{suffix}@example.com",
                hashed_password="unused-synthetic-hash",
                role=UserRole.CONTRIBUTOR,
            )
            reviewer = User(
                full_name="Reviewer test",
                email=f"reviewer-{suffix}@example.com",
                hashed_password="unused-synthetic-hash",
                role=UserRole.REVIEWER,
            )
            database.add_all(
                [
                    contributor,
                    reviewer,
                    StoredObject(
                        object_address=object_address,
                        sha256_checksum="a" * 64,
                        content_size_bytes=4,
                        data=b"test",
                    ),
                ]
            )
            await database.commit()
            # Persisting CONTRIBUTOR also checks the migrated native PostgreSQL enum.
            document = await CurationRepository(database).create(
                actor=contributor,
                object_address=object_address,
                source_url="https://example.com/bula.pdf",
                source_description="Synthetic source",
                checksum="a" * 64,
                size=4,
                product_name="Synthetic product",
                manufacturer=None,
                operation_id=uuid4(),
                request_fingerprint="a" * 64,
            )
            identifier = document.bula.id
            reviewer_id = int(reviewer.id)
        async with sessions() as first_database, sessions() as second_database:
            first_repository = CurationRepository(first_database)
            second_repository = CurationRepository(second_database)
            first_document = await first_repository.get(identifier)
            second_document = await second_repository.get(identifier)
            first_reviewer = await first_database.get(User, reviewer_id)
            second_reviewer = await second_database.get(User, reviewer_id)
            assert first_document is not None and second_document is not None
            assert first_reviewer is not None and second_reviewer is not None
            operation_id = uuid4()
            results = await asyncio.gather(
                first_repository.transition(
                    bula=first_document,
                    actor=first_reviewer,
                    expected_version=1,
                    expected_status="pending",
                    target_status="approved",
                    action="approved",
                    reason="First independent decision",
                    product_name="Reviewed product",
                    operation_id=operation_id,
                    request_fingerprint="b" * 64,
                ),
                second_repository.transition(
                    bula=second_document,
                    actor=second_reviewer,
                    expected_version=1,
                    expected_status="pending",
                    target_status="approved" if same_operation else "rejected",
                    action="approved" if same_operation else "rejected",
                    reason="Second independent decision",
                    product_name="Reviewed product",
                    operation_id=operation_id if same_operation else uuid4(),
                    request_fingerprint="b" * 64 if same_operation else "c" * 64,
                ),
                return_exceptions=True,
            )
            assert sum(
                isinstance(result, CurationMutationResult) for result in results
            ) == (2 if same_operation else 1)
            assert sum(
                isinstance(result, CurationConflictError) for result in results
            ) == (0 if same_operation else 1)
            if same_operation:
                assert sorted(
                    result.replayed
                    for result in results
                    if isinstance(result, CurationMutationResult)
                ) == [False, True]
        async with sessions() as database:
            submission = await database.get(SharedBulaSubmission, identifier)
            assert submission is not None and submission.version == 2
            queue_table = table("pgqueuer", column("payload", LargeBinary))
            queue_count = await database.scalar(
                select(func.count())
                .select_from(queue_table)
                .where(queue_table.c.payload == str(identifier).encode())
            )
            assert queue_count == (1 if submission.review_status == "approved" else 0)
            assert (
                await database.scalar(
                    select(func.count())
                    .select_from(BulaCurationEvent)
                    .where(BulaCurationEvent.bula_id == identifier)
                )
                == 2
            )
    finally:
        async with sessions() as database:
            if identifier is not None:
                queue_table = table("pgqueuer", column("payload", LargeBinary))
                await database.execute(
                    delete(queue_table).where(
                        queue_table.c.payload == str(identifier).encode()
                    )
                )
                await database.execute(delete(Bula).where(Bula.id == identifier))
            await database.execute(
                delete(StoredObject).where(
                    StoredObject.object_address == object_address
                )
            )
            await database.execute(
                delete(User).where(
                    User.email.in_(
                        [
                            f"sender-{suffix}@example.com",
                            f"reviewer-{suffix}@example.com",
                        ]
                    )
                )
            )
            await database.commit()
        await engine.dispose()


@pytest.mark.anyio
async def test_postgres_migration_preserves_accounts_and_guards_contributor_downgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = disposable_database_url()
    monkeypatch.setenv("DATABASE_URL", database_url)
    configuration = Config("alembic.ini")
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    email = f"migration-{uuid4().hex}@example.com"
    try:
        async with sessions() as database:
            database.add(
                User(
                    full_name="Migration sentinel",
                    email=email,
                    hashed_password="unused-synthetic-hash",
                    role=UserRole.CONTRIBUTOR,
                )
            )
            await database.commit()
        with pytest.raises(RuntimeError, match="Reassign contributor"):
            await asyncio.to_thread(command.downgrade, configuration, "d510a102b002")
        async with engine.connect() as connection:
            revision = await connection.run_sync(
                lambda sync: MigrationContext.configure(sync).get_current_revision()
            )
            assert revision == "e610a130b002"
        async with sessions() as database:
            user = await database.scalar(select(User).where(User.email == email))
            assert user is not None and user.role == UserRole.CONTRIBUTOR
            user.role = UserRole.USER
            await database.commit()
        # Dispose pooled connections before the enum type is rebuilt.
        await engine.dispose()
        await asyncio.to_thread(command.downgrade, configuration, "d510a102b002")
        async with engine.connect() as connection:
            assert not await connection.run_sync(
                lambda sync: inspect(sync).has_table("shared_bula_submissions")
            )
        await asyncio.to_thread(command.upgrade, configuration, "head")
        await engine.dispose()
        async with sessions() as database:
            user = await database.scalar(select(User).where(User.email == email))
            assert user is not None and user.role == UserRole.USER
            assert user.full_name == "Migration sentinel"
    finally:
        await asyncio.to_thread(command.upgrade, configuration, "head")
        await engine.dispose()
        async with sessions() as database:
            await database.execute(delete(User).where(User.email == email))
            await database.commit()
        await engine.dispose()
