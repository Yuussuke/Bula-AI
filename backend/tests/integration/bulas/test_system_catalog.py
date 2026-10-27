from datetime import UTC, datetime
from uuid import uuid4
import unicodedata

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Connection

from app.modules.bulas.models import (
    Bula,
    BulaCorpus,
    BulaStatus,
    SystemBulaPublication,
    SystemBulaPublicationState,
)
from app.modules.storage.models import StoredObject


async def get_access_token(client: AsyncClient, *, email: str) -> str:
    user = {
        "full_name": "Catalog User",
        "email": email,
        "password": "Secret123!",
    }
    await client.post("/api/v1/auth/register", json=user)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": user["password"]},
    )
    return str(response.json()["token"]["access_token"])


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def create_system_bula(
    db_session: AsyncSession,
    *,
    owner_id: int,
    product_name: str,
    state: SystemBulaPublicationState,
    status: BulaStatus = BulaStatus.READY,
    has_matching_checksum: bool = True,
) -> Bula:
    object_address = f"stored_objects/{uuid4()}"
    publication_checksum = "a" * 64
    stored_checksum = publication_checksum if has_matching_checksum else "b" * 64
    stored_object = StoredObject(
        object_address=object_address,
        original_filename="leaflet.pdf",
        content_type="application/pdf",
        content_size_bytes=1024,
        sha256_checksum=stored_checksum,
        data=b"%PDF-test",
    )
    bula = Bula(
        user_id=owner_id,
        drug_name=product_name,
        manufacturer="Example Pharma",
        file_address=object_address,
        status=status,
        corpus=BulaCorpus.SYSTEM,
    )
    db_session.add_all([stored_object, bula])
    await db_session.flush()

    now = datetime.now(UTC)
    publication = SystemBulaPublication(
        bula_id=bula.id,
        state=state,
        target_id=product_name.lower().replace(" ", "-"),
        active_ingredient="dipirona monoidratada",
        product_name=product_name,
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
        source_record_id=str(abs(hash(product_name))),
        canonical_source_url="https://consultas.anvisa.gov.br/documento.pdf",
        source_published_at=now,
        source_updated_at=now,
        search_query="Dipirona",
        downloader_version="2.0",
        downloaded_at=now,
        filename="leaflet.pdf",
        sha256_checksum=publication_checksum,
        content_size_bytes=1024,
        reviewed_by_name="Clinical Reviewer",
        reviewed_at=now,
        published_by_name="Administrator",
        published_at=now,
    )
    db_session.add(publication)
    await db_session.commit()
    await db_session.refresh(bula)
    return bula


@pytest.mark.anyio
async def test_verified_publication_preserves_unknown_metadata_and_full_strength(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client, email="import-catalog@example.com")
    bula = await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Verified Import",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    publication = await db_session.get(SystemBulaPublication, bula.id)
    assert publication is not None
    publication.manufacturer = None
    publication.expedition_number = None
    publication.transaction_number = None
    publication.source_record_id = None
    publication.source_published_at = None
    publication.source_updated_at = None
    publication.search_query = None
    publication.downloader_version = None
    publication.downloaded_at = None
    publication.reviewed_by_name = None
    publication.reviewed_at = None
    publication.strength = "; ".join(
        f"Presentation {index}: {index} mg" for index in range(25)
    )
    await db_session.commit()

    response = await client.get(
        "/api/v1/bulas/system", headers=auth_headers(access_token)
    )

    assert response.status_code == 200
    item = response.json()[0]
    assert item["strength"] == publication.strength
    for key in (
        "manufacturer",
        "expedition_number",
        "transaction_number",
        "source_record_id",
        "source_published_at",
        "reviewed_by",
        "reviewed_at",
    ):
        assert item[key] is None


