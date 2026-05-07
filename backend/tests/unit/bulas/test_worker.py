from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from pgqueuer.models import Job

from app.modules.bulas.models import Bula, BulaCorpus, BulaStatus
from app.worker import (
    build_error_message,
    mark_bula_ingestion_failed_after_retries,
)


class FakeSessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        return None


class FakeBulaRepository:
    updated_status: BulaStatus | None = None
    updated_error_message: str | None = None

    def __init__(self, db: object) -> None:
        self.db = db

    async def get_by_id(self, *, bula_id: UUID) -> Bula | None:
        return Bula(
            id=bula_id,
            user_id=1,
            drug_name="Dipirona",
            file_address="stored_objects/pdf-123",
            status=BulaStatus.PROCESSING,
            corpus=BulaCorpus.PRIVATE,
        )

    async def update_ingestion_status(
        self,
        *,
        bula: Bula,
        status: BulaStatus,
        error_message: str | None = None,
        qdrant_collection: str | None = None,
    ) -> Bula:
        _ = qdrant_collection
        self.__class__.updated_status = status
        self.__class__.updated_error_message = error_message
        bula.status = status
        bula.error_message = error_message
        return bula


def test_build_error_message_prefers_original_exception_cause() -> None:
    original_error = RuntimeError("OpenRouter rate limit")
    wrapped_error = RuntimeError("Max retries")
    wrapped_error.__cause__ = original_error

    error_message = build_error_message(wrapped_error)

    assert error_message == "OpenRouter rate limit"


@pytest.mark.anyio
async def test_mark_bula_ingestion_failed_after_retries_sets_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeBulaRepository.updated_status = None
    FakeBulaRepository.updated_error_message = None
    bula_id = UUID("11111111-1111-1111-1111-111111111111")
    fake_job = cast(Job, SimpleNamespace(payload=str(bula_id).encode()))

    monkeypatch.setattr(
        "app.worker.async_session_factory", lambda: FakeSessionContext()
    )
    monkeypatch.setattr("app.worker.BulaRepository", FakeBulaRepository)

    await mark_bula_ingestion_failed_after_retries(
        job=fake_job,
        exc=RuntimeError("permanent failure"),
    )

    assert FakeBulaRepository.updated_status == BulaStatus.ERROR
    assert FakeBulaRepository.updated_error_message == "permanent failure"
