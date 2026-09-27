"""Operator command for reprocessing one stored system leaflet."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory, close_engine
from app.modules.auth.models import UserRole
from app.modules.auth.repository import UserRepository
from app.modules.bulas.models import Bula, BulaCorpus, BulaStatus
from app.modules.bulas.repository import BulaRepository
from app.modules.rag.dependencies import (
    get_bm25_index,
    get_chunker,
    get_embeddings,
    get_ingestion_debug_artifacts,
    get_llm_client,
    get_parser,
    get_qdrant_store,
)
from app.modules.rag.qdrant_client import create_qdrant_client
from app.modules.rag.service import BulaIngestionError, RAGIngestionService
from app.modules.storage.client import PgObjectStoreClient
from app.modules.storage.repository import StoredObjectRepository


class SystemBulaReprocessingError(RuntimeError):
    """Safe operator-facing validation failure."""


@dataclass(frozen=True)
class ReprocessArguments:
    bula_id: UUID
    actor_email: str
    is_apply: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or reprocess one stored system bula."
    )
    parser.add_argument("--bula-id", required=True, type=UUID)
    parser.add_argument("--actor-email", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Replace both indexes and return the bula to staged review.",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> ReprocessArguments:
    arguments = build_parser().parse_args(argv)
    return ReprocessArguments(
        bula_id=arguments.bula_id,
        actor_email=arguments.actor_email.strip(),
        is_apply=arguments.apply,
    )


async def validate_operator_and_source(
    *, session: AsyncSession, arguments: ReprocessArguments
) -> Bula:
    actor = await UserRepository(db=session).get_user_by_email(arguments.actor_email)
    if actor is None or not actor.is_active or actor.role != UserRole.ADMIN:
        raise SystemBulaReprocessingError("An active administrator is required.")

    bula = await BulaRepository(db=session).get_by_id(bula_id=arguments.bula_id)
    if bula is None or bula.corpus != BulaCorpus.SYSTEM:
        raise SystemBulaReprocessingError("System bula not found.")
    if bula.status not in {BulaStatus.READY, BulaStatus.ERROR, BulaStatus.FAILED}:
        raise SystemBulaReprocessingError(
            "Bula is not in a reprocessable terminal state."
        )

    publication = bula.system_publication
    if publication is None or bula.file_address is None:
        raise SystemBulaReprocessingError("Bula has no verified stored PDF.")

    object_store = PgObjectStoreClient(repository=StoredObjectRepository(db=session))
    stored_metadata = await object_store.get_metadata(bula.file_address)
    pdf_bytes = await object_store.get_bytes(bula.file_address)
    if (
        stored_metadata.sha256_checksum != publication.sha256_checksum
        or stored_metadata.content_size_bytes != publication.content_size_bytes
        or hashlib.sha256(pdf_bytes).hexdigest() != publication.sha256_checksum
        or len(pdf_bytes) != publication.content_size_bytes
    ):
        raise SystemBulaReprocessingError(
            "Stored PDF does not match system publication provenance."
        )
    return bula


async def reprocess_system_bula(arguments: ReprocessArguments) -> Bula:
    async with async_session_factory() as session:
        bula = await validate_operator_and_source(session=session, arguments=arguments)
        if not arguments.is_apply:
            return bula

        settings = get_settings()
        llm_client = get_llm_client(settings=settings)
        qdrant_client = create_qdrant_client(settings=settings)
        bula_repository = BulaRepository(db=session)
        try:
            service = RAGIngestionService(
                parser=get_parser(),
                chunker=get_chunker(llm=llm_client, settings=settings),
                embeddings=get_embeddings(settings=settings),
                qdrant_store=get_qdrant_store(
                    qdrant_client=qdrant_client, settings=settings
                ),
                object_store=PgObjectStoreClient(
                    repository=StoredObjectRepository(db=session)
                ),
                bula_repo=bula_repository,
                bm25_index=get_bm25_index(db=session),
                debug_artifacts=get_ingestion_debug_artifacts(settings=settings),
            )
            try:
                return await service.ingest_bula(
                    bula_id=arguments.bula_id, is_reprocessing=True
                )
            except Exception:
                failed_bula = await bula_repository.get_by_id(bula_id=arguments.bula_id)
                if (
                    failed_bula is not None
                    and failed_bula.status == BulaStatus.PROCESSING
                ):
                    await bula_repository.update_ingestion_status(
                        bula=failed_bula,
                        status=BulaStatus.ERROR,
                        error_message="Reprocessing failed; inspect operator logs.",
                    )
                raise
        finally:
            await qdrant_client.close()
            await llm_client.close()


async def async_main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        bula = await reprocess_system_bula(arguments)
        mode = "apply" if arguments.is_apply else "preview"
        publication_state = (
            bula.system_publication.state.value
            if bula.system_publication is not None
            else "missing"
        )
        print(
            f"System bula reprocessing ({mode}): "
            f"bula_id={bula.id} status={bula.status.value} "
            f"publication={publication_state}"
        )
        return 0
    except (BulaIngestionError, SystemBulaReprocessingError) as exc:
        print(f"Reprocessing rejected: {exc}")
        return 1
    except Exception as exc:
        print(f"Reprocessing failed: {type(exc).__name__}. Check operator logs.")
        return 1
    finally:
        await close_engine()


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