@pytest.mark.anyio
async def test_catalog_lists_only_published_ready_integrity_valid_system_bulas(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client, email="catalog@example.com")
    owner_id = 1
    published = await create_system_bula(
        db_session,
        owner_id=owner_id,
        product_name="Dipirona Published",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    await create_system_bula(
        db_session,
        owner_id=owner_id,
        product_name="Dipirona Staged",
        state=SystemBulaPublicationState.STAGED,
    )
    await create_system_bula(
        db_session,
        owner_id=owner_id,
        product_name="Dipirona Rejected",
        state=SystemBulaPublicationState.REJECTED,
    )
    await create_system_bula(
        db_session,
        owner_id=owner_id,
        product_name="Dipirona Pending",
        state=SystemBulaPublicationState.PUBLISHED,
        status=BulaStatus.PENDING,
    )
    await create_system_bula(
        db_session,
        owner_id=owner_id,
        product_name="Dipirona Failed",
        state=SystemBulaPublicationState.PUBLISHED,
        status=BulaStatus.ERROR,
    )
    await create_system_bula(
        db_session,
        owner_id=owner_id,
        product_name="Dipirona Changed",
        state=SystemBulaPublicationState.PUBLISHED,
        has_matching_checksum=False,
    )

    response = await client.get(
        "/api/v1/bulas/system",
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(published.id),
            "target_id": "dipirona-published",
            "product_name": "Dipirona Published",
            "active_ingredient": "dipirona monoidratada",
            "strength": "500 mg",
            "pharmaceutical_form": "comprimido",
            "presentation": "caixa com 10 comprimidos",
            "audience": "patient",
            "manufacturer": "Example Pharma",
            "company_tax_id": "00000000000100",
            "anvisa_product_id": 10,
            "registration_number": "123456789",
            "process_number": "process-1",
            "expedition_number": "987654",
            "transaction_number": "transaction-1",
            "source_record_id": str(abs(hash("Dipirona Published"))),
            "canonical_source_url": "https://consultas.anvisa.gov.br/documento.pdf",
            "source_published_at": response.json()[0]["source_published_at"],
            "source_updated_at": response.json()[0]["source_updated_at"],
            "sha256_checksum": "a" * 64,
            "content_size_bytes": 1024,
            "ingestion_status": "ready",
            "publication_state": "published",
            "reviewed_by": "Clinical Reviewer",
            "reviewed_at": response.json()[0]["reviewed_at"],
            "published_at": response.json()[0]["published_at"],
        }
    ]


@pytest.mark.anyio
async def test_system_detail_returns_published_ready_integrity_valid_document(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client, email="published-detail@example.com")
    published = await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Published Detail",
        state=SystemBulaPublicationState.PUBLISHED,
    )

    response = await client.get(
        f"/api/v1/bulas/system/{published.id}",
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(published.id)
    assert response.json()["publication_state"] == "published"
    assert response.json()["ingestion_status"] == "ready"
    assert response.json()["source_record_id"] == str(abs(hash("Published Detail")))


@pytest.mark.anyio
async def test_queryable_detail_normalizes_published_system_bula_for_chat(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client, email="queryable-system@example.com")
    published = await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Published Detail",
        state=SystemBulaPublicationState.PUBLISHED,
    )

    response = await client.get(
        f"/api/v1/bulas/{published.id}",
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(published.id),
        "product_name": "Published Detail",
        "alias": None,
        "active_ingredient": "dipirona monoidratada",
        "strength": "500 mg",
        "manufacturer": "Example Pharma",
        "corpus": "system",
        "ingestion_status": "ready",
    }


@pytest.mark.anyio
async def test_system_detail_hides_unpublished_document(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    access_token = await get_access_token(client, email="detail@example.com")
    staged = await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Hidden Bula",
        state=SystemBulaPublicationState.STAGED,
    )

    response = await client.get(
        f"/api/v1/bulas/system/{staged.id}",
        headers=auth_headers(access_token),
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_system_catalog_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/bulas/system")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_personal_list_includes_only_owned_private_bulas(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token = await get_access_token(client, email="personal-catalog@example.com")
    await get_access_token(client, email="other-catalog@example.com")
    await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Public source owned by user",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    own_private = Bula(
        user_id=1,
        drug_name="My private document",
        corpus=BulaCorpus.PRIVATE,
        status=BulaStatus.PENDING,
    )
    other_private = Bula(
        user_id=2,
        drug_name="Another user's document",
        corpus=BulaCorpus.PRIVATE,
        status=BulaStatus.READY,
    )
    db_session.add_all([own_private, other_private])
    await db_session.commit()

    response = await client.get("/api/v1/bulas/", headers=auth_headers(token))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(own_private.id)]
    assert response.json()[0]["status"] == "pending"


