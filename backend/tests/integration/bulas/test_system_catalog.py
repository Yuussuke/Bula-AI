from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
