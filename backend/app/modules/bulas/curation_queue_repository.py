"""Enqueue using PGQueuer's public driver on the ORM's existing transaction."""

from typing import Protocol
from uuid import UUID

import asyncpg
from pgqueuer.db import AsyncpgDriver
from pgqueuer.queries import Queries
from sqlalchemy import LargeBinary, String, column, exists, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bulas.queue import INGEST_BULA_ENTRYPOINT


class IngestionQueueUnavailableError(Exception):
    """No review decision may commit when its ingestion job cannot be persisted."""


class CurationIngestionQueue(Protocol):
    async def enqueue(self, *, bula_id: UUID, operation_id: UUID) -> int: ...
    async def has_active_job(self, *, bula_id: UUID) -> bool: ...


class CurationQueueRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def has_active_job(self, *, bula_id: UUID) -> bool:
        # Read-only compatibility check for interrupted approvals from the older
        # implementation. Runtime uses PGQueuer's default table/entrypoint names.
        queue = table(
            "pgqueuer", column("entrypoint", String), column("payload", LargeBinary)
        )
        return bool(
            await self.db.scalar(
                select(
                    exists().where(
                        queue.c.entrypoint == INGEST_BULA_ENTRYPOINT,
                        queue.c.payload == str(bula_id).encode(),
                    )
                )
            )
        )

    async def enqueue(self, *, bula_id: UUID, operation_id: UUID) -> int:
        connection = await self.db.connection()
        raw_connection = await connection.get_raw_connection()
        driver_connection = raw_connection.driver_connection
        if (
            not isinstance(driver_connection, asyncpg.Connection)
            or not driver_connection.is_in_transaction()
        ):
            raise IngestionQueueUnavailableError(
                "Curation requires the active PostgreSQL transaction."
            )
        # No second connection, no independently committed job and no hand-written
        # INSERT into PGQueuer's internal schema. SQLAlchemy owns this connection.
        queries = Queries(AsyncpgDriver(driver_connection))
        try:
            jobs = await queries.enqueue(
                INGEST_BULA_ENTRYPOINT,
                str(bula_id).encode(),
                priority=0,
                dedupe_key=f"shared-ingestion:{bula_id}:{operation_id}",
                headers={"curation_operation_id": str(operation_id)},
            )
        except Exception as error:
            raise IngestionQueueUnavailableError(
                "Could not persist the ingestion job."
            ) from error
        if len(jobs) != 1:
            raise IngestionQueueUnavailableError(
                "Ingestion did not return exactly one job."
            )
        return int(jobs[0])
