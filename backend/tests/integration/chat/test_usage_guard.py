import pytest
from httpx import AsyncClient

from app.main import app
from app.modules.chat.dependencies import get_chat_usage_guard
from app.modules.chat.usage_guard import ChatUsageGuard
from tests.integration.chat.test_chat import get_access_token, build_auth_headers


@pytest.mark.anyio
async def test_chat_endpoints_share_the_authenticated_user_limit(
    client: AsyncClient,
) -> None:
    token = await get_access_token(client)
    guard = ChatUsageGuard(requests_per_minute=1)
    app.dependency_overrides[get_chat_usage_guard] = lambda: guard
    headers = build_auth_headers(token)
    assert (
        await client.post(
            "/api/v1/chat/ask", json={"question": "Dúvida"}, headers=headers
        )
    ).status_code == 200
    for path in (
        "/api/v1/chat/ask",
        "/api/v1/chat/sessions/11111111-1111-4111-8111-111111111111/ask",
        "/api/v1/chat/sessions/11111111-1111-4111-8111-111111111111/messages",
    ):
        response = await client.post(path, json={"question": "Dúvida"}, headers=headers)
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"
    assert guard.active == {}