@pytest.fixture
async def catalog_search_functions(db_session: AsyncSession) -> None:
    """Provide the existing PostgreSQL unaccent dependency in the SQLite fixture."""

    def unaccent(value: str | None) -> str | None:
        if value is None:
            return None
        return "".join(
            character
            for character in unicodedata.normalize("NFD", value)
            if not unicodedata.combining(character)
        )

    def register(connection: Connection) -> None:
        connection.connection.dbapi_connection.create_function("unaccent", 1, unaccent)

    connection = await db_session.connection()
    await connection.run_sync(register)


@pytest.mark.anyio
async def test_catalog_search_filters_before_pagination_and_counts_only_authorized_sources(
    client: AsyncClient, db_session: AsyncSession, catalog_search_functions: None
) -> None:
    token = await get_access_token(client, email="paged-catalog@example.com")
    for number in range(25):
        await create_system_bula(
            db_session,
            owner_id=1,
            product_name=f"Produto {number:02}",
            state=SystemBulaPublicationState.PUBLISHED,
        )
    private = await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Produto privado",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    private.corpus = BulaCorpus.PRIVATE
    await db_session.commit()
    await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Produto retirado",
        state=SystemBulaPublicationState.WITHDRAWN,
    )
    await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Produto divergente",
        state=SystemBulaPublicationState.PUBLISHED,
        has_matching_checksum=False,
    )

    first = await client.get("/api/v1/bulas/system/search", headers=auth_headers(token))
    second = await client.get(
        "/api/v1/bulas/system/search",
        params={"offset": 20},
        headers=auth_headers(token),
    )
    matched = await client.get(
        "/api/v1/bulas/system/search",
        params={"query": "PRODUTO 24"},
        headers=auth_headers(token),
    )

    assert first.status_code == second.status_code == matched.status_code == 200
    assert first.json()["total"] == second.json()["total"] == 25
    assert len(first.json()["items"]) == 20 and len(second.json()["items"]) == 5
    assert second.json()["offset"] == 20
    assert not {row["id"] for row in first.json()["items"]} & {
        row["id"] for row in second.json()["items"]
    }
    assert matched.json()["total"] == 1
    assert matched.json()["items"][0]["product_name"] == "Produto 24"
    descending = await client.get(
        "/api/v1/bulas/system/search",
        params={"sort": "name_desc", "limit": 1},
        headers=auth_headers(token),
    )
    assert descending.json()["total"] == 25
    assert descending.json()["items"][0]["product_name"] == "Produto 24"
    assert all(
        row["id"] != str(private.id)
        for row in first.json()["items"] + second.json()["items"]
    )


@pytest.mark.anyio
async def test_catalog_search_handles_accents_multiple_fields_literal_wildcards_and_audience(
    client: AsyncClient, db_session: AsyncSession, catalog_search_functions: None
) -> None:
    token = await get_access_token(client, email="accent-catalog@example.com")
    bula = await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Ácido 10%",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    publication = await db_session.get(SystemBulaPublication, bula.id)
    assert publication is not None
    publication.audience = "professional"
    publication.manufacturer = None
    publication.strength = "100 mg"
    await db_session.commit()
    await create_system_bula(
        db_session,
        owner_id=1,
        product_name="Outro produto",
        state=SystemBulaPublicationState.PUBLISHED,
    )
    for query in ("acido 100", "ÁCIDO", "%"):
        response = await client.get(
            "/api/v1/bulas/system/search",
            params={"query": query},
            headers=auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["id"] == str(bula.id)
    response = await client.get(
        "/api/v1/bulas/system/search",
        params={"audience": "patient", "query": "acido"},
        headers=auth_headers(token),
    )
    assert response.json()["total"] == 0 and response.json()["items"] == []
    unauthorized = await client.get("/api/v1/bulas/system/search")
    assert unauthorized.status_code == 401
