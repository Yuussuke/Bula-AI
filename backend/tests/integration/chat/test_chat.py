import pytest
from httpx import AsyncClient
from langchain_core.runnables import RunnableLambda
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import UTC, datetime
from uuid import UUID
from uuid import uuid4

from app.main import app
from app.modules.auth.models import User
from app.modules.bulas.models import (
    Bula,
    BulaCorpus,
    BulaStatus,
    SystemBulaPublication,
    SystemBulaPublicationState,
)
from app.modules.chat.models import ChatMessage, ChatRole, ChatSession, RetrievalMode
from app.modules.chat.repository import ChatRepository
from app.modules.rag.dependencies import get_rag_chain_factory
from app.modules.storage.models import StoredObject


TEST_USER = {
    "full_name": "Chat Test User",
    "email": "chat-test@bulaai.com",
    "password": "Secret123!",
}


async def get_access_token(client: AsyncClient) -> str:
    await client.post("/api/v1/auth/register", json=TEST_USER)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    return str(login_response.json()["token"]["access_token"])


def build_auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def get_user_by_email(db_session: AsyncSession, *, email: str) -> User:
    result = await db_session.execute(select(User).where(User.email == email))
    return result.scalar_one()


async def create_ready_bula(
    db_session: AsyncSession,
    *,
    user_id: int,
    status: BulaStatus = BulaStatus.READY,
) -> Bula:
    bula = Bula(
        user_id=user_id,
        drug_name="Dipirona",
        manufacturer="Example Pharma",
        file_address="stored_objects/test.pdf",
        status=status,
    )
    db_session.add(bula)
    await db_session.commit()
    await db_session.refresh(bula)
    return bula


async def create_system_bula(
    db_session: AsyncSession,
    *,
    owner_id: int,
    state: SystemBulaPublicationState,
    has_matching_checksum: bool = True,
) -> Bula:
    object_address = f"stored_objects/{uuid4()}"
    publication_checksum = "a" * 64
    stored_object = StoredObject(
        object_address=object_address,
        original_filename="system.pdf",
        content_type="application/pdf",
        content_size_bytes=1024,
        sha256_checksum=(publication_checksum if has_matching_checksum else "b" * 64),
        data=b"%PDF-test",
    )
    bula = Bula(
        user_id=owner_id,
        drug_name="Dipirona System",
        manufacturer="Example Pharma",
        file_address=object_address,
        status=BulaStatus.READY,
        corpus=BulaCorpus.SYSTEM,
    )
    db_session.add_all([stored_object, bula])
    await db_session.flush()
    now = datetime.now(UTC)
    db_session.add(
        SystemBulaPublication(
            bula_id=bula.id,
            state=state,
            target_id="dipirona-system",
            active_ingredient="dipirona monoidratada",
            product_name="Dipirona System",
            strength="500 mg",
            pharmaceutical_form="comprimido",
            presentation="caixa com 10 comprimidos",
            audience="patient",
            manufacturer="Example Pharma",
            company_tax_id="00000000000100",
            anvisa_product_id=10,
            registration_number="123456789",
            process_number="process-1",
            expedition_number="987654",
            transaction_number="transaction-1",
            source_record_id="111",
            canonical_source_url="https://consultas.anvisa.gov.br/documento.pdf",
            source_published_at=now,
            source_updated_at=now,
            search_query="Dipirona",
            downloader_version="2.0",
            downloaded_at=now,
            filename="system.pdf",
            sha256_checksum=publication_checksum,
            content_size_bytes=1024,
            reviewed_by_name="Reviewer",
            reviewed_at=now,
            published_by_name="Administrator",
            published_at=now,
        )
    )
    await db_session.commit()
    await db_session.refresh(bula)
    return bula


class FakeRAGChainFactory:
    def __init__(
        self,
        *,
        response_text: str = "Resposta com citacao [Posologia].",
    ) -> None:
        self.response_text = response_text
        self.built_bula_ids: list[str] = []

    def build_dense_chain(self, *, bula_id: str) -> RunnableLambda:
        self.built_bula_ids.append(bula_id)
        return RunnableLambda(
            lambda inputs: {
                "answer": self.response_text,
                "source_chunks": [
                    {
                        "section_title": "Posologia",
                        "chunk_text": "Dose usual: 1 comprimido.",
                        "relevance_score": 0.95,
                    }
                ],
            }
        )


