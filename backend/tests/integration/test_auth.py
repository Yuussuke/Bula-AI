import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.config import Settings
from app.modules.auth.dependencies import require_admin
from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import RefreshTokenRepository, UserRepository
from app.modules.auth.router import set_refresh_cookie
from app.modules.auth.schemas import UserCreate
from app.modules.auth.security import PasswordHasher
from app.modules.auth.service import AuthService, TokenService

TEST_USER = {
    "full_name": "Test User",
    "email": "test@bulaai.com",
    "password": "Secret123!",
}


@pytest.mark.anyio
async def test_register_creates_user_and_returns_201(client: AsyncClient):
    """Tests that registering a new user works and returns the expected response."""
    response = await client.post("/api/v1/auth/register", json=TEST_USER)

    assert response.status_code == 201, response.json()

    data = response.json()
    assert data["user"]["email"] == TEST_USER["email"]
    assert data["user"]["name"] == TEST_USER["full_name"]
    assert data["user"]["role"] == "user"
    assert "id" in data["user"]
    assert "full_name" not in data["user"]
    assert "is_active" not in data["user"]
    assert "password" not in data["user"]
    assert "hashed_password" not in data["user"]


@pytest.mark.anyio
async def test_register_rejects_role_payload(client: AsyncClient):
    payload = {**TEST_USER, "email": "role-attempt@bulaai.com", "role": "admin"}

    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 401


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
    assert data["user"]["name"] == TEST_USER["full_name"]
    assert data["user"]["role"] == "user"
    assert "full_name" not in data["user"]
    assert "is_active" not in data["user"]


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
    data = response.json()
    assert data["email"] == TEST_USER["email"]
    assert data["name"] == TEST_USER["full_name"]
    assert data["role"] == "user"
    assert "full_name" not in data
    assert "is_active" not in data


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


@pytest.mark.anyio
async def test_refresh_returns_new_access_token_and_rotates_cookie(client: AsyncClient):
    """Testa se a rota de refresh gera um novo token e rotaciona o cookie de forma segura."""
    await client.post("/api/v1/auth/register", json=TEST_USER)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )

    raw_cookie = login_response.cookies.get("refresh_token")
    assert raw_cookie is not None
    client.cookies.set("refresh_token", raw_cookie)

    refresh_response = await client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert refresh_response.cookies.get("refresh_token") is not None
    assert refresh_response.cookies.get("refresh_token") != raw_cookie

    client.cookies.delete("refresh_token")


@pytest.mark.anyio
async def test_refresh_with_no_cookie_returns_401(client: AsyncClient):
    """Trying to refresh the session without the HttpOnly cookie is blocked."""
    client.cookies.delete("refresh_token")

    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_logout_clears_cookie_and_revokes_token(client: AsyncClient):
    """Testa se o logout revoga o token no banco e impede um novo refresh."""
    await client.post("/api/v1/auth/register", json=TEST_USER)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )

    raw_cookie = login_response.cookies.get("refresh_token")
    client.cookies.set("refresh_token", raw_cookie)

    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    refresh_response = await client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401

    client.cookies.delete("refresh_token")


@pytest.mark.anyio
async def test_login_rate_limiting_works(client: AsyncClient):
    """
    Tests that the login endpoint is protected by rate limiting
    and blocks after 5 failed attempts.
    """
    from app.main import app

    app.state.limiter.enabled = True

    try:
        payload = {"email": TEST_USER["email"], "password": TEST_USER["password"]}

        for i in range(5):
            response = await client.post("/api/v1/auth/login", json=payload)
            assert response.status_code == 401
            assert response.json()["detail"] == "Incorrect email or password."

        blocked_response = await client.post("/api/v1/auth/login", json=payload)

        assert blocked_response.status_code == 429
        assert "Rate limit exceeded" in blocked_response.json()["error"]

    finally:
        app.state.limiter.enabled = False


def test_refresh_cookie_uses_secure_settings_in_production(monkeypatch):
    from app.modules.auth import router as auth_router

    monkeypatch.setattr(auth_router.settings, "environment", "production")
    response = Response()

    set_refresh_cookie(response, "raw-refresh-token")

    cookie_header = response.headers["set-cookie"]
    assert "HttpOnly" in cookie_header
    assert "Path=/api/v1/auth/refresh" in cookie_header
    assert "SameSite=none" in cookie_header
    assert "Secure" in cookie_header


def test_secret_key_validator_rejects_weak_key():
    with pytest.raises(ValueError):
        Settings(secret_key="changeme")


@pytest.mark.anyio
async def test_require_admin_allows_admin_user():
    admin_user = User(
        id=1,
        full_name="Admin User",
        email="admin@bulaai.com",
        hashed_password="hashed",
        role=UserRole.ADMIN,
    )

    result = await require_admin(current_user=admin_user)

    assert result is admin_user


@pytest.mark.anyio
async def test_require_admin_rejects_regular_user():
    regular_user = User(
        id=1,
        full_name="Regular User",
        email="user@bulaai.com",
        hashed_password="hashed",
        role=UserRole.USER,
    )

    with pytest.raises(HTTPException) as exception_info:
        await require_admin(current_user=regular_user)

    assert exception_info.value.status_code == 403


@pytest.mark.anyio
async def test_create_admin_user_creates_admin_that_can_login(
    client: AsyncClient,
    db_session: AsyncSession,
):
    auth_service = AuthService(
        user_repository=UserRepository(db=db_session),
        refresh_token_repository=RefreshTokenRepository(db=db_session),
        password_hasher=PasswordHasher(),
        token_service=TokenService(
            secret_key="long_and_secure_secret_key_for_testing_purposes_only_1234567890",
            algorithm="HS256",
            access_token_expire_minutes=30,
        ),
    )
    admin_payload = UserCreate(
        full_name="Admin User",
        email="admin@bulaai.com",
        password="Secret123!",
    )

    admin_user = await auth_service.create_admin_user(admin_payload)

    assert admin_user.role == UserRole.ADMIN
    assert admin_user.hashed_password != admin_payload.password

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_payload.email, "password": admin_payload.password},
    )

    assert login_response.status_code == 200, login_response.json()
    assert login_response.json()["user"]["role"] == "admin"
