"""Mutation effects, recovery and audit provenance, without providers or real PDFs."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.modules.auth.models import UserRole, UserRoleAssignment
from app.modules.bulas.dependencies import get_curation_queue_repository
from app.modules.bulas.models import (
    Bula,
    BulaCurationEvent,
    BulaStatus,
    SharedBulaSubmission,
)
from app.modules.bulas.repository import BulaRepository
from app.modules.storage.models import StoredObject
from tests.integration.bulas.test_curation import CurationQueue, account, pdf, submit
from tests.integration.bulas.test_curation import mutation_keys as mutation_keys


@pytest.mark.anyio
async def test_repeated_submission_returns_one_document_and_never_reuses_key_for_other_content(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    headers = {**contributor, "Idempotency-Key": str(uuid4())}
    first = await submit(client, headers)
    second = await submit(client, headers)
    assert first["id"] == second["id"] and second["replayed"] is True
    assert first["replayed"] is False
    changed = await client.post(
        "/api/v1/bulas/shared",
        headers=headers,
        data={
            "product_name": "Outro medicamento",
            "source_url": "https://fabricante.example/bula.pdf",
            "source_description": "Fonte identificada para revisão documental.",
        },
        files={"file": ("bula.pdf", pdf(), "application/pdf")},
    )
    assert changed.status_code == 409
    for model in (Bula, StoredObject, BulaCurationEvent):
        assert await db_session.scalar(select(func.count()).select_from(model)) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("terminal_action", ["reject", "withdraw"])
async def test_duplicate_active_pdf_is_blocked_but_new_review_preserves_lineage(
    client: AsyncClient, db_session: AsyncSession, terminal_action: str
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    _, other_contributor = await account(
        client, db_session, UserRole.CONTRIBUTOR, "another-sender"
    )
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    queue = CurationQueue()
    app.dependency_overrides[get_curation_queue_repository] = lambda: queue
    first = await submit(client, contributor)
    duplicate = await client.post(
        "/api/v1/bulas/shared",
        headers=other_contributor,
        data={
            "product_name": "Mesmo PDF",
            "source_url": "https://example.com/other-source",
            "source_description": "Outra origem declarada",
        },
        files={"file": ("copy.pdf", pdf(), "application/pdf")},
    )
    assert duplicate.status_code == 409
    assert await db_session.scalar(select(func.count()).select_from(StoredObject)) == 1
    endpoint = f"/api/v1/bulas/shared/{first['id']}"
    version = 1
    if terminal_action == "withdraw":
        assert (
            await client.post(
                endpoint + "/approve",
                headers=reviewer,
                json={
                    "expected_version": 1,
                    "product_name": "Identificação conferida",
                    "reason": "Conferência documental.",
                },
            )
        ).status_code == 200
        version = 2
    assert (
        await client.post(
            endpoint + "/" + terminal_action,
            headers=reviewer,
            json={
                "expected_version": version,
                "reason": "Nova revisão documental necessária.",
            },
        )
    ).status_code == 200
    second = await submit(client, other_contributor)
    assert second["id"] != first["id"] and second["supersedes_bula_id"] == first["id"]
    assert second["review_status"] == "pending" and second["version"] == 1
    preserved = await db_session.get(SharedBulaSubmission, UUID(str(first["id"])))
    assert preserved is not None and preserved.review_status == (
        "rejected" if terminal_action == "reject" else "withdrawn"
    )


@pytest.mark.anyio
async def test_decision_replay_does_not_add_event_or_job_and_cannot_change_action(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    queue = CurationQueue()
    app.dependency_overrides[get_curation_queue_repository] = lambda: queue
    document = await submit(client, contributor)
    endpoint = f"/api/v1/bulas/shared/{document['id']}"
    headers = {**reviewer, "Idempotency-Key": str(uuid4())}
    payload = {
        "expected_version": 1,
        "product_name": "Nome conferido",
        "manufacturer": "Fabricante conferido",
        "presentation": "Comprimidos",
        "strength": "10 mg",
        "reason": "Identificação e PDF conferidos.",
    }
    first = await client.post(endpoint + "/approve", headers=headers, json=payload)
    repeated = await client.post(endpoint + "/approve", headers=headers, json=payload)
    assert first.status_code == repeated.status_code == 200
    assert repeated.json()["replayed"] and repeated.json()["version"] == 2
    assert (
        await client.post(endpoint + "/reject", headers=headers, json=payload)
    ).status_code == 409
    assert (
        await client.post(
            endpoint + "/approve",
            headers=headers,
            json={**payload, "reason": "Outro parecer"},
        )
    ).status_code == 409
    assert (
        await client.post(endpoint + "/approve", headers=reviewer, json=payload)
    ).status_code == 409
    assert len(queue.jobs) == 1
    events = (await client.get(endpoint, headers=reviewer)).json()["events"]
    assert len(events) == 2
    approval = next(event for event in events if event["action"] == "approved")
    assert (
        approval["actor_role"] == "reviewer"
        and approval["operation_id"] == headers["Idempotency-Key"]
    )
    assert len(approval["request_fingerprint"]) == 64
    assert approval["before_state"]["product_name"] == "Medicamento sintético"
    assert approval["after_state"]["product_name"] == "Nome conferido"
    assert approval["after_state"]["sha256_checksum"] == document["sha256_checksum"]
    assert (
        approval["after_state"]["ingestion_job_id"] == first.json()["ingestion_job_id"]
    )


@pytest.mark.anyio
@pytest.mark.parametrize("has_active_job", [False, True])
async def test_legacy_approval_without_dispatch_has_safe_explicit_recovery(
    client: AsyncClient, db_session: AsyncSession, has_active_job: bool
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    reviewer_id, reviewer = await account(
        client, db_session, UserRole.REVIEWER, "reviewer"
    )
    queue = CurationQueue()
    app.dependency_overrides[get_curation_queue_repository] = lambda: queue
    document = await submit(client, contributor)
    identifier = UUID(str(document["id"]))
    submission = await db_session.get(SharedBulaSubmission, identifier)
    assert submission is not None
    submission.review_status = "approved"
    submission.version = 2
    db_session.add(
        BulaCurationEvent(
            bula_id=identifier,
            actor_id=reviewer_id,
            actor_name="Historical reviewer",
            action="approved",
            reason="Historical approval",
            version=2,
        )
    )
    await db_session.commit()
    if has_active_job:
        queue.active_jobs.add(identifier)
    response = await client.post(
        f"/api/v1/bulas/shared/{identifier}/retry",
        headers=reviewer,
        json={
            "expected_version": 2,
            "reason": "Recuperar envio sem trabalho confirmado.",
        },
    )
    assert response.status_code == (409 if has_active_job else 200)
    assert len(queue.jobs) == (0 if has_active_job else 1)
    historical = await db_session.scalar(
        select(BulaCurationEvent).where(
            BulaCurationEvent.reason == "Historical approval"
        )
    )
    assert (
        historical is not None
        and historical.operation_id is None
        and historical.after_state is None
    )


@pytest.mark.anyio
async def test_ingestion_lifecycle_is_audited_without_inventing_human_decisions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    app.dependency_overrides[get_curation_queue_repository] = lambda: CurationQueue()
    document = await submit(client, contributor)
    identifier = UUID(str(document["id"]))
    approval = await client.post(
        f"/api/v1/bulas/shared/{identifier}/approve",
        headers=reviewer,
        json={
            "expected_version": 1,
            "product_name": "Nome conferido",
            "reason": "Conferência documental.",
        },
    )
    assert approval.status_code == 200
    repository = BulaRepository(db_session)
    bula = await repository.get_by_id(bula_id=identifier)
    assert bula is not None
    bula = await repository.update_ingestion_status(
        bula=bula, status=BulaStatus.PROCESSING
    )
    bula = await repository.update_ingestion_status(
        bula=bula, status=BulaStatus.READY, qdrant_collection="synthetic"
    )
    await repository.update_ingestion_status(
        bula=bula, status=BulaStatus.READY, qdrant_collection="synthetic"
    )
    events = list(
        (
            await db_session.execute(
                select(BulaCurationEvent).where(BulaCurationEvent.bula_id == identifier)
            )
        ).scalars()
    )
    technical = [event for event in events if event.actor_role == "system"]
    assert {event.action for event in technical} == {
        "ingestion_processing",
        "ingestion_ready",
    }
    assert len(technical) == 2
    assert all(
        event.actor_id is None and event.operation_id is None for event in technical
    )
    assert all(
        event.after_state
        and event.after_state["ingestion_operation_id"]
        == approval.json()["operation_id"]
        for event in technical
    )
    assert len([event for event in events if event.action == "approved"]) == 1


@pytest.mark.anyio
async def test_role_assignment_replay_history_and_conflicting_payload(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, admin = await account(client, db_session, UserRole.ADMIN, "admin")
    target_id, reader = await account(client, db_session, UserRole.USER, "target")
    endpoint = f"/api/v1/auth/users/{target_id}"
    headers = {**admin, "Idempotency-Key": str(uuid4())}
    payload = {
        "role": "reviewer",
        "expected_role": "user",
        "reason": "Designação documental pelo responsável.",
    }
    first = await client.patch(endpoint + "/role", headers=headers, json=payload)
    replay = await client.patch(endpoint + "/role", headers=headers, json=payload)
    assert first.status_code == replay.status_code == 200 and replay.json()["replayed"]
    assert (
        await client.patch(
            endpoint + "/role", headers=headers, json={**payload, "role": "contributor"}
        )
    ).status_code == 409
    assert (
        await db_session.scalar(select(func.count()).select_from(UserRoleAssignment))
        == 1
    )
    assert (
        await client.get(endpoint + "/role-history", headers=reader)
    ).status_code == 403
    history = (await client.get(endpoint + "/role-history", headers=admin)).json()
    assert (
        len(history) == 1 and history[0]["operation_id"] == headers["Idempotency-Key"]
    )
    assert history[0]["actor_role"] == "admin" and history[0]["actor_name"] == "admin"
    assert (
        history[0]["previous_role"] == "user"
        and history[0]["assigned_role"] == "reviewer"
    )
