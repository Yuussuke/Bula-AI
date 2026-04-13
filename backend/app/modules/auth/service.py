from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.modules.auth import schemas, repository, security
from app.modules.auth.models import User

class TokenService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int,
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
        Creates a JWT access token with the given data and expiration.
        """
        return self.token_service.create_access_token(data, expires_delta)

    async def register_new_user(self, user_in: schemas.UserCreate) -> User:
        """
        Registers a new user and Hashes the password before saving to the database.
        """
        existing_user = await self.user_repository.get_user_by_email(email=user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            )

        hashed_password = self.password_hasher.get_password_hash(user_in.password)

        try:
            new_user = await self.user_repository.create_user(
                email=user_in.email,
                hashed_password=hashed_password,
            )
        except IntegrityError as exc:
            error_msg = str(getattr(exc, "orig", "")).lower()
            if "unique constraint" in error_msg or "23505" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered.",
                ) from None
            raise exc
        return new_user

    async def authenticate_user(self, email: str, password: str) -> schemas.Token:
        """
        Authenticates a user by email and password and returns a JWT token
        """
        user = await self.user_repository.get_user_by_email(email=email)

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

    async def get_user_from_token(self, token: str) -> User:
        """
        Validates the JWT token and retrieves the corresponding user from the database.
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

        user = await self.user_repository.get_user_by_email(email=email)

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account",
            )

        return user