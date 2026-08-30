from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import UUID

import asyncpg
from pgqueuer import PgQueuer, errors
from pgqueuer.db import AsyncpgDriver
from pgqueuer.executors import RetryWithBackoffEntrypointExecutor
from pgqueuer.models import Context, Job

from app.core.config import get_settings, settings
from app.core.database import async_session_factory, close_engine
from app.core.logging_config import configure_logging
from app.core.pgqueuer import build_asyncpg_dsn
from app.modules.bulas.models import BulaStatus
from app.modules.bulas.queue import INGEST_BULA_ENTRYPOINT
from app.modules.bulas.repository import BulaRepository
from app.modules.rag.dependencies import (
    get_chunker,
    get_embeddings,
    get_ingestion_debug_artifacts,
    get_llm_client,
    get_parser,
    get_qdrant_store,
)
from app.modules.rag.qdrant_client import create_qdrant_client
from app.modules.rag.service import RAGIngestionService
from app.modules.storage.client import PgObjectStoreClient
from app.modules.storage.repository import StoredObjectRepository


configure_logging(
    log_level=settings.log_level,
    json_logs=settings.json_logs,
    app_version="0.1.0",
    environment=settings.environment,
)


class BulaIngestionRetryExecutor(RetryWithBackoffEntrypointExecutor):
    async def execute(self, job: Job, context: Context) -> None:
        try:
            await super().execute(job, context)
        except (errors.MaxRetriesExceeded, errors.MaxTimeExceeded) as exc:
            await mark_bula_ingestion_failed_after_retries(job=job, exc=exc)
            raise


def build_stale_job_retry_timer(*, retry_after_seconds: int) -> timedelta:
    return timedelta(seconds=retry_after_seconds)


@asynccontextmanager
async def create_worker() -> AsyncIterator[PgQueuer]:
    worker_settings = get_settings()
    connection = await asyncpg.connect(
        dsn=build_asyncpg_dsn(worker_settings.database_url),
    )
    pgq = PgQueuer(AsyncpgDriver(connection))

    parser = get_parser()
    llm_client = get_llm_client(settings=worker_settings)
    chunker = get_chunker(llm=llm_client, settings=worker_settings)
    embeddings = get_embeddings(settings=worker_settings)
    debug_artifacts = get_ingestion_debug_artifacts(settings=worker_settings)
    qdrant_client = create_qdrant_client(settings=worker_settings)
    qdrant_store = get_qdrant_store(
        qdrant_client=qdrant_client,
        settings=worker_settings,
    )

    @pgq.entrypoint(
        INGEST_BULA_ENTRYPOINT,
        concurrency_limit=2,
        retry_timer=build_stale_job_retry_timer(
            retry_after_seconds=(
                worker_settings.rag_ingestion.stale_job_retry_after_seconds
            ),
        ),
        executor_factory=lambda parameters: BulaIngestionRetryExecutor(
            parameters=parameters,
            max_attempts=3,
            initial_delay=30.0,
            max_delay=timedelta(minutes=5),
            max_time=None,
            backoff_multiplier=2.0,
        ),
    )
    async def ingest_bula(job: Job) -> None:
        bula_id = extract_bula_id_from_job(job)

        async with async_session_factory() as db:
            service = RAGIngestionService(
                parser=parser,
                chunker=chunker,
                embeddings=embeddings,
                qdrant_store=qdrant_store,
                object_store=PgObjectStoreClient(
                    repository=StoredObjectRepository(db=db),
                ),
                bula_repo=BulaRepository(db=db),
                debug_artifacts=debug_artifacts,
            )
            await service.ingest_bula(bula_id=bula_id)

    try:
        yield pgq
    finally:
        # The worker context owns this process-local Qdrant client.
        await qdrant_client.close()
        await llm_client.close()
        await connection.close()
        await close_engine()


def extract_bula_id_from_job(job: Job) -> UUID:
    if job.payload is None:
        raise ValueError("Ingestion job payload is empty.")

    return UUID(job.payload.decode())


async def mark_bula_ingestion_failed_after_retries(
    *,
    job: Job,
    exc: BaseException,
) -> None:
    try:
        bula_id = extract_bula_id_from_job(job)
    except UnicodeDecodeError, ValueError:
        return

    error_message = build_error_message(exc)
    async with async_session_factory() as db:
        bula_repo = BulaRepository(db=db)
        bula = await bula_repo.get_by_id(bula_id=bula_id)
        if bula is None:
            return

        await bula_repo.update_ingestion_status(
            bula=bula,
            status=BulaStatus.ERROR,
            error_message=error_message,
        )


def build_error_message(exc: BaseException) -> str:
    original_error = exc.__cause__ or exc
    error_message = str(original_error).strip()
    if error_message:
        return error_message

    return original_error.__class__.__name__
