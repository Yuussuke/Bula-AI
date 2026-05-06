from app.core.pgqueuer import build_asyncpg_dsn


def test_build_asyncpg_dsn_removes_sqlalchemy_asyncpg_driver() -> None:
    dsn = build_asyncpg_dsn("postgresql+asyncpg://bulaai:secret@postgres:5432/bulaai")

    assert dsn == "postgresql://bulaai:secret@postgres:5432/bulaai"


def test_build_asyncpg_dsn_keeps_plain_postgresql_driver() -> None:
    dsn = build_asyncpg_dsn("postgresql://bulaai:secret@postgres:5432/bulaai")

    assert dsn == "postgresql://bulaai:secret@postgres:5432/bulaai"
