from datetime import datetime, timedelta, timezone

import jwt
import structlog
from sqlalchemy.exc import IntegrityError

from app.modules.auth import schemas, repository, security
from app.modules.auth.models import User

logger = structlog.get_logger(__name__)


class UserAlreadyExistsError(Exception):
    """Raised when trying to register a user with an email that already exists."""

    pass


class InvalidCredentialsError(Exception):
    """Raised when authentication fails due to invalid email or password."""

    pass


class UserNotFoundError(Exception):
    """Raised when a user is not found in the database."""

    pass


class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token is missing, expired, or revoked."""

    pass


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

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_subject(self, token: str) -> str | None:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        return payload.get("sub")


class AuthService:
    def __init__(
        self,
        user_repository: repository.UserRepository,
        refresh_token_repository: repository.RefreshTokenRepository,
        password_hasher: security.PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        self.password_hasher = password_hasher
        self.token_service = token_service

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        """
        Creates a JWT access token with the given data and expiration.
        """
        return self.token_service.create_access_token(data, expires_delta)

    async def register_new_user(self, user_in: schemas.UserCreate) -> User:
        normalized_email = user_in.email.lower().strip()
        logger.info("user_registration_attempt", email=normalized_email)

        existing_user = await self.user_repository.get_user_by_email(
            email=normalized_email
        )
        if existing_user:
            logger.warning(
                "user_registration_failed",
                reason="email_already_exists",
                email=normalized_email,
            )
            raise UserAlreadyExistsError()

        hashed_password = self.password_hasher.get_password_hash(user_in.password)

        try:
            new_user = await self.user_repository.create_user(
                full_name=user_in.full_name,
                email=normalized_email,
                hashed_password=hashed_password,
            )
        except IntegrityError as exc:
            error_msg = str(getattr(exc, "orig", "")).lower()
            if "unique constraint" in error_msg or "23505" in error_msg:
                raise UserAlreadyExistsError()
            raise exc
        logger.info(
            "user_registered_successfully", user_id=new_user.id, email=new_user.email
        )
        return new_user

    async def authenticate_user(
        self, email: str, password: str
    ) -> tuple[schemas.Token, str]:
        """
        Authenticates a user and returns (access_token_schema, raw_refresh_token_string).
        The raw refresh token string is what gets stored in the HttpOnly cookie.
        """
        normalized_email = email.lower().strip()
        logger.info("attempting_authenticate_user", email=normalized_email)
        user = await self.user_repository.get_user_by_email(email=normalized_email)

        if user is None:
            raise InvalidCredentialsError()

        password_is_valid = self.password_hasher.verify_password(
            password, user.hashed_password
        )
        if not password_is_valid:
            logger.warning(
                "authentication_failed",
                reason="invalid_password",
                email=normalized_email,
            )
            raise InvalidCredentialsError()

        logger.info("authentication_succeeded", user_id=user.id, email=normalized_email)

        access_token_expires = timedelta(
            minutes=self.token_service.access_token_expire_minutes
        )
        access_token = self.create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires,
        )

        raw_refresh_token = await self.refresh_token_repository.create(user_id=user.id)

        return (
            schemas.Token(access_token=access_token, token_type="bearer"),
            raw_refresh_token,
            user,
        )

    async def get_user_from_token(self, token: str) -> User:
        """
        Validates the JWT token and retrieves the corresponding user from the database by ID.
        """
        logger.info("token_validation_attempt")
        credentials_exception = InvalidCredentialsError()
        try:
            subject = self.token_service.decode_subject(token)
            if subject is None:
                logger.warning("token_validation_failed", reason="missing_subject")
                raise credentials_exception

            user_id = int(subject)

        except (jwt.PyJWTError, ValueError):
            logger.warning("token_validation_failed", reason="invalid_token")
            raise credentials_exception

        user = await self.user_repository.get_user_by_id(user_id=user_id)

        if user is None:
            logger.warning(
                "token_validation_failed",
                reason="user_not_found",
                user_id=user_id,
            )
            raise credentials_exception

        if not user.is_active:
            logger.warning(
                "token_validation_failed",
                reason="inactive_user",
                user_id=user.id,
            )
            raise credentials_exception

        logger.info("token_validation_succeeded", user_id=user.id)

        return user

    async def refresh_session(
        self, raw_refresh_token: str
    ) -> tuple[schemas.Token, str]:
        """
        Validates the refresh token, revokes it, and issues a new access token and refresh token.
        Returns (access_token_schema, raw_refresh_token_string).
        """
        consumed_token = await self.refresh_token_repository.consume_atomically(
            raw_refresh_token
        )

        if consumed_token is None:
            raise InvalidRefreshTokenError()

        access_token_expires = timedelta(
            minutes=self.token_service.access_token_expire_minutes
        )

        new_access_token = self.create_access_token(
            data={"sub": str(consumed_token.user_id)},
            expires_delta=access_token_expires,
        )

        new_raw_refresh_token = await self.refresh_token_repository.create(
            user_id=consumed_token.user_id
        )

        return schemas.Token(
            access_token=new_access_token, token_type="bearer"
        ), new_raw_refresh_token

    async def logout(self, raw_refresh_token: str) -> None:
        """
        Revokes the refresh token identified by the given value.
        If the token does not exist or is already revoked, this is a no-op.
        """
        existing_token = await self.refresh_token_repository.get_valid_token(
            raw_refresh_token
        )

        if existing_token is not None:
            await self.refresh_token_repository.revoke(existing_token)
