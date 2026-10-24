"""General-chat contracts with real persistence and synthetic providers only."""

from uuid import UUID

import pytest
from httpx import AsyncClient
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableLambda
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.modules.bulas.models import (
    BulaCorpus,
    BulaStatus,
    SystemBulaPublication,
    SystemBulaPublicationState,
)
from app.modules.bulas.repository import BulaRepository
from app.modules.chat.models import ChatMessage, ChatSession, ChatScope
from app.modules.rag.bm25_index import PostgreSQLBM25Index
from app.modules.rag.chain import RAGChainFactory
from app.modules.rag.dependencies import get_rag_chain_factory
from app.modules.rag.models import ChunkMetadata
from app.modules.rag.repository import ChunkMetadataRepository
from app.modules.rag.retrieval_mode import RetrievalMode
from app.modules.rag.retriever_factory import RetrieverStrategyFactory
from tests.integration.chat.test_chat import (
    TEST_USER,
    build_auth_headers,
    create_ready_bula,
    create_system_bula,
    get_access_token,
    get_user_by_email,
)


class SourceRetriever(BaseRetriever):
    documents: list[Document]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return self.documents


def install_factory(
    db: AsyncSession,
    documents: list[Document],
    responses: list[str],
    observed_scopes: list[tuple[UUID, ...]],
) -> None:
    def build(
        *,
        bula_id: UUID | None,
        corpus: tuple[BulaCorpus, ...] | None,
        k: int,
        allowed_bula_ids: tuple[UUID, ...] | None = None,
    ) -> BaseRetriever:
        assert bula_id is None
        assert corpus == (BulaCorpus.SYSTEM,)
        assert allowed_bula_ids is not None
        observed_scopes.append(allowed_bula_ids)
        return SourceRetriever(documents=documents[:k])

    factory = RAGChainFactory(
        retriever_factory=RetrieverStrategyFactory(
            builders={mode: build for mode in RetrievalMode}
        ),
        llm_builder=lambda: FakeListChatModel(responses=responses),
        source_index=PostgreSQLBM25Index(ChunkMetadataRepository(db)),
    )
    app.dependency_overrides[get_rag_chain_factory] = lambda: factory


async def add_chunk(
    db: AsyncSession, bula_id: UUID, text: str, suffix: str = "a"
) -> Document:
    chunk_id = f"{bula_id}:{suffix}"
    db.add(
        ChunkMetadata(
            chunk_id=chunk_id,
            doc_id=str(bula_id),
            bula_id=bula_id,
            corpus="system",
            drug_name="Produto",
            section_title="Advertências",
            chunk_text=text,
            search_text=text,
        )
    )
    await db.commit()
    return Document(
        page_content=text,
        metadata={
            "chunk_id": chunk_id,
            "bula_id": str(bula_id),
            "corpus": "system",
            "section_title": "Advertências",
            "score": 0.5,
        },
    )


