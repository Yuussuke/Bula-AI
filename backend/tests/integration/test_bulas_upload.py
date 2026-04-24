import uuid

import pytest
from httpx import AsyncClient

from app.main import app
from app.modules.bulas.dependencies import get_bula_service
from app.modules.bulas.schemas import BulaUploadResponse

TEST_USER = {
    "full_name": "Upload Test User",
    "email": "upload-test@bulaai.com",
    "password": "Secret123!",
}


class FakeBulaService:
    async def process_pdf(
        self,
        *,
        user_id: int,
        drug_name: str,
        manufacturer: str | None,
        file,
        filename: str | None = None,
    ) -> BulaUploadResponse:
        _ = user_id
        _ = drug_name
        _ = manufacturer
        _ = file
        return BulaUploadResponse(
            filename=filename or "arquivo_sem_nome.pdf",
            pages=1,
            characters=10,
            chunks=1,
            bula_id=uuid.uuid4(),
        )


async def get_access_token(client: AsyncClient) -> str:
    await client.post("/api/v1/auth/register", json=TEST_USER)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    return str(login_response.json()["token"]["access_token"])


def build_auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.anyio
async def test_upload_valid_pdf_keeps_current_flow(client: AsyncClient):
    access_token = await get_access_token(client)
    app.dependency_overrides[get_bula_service] = lambda: FakeBulaService()

    try:
        response = await client.post(
            "/api/v1/bulas/upload",
            data={"drug_name": "Dipirona", "manufacturer": "Medley"},
            files={"file": ("bula.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
            headers=build_auth_headers(access_token),
        )
    finally:
        app.dependency_overrides.pop(get_bula_service, None)

    assert response.status_code == 201, response.json()
    assert response.json()["filename"] == "bula.pdf"


@pytest.mark.anyio
async def test_upload_rejects_non_pdf_content_type(client: AsyncClient):
    access_token = await get_access_token(client)

    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipirona"},
        files={"file": ("imagem.png", b"fake image", "image/png")},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Apenas arquivos PDF são aceitos"


@pytest.mark.anyio
async def test_upload_rejects_files_larger_than_10_mb(client: AsyncClient):
    access_token = await get_access_token(client)
    oversized_file = b"0" * (10 * 1024 * 1024 + 1)

    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipirona"},
        files={"file": ("grande.pdf", oversized_file, "application/pdf")},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "O arquivo deve ter no máximo 10 MB"


@pytest.mark.anyio
async def test_upload_corrupted_pdf_still_returns_400(client: AsyncClient):
    access_token = await get_access_token(client)

    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipirona"},
        files={"file": ("corrompido.pdf", b"not a real pdf", "application/pdf")},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Arquivo PDF invalido ou corrompido."
