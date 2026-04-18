from functools import lru_cache
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings

from app.modules.auth.repository import UserRepository
from app.modules.auth.service import AuthService, InvalidCredentialsError, TokenService
from app.modules.auth.security import PasswordHasher
from app.modules.auth.models import User

security = HTTPBearer(auto_error=False)


@lru_cache
def get_password_hasher() -> PasswordHasher:
    """
    Provides a cached instance of PasswordHasher for secure password hashing.
    """
    return PasswordHasher()


@lru_cache
def get_token_service() -> TokenService:
    """
    Provides a cached instance of TokenService configured with application settings.
    """
    return TokenService(
        secret_key=settings.secret_key,
        algorithm=settings.algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
    )


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """FastAPI gets the database session and wires the User Repository."""
    return UserRepository(db=db)


def get_auth_service(
    repo: UserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
    token_srv: TokenService = Depends(get_token_service),
) -> AuthService:
    """FastAPI gets the Repository, Hasher, and TokenService, and wires the Auth Service."""
    return AuthService(
        user_repository=repo, password_hasher=hasher, token_service=token_srv
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """FastAPI gets the token from the Authorization header, and the Auth Service."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        current_user = await auth_service.get_user_from_token(
            token=credentials.credentials
        )
        structlog.contextvars.bind_contextvars(user_id=current_user.id)
        return current_user
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
