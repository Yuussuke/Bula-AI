"""Navigation relevance, bounded paging and private message search."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bulas.models import SystemBulaPublicationState
from app.modules.chat.models import ChatMessage, ChatRole, ChatScope
from tests.integration.bulas.test_public_catalog import create_shared_bula
from tests.integration.bulas.test_system_catalog import (
    auth_headers,
    get_access_token,
    create_system_bula,
    catalog_search_functions as catalog_search_functions,
)
from tests.integration.chat.test_session_management import create_conversation


@pytest.mark.anyio
async def test_search_pages_preserve_relevance_privacy_and_latest_user_message(
    client: AsyncClient,
    db_session: AsyncSession,
    catalog_search_functions: None,
) -> None:
    token = await get_access_token(client, email="workspace-owner@example.com")
    await get_access_token(client, email="workspace-other@example.com")
    title = await create_conversation(db_session, user_id=1, scope=ChatScope.CROSS_BULA)
    title.title = "Conversa sobre testes"
    prefix_drug = await create_shared_bula(db_session, name="Testemed")
    contains_drug = await create_shared_bula(db_session, name="Atestado")
    contains_title = await create_conversation(
        db_session, user_id=1, scope=ChatScope.CROSS_BULA
    )
    contains_title.title = "Atestado da conversa"
    message_chat = await create_conversation(
        db_session, user_id=1, scope=ChatScope.CROSS_BULA
    )
    message_chat.title = "Outra conversa"
    older = ChatMessage(
        session_id=message_chat.id,
        role=ChatRole.USER,
        content="Primeiro teste",
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    latest = ChatMessage(
        session_id=message_chat.id,
        role=ChatRole.USER,
        content="Contexto inicial. Estou testando a busca.",
    )
    db_session.add_all([older, latest])
    foreign = await create_conversation(
        db_session, user_id=2, scope=ChatScope.CROSS_BULA
    )
    foreign.title = "Teste de outra pessoa"
    db_session.add(
        ChatMessage(session_id=foreign.id, role=ChatRole.USER, content="Teste privado")
    )
    assistant_only = await create_conversation(
        db_session, user_id=1, scope=ChatScope.CROSS_BULA
    )
    db_session.add(
        ChatMessage(
            session_id=assistant_only.id,
            role=ChatRole.ASSISTANT,
            content="Teste escrito pelo assistente",
        )
    )
    # Prefix matches win over a substring title in the same chat and appear only once.
    message_chat.title = "Atestado e contexto"
    await create_shared_bula(
        db_session, name="Teste retirado", review_status="withdrawn"
    )
    await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Teste não publicado",
        state=SystemBulaPublicationState.STAGED,
    )
    await db_session.commit()
    items = []
    cursor = None
    for _ in range(5):
        params = {"query": " TÉS ", "limit": 2}
        if cursor:
            params["cursor"] = cursor
        response = await client.get(
            "/api/v1/chat/search", params=params, headers=auth_headers(token)
        )
        assert response.status_code == 200, response.text
        page = response.json()
        assert len(page["items"]) <= 2
        items.extend(page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert cursor is None
    assert [
        (item["kind"], item.get("session", item.get("medication"))["id"])
        for item in items
    ] == [
        ("chat", str(title.id)),
        ("medication", str(prefix_drug.id)),
        ("chat", str(message_chat.id)),
        ("medication", str(contains_drug.id)),
        ("chat", str(contains_title.id)),
    ]
    assert items[2]["message_id"] == str(latest.id)
    assert "testando" in items[2]["excerpt"]
    assert items[2]["session"]["messages"] == []
    for kind, expected in [
        ("chats", ["chat"] * 3),
        ("medications", ["medication"] * 2),
    ]:
        page = await client.get(
            "/api/v1/chat/search",
            params={"query": "tes", "kind": kind},
            headers=auth_headers(token),
        )
        assert [item["kind"] for item in page.json()["items"]] == expected


@pytest.mark.anyio
async def test_search_treats_metacharacters_literally_and_requires_authentication(
    client: AsyncClient,
    db_session: AsyncSession,
    catalog_search_functions: None,
) -> None:
    token = await get_access_token(client, email="literal-search@example.com")
    literal = await create_conversation(
        db_session, user_id=1, scope=ChatScope.CROSS_BULA
    )
    literal.title = "Dúvida sobre .* literal"
    await create_conversation(db_session, user_id=1, scope=ChatScope.CROSS_BULA)
    await db_session.commit()
    response = await client.get(
        "/api/v1/chat/search", params={"query": ".*"}, headers=auth_headers(token)
    )
    assert response.status_code == 200, response.text
    assert [item["session"]["id"] for item in response.json()["items"]] == [
        str(literal.id)
    ]
    unauthenticated = await client.get("/api/v1/chat/search", params={"query": "tes"})
    assert unauthenticated.status_code == 401
