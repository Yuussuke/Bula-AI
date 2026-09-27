from __future__ import annotations

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.modules.auth.models import UserRole
from app.modules.bulas.models import (
    Bula,
    BulaCorpus,
    BulaStatus,
    SystemBulaPublication,
)
from app.scripts import reprocess_system_bula as command


BULA_ID = UUID("11111111-1111-1111-1111-111111111111")
PDF_BYTES = b"%PDF-1.4\n%%EOF"
PDF_SHA256 = hashlib.sha256(PDF_BYTES).hexdigest()


def build_bula() -> Bula:
    bula = Bula(
        id=BULA_ID,
        user_id=1,
        drug_name="Test medicine",
        file_address="stored_objects/test",
        corpus=BulaCorpus.SYSTEM,
        status=BulaStatus.READY,
    )
    bula.system_publication = SystemBulaPublication(
        bula_id=BULA_ID,
        sha256_checksum=PDF_SHA256,
        content_size_bytes=len(PDF_BYTES),
    )
    return bula


def test_command_defaults_to_preview() -> None:
    arguments = command.parse_arguments(
        ["--bula-id", str(BULA_ID), "--actor-email", " admin@example.com "]
    )

    assert arguments.bula_id == BULA_ID
    assert arguments.actor_email == "admin@example.com"
    assert arguments.is_apply is False


@pytest.mark.anyio
async def test_preflight_rejects_non_admin_before_reading_bula(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_lookup = AsyncMock(
        return_value=SimpleNamespace(is_active=True, role=UserRole.USER)
    )
    bula_lookup = AsyncMock()
    monkeypatch.setattr(
        command,
        "UserRepository",
        lambda db: SimpleNamespace(get_user_by_email=user_lookup),
    )
    monkeypatch.setattr(
        command,
        "BulaRepository",
        lambda db: SimpleNamespace(get_by_id=bula_lookup),
    )

    with pytest.raises(command.SystemBulaReprocessingError, match="administrator"):
        await command.validate_operator_and_source(
            session=object(),
            arguments=command.ReprocessArguments(BULA_ID, "user@example.com", False),
        )

    bula_lookup.assert_not_awaited()


@pytest.mark.anyio
async def test_preflight_accepts_matching_stored_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bula = build_bula()
    monkeypatch.setattr(
        command,
        "UserRepository",
        lambda db: SimpleNamespace(
            get_user_by_email=AsyncMock(
                return_value=SimpleNamespace(is_active=True, role=UserRole.ADMIN)
            )
        ),
    )
    monkeypatch.setattr(
        command,
        "BulaRepository",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=bula)),
    )
    monkeypatch.setattr(
        command,
        "StoredObjectRepository",
        lambda db: object(),
    )
    monkeypatch.setattr(
        command,
        "PgObjectStoreClient",
        lambda repository: SimpleNamespace(
            get_metadata=AsyncMock(
                return_value=SimpleNamespace(
                    sha256_checksum=PDF_SHA256,
                    content_size_bytes=len(PDF_BYTES),
                )
            ),
            get_bytes=AsyncMock(return_value=PDF_BYTES),
        ),
    )

    result = await command.validate_operator_and_source(
        session=object(),
        arguments=command.ReprocessArguments(BULA_ID, "admin@example.com", False),
    )

    assert result is bula


@pytest.mark.anyio
async def test_preflight_rejects_tampered_pdf_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bula = build_bula()
    monkeypatch.setattr(
        command,
        "UserRepository",
        lambda db: SimpleNamespace(
            get_user_by_email=AsyncMock(
                return_value=SimpleNamespace(is_active=True, role=UserRole.ADMIN)
            )
        ),
    )
    monkeypatch.setattr(
        command,
        "BulaRepository",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=bula)),
    )
    monkeypatch.setattr(command, "StoredObjectRepository", lambda db: object())
    monkeypatch.setattr(
        command,
        "PgObjectStoreClient",
        lambda repository: SimpleNamespace(
            get_metadata=AsyncMock(
                return_value=SimpleNamespace(
                    sha256_checksum=PDF_SHA256,
                    content_size_bytes=len(PDF_BYTES),
                )
            ),
            get_bytes=AsyncMock(return_value=b"tampered source"),
        ),
    )

    with pytest.raises(command.SystemBulaReprocessingError, match="does not match"):
        await command.validate_operator_and_source(
            session=object(),
            arguments=command.ReprocessArguments(BULA_ID, "admin@example.com", False),
        )
