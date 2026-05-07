import pytest
from httpx import AsyncClient

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


@pytest.mark.anyio
async def test_direct_ask_requires_authentication(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat/direct-ask",
        json={"question": "Posso tomar este medicamento?"},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_direct_ask_returns_501_until_rag_is_available(client: AsyncClient):
    access_token = await get_access_token(client)

    response = await client.post(
        "/api/v1/chat/direct-ask",
        json={"question": "Posso tomar este medicamento?"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 501
    assert response.json()["detail"] == (
        "O chat RAG ainda não está disponível. "
        "A camada de retrieval ainda não foi implementada."
    )
