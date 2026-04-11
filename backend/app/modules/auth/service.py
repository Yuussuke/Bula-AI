# Business logic (Hashing, Token generation)
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth import schemas, repository, security
from app.modules.auth.models import User


class TokenService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_subject(self, token: str) -> str | None:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        return payload.get("sub")


class AuthService:
    def __init__(
        self,
        user_repository: repository.UserRepository,
        password_hasher: security.PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self.user_repository = user_repository
        self.password_hasher = password_hasher
        self.token_service = token_service

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        """
        Generates a JWT token containing the user's data and an expiration time.
        """
        return self.token_service.create_access_token(data, expires_delta)

    async def register_new_user(self, db: AsyncSession, user_in: schemas.UserCreate) -> User:
        """
        Validates if the user exists, hashes the password, and delegates creation to the repository.
        """
        existing_user = await self.user_repository.get_user_by_email(db, email=user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            )

        hashed_password = self.password_hasher.get_password_hash(user_in.password)

        try:
            new_user = await self.user_repository.create_user(
                db=db,
                email=user_in.email,
                hashed_password=hashed_password,
            )
        except IntegrityError:
            error_msg = str(IntegrityError.orig).lower()
            if "unique constraint" in error_msg or "23505" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered.",
                ) from None
            raise IntegrityError
        return new_user

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> schemas.Token:
        """
        Validates credentials and returns a JWT token if successful.
        """
        user = await self.user_repository.get_user_by_email(db, email=email)

        if not user or not self.password_hasher.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=self.token_service.access_token_expire_minutes)
        access_token = self.create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires,
        )

        return schemas.Token(access_token=access_token, token_type="bearer")

    async def get_user_from_token(self, db: AsyncSession, token: str) -> User:
        """
        Decodes the JWT token and fetches the user from the database.
        Raises exceptions if the token is invalid or the user is not found/inactive.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            email = self.token_service.decode_subject(token)
            if email is None:
                raise credentials_exception
        except jwt.PyJWTError:
            raise credentials_exception

        user = await self.user_repository.get_user_by_email(db, email=email)

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account",
            )

        return user


SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is required. Set it in the container environment.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

TOKEN_SERVICE = TokenService(
    secret_key=SECRET_KEY,
    algorithm=ALGORITHM,
    access_token_expire_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
)

AUTH_SERVICE = AuthService(
    user_repository=repository.USER_REPOSITORY,
    password_hasher=security.PASSWORD_HASHER,
    token_service=TOKEN_SERVICE,
)