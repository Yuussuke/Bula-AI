import pytest
from httpx import AsyncClient


MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF-"


def build_user(email: str) -> dict[str, str]:
    return {
        "full_name": "Upload Test User",
        "email": email,
        "password": "Secret123!",
    }


async def get_access_token(client: AsyncClient, *, email: str) -> str:
    test_user = build_user(email)
    await client.post("/api/v1/auth/register", json=test_user)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user["email"], "password": test_user["password"]},
    )
    return str(login_response.json()["token"]["access_token"])


def build_auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.anyio
async def test_upload_valid_pdf_returns_created_bula(client: AsyncClient) -> None:
    access_token = await get_access_token(client, email="upload-test@bulaai.com")

    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipyrone", "manufacturer": "Example Pharma"},
        files={"file": ("leaflet.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        headers=build_auth_headers(access_token),
    )

    response_body = response.json()
    assert response.status_code == 201, response_body
    assert response_body["drug_name"] == "Dipyrone"
    assert response_body["manufacturer"] == "Example Pharma"
    assert response_body["file_url"] is None
    assert response_body["file_address"].startswith("stored_objects/")
    assert "data" not in response_body


@pytest.mark.anyio
async def test_upload_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipyrone"},
        files={"file": ("leaflet.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_upload_rejects_missing_drug_name_with_400(
    client: AsyncClient,
) -> None:
    access_token = await get_access_token(
        client,
        email="missing-drug-name@bulaai.com",
    )

    response = await client.post(
        "/api/v1/bulas/upload",
        files={"file": ("leaflet.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_upload_rejects_missing_file_with_400(client: AsyncClient) -> None:
    access_token = await get_access_token(client, email="missing-file@bulaai.com")

    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipyrone"},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_upload_rejects_empty_file_with_400(client: AsyncClient) -> None:
    access_token = await get_access_token(client, email="empty-file@bulaai.com")

    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipyrone"},
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_upload_rejects_non_pdf_content_type_with_415(
    client: AsyncClient,
) -> None:
    access_token = await get_access_token(client, email="non-pdf@bulaai.com")

    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipyrone"},
        files={"file": ("imagem.png", b"fake image", "image/png")},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 415


@pytest.mark.anyio
async def test_upload_rejects_invalid_pdf_magic_bytes_with_415(
    client: AsyncClient,
) -> None:
    access_token = await get_access_token(client, email="invalid-magic@bulaai.com")

    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipyrone"},
        files={"file": ("corrupted.pdf", b"not a real pdf", "application/pdf")},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 415


@pytest.mark.anyio
async def test_upload_rejects_files_larger_than_10_mb_with_413(
    client: AsyncClient,
) -> None:
    access_token = await get_access_token(client, email="oversized@bulaai.com")
    padding_size_bytes = MAX_UPLOAD_SIZE_BYTES - len(PDF_MAGIC_BYTES) + 1
    oversized_file = PDF_MAGIC_BYTES + b"0" * padding_size_bytes

    response = await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Dipyrone"},
        files={"file": ("grande.pdf", oversized_file, "application/pdf")},
        headers=build_auth_headers(access_token),
    )

    assert response.status_code == 413


@pytest.mark.anyio
async def test_list_bulas_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/bulas/")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_list_bulas_returns_only_current_user_bulas_newest_first(
    client: AsyncClient,
) -> None:
    first_user_token = await get_access_token(client, email="first-user@bulaai.com")
    second_user_token = await get_access_token(client, email="second-user@bulaai.com")

    await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "First Bula"},
        files={"file": ("first.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        headers=build_auth_headers(first_user_token),
    )
    await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Second Bula"},
        files={"file": ("second.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        headers=build_auth_headers(first_user_token),
    )
    await client.post(
        "/api/v1/bulas/upload",
        data={"drug_name": "Other User Bula"},
        files={"file": ("other.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        headers=build_auth_headers(second_user_token),
    )

    response = await client.get(
        "/api/v1/bulas/",
        headers=build_auth_headers(first_user_token),
    )

    response_body = response.json()
    returned_drug_names = [bula["drug_name"] for bula in response_body]
    assert response.status_code == 200, response_body
    assert returned_drug_names == ["Second Bula", "First Bula"]
    has_only_object_ref_addresses = all(
        bula["file_address"].startswith("stored_objects/") for bula in response_body
    )
    assert has_only_object_ref_addresses
