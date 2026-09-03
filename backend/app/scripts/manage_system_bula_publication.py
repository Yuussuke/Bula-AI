from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, close_engine
from app.modules.auth.repository import UserRepository
from app.modules.bulas.models import SystemBulaPublication
from app.modules.bulas.repository import BulaRepository
from app.modules.bulas.service import (
    SystemBulaPublicationError,
    SystemBulaPublicationService,
)
from app.modules.storage.client import PgObjectStoreClient
from app.modules.storage.repository import StoredObjectRepository


PublicationAction = Literal["vet", "publish", "withdraw", "reject"]


@dataclass(frozen=True)
class PublicationArguments:
    action: PublicationAction
    bula_id: UUID
    actor_email: str
    notes: str | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage the post-ingestion system bula publication lifecycle.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("vet", "publish", "withdraw", "reject"):
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument("--bula-id", required=True, type=UUID)
        action_parser.add_argument("--actor-email", required=True)
        if action != "publish":
            action_parser.add_argument("--notes")
    return parser


def parse_arguments(
    argv: Sequence[str] | None = None,
) -> PublicationArguments:
    parsed_arguments = build_parser().parse_args(argv)
    action = str(parsed_arguments.action)
    if action not in {"vet", "publish", "withdraw", "reject"}:
        raise ValueError("Unsupported publication action.")

    return PublicationArguments(
        action=cast(PublicationAction, action),
        bula_id=parsed_arguments.bula_id,
        actor_email=parsed_arguments.actor_email,
        notes=getattr(parsed_arguments, "notes", None),
    )


def build_service(*, session: AsyncSession) -> SystemBulaPublicationService:
    return SystemBulaPublicationService(
        user_repository=UserRepository(db=session),
        bula_repository=BulaRepository(db=session),
        object_store=PgObjectStoreClient(
            repository=StoredObjectRepository(db=session),
        ),
    )


async def manage_publication(
    arguments: PublicationArguments,
) -> SystemBulaPublication:
    async with async_session_factory() as session:
        service = build_service(session=session)
        if arguments.action == "vet":
            return await service.vet_document(
                bula_id=arguments.bula_id,
                actor_email=arguments.actor_email,
                review_notes=arguments.notes,
            )
        if arguments.action == "publish":
            return await service.publish_document(
                bula_id=arguments.bula_id,
                actor_email=arguments.actor_email,
            )
        if arguments.action == "withdraw":
            return await service.withdraw_document(
                bula_id=arguments.bula_id,
                actor_email=arguments.actor_email,
                reason=arguments.notes or "",
            )
        return await service.reject_document(
            bula_id=arguments.bula_id,
            actor_email=arguments.actor_email,
            reason=arguments.notes or "",
        )


async def async_main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        publication = await manage_publication(arguments)
        print(
            "System bula publication updated: "
            f"bula_id={publication.bula_id} state={publication.state.value}"
        )
        return 0
    except SystemBulaPublicationError as exc:
        print(str(exc))
        return 1
    finally:
        await close_engine()


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