def override_rag_chain_factory(
    response_text: str = "Resposta com citacao [Posologia].",
) -> FakeRAGChainFactory:
    fake_factory = FakeRAGChainFactory(response_text=response_text)
    app.dependency_overrides[get_rag_chain_factory] = lambda: fake_factory
    return fake_factory


def build_failing_rag_chain_factory() -> FakeRAGChainFactory:
    class FailingRAGChainFactory(FakeRAGChainFactory):
        def build_dense_chain(self, *, bula_id: str) -> RunnableLambda:
            self.built_bula_ids.append(bula_id)

            async def fail_chain(inputs: dict[str, str]) -> dict[str, object]:
                _ = inputs
                raise RuntimeError("LLM unavailable")

            return RunnableLambda(fail_chain)

    fake_factory = FailingRAGChainFactory()
    app.dependency_overrides[get_rag_chain_factory] = lambda: fake_factory
    return fake_factory


@pytest.mark.anyio
async def test_direct_ask_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/chat/direct-ask",
        json={"question": "Posso tomar este medicamento?"},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_direct_ask_returns_501_until_rag_is_available(
    client: AsyncClient,
) -> None:
    access_token = await get_access_token(client)

    response = await client.post(
        "/api/v1/chat/direct-ask",
        json={"question": "Posso tomar este medicamento?"},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 501
    assert response.json()["detail"] == (
        "RAG chat is not yet available on this endpoint. "
        "Use /api/v1/chat/sessions/{bula_id}/ask."
    )


@pytest.mark.anyio
async def test_ask_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/chat/sessions/11111111-1111-1111-1111-111111111111/ask",
        json={"question": "Como devo tomar?"},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_endpoint_creates_session_first_message(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    bula = await create_ready_bula(db_session, user_id=user.id)
    override_rag_chain_factory()

    response = await client.post(
        f"/api/v1/chat/sessions/{bula.id}/ask",
        json={"question": "Como devo tomar este medicamento?"},
        headers=build_auth_headers(access_token),
    )

    response_body = response.json()
    assert response.status_code == 200, response_body
    assert response_body["answer"] == "Resposta com citacao [Posologia]."
    assert response_body["session_id"]


@pytest.mark.anyio
async def test_endpoint_persists_both_messages(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    bula = await create_ready_bula(db_session, user_id=user.id)
    override_rag_chain_factory()

    response = await client.post(
        f"/api/v1/chat/sessions/{bula.id}/ask",
        json={"question": "Qual e a dose?"},
        headers=build_auth_headers(access_token),
    )

    response_body = response.json()
    chat_repo = ChatRepository(db=db_session)
    messages = await chat_repo.get_session_history(
        session_id=UUID(response_body["session_id"])
    )

    assert response.status_code == 200, response_body
    assert len(messages) == 2
    assert [message.role for message in messages] == [
        ChatRole.USER,
        ChatRole.ASSISTANT,
    ]
    assert [message.retrieval_mode for message in messages] == [
        RetrievalMode.DENSE,
        RetrievalMode.DENSE,
    ]
    assert messages[0].content == "Qual e a dose?"
    assert messages[1].content == "Resposta com citacao [Posologia]."


@pytest.mark.anyio
async def test_endpoint_returns_source_chunks(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    bula = await create_ready_bula(db_session, user_id=user.id)
    override_rag_chain_factory()

    response = await client.post(
        f"/api/v1/chat/sessions/{bula.id}/ask",
        json={"question": "Qual e a dose?"},
        headers=build_auth_headers(access_token),
    )

    response_body = response.json()
    assert response.status_code == 200, response_body
    assert response_body["source_chunks"] == [
        {
            "section_title": "Posologia",
            "chunk_text": "Dose usual: 1 comprimido.",
            "relevance_score": 0.95,
        }
    ]


@pytest.mark.anyio
async def test_endpoint_404_missing_bula(client: AsyncClient) -> None:
    access_token = await get_access_token(client)
    fake_factory = override_rag_chain_factory()

    response = await client.post(
        "/api/v1/chat/sessions/11111111-1111-1111-1111-111111111111/ask",
        json={"question": "Qual e a dose?"},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 404
    assert fake_factory.built_bula_ids == []


@pytest.mark.anyio
async def test_endpoint_404_uningested_bula(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    bula = await create_ready_bula(
        db_session, user_id=user.id, status=BulaStatus.PENDING
    )
    fake_factory = override_rag_chain_factory()

    response = await client.post(
        f"/api/v1/chat/sessions/{bula.id}/ask",
        json={"question": "Qual e a dose?"},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 404
    assert fake_factory.built_bula_ids == []


@pytest.mark.anyio
async def test_endpoint_returns_501_for_future_retrieval_modes(
    client: AsyncClient,
) -> None:
    access_token = await get_access_token(client)
    fake_factory = override_rag_chain_factory()

    response = await client.post(
        "/api/v1/chat/sessions/11111111-1111-1111-1111-111111111111/ask",
        json={"question": "Qual e a dose?", "retrieval_mode": "bm25"},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 501
    assert fake_factory.built_bula_ids == []


@pytest.mark.anyio
async def test_endpoint_does_not_persist_when_chain_fails(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    bula = await create_ready_bula(db_session, user_id=user.id)
    fake_factory = build_failing_rag_chain_factory()

    with pytest.raises(RuntimeError, match="LLM unavailable"):
        await client.post(
            f"/api/v1/chat/sessions/{bula.id}/ask",
            json={"question": "Qual e a dose?"},
            headers=build_auth_headers(access_token),
        )

    session_count = await db_session.scalar(
        select(func.count()).select_from(ChatSession)
    )
    message_count = await db_session.scalar(
        select(func.count()).select_from(ChatMessage)
    )

    assert session_count == 0
    assert message_count == 0
    assert fake_factory.built_bula_ids == [str(bula.id)]


@pytest.mark.anyio
async def test_ordinary_user_can_query_published_ready_system_bula(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client)
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "System Owner",
            "email": "system-owner@bulaai.com",
            "password": "Secret123!",
        },
    )
    owner = await get_user_by_email(
        db_session,
        email="system-owner@bulaai.com",
    )
    bula = await create_system_bula(
        db_session,
        owner_id=owner.id,
        state=SystemBulaPublicationState.PUBLISHED,
    )
    fake_factory = override_rag_chain_factory()

    response = await client.post(
        f"/api/v1/chat/sessions/{bula.id}/ask",
        json={"question": "Qual e a dose?"},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 200, response.json()
    assert fake_factory.built_bula_ids == [str(bula.id)]


@pytest.mark.anyio
async def test_user_cannot_query_another_users_private_bula(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client)
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Private Owner",
            "email": "private-owner@bulaai.com",
            "password": "Secret123!",
        },
    )
    owner = await get_user_by_email(
        db_session,
        email="private-owner@bulaai.com",
    )
    bula = await create_ready_bula(db_session, user_id=owner.id)
    fake_factory = override_rag_chain_factory()

    response = await client.post(
        f"/api/v1/chat/sessions/{bula.id}/ask",
        json={"question": "Qual e a dose?"},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 404
    assert fake_factory.built_bula_ids == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("publication_state", "has_matching_checksum"),
    [
        (SystemBulaPublicationState.STAGED, True),
        (SystemBulaPublicationState.VETTED, True),
        (SystemBulaPublicationState.WITHDRAWN, True),
        (SystemBulaPublicationState.REJECTED, True),
        (SystemBulaPublicationState.PUBLISHED, False),
    ],
)
async def test_ordinary_user_cannot_query_unpublished_or_changed_system_bula(
    client: AsyncClient,
    db_session: AsyncSession,
    publication_state: SystemBulaPublicationState,
    has_matching_checksum: bool,
) -> None:
    access_token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    bula = await create_system_bula(
        db_session,
        owner_id=user.id,
        state=publication_state,
        has_matching_checksum=has_matching_checksum,
    )
    fake_factory = override_rag_chain_factory()

    response = await client.post(
        f"/api/v1/chat/sessions/{bula.id}/ask",
        json={"question": "Qual e a dose?"},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 404
    assert fake_factory.built_bula_ids == []
