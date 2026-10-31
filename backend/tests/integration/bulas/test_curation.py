from io import BytesIO
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient, Request
from pypdf import PdfWriter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.modules.auth.models import User, UserRole, UserRoleAssignment
from app.modules.bulas.dependencies import get_curation_queue_repository
from app.modules.bulas.curation_queue_repository import IngestionQueueUnavailableError
from app.modules.bulas.models import (
    Bula,
    BulaStatus,
    BulaCurationEvent,
    SharedBulaSubmission,
)
from app.modules.bulas.repository import BulaRepository
from app.modules.storage.models import StoredObject
from app.modules.rag.retrieval_mode import RetrievalMode
from tests.integration.chat.test_cross_bula import add_chunk, install_factory


class CurationQueue:
    def __init__(self) -> None:
        self.jobs: list[UUID] = []
        self.should_fail = False
        self.active_jobs: set[UUID] = set()

    async def enqueue(self, *, bula_id: UUID, operation_id: UUID) -> int:
        if self.should_fail:
            raise IngestionQueueUnavailableError("Synthetic queue outage")
        self.jobs.append(bula_id)
        self.active_jobs.add(bula_id)
        return len(self.jobs)

    async def has_active_job(self, *, bula_id: UUID) -> bool:
        return bula_id in self.active_jobs


@pytest.fixture(autouse=True)
def mutation_keys(client: AsyncClient) -> None:
    async def add_operation_key(request: Request) -> None:
        if request.method in {"POST", "PATCH"}:
            request.headers.setdefault("Idempotency-Key", str(uuid4()))

    client.event_hooks["request"].append(add_operation_key)


async def account(
    client: AsyncClient, database: AsyncSession, role: UserRole, name: str
) -> tuple[int, dict[str, str]]:
    email = f"{name}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"full_name": name, "email": email, "password": "Secret123!"},
    )
    assert response.status_code == 201
    user_id = response.json()["user"]["id"]
    user = await database.get(User, user_id)
    assert user is not None
    user.role = role
    await database.commit()
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Secret123!"}
    )
    return user_id, {"Authorization": "Bearer " + login.json()["token"]["access_token"]}


def pdf(width: int = 100) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=100)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


