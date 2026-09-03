from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import UUID

import pytest

from app.modules.auth.models import UserRole
from app.modules.bulas.models import (
    BulaCorpus,
    BulaStatus,
    SystemBulaPublicationState,
)
from app.modules.bulas.service import (
    SystemBulaPublicationError,
    SystemBulaPublicationService,
)
from app.modules.storage.schemas import StoredObjectRef


BULA_ID = UUID("11111111-1111-1111-1111-111111111111")


def build_service(
    *,
    state: SystemBulaPublicationState = SystemBulaPublicationState.STAGED,
    status: BulaStatus = BulaStatus.READY,
    actor_role: UserRole = UserRole.ADMIN,
) -> tuple[SystemBulaPublicationService, AsyncMock, AsyncMock, AsyncMock, object]:
    user_repository = AsyncMock()
    bula_repository = AsyncMock()
    object_store = AsyncMock()
    actor = SimpleNamespace(
        id=7,
        email="reviewer@example.com",
        full_name="Clinical Reviewer",
        role=actor_role,
        is_active=True,
    )
    publication = SimpleNamespace(
        bula_id=BULA_ID,
        state=state,
        sha256_checksum="a" * 64,
        content_size_bytes=1024,
    )
    bula = SimpleNamespace(
        id=BULA_ID,
        corpus=BulaCorpus.SYSTEM,
        status=status,
        file_address="stored_objects/bula",
        system_publication=publication,
    )
    user_repository.get_user_by_email.return_value = actor
    bula_repository.get_by_id.return_value = bula
    bula_repository.update_system_publication_state.return_value = publication
    object_store.get_metadata.return_value = SimpleNamespace(
        spec=StoredObjectRef,
        sha256_checksum="a" * 64,
        content_size_bytes=1024,
    )
    service = SystemBulaPublicationService(
        user_repository=user_repository,
        bula_repository=bula_repository,
        object_store=object_store,
    )
    return service, user_repository, bula_repository, object_store, publication


@pytest.mark.anyio
@pytest.mark.parametrize(
    "initial_state",
    [
        SystemBulaPublicationState.STAGED,
        SystemBulaPublicationState.WITHDRAWN,
    ],
)
async def test_vet_ready_system_bula_records_reviewer_evidence(
    initial_state: SystemBulaPublicationState,
) -> None:
    service, users, bulas, storage, publication = build_service(
        state=initial_state, actor_role=UserRole.REVIEWER
    )

    await service.vet_document(
        bula_id=BULA_ID,
        actor_email=" REVIEWER@example.com ",
        review_notes="  Confirmed against ANVISA.  ",
    )

    users.get_user_by_email.assert_awaited_once_with("reviewer@example.com")
    storage.get_metadata.assert_awaited_once_with("stored_objects/bula")
    bulas.update_system_publication_state.assert_awaited_once_with(
        publication=publication,
        state=SystemBulaPublicationState.VETTED,
        reviewed_by_user_id=7,
        reviewed_by_name="Clinical Reviewer",
        reviewed_at=ANY,
        review_notes="Confirmed against ANVISA.",
    )


@pytest.mark.anyio
async def test_vet_rejects_bula_that_is_not_ready() -> None:
    service, _, bulas, storage, _ = build_service(status=BulaStatus.ERROR)

    with pytest.raises(SystemBulaPublicationError, match="successfully ingested"):
        await service.vet_document(
            bula_id=BULA_ID,
            actor_email="reviewer@example.com",
            review_notes=None,
        )

    storage.get_metadata.assert_not_awaited()
    bulas.update_system_publication_state.assert_not_awaited()


@pytest.mark.anyio
async def test_publish_requires_vetted_state_and_matching_integrity() -> None:
    service, _, bulas, storage, publication = build_service(
        state=SystemBulaPublicationState.VETTED
    )

    await service.publish_document(
        bula_id=BULA_ID,
        actor_email="reviewer@example.com",
    )

    storage.get_metadata.assert_awaited_once_with("stored_objects/bula")
    bulas.update_system_publication_state.assert_awaited_once_with(
        publication=publication,
        state=SystemBulaPublicationState.PUBLISHED,
        published_by_user_id=7,
        published_by_name="Clinical Reviewer",
        published_at=ANY,
    )


@pytest.mark.anyio
async def test_publish_rejects_checksum_mismatch() -> None:
    service, _, bulas, storage, _ = build_service(
        state=SystemBulaPublicationState.VETTED
    )
    storage.get_metadata.return_value.sha256_checksum = "b" * 64

    with pytest.raises(SystemBulaPublicationError, match="integrity"):
        await service.publish_document(
            bula_id=BULA_ID,
            actor_email="reviewer@example.com",
        )

    bulas.update_system_publication_state.assert_not_awaited()


@pytest.mark.anyio
async def test_withdraw_requires_admin_and_explainable_reason() -> None:
    service, _, bulas, _, publication = build_service(
        state=SystemBulaPublicationState.PUBLISHED
    )

    await service.withdraw_document(
        bula_id=BULA_ID,
        actor_email="reviewer@example.com",
        reason="  ANVISA source changed.  ",
    )

    bulas.update_system_publication_state.assert_awaited_once_with(
        publication=publication,
        state=SystemBulaPublicationState.WITHDRAWN,
        withdrawal_reason="ANVISA source changed.",
    )


@pytest.mark.anyio
async def test_regular_user_cannot_manage_publication() -> None:
    service, _, bulas, storage, _ = build_service(actor_role=UserRole.USER)

    with pytest.raises(SystemBulaPublicationError, match="not authorized"):
        await service.vet_document(
            bula_id=BULA_ID,
            actor_email="reviewer@example.com",
            review_notes=None,
        )

    bulas.get_by_id.assert_not_awaited()
    storage.get_metadata.assert_not_awaited()
