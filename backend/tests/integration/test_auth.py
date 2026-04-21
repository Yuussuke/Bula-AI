import pytest
from httpx import AsyncClient

TEST_USER = {
    "full_name": "Test User",
    "email": "test@bulaai.com",
    "password": "secretpassword",
}


@pytest.mark.anyio
async def test_register_creates_user_and_returns_201(client: AsyncClient):
    """Tests that registering a new user works and returns the expected response."""
    response = await client.post("/api/v1/auth/register", json=TEST_USER)

    assert response.status_code == 201, response.json()

    data = response.json()
    assert data["user"]["email"] == TEST_USER["email"]
    assert data["user"]["full_name"] == TEST_USER["full_name"]
    assert "id" in data["user"]
    assert "is_active" in data["user"]
    assert "password" not in data["user"]
    assert "hashed_password" not in data["user"]


@pytest.mark.anyio
async def test_register_duplicate_email_returns_409(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=TEST_USER)

    response = await client.post("/api/v1/auth/register", json=TEST_USER)

    assert response.status_code == 409
    assert "detail" in response.json()


@pytest.mark.anyio
async def test_login_with_valid_credentials_returns_token(client: AsyncClient):
    """Tests if login with correct email and password returns a JWT token."""
    await client.post("/api/v1/auth/register", json=TEST_USER)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )

    assert response.status_code == 200, response.json()

    data = response.json()
    assert "token" in data
    assert "access_token" in data["token"]
    assert data["token"]["token_type"] == "bearer"
        
    assert "user" in data
    assert data["user"]["email"] == TEST_USER["email"]
@pytest.mark.anyio
async def test_login_wrong_password_returns_401(client: AsyncClient):
    """Tests if login with incorrect password is rejected."""
    await client.post("/api/v1/auth/register", json=TEST_USER)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": "senhaincorreta"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_me_with_valid_token_returns_user(client: AsyncClient):
    """Tests if the protected route returns the user profile when a valid token is sent."""
    await client.post("/api/v1/auth/register", json=TEST_USER)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    assert login_response.status_code == 200, login_response.json()

    token = login_response.json()["token"]["access_token"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == TEST_USER["email"]


@pytest.mark.anyio
async def test_get_me_without_token_returns_401(client: AsyncClient):
    """Tests if the protected route is blocked when no token is sent."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.anyio
async def test_get_me_with_invalid_token_returns_401(client: AsyncClient):
    """Tests if the protected route is blocked when an invalid token is sent."""
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
