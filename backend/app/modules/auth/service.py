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
        password_hasher: security.PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self.user_repository = user_repository
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
        logger.info("user_registration_attempt", email=user_in.email)

        existing_user = await self.user_repository.get_user_by_email(
            email=user_in.email.lower()
        )
        if existing_user:
            logger.warning(
                "user_registration_failed",
                reason="email_already_exists",
                email=user_in.email,
            )
            raise UserAlreadyExistsError()

        hashed_password = self.password_hasher.get_password_hash(user_in.password)

        try:
            new_user = await self.user_repository.create_user(
                full_name=user_in.full_name,
                email=user_in.email.lower(),
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

    async def authenticate_user(self, email: str, password: str) -> schemas.Token:
        """
        Authenticates a user by email and password and returns a JWT token
        """
        logger.info("user_login_attempt", email=email)

        user = await self.user_repository.get_user_by_email(email=email.lower())

        if not user or not self.password_hasher.verify_password(
            password, user.hashed_password
        ):
            logger.warning(
                "user_authentication_failed", reason="invalid_credentials", email=email
            )
            raise InvalidCredentialsError()

        access_token_expires = timedelta(
            minutes=self.token_service.access_token_expire_minutes
        )
        access_token = self.create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires,
        )

        return schemas.Token(access_token=access_token, token_type="bearer")

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
