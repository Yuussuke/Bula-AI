"""Public browsing and chat share the same narrowed authorization boundary."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bulas.models import (
    Bula,
    BulaCorpus,
    BulaStatus,
    BulaCurationEvent,
    SharedBulaSubmission,
    SystemBulaPublicationState,
)
from app.modules.storage.models import StoredObject
from app.modules.rag.retrieval_mode import RetrievalMode
from tests.integration.bulas.test_system_catalog import (
    create_system_bula,
    get_access_token,
    auth_headers,
    catalog_search_functions as catalog_search_functions,
)
from tests.integration.chat.test_cross_bula import add_chunk, install_factory


async def create_shared_bula(
    database: AsyncSession,
    *,
    name: str,
    review_status: str = "approved",
    status: BulaStatus = BulaStatus.READY,
    has_approval: bool = True,
    has_matching_checksum: bool = True,
) -> Bula:
    checksum = uuid4().hex * 2
    address = f"synthetic/{uuid4()}"
    bula = Bula(
        user_id=1,
        drug_name=name,
        manufacturer="Shared Pharma",
        file_address=address,
        corpus=BulaCorpus.SHARED,
        status=status,
    )
    database.add_all(
        [
            bula,
            StoredObject(
                object_address=address,
                original_filename="test.pdf",
                content_type="application/pdf",
                content_size_bytes=100,
                sha256_checksum=checksum if has_matching_checksum else "0" * 64,
                data=b"synthetic",
            ),
        ]
    )
    await database.flush()
    database.add(
        SharedBulaSubmission(
            bula_id=bula.id,
            source_url="https://source.example/leaflet.pdf",
            source_description="Synthetic fixture",
            sha256_checksum=checksum,
            content_size_bytes=100,
            review_status=review_status,
            presentation="Oral drops",
            strength="10 mg/mL",
        )
    )
    if has_approval:
        database.add(
            BulaCurationEvent(
                bula_id=bula.id,
                actor_name="Synthetic reviewer",
                action="approved",
                reason="Synthetic fixture",
                version=1,
            )
        )
    await database.commit()
    return bula


@pytest.mark.anyio
async def test_unified_catalog_filters_authorized_documents_before_pagination(
    client: AsyncClient,
    db_session: AsyncSession,
    catalog_search_functions: None,
) -> None:
    token = await get_access_token(client, email="unified@example.com")
    system = await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Zulu",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    shared = await create_shared_bula(db_session, name="Alpha")
    for options in [
        dict(review_status="pending"),
        dict(review_status="withdrawn"),
        dict(review_status="rejected"),
        dict(has_approval=False),
        dict(has_matching_checksum=False),
        dict(status=BulaStatus.PROCESSING),
    ]:
        await create_shared_bula(db_session, name="Excluded", **options)
    private = Bula(
        user_id=1,
        drug_name="Private",
        corpus=BulaCorpus.PRIVATE,
        status=BulaStatus.READY,
    )
    db_session.add(private)
    await db_session.commit()

    for scope, expected in [
        ("all", [shared.id, system.id]),
        ("system", [system.id]),
        ("shared", [shared.id]),
    ]:
        response = await client.get(
            f"/api/v1/bulas/catalog/search?catalog_scope={scope}&limit=1",
            headers=auth_headers(token),
        )
        assert response.status_code == 200, response.text
        page = response.json()
        assert page["total"] == len(expected)
        assert page["items"][0]["id"] == str(expected[0])
    second = await client.get(
        "/api/v1/bulas/catalog/search?limit=1&offset=1", headers=auth_headers(token)
    )
    assert second.json()["items"][0]["id"] == str(system.id)
    shared_item = (
        await client.get(
            "/api/v1/bulas/catalog/search?catalog_scope=shared",
            headers=auth_headers(token),
        )
    ).json()["items"][0]
    assert shared_item["source_url"] == "https://source.example/leaflet.pdf"
    assert (
        shared_item["audience"] is None and shared_item["registration_number"] is None
    )
    assert shared_item["strength"] == "10 mg/mL"
    for scope, query, count in [
        ("shared", "shared pharma 10 mg", 1),
        ("system", "shared", 0),
        ("all", "Alpha", 1),
    ]:
        response = await client.get(
            "/api/v1/bulas/catalog/search",
            params={"catalog_scope": scope, "query": query},
            headers=auth_headers(token),
        )
        assert response.json()["total"] == count
    audience = await client.get(
        "/api/v1/bulas/catalog/search?audience=patient", headers=auth_headers(token)
    )
    assert [item["id"] for item in audience.json()["items"]] == [str(system.id)]


@pytest.mark.anyio
@pytest.mark.parametrize("mode", list(RetrievalMode))
@pytest.mark.parametrize("scope", ["all", "system", "shared"])
async def test_chat_preserves_catalog_boundary_on_creation_continuation_and_history(
    client: AsyncClient,
    db_session: AsyncSession,
    mode: RetrievalMode,
    scope: str,
) -> None:
    token = await get_access_token(client, email="source-chat@example.com")
    system = await create_system_bula(
        db_session,
        owner_id=1,
        product_name="System",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    shared = await create_shared_bula(db_session, name="Shared")
    selected = shared if scope == "shared" else system
    document = await add_chunk(
        db_session, selected.id, "Read the instructions.", corpus=selected.corpus.value
    )
    seen: list[tuple[UUID, ...]] = []
    install_factory(
        db_session,
        [document],
        ['{"unit_ids":["E1"],"limitation":null}', "Read the instructions [1]."],
        seen,
    )
    created = await client.post(
        "/api/v1/chat/ask",
        headers=auth_headers(token),
        json={"question": "How to use?", "mode": mode.value, "catalog_scope": scope},
    )
    assert created.status_code == 200, created.text
    expected = {system.id, shared.id} if scope == "all" else {selected.id}
    assert set(seen[0]) == expected
    session_id = created.json()["session_id"]
    assert created.json()["catalog_scope"] == scope
    continued = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"question": "Repeat?", "mode": mode.value},
    )
    assert continued.status_code == 200, continued.text
    assert set(seen[-1]) == expected
    history = await client.get(
        f"/api/v1/chat/sessions/{session_id}", headers=auth_headers(token)
    )
    assert history.json()["catalog_scope"] == scope
    forbidden_override = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"question": "Widen the sources", "catalog_scope": "all"},
    )
    assert forbidden_override.status_code == 422


@pytest.mark.anyio
async def test_empty_selected_catalog_never_falls_back_to_another_corpus(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token = await get_access_token(client, email="empty-source@example.com")
    await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Available elsewhere",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    seen: list[tuple[UUID, ...]] = []
    install_factory(db_session, [], [], seen)
    response = await client.post(
        "/api/v1/chat/ask",
        headers=auth_headers(token),
        json={"question": "Any information?", "catalog_scope": "shared"},
    )
    assert response.status_code == 200
    assert response.json()["source_chunks"] == [] and seen == []
    invalid = await client.post(
        "/api/v1/chat/ask",
        headers=auth_headers(token),
        json={"question": "Private?", "catalog_scope": "private"},
    )
    assert invalid.status_code == 422


@pytest.mark.anyio
@pytest.mark.parametrize("mode", list(RetrievalMode))
@pytest.mark.parametrize("scope", ["system", "shared"])
async def test_unselected_catalog_cannot_reach_the_model_even_if_returned_by_stale_index(
    client: AsyncClient,
    db_session: AsyncSession,
    mode: RetrievalMode,
    scope: str,
) -> None:
    token = await get_access_token(client, email="stale-catalog@example.com")
    system = await create_system_bula(
        db_session,
        owner_id=1,
        product_name="System",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    shared = await create_shared_bula(db_session, name="Shared")
    forbidden = shared if scope == "system" else system
    stale_document = await add_chunk(
        db_session,
        forbidden.id,
        "Do not expose this source.",
        corpus=forbidden.corpus.value,
    )
    seen: list[tuple[UUID, ...]] = []
    # No synthetic model outputs: attempting selection/generation would fail.
    install_factory(db_session, [stale_document], [], seen)
    response = await client.post(
        "/api/v1/chat/ask",
        headers=auth_headers(token),
        json={"question": "Instructions?", "mode": mode.value, "catalog_scope": scope},
    )
    assert response.status_code == 200, response.text
    assert forbidden.id not in seen[0]
    assert response.json()["source_chunks"] == []