@pytest.mark.anyio
@pytest.mark.parametrize("mode", list(RetrievalMode))
async def test_cross_bula_keeps_authorized_sources_and_history(
    client: AsyncClient, db_session: AsyncSession, mode: RetrievalMode
) -> None:
    token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    first = await create_system_bula(
        db_session, owner_id=user.id, state=SystemBulaPublicationState.PUBLISHED
    )
    second = await create_system_bula(
        db_session, owner_id=user.id, state=SystemBulaPublicationState.PUBLISHED
    )
    second.drug_name = "Outro produto"
    await db_session.commit()
    for state in (
        SystemBulaPublicationState.STAGED,
        SystemBulaPublicationState.VETTED,
        SystemBulaPublicationState.WITHDRAWN,
        SystemBulaPublicationState.REJECTED,
    ):
        await create_system_bula(db_session, owner_id=user.id, state=state)
    await create_system_bula(
        db_session,
        owner_id=user.id,
        state=SystemBulaPublicationState.PUBLISHED,
        has_matching_checksum=False,
    )
    shared = await create_system_bula(
        db_session, owner_id=user.id, state=SystemBulaPublicationState.PUBLISHED
    )
    shared.corpus = BulaCorpus.SHARED
    processing = await create_system_bula(
        db_session, owner_id=user.id, state=SystemBulaPublicationState.PUBLISHED
    )
    processing.status = BulaStatus.PROCESSING
    await create_ready_bula(db_session, user_id=user.id)
    documents = [
        await add_chunk(db_session, first.id, "Não utilize com a substância X."),
        await add_chunk(
            db_session, second.id, "Converse com o médico sobre a substância X."
        ),
    ]
    scopes: list[tuple[UUID, ...]] = []
    repository = BulaRepository(db_session)
    assert await repository.list_queryable_system_bulas(bula_ids=[]) == []
    selected_documents = await repository.list_queryable_system_bulas(
        bula_ids=[first.id, shared.id]
    )
    assert [bula.id for bula in selected_documents] == [first.id]
    install_factory(
        db_session,
        documents,
        [
            '{"unit_ids":["E1","E2"],"limitation":null}',
            "Cada medicamento tem uma orientação própria. [1,2]",
        ],
        scopes,
    )
    response = await client.post(
        "/api/v1/chat/ask",
        json={"question": "O que dizem sobre X?", "mode": mode.value},
        headers=build_auth_headers(token),
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert set(scopes[0]) == {first.id, second.id}
    assert [source["drug_name"] for source in result["source_bulas"]] == [
        first.drug_name,
        second.drug_name,
    ]
    assert [source["chunk_id"] for source in result["source_chunks"]] == [
        document.metadata["chunk_id"] for document in documents
    ]
    assert all(
        source["source_url"].startswith("https://consultas.anvisa.gov.br/")
        for source in result["source_chunks"]
    )
    session_id = result["session_id"]
    continuation = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"question": "E quanto ao outro?", "mode": mode.value},
        headers=build_auth_headers(token),
    )
    assert continuation.status_code == 200, continuation.text
    history = await client.get(
        f"/api/v1/chat/sessions/{session_id}", headers=build_auth_headers(token)
    )
    assert history.json()["scope"] == "cross_bula"
    assert history.json()["bula_id"] is None
    assert len(history.json()["messages"]) == 4
    assert history.json()["messages"][1]["source_chunks"] == result["source_chunks"]
    assert history.json()["messages"][1]["source_bulas"] == result["source_bulas"]
    listed = await client.get(
        "/api/v1/chat/sessions?scope=cross_bula&limit=1",
        headers=build_auth_headers(token),
    )
    assert [item["id"] for item in listed.json()] == [session_id]
    scoped = await client.get(
        "/api/v1/chat/sessions?scope=bula&limit=1", headers=build_auth_headers(token)
    )
    assert scoped.json() == []


