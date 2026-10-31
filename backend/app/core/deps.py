"""Shared HTTP dependencies for traceable, explicitly keyed mutations."""

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Header, HTTPException

logger = structlog.get_logger(__name__)


async def get_idempotency_key(
    operation_id: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> AsyncIterator[UUID]:
    try:
        yield operation_id
    except HTTPException as error:
        logger.info(
            "mutation_request_rejected",
            operation_id=str(operation_id),
            http_status=error.status_code,
        )
        raise
    except asyncio.CancelledError:
        logger.warning("mutation_request_cancelled", operation_id=str(operation_id))
        raise
    except Exception:
        logger.exception("mutation_request_failed", operation_id=str(operation_id))
        raise
    else:
        logger.info("mutation_request_completed", operation_id=str(operation_id))