async def submit(
    client: AsyncClient, headers: dict[str, str], *, content: bytes | None = None
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/bulas/shared",
        headers=headers,
        data={
            "product_name": "Medicamento sintético",
            "source_url": "https://fabricante.example/bula.pdf",
            "source_description": "Fonte identificada para revisão documental.",
        },
        files={
            "file": (
                "bula.pdf",
                content if content is not None else pdf(),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_review_gates_ingestion_public_access_and_withdrawal(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_id, contributor = await account(
        client, db_session, UserRole.CONTRIBUTOR, "contributor"
    )
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    _, reader = await account(client, db_session, UserRole.USER, "reader")
    queue = CurationQueue()
    app.dependency_overrides[get_curation_queue_repository] = lambda: queue
    document = await submit(client, contributor)
    identifier = str(document["id"])
    assert document["review_status"] == "pending" and not document["is_available"]
    assert queue.jobs == []
    assert (
        await client.get(f"/api/v1/bulas/shared/{identifier}/pdf", headers=reader)
    ).status_code == 404
    assert (
        await client.get("/api/v1/bulas/shared?view=review", headers=reader)
    ).status_code == 403
    denied = await client.post(
        f"/api/v1/bulas/shared/{identifier}/approve",
        headers=contributor,
        json={
            "expected_version": 1,
            "product_name": "Medicamento sint?tico",
            "reason": "Tentativa indevida",
        },
    )
    assert denied.status_code == 403
    response = await client.post(
        f"/api/v1/bulas/shared/{identifier}/approve",
        headers=reviewer,
        json={
            "expected_version": 1,
            "product_name": "Medicamento sint?tico",
            "reason": "Documento conferido e fonte identificada.",
            "presentation": "Apresentação literal conferida",
        },
    )
    assert response.status_code == 200, response.text
    assert not response.json()["is_available"]
    assert queue.jobs == [UUID(identifier)]
    stale = await client.post(
        f"/api/v1/bulas/shared/{identifier}/reject",
        headers=reviewer,
        json={
            "expected_version": 1,
            "product_name": "Medicamento sint?tico",
            "reason": "Decisão desatualizada",
        },
    )
    assert stale.status_code == 409
    assert (await client.get("/api/v1/bulas/shared", headers=reader)).json()[
        "total"
    ] == 0
    bula = await db_session.get(Bula, UUID(identifier))
    assert bula is not None and bula.user_id == owner_id
    # Synthetic ingestion completion; no parser, embeddings or provider is called.
    bula.status = BulaStatus.READY
    bula.drug_name = "Medicamento sintético"
    await db_session.commit()
    public = await client.get("/api/v1/bulas/shared", headers=reader)
    assert public.json()["total"] == 1 and public.json()["items"][0]["is_available"]
    assert (
        await client.get(f"/api/v1/bulas/{identifier}", headers=reader)
    ).status_code == 200
    approved = await BulaRepository(db_session).list_queryable_public_bulas()
    assert [row.id for row in approved] == [bula.id]
    original_pdf = await client.get(
        f"/api/v1/bulas/shared/{identifier}/pdf", headers=reviewer
    )
    assert (
        original_pdf.content == pdf()
        and original_pdf.headers["cache-control"] == "private, no-store"
    )
    assert (
        await client.get(f"/api/v1/bulas/shared/{identifier}", headers=reader)
    ).json()["events"] == []
    withdrawn = await client.post(
        f"/api/v1/bulas/shared/{identifier}/withdraw",
        headers=reviewer,
        json={
            "expected_version": 2,
            "product_name": "Medicamento sint?tico",
            "reason": "Fonte precisa de nova conferência.",
        },
    )
    assert withdrawn.status_code == 200
    assert (
        await client.get(f"/api/v1/bulas/{identifier}", headers=reader)
    ).status_code == 404
    assert await BulaRepository(db_session).list_queryable_public_bulas() == []
    details = (
        await client.get(f"/api/v1/bulas/shared/{identifier}", headers=contributor)
    ).json()
    assert [event["action"] for event in details["events"]] == [
        "submitted",
        "approved",
        "withdrawn",
    ]


@pytest.mark.anyio
async def test_self_review_and_unauthorized_submission_are_blocked(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, administrator = await account(client, db_session, UserRole.ADMIN, "admin")
    _, reader = await account(client, db_session, UserRole.USER, "reader")
    response = await client.post(
        "/api/v1/bulas/shared",
        headers=reader,
        data={
            "source_url": "https://example.com/bula",
            "source_description": "Fonte documental",
            "product_name": "Medicamento sint?tico",
        },
        files={"file": ("bula.pdf", pdf(), "application/pdf")},
    )
    assert response.status_code == 403
    document = await submit(client, administrator)
    response = await client.post(
        f"/api/v1/bulas/shared/{document['id']}/approve",
        headers=administrator,
        json={
            "expected_version": 1,
            "product_name": "Medicamento sint?tico",
            "reason": "Revisão da própria submissão",
        },
    )
    assert response.status_code == 403
    assert (
        await db_session.scalar(select(func.count()).select_from(BulaCurationEvent))
        == 1
    )


@pytest.mark.anyio
async def test_queue_failure_rolls_back_approval_and_retry_is_idempotent(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    queue = CurationQueue()
    queue.should_fail = True
    app.dependency_overrides[get_curation_queue_repository] = lambda: queue
    document = await submit(client, contributor)
    endpoint = f"/api/v1/bulas/shared/{document['id']}"
    headers = {**reviewer, "Idempotency-Key": str(uuid4())}
    payload = {
        "expected_version": 1,
        "product_name": "Medicamento sint?tico",
        "reason": "Fonte e PDF conferidos.",
    }
    assert (
        await client.post(endpoint + "/approve", headers=headers, json=payload)
    ).status_code == 503
    detail = (await client.get(endpoint, headers=reviewer)).json()["document"]
    assert detail["review_status"] == "pending" and detail["version"] == 1
    assert detail["ingestion_job_id"] is None and queue.jobs == []
    queue.should_fail = False
    first = await client.post(endpoint + "/approve", headers=headers, json=payload)
    assert first.status_code == 200 and first.json()["version"] == 2
    repeated = await client.post(endpoint + "/approve", headers=headers, json=payload)
    assert repeated.status_code == 200 and repeated.json()["replayed"] is True
    assert len(queue.jobs) == 1
    assert (
        await db_session.scalar(select(func.count()).select_from(BulaCurationEvent))
        == 2
    )
    assert (
        await client.post(
            endpoint + "/retry",
            headers=reviewer,
            json={"expected_version": 2, "reason": "Tentativa duplicada"},
        )
    ).status_code == 409


@pytest.mark.anyio
async def test_only_admin_designates_roles_with_audit_and_no_self_registration(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, admin = await account(client, db_session, UserRole.ADMIN, "administrator")
    user_id, reader = await account(client, db_session, UserRole.USER, "reader")
    payload = {
        "role": "reviewer",
        "expected_role": "user",
        "reason": "Profissional designado pelo responsável.",
    }
    assert (
        await client.patch(
            f"/api/v1/auth/users/{user_id}/role", headers=reader, json=payload
        )
    ).status_code == 403
    assert (await client.get("/api/v1/auth/users", headers=reader)).status_code == 403
    changed = await client.patch(
        f"/api/v1/auth/users/{user_id}/role", headers=admin, json=payload
    )
    assert changed.status_code == 200 and changed.json()["role"] == "reviewer"
    assert (
        await db_session.scalar(select(func.count()).select_from(UserRoleAssignment))
        == 1
    )
    # An existing JWT reads the current role from the database on each request.
    assert (
        await client.get("/api/v1/bulas/shared?view=review", headers=reader)
    ).status_code == 200
    signup = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Escalation",
            "email": "escalate@example.com",
            "password": "Secret123!",
            "role": "reviewer",
        },
    )
    assert signup.status_code == 422


@pytest.mark.anyio
async def test_changed_pdf_blocks_decision(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    document = await submit(client, contributor)
    stored = await db_session.scalar(select(StoredObject))
    assert stored is not None
    stored.data = b"changed"
    await db_session.commit()
    decision = await client.post(
        f"/api/v1/bulas/shared/{document['id']}/approve",
        headers=reviewer,
        json={
            "expected_version": 1,
            "product_name": "Medicamento sint?tico",
            "reason": "Conferência documental",
        },
    )
    assert decision.status_code == 409
    assert (
        await db_session.scalar(select(func.count()).select_from(BulaCurationEvent))
        == 1
    )


@pytest.mark.anyio
async def test_withdrawal_remains_possible_when_the_stored_pdf_is_damaged(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    app.dependency_overrides[get_curation_queue_repository] = lambda: CurationQueue()
    document = await submit(client, contributor)
    endpoint = f"/api/v1/bulas/shared/{document['id']}"
    assert (
        await client.post(
            endpoint + "/approve",
            headers=reviewer,
            json={
                "expected_version": 1,
                "product_name": "Medicamento sint?tico",
                "reason": "PDF conferido.",
            },
        )
    ).status_code == 200
    stored = await db_session.scalar(select(StoredObject))
    assert stored is not None
    stored.data = b"damaged"
    await db_session.commit()
    withdrawal = await client.post(
        endpoint + "/withdraw",
        headers=reviewer,
        json={
            "expected_version": 2,
            "product_name": "Medicamento sint?tico",
            "reason": "Arquivo armazenado danificado.",
        },
    )
    assert (
        withdrawal.status_code == 200
        and withdrawal.json()["review_status"] == "withdrawn"
    )
    assert await BulaRepository(db_session).list_queryable_public_bulas() == []


@pytest.mark.anyio
@pytest.mark.parametrize("mode", list(RetrievalMode))
@pytest.mark.parametrize("scenario", ["cross_bula", "bula"])
async def test_shared_sources_reach_chat_only_after_review_and_remain_attributed(
    client: AsyncClient, db_session: AsyncSession, mode: RetrievalMode, scenario: str
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    _, reader = await account(client, db_session, UserRole.USER, "reader")
    queue = CurationQueue()
    app.dependency_overrides[get_curation_queue_repository] = lambda: queue
    approved = await submit(client, contributor)
    pending = await submit(client, contributor, content=pdf(width=101))
    approval = await client.post(
        f"/api/v1/bulas/shared/{approved['id']}/approve",
        headers=reviewer,
        json={
            "expected_version": 1,
            "product_name": "Medicamento sint?tico",
            "reason": "PDF e origem conferidos.",
            "presentation": "Comprimidos",
            "strength": "10 mg",
        },
    )
    assert approval.status_code == 200
    approved_id = UUID(str(approved["id"]))
    pending_id = UUID(str(pending["id"]))
    for identifier in (approved_id, pending_id):
        bula = await db_session.get(Bula, identifier)
        assert bula is not None
        bula.status = BulaStatus.READY
        bula.drug_name = "Produto documentado"
    await db_session.commit()
    document = await add_chunk(
        db_session, approved_id, "Conservar abaixo de 30 °C.", corpus="shared"
    )
    scopes: list[tuple[UUID, ...]] = []
    install_factory(
        db_session,
        [document],
        [
            '{"unit_ids":["E1"],"limitation":null}',
            "Conserve abaixo de 30 °C. [1]",
        ],
        scopes,
        scoped_bula_id=approved_id if scenario == "bula" else None,
    )
    endpoint = (
        f"/api/v1/chat/sessions/{approved_id}/ask"
        if scenario == "bula"
        else "/api/v1/chat/ask"
    )
    response = await client.post(
        endpoint,
        headers=reader,
        json={"question": "Como conservar?", "mode": mode.value},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert scopes == [(approved_id,)]
    assert result["source_chunks"], result
    source = result["source_chunks"][0]
    assert source["corpus"] == "shared" and source["bula_id"] == str(approved_id)
    assert source["source_url"] == "https://fabricante.example/bula.pdf"
    assert source["presentation"] == "Comprimidos" and source["strength"] == "10 mg"
    history = await client.get(
        f"/api/v1/chat/sessions/{result['session_id']}", headers=reader
    )
    assert history.json()["messages"][1]["source_chunks"] == result["source_chunks"]
    withdrawn = await client.post(
        f"/api/v1/bulas/shared/{approved_id}/withdraw",
        headers=reviewer,
        json={
            "expected_version": 2,
            "product_name": "Medicamento sint?tico",
            "reason": "Nova dúvida documental.",
        },
    )
    assert withdrawn.status_code == 200
    # Both withdrawn and unreviewed READY rows stay outside all public retrieval scopes.
    assert await BulaRepository(db_session).list_queryable_public_bulas() == []
    assert queue.jobs == [approved_id]


@pytest.mark.anyio
async def test_rejection_is_final_and_never_enqueues_ingestion(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    queue = CurationQueue()
    app.dependency_overrides[get_curation_queue_repository] = lambda: queue
    document = await submit(client, contributor)
    endpoint = f"/api/v1/bulas/shared/{document['id']}"
    rejected = await client.post(
        endpoint + "/reject",
        headers=reviewer,
        json={
            "expected_version": 1,
            "product_name": "Medicamento sint?tico",
            "reason": "Documento sem identificação suficiente.",
        },
    )
    assert (
        rejected.status_code == 200 and rejected.json()["review_status"] == "rejected"
    )
    assert (
        await client.post(
            endpoint + "/approve",
            headers=reviewer,
            json={
                "expected_version": 2,
                "product_name": "Medicamento sint?tico",
                "reason": "Tentativa inválida",
            },
        )
    ).status_code == 409
    assert queue.jobs == []


@pytest.mark.anyio
@pytest.mark.parametrize("defect", ["missing_event", "checksum", "size"])
async def test_ready_row_cannot_bypass_audit_or_integrity(
    client: AsyncClient, db_session: AsyncSession, defect: str
) -> None:
    _, contributor = await account(client, db_session, UserRole.CONTRIBUTOR, "sender")
    _, reviewer = await account(client, db_session, UserRole.REVIEWER, "reviewer")
    _, reader = await account(client, db_session, UserRole.USER, "reader")
    app.dependency_overrides[get_curation_queue_repository] = lambda: CurationQueue()
    document = await submit(client, contributor)
    identifier = UUID(str(document["id"]))
    if defect != "missing_event":
        assert (
            await client.post(
                f"/api/v1/bulas/shared/{identifier}/approve",
                headers=reviewer,
                json={
                    "expected_version": 1,
                    "product_name": "Medicamento sint?tico",
                    "reason": "Documento conferido.",
                },
            )
        ).status_code == 200
    bula = await db_session.get(Bula, identifier)
    submission = await db_session.get(SharedBulaSubmission, identifier)
    assert bula is not None and submission is not None
    bula.status = BulaStatus.READY
    submission.review_status = "approved"
    if defect == "checksum":
        submission.sha256_checksum = "0" * 64
    if defect == "size":
        submission.content_size_bytes += 1
    await db_session.commit()
    assert (await client.get("/api/v1/bulas/shared", headers=reader)).json()[
        "total"
    ] == 0
    assert (
        await client.get(f"/api/v1/bulas/{identifier}", headers=reader)
    ).status_code == 404
    assert await BulaRepository(db_session).list_queryable_public_bulas() == []
