import os
from uuid import UUID

os.environ.setdefault(
    "SECRET_KEY", "long_and_secure_secret_key_for_testing_purposes_only_1234567890"
)

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.base import Base

# Import from database module which also imports all models.
# This ensures SQLAlchemy mapper configuration works with forward references.
from app.core.database import get_db
from app.modules.bulas.dependencies import get_bula_ingestion_queue

app.state.limiter.enabled = False

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    _ = connection_record
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = async_sessionmaker(
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
)


class FakeBulaIngestionQueue:
    def __init__(self) -> None:
        self.enqueued_bula_ids: list[UUID] = []

    async def enqueue_bula_ingestion(self, *, bula_id: UUID) -> None:
        self.enqueued_bula_ids.append(bula_id)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_db) -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def fake_bula_ingestion_queue() -> FakeBulaIngestionQueue:
    return FakeBulaIngestionQueue()


@pytest.fixture
async def client(
    db_session: AsyncSession,
    fake_bula_ingestion_queue: FakeBulaIngestionQueue,
) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_bula_ingestion_queue] = lambda: (
        fake_bula_ingestion_queue
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
