from __future__ import annotations

from typing import cast

import asyncpg
from fastapi import Request
from pgqueuer.db import AsyncpgPoolDriver
from pgqueuer.queries import Queries
from sqlalchemy.engine import make_url


PGQ_QUERIES_STATE_KEY = "pgq_queries"


def build_asyncpg_dsn(database_url: str) -> str:
    parsed_url = make_url(database_url)

    if parsed_url.drivername == "postgresql+asyncpg":
        parsed_url = parsed_url.set(drivername="postgresql")

    if parsed_url.drivername not in {"postgresql", "postgres"}:
        raise ValueError("PGQueuer requires a PostgreSQL database URL.")

    return parsed_url.render_as_string(hide_password=False)


async def create_pgq_queries(database_url: str) -> tuple[asyncpg.Pool, Queries]:
    pool = await asyncpg.create_pool(dsn=build_asyncpg_dsn(database_url))
    queries = Queries(AsyncpgPoolDriver(pool))
    return pool, queries


def get_pgq_queries(request: Request) -> Queries:
    queries = getattr(request.app.state, PGQ_QUERIES_STATE_KEY, None)
    if queries is None:
        raise RuntimeError("PGQueuer queries were not initialized.")

    return cast(Queries, queries)
