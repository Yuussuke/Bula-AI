"""Copy existing Qdrant text into PostgreSQL BM25 without model/API inference."""

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import structlog
import httpx
from sqlalchemy.exc import SQLAlchemyError
from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException

from app.core.config import settings
from app.core.database import async_session_factory, close_engine
from app.modules.bulas.repository import BulaRepository
from app.modules.rag.backfill_service import (
    ChunkBackfillResult,
    ChunkMetadataBackfillService,
)
from app.modules.rag.dependencies import get_bm25_index, get_qdrant_store
from app.modules.rag.qdrant_client import create_qdrant_client
from app.modules.rag.repository import ChunkIndexPersistenceError


@dataclass(frozen=True)
class BackfillArguments:
    bula_id: UUID | None
    batch_size: int
    is_dry_run: bool


def parse_arguments(argv: Sequence[str] | None = None) -> BackfillArguments:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bula-id", type=UUID, help="Omit to copy all ready bulas.")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate without writing."
    )
    parsed = parser.parse_args(argv)
    if not 1 <= parsed.batch_size <= 1000:
        parser.error("--batch-size must be between 1 and 1000")
    return BackfillArguments(parsed.bula_id, parsed.batch_size, parsed.dry_run)


async def run_backfill(arguments: BackfillArguments) -> ChunkBackfillResult:
    qdrant_client = create_qdrant_client(settings=settings)
    try:
        async with async_session_factory() as db:
            service = ChunkMetadataBackfillService(
                bula_repository=BulaRepository(db=db),
                qdrant_store=get_qdrant_store(
                    qdrant_client=qdrant_client, settings=settings
                ),
                bm25_index=get_bm25_index(db=db),
            )
            return await service.backfill(
                bula_id=arguments.bula_id,
                batch_size=arguments.batch_size,
                is_dry_run=arguments.is_dry_run,
            )
    finally:
        await qdrant_client.close()
        await close_engine()


async def async_main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        result = await run_backfill(arguments)
    except (
        ValueError,
        ChunkIndexPersistenceError,
        SQLAlchemyError,
        UnexpectedResponse,
        ResponseHandlingException,
        httpx.HTTPError,
    ) as exc:
        # SQLAlchemy exception strings may contain SQL parameters/source text.
        structlog.get_logger(__name__).error(
            "chunk_metadata_backfill_failed", error_type=type(exc).__name__
        )
        print(
            "Backfill failed. Check database migrations and source identities; retry is safe."
        )
        return 1
    mode = "dry-run" if result.is_dry_run else "write"
    print(f"Chunk metadata backfill ({mode})")
    print(f"  bulas:  {result.bula_count}")
    print(f"  chunks: {result.chunk_count}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
