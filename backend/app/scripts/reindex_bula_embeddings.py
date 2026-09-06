from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.core.config import settings
from app.modules.rag.dependencies import get_embeddings, get_qdrant_store
from app.modules.rag.qdrant_client import create_qdrant_client
from app.modules.rag.reindex_service import (
    DenseEmbeddingReindexError,
    DenseEmbeddingReindexResult,
    DenseEmbeddingReindexService,
)


@dataclass(frozen=True)
class ReindexArguments:
    bula_id: UUID
    is_dry_run: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Re-embed existing Qdrant chunks using the configured embedding input contract."
        ),
    )
    parser.add_argument("--bula-id", required=True, type=UUID)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate existing chunks without embedding or writing to Qdrant.",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> ReindexArguments:
    parsed_arguments = build_parser().parse_args(argv)
    return ReindexArguments(
        bula_id=parsed_arguments.bula_id,
        is_dry_run=parsed_arguments.dry_run,
    )


async def reindex_bula_embeddings(
    arguments: ReindexArguments,
) -> DenseEmbeddingReindexResult:
    qdrant_client = create_qdrant_client(settings=settings)
    try:
        service = DenseEmbeddingReindexService(
            embeddings=get_embeddings(settings=settings),
            qdrant_store=get_qdrant_store(
                qdrant_client=qdrant_client,
                settings=settings,
            ),
        )
        return await service.reindex_bula(
            bula_id=str(arguments.bula_id),
            is_dry_run=arguments.is_dry_run,
        )
    finally:
        await qdrant_client.close()


def print_result(result: DenseEmbeddingReindexResult) -> None:
    mode = "dry-run" if result.is_dry_run else "write"
    print(f"Dense embedding reindex ({mode})")
    print(f"  bula_id:           {result.bula_id}")
    print(f"  points:            {result.point_count}")
    print(f"  embedding_profile: {result.embedding_profile}")


async def async_main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        result = await reindex_bula_embeddings(arguments)
        print_result(result)
        return 0
    except DenseEmbeddingReindexError as exc:
        print(f"Reindex failed: {exc}")
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
