"""Personal history management never invokes retrieval or generation."""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bulas.models import PublicCatalogScope
from app.modules.chat.models import ChatSession, ChatMessage, ChatScope
from app.modules.chat.repository import ChatRepository
from app.modules.rag.retrieval_mode import RetrievalMode
from tests.integration.bulas.test_system_catalog import get_access_token, auth_headers


async def create_conversation(
    database: AsyncSession, *, user_id: int, scope: ChatScope
) -> ChatSession:
    session, _, _ = await ChatRepository(database).create_session_with_messages(
        user_id=user_id,
        bula_id=None,
        scope=scope,
        catalog_scope=PublicCatalogScope.SHARED
        if scope == ChatScope.CROSS_BULA
        else PublicCatalogScope.ALL,
        first_question="Original question",
        answer="Original answer",
        retrieval_mode=RetrievalMode.HYBRID,
        source_chunks=[
            {
                "section_title": "Synthetic",
                "chunk_text": "Original evidence",
                "relevance_score": 0.5,
            }
        ],
    )
    return session


@pytest.mark.anyio
@pytest.mark.parametrize("scope", list(ChatScope))
async def test_owner_can_rename_and_delete_without_changing_other_history(
    client: AsyncClient,
    db_session: AsyncSession,
    scope: ChatScope,
) -> None:
    token = await get_access_token(client, email="owner@example.com")
    session = await create_conversation(db_session, user_id=1, scope=scope)
    preserved = await create_conversation(db_session, user_id=1, scope=scope)
    before = (
        await client.get(
            f"/api/v1/chat/sessions/{session.id}", headers=auth_headers(token)
        )
    ).json()
    renamed = await client.patch(
        f"/api/v1/chat/sessions/{session.id}",
        json={"title": "  My new name  "},
        headers=auth_headers(token),
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "My new name"
    after = (
        await client.get(
            f"/api/v1/chat/sessions/{session.id}", headers=auth_headers(token)
        )
    ).json()
    assert after["messages"] == before["messages"]
    assert (
        after["scope"] == before["scope"]
        and after["catalog_scope"] == before["catalog_scope"]
    )
    listing = (
        await client.get("/api/v1/chat/sessions", headers=auth_headers(token))
    ).json()
    assert (
        next(row for row in listing if row["id"] == str(session.id))["title"]
        == "My new name"
    )
    deleted = await client.delete(
        f"/api/v1/chat/sessions/{session.id}", headers=auth_headers(token)
    )
    assert deleted.status_code == 200 and deleted.json()["session_id"] == str(
        session.id
    )
    assert (
        await client.get(
            f"/api/v1/chat/sessions/{session.id}", headers=auth_headers(token)
        )
    ).status_code == 404
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.session_id == session.id)
        )
        == 0
    )
    assert await db_session.get(ChatSession, preserved.id) is not None
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.session_id == preserved.id)
        )
        == 2
    )


@pytest.mark.anyio
async def test_other_users_and_anonymous_clients_cannot_manage_a_conversation(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await get_access_token(client, email="owner@example.com")
    other_token = await get_access_token(client, email="other@example.com")
    session = await create_conversation(
        db_session, user_id=1, scope=ChatScope.CROSS_BULA
    )
    for headers, expected_status in [(auth_headers(other_token), 404), ({}, 401)]:
        renamed = await client.patch(
            f"/api/v1/chat/sessions/{session.id}",
            json={"title": "Forbidden"},
            headers=headers,
        )
        deleted = await client.delete(
            f"/api/v1/chat/sessions/{session.id}", headers=headers
        )
        assert renamed.status_code == deleted.status_code == expected_status
        pinned = await client.patch(
            f"/api/v1/chat/sessions/{session.id}",
            json={"is_pinned": True},
            headers=headers,
        )
        assert pinned.status_code == expected_status
    await db_session.refresh(session)
    assert session.title == "Original question"
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.session_id == session.id)
        )
        == 2
    )


@pytest.mark.anyio
async def test_invalid_rename_cannot_change_title_or_document_boundary(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token = await get_access_token(client, email="owner@example.com")
    session = await create_conversation(
        db_session, user_id=1, scope=ChatScope.CROSS_BULA
    )
    for payload in [
        {},
        {"is_pinned": None},
        {"title": None},
        {"title": " "},
        {"title": "a" * 51},
        {"title": "New", "catalog_scope": "all"},
    ]:
        response = await client.patch(
            f"/api/v1/chat/sessions/{session.id}",
            json=payload,
            headers=auth_headers(token),
        )
        assert response.status_code == 422
    await db_session.refresh(session)
    assert session.title == "Original question" and session.catalog_scope == "shared"


@pytest.mark.anyio
@pytest.mark.parametrize("scope", list(ChatScope))
async def test_pins_persist_and_filter_before_pagination_without_changing_messages(
    client: AsyncClient, db_session: AsyncSession, scope: ChatScope
) -> None:
    token = await get_access_token(client, email="owner@example.com")
    headers = auth_headers(token)
    older = await create_conversation(db_session, user_id=1, scope=scope)
    newer = await create_conversation(db_session, user_id=1, scope=scope)
    original = (
        await client.get(f"/api/v1/chat/sessions/{older.id}", headers=headers)
    ).json()
    for _ in range(2):
        response = await client.patch(
            f"/api/v1/chat/sessions/{older.id}",
            json={"is_pinned": True},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["is_pinned"] is True
    pinned = (
        await client.get(
            "/api/v1/chat/sessions",
            params={
                "is_pinned": True,
                "scope": scope.value,
                "limit": 1,
                "sort": "updated_at",
            },
            headers=headers,
        )
    ).json()
    assert [row["id"] for row in pinned] == [str(older.id)]
    recent = (
        await client.get(
            "/api/v1/chat/sessions",
            params={"is_pinned": False, "scope": scope.value, "limit": 1},
            headers=headers,
        )
    ).json()
    assert [row["id"] for row in recent] == [str(newer.id)]
    reloaded = (
        await client.get(f"/api/v1/chat/sessions/{older.id}", headers=headers)
    ).json()
    for field in ("messages", "title", "scope", "catalog_scope", "updated_at"):
        assert reloaded[field] == original[field]
    assert reloaded["is_pinned"] is True
    unpinned = await client.patch(
        f"/api/v1/chat/sessions/{older.id}", json={"is_pinned": False}, headers=headers
    )
    assert unpinned.json()["is_pinned"] is False
    assert (
        await client.get(
            "/api/v1/chat/sessions", params={"is_pinned": True}, headers=headers
        )
    ).json() == []
