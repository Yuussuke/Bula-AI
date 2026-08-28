from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory, close_engine
from app.core.pgqueuer import create_pgq_queries
from app.modules.auth.repository import UserRepository
from app.modules.bulas.queue import BulaIngestionQueue
from app.modules.bulas.repository import BulaRepository
from app.modules.bulas.schemas import (
    SystemBulaManifest,
    SystemBulaSeedCandidate,
    SystemBulaSeedSummary,
)
from app.modules.bulas.service import (
    SystemBulaSeedConfigurationError,
    SystemBulaSeedService,
)
from app.modules.storage.client import PgObjectStoreClient
from app.modules.storage.repository import StoredObjectRepository


DEFAULT_INPUT_DIRECTORY = Path("tmp/anvisa-bulas-v2")
DEFAULT_MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class SeedArguments:
    input_directory: Path
    manifest_path: Path
    admin_email: str
    is_dry_run: bool
    limit: int | None


def positive_integer(value: str) -> int:
    parsed_value = int(value)
    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")
    return parsed_value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed ANVISA leaflets into the shared system corpus.",
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_DIRECTORY),
        help="Directory containing downloaded PDF files.",
    )
    parser.add_argument(
        "--manifest",
        help="Manifest path. Defaults to <input>/manifest.json.",
    )
    parser.add_argument(
        "--admin-email",
        required=True,
        help="Existing active administrator that will own the system bulas.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report changes without writing or enqueueing.",
    )
    parser.add_argument(
        "--limit",
        type=positive_integer,
        help="Process only the first N manifest entries.",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> SeedArguments:
    parsed_arguments = build_parser().parse_args(argv)
    input_directory = Path(parsed_arguments.input)
    manifest_path = (
        Path(parsed_arguments.manifest)
        if parsed_arguments.manifest
        else input_directory / DEFAULT_MANIFEST_FILENAME
    )
    return SeedArguments(
        input_directory=input_directory,
        manifest_path=manifest_path,
        admin_email=parsed_arguments.admin_email,
        is_dry_run=parsed_arguments.dry_run,
        limit=parsed_arguments.limit,
    )


def load_seed_candidates(arguments: SeedArguments) -> list[SystemBulaSeedCandidate]:
    manifest_content = arguments.manifest_path.read_text(encoding="utf-8")
    manifest = SystemBulaManifest.model_validate_json(manifest_content)
    manifest_entries = manifest.documents
    if arguments.limit is not None:
        manifest_entries = manifest_entries[: arguments.limit]

    resolved_input_directory = arguments.input_directory.resolve()
    candidates: list[SystemBulaSeedCandidate] = []
    for manifest_entry in manifest_entries:
        pdf_path = (resolved_input_directory / manifest_entry.filename).resolve()
        if not pdf_path.is_relative_to(resolved_input_directory):
            raise ValueError(
                f"Manifest file escapes the input directory: {manifest_entry.filename}"
            )

        candidates.append(
            SystemBulaSeedCandidate(
                manifest_entry=manifest_entry,
                content=pdf_path.read_bytes(),
            )
        )

    return candidates


def build_seed_service(
    *,
    session: AsyncSession,
    ingestion_queue: BulaIngestionQueue,
) -> SystemBulaSeedService:
    stored_object_repository = StoredObjectRepository(db=session)
    return SystemBulaSeedService(
        user_repository=UserRepository(db=session),
        bula_repository=BulaRepository(db=session),
        object_store=PgObjectStoreClient(repository=stored_object_repository),
        ingestion_queue=ingestion_queue,
        max_upload_size_bytes=settings.max_bula_upload_size_bytes,
    )


async def seed_system_bulas(arguments: SeedArguments) -> SystemBulaSeedSummary:
    candidates = load_seed_candidates(arguments)
    pgq_pool, pgq_queries = await create_pgq_queries(settings.database_url)

    try:
        async with async_session_factory() as session:
            service = build_seed_service(
                session=session,
                ingestion_queue=BulaIngestionQueue(queries=pgq_queries),
            )
            return await service.seed_documents(
                admin_email=arguments.admin_email,
                candidates=candidates,
                is_dry_run=arguments.is_dry_run,
            )
    finally:
        await pgq_pool.close()


def print_summary(summary: SystemBulaSeedSummary, *, is_dry_run: bool) -> None:
    mode = "dry-run" if is_dry_run else "write"
    print(f"System corpus seed summary ({mode})")
    print(f"  planned:  {summary.planned}")
    print(f"  inserted: {summary.inserted}")
    print(f"  skipped:  {summary.skipped}")
    print(f"  queued:   {summary.queued}")
    print(f"  failed:   {summary.failed}")

    for failure in summary.failures:
        print(f"  [failed] {failure.filename}: {failure.reason}")


async def async_main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)

    try:
        summary = await seed_system_bulas(arguments)
        print_summary(summary, is_dry_run=arguments.is_dry_run)
        return 1 if summary.failed > 0 else 0
    except (OSError, ValidationError, ValueError) as exc:
        print(f"Invalid seed input: {exc}")
        return 1
    except SystemBulaSeedConfigurationError as exc:
        print(str(exc))
        return 1
    finally:
        await close_engine()


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
