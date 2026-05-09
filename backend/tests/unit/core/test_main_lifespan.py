from fastapi import FastAPI
import pytest

from app import main as app_main
from app.core.pgqueuer import PGQ_QUERIES_STATE_KEY
from app.modules.rag.qdrant_client import QDRANT_CLIENT_STATE_KEY


class FakePool:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class FakeQdrantClient:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


@pytest.mark.anyio
async def test_lifespan_owns_shared_qdrant_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    fake_pool = FakePool()
    fake_queries = object()
    fake_qdrant_client = FakeQdrantClient()
    is_engine_closed = False

    async def fake_create_pgq_queries(database_url: str) -> tuple[FakePool, object]:
        _ = database_url
        return fake_pool, fake_queries

    def fake_create_qdrant_client(*, settings: object) -> FakeQdrantClient:
        _ = settings
        return fake_qdrant_client

    async def fake_close_engine() -> None:
        nonlocal is_engine_closed
        is_engine_closed = True

    monkeypatch.setattr(app_main, "create_pgq_queries", fake_create_pgq_queries)
    monkeypatch.setattr(app_main, "create_qdrant_client", fake_create_qdrant_client)
    monkeypatch.setattr(app_main, "close_engine", fake_close_engine)

    async with app_main.lifespan(app):
        assert getattr(app.state, PGQ_QUERIES_STATE_KEY) is fake_queries
        assert getattr(app.state, QDRANT_CLIENT_STATE_KEY) is fake_qdrant_client
        assert fake_qdrant_client.closed is False

    assert fake_qdrant_client.closed is True
    assert fake_pool.closed is True
    assert is_engine_closed is True