@pytest.mark.anyio
async def test_empty_public_corpus_abstains_without_provider_calls(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token = await get_access_token(client)
    scopes: list[tuple[UUID, ...]] = []
    install_factory(db_session, [], [], scopes)
    response = await client.post(
        "/api/v1/chat/ask",
        json={"question": "Qual medicamento usar?"},
        headers=build_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["source_chunks"] == []
    assert response.json()["source_bulas"] == []
    assert "Não encontrei" in response.json()["answer"]


@pytest.mark.anyio
@pytest.mark.parametrize("defect", ["text", "identity", "missing", "section", "corpus"])
async def test_stale_or_misattributed_index_never_reaches_selector(
    client: AsyncClient, db_session: AsyncSession, defect: str
) -> None:
    token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    bula = await create_system_bula(
        db_session, owner_id=user.id, state=SystemBulaPublicationState.PUBLISHED
    )
    document = await add_chunk(db_session, bula.id, "Informação original.")
    if defect == "text":
        document.page_content = "Afirmação adulterada."
    elif defect == "identity":
        document.metadata["bula_id"] = str(UUID(int=999))
    elif defect == "section":
        document.metadata["section_title"] = "Posologia"
    elif defect == "corpus":
        document.metadata["corpus"] = "private"
    else:
        document.metadata["chunk_id"] = "missing"
    install_factory(db_session, [document], [], [])
    response = await client.post(
        "/api/v1/chat/ask",
        json={"question": "O que informa?"},
        headers=build_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["source_chunks"] == []


@pytest.mark.anyio
async def test_withdrawal_during_generation_does_not_persist_answer(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    bula = await create_system_bula(
        db_session, owner_id=user.id, state=SystemBulaPublicationState.PUBLISHED
    )

    class WithdrawingFactory:
        def build_cross_bula_chain(
            self, *, mode: RetrievalMode, sources: dict[UUID, dict[str, str]]
        ) -> RunnableLambda:
            async def withdraw(inputs: dict[str, object]) -> dict[str, object]:
                publication = await db_session.get(SystemBulaPublication, bula.id)
                assert publication is not None
                publication.state = SystemBulaPublicationState.WITHDRAWN
                await db_session.commit()
                source = {
                    key: value
                    for key, value in sources[bula.id].items()
                    if key != "content_sha256"
                }
                return {
                    "answer": "Resposta [1]",
                    "source_chunks": [
                        {
                            **source,
                            "chunk_id": "a",
                            "bula_id": str(bula.id),
                            "section_title": "Informações",
                            "chunk_text": "Texto.",
                            "relevance_score": 1.0,
                        }
                    ],
                }

            return RunnableLambda(withdraw)

    app.dependency_overrides[get_rag_chain_factory] = WithdrawingFactory
    response = await client.post(
        "/api/v1/chat/ask",
        json={"question": "Dúvida"},
        headers=build_auth_headers(token),
    )
    assert response.status_code == 409
    assert await db_session.scalar(select(func.count()).select_from(ChatSession)) == 0
    assert await db_session.scalar(select(func.count()).select_from(ChatMessage)) == 0


@pytest.mark.anyio
async def test_general_chat_requires_auth_and_rejects_client_scope(
    client: AsyncClient,
) -> None:
    assert (
        await client.post("/api/v1/chat/ask", json={"question": "Dúvida"})
    ).status_code == 401
    token = await get_access_token(client)
    for extra in ({"corpus": ["private"]}, {"bula_id": str(UUID(int=1))}):
        response = await client.post(
            "/api/v1/chat/ask",
            json={"question": "Dúvida", **extra},
            headers=build_auth_headers(token),
        )
        assert response.status_code == 422

    response = await client.get(
        "/api/v1/chat/sessions?scope=cross_bula&bula_id=11111111-1111-4111-8111-111111111111",
        headers=build_auth_headers(token),
    )
    assert response.status_code == 422
    assert "Conversas gerais" in response.json()["detail"]


@pytest.mark.anyio
async def test_orphan_session_stays_scoped_and_cannot_be_continued(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    session = ChatSession(user_id=user.id, title="Bula excluída", bula_id=None)
    db_session.add(session)
    await db_session.commit()
    response = await client.post(
        f"/api/v1/chat/sessions/{session.id}/messages",
        json={"question": "E agora?"},
        headers=build_auth_headers(token),
    )
    assert response.status_code == 404
    assert session.scope == ChatScope.BULA.value


@pytest.mark.anyio
async def test_other_user_cannot_read_continue_or_list_general_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token = await get_access_token(client)
    response = await client.post(
        "/api/v1/chat/ask",
        json={"question": "Dúvida sem fontes"},
        headers=build_auth_headers(token),
    )
    session_id = response.json()["session_id"]
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Another Test User",
            "email": "another-cross@example.com",
            "password": "Secret123!",
        },
    )
    other_token = registration.json()["token"]["access_token"]
    assert (
        await client.get(
            f"/api/v1/chat/sessions/{session_id}",
            headers=build_auth_headers(other_token),
        )
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"question": "Dúvida"},
            headers=build_auth_headers(other_token),
        )
    ).status_code == 404
    listed = await client.get(
        "/api/v1/chat/sessions?scope=cross_bula",
        headers=build_auth_headers(other_token),
    )
    assert listed.json() == []


@pytest.mark.anyio
async def test_empty_selection_and_provider_failure_are_not_interchangeable(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token = await get_access_token(client)
    user = await get_user_by_email(db_session, email=TEST_USER["email"])
    bula = await create_system_bula(
        db_session, owner_id=user.id, state=SystemBulaPublicationState.PUBLISHED
    )
    document = await add_chunk(db_session, bula.id, "Informação relacionada.")
    install_factory(db_session, [document], ['{"unit_ids":[],"limitation":null}'], [])
    response = await client.post(
        "/api/v1/chat/ask",
        json={"question": "Dúvida sem suporte"},
        headers=build_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["source_chunks"] == []
    assert "não trazem informação suficiente" in response.json()["answer"]
    install_factory(
        db_session,
        [document],
        ['{"unit_ids":["E1"],"limitation":null}', "Resposta sem citação."],
        [],
    )
    with pytest.raises(RuntimeError, match="missing_source_citation"):
        await client.post(
            "/api/v1/chat/ask",
            json={"question": "Outra dúvida"},
            headers=build_auth_headers(token),
        )
    assert await db_session.scalar(select(func.count()).select_from(ChatSession)) == 1
    assert await db_session.scalar(select(func.count()).select_from(ChatMessage)) == 2
