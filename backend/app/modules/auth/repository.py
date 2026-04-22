import hashlib
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User, RefreshToken
import secrets
from datetime import datetime, timedelta, timezone


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Fetches a user from the database by their email address.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_user_by_id(self, user_id: int) -> User | None:
        """
        Fetches a user from the database by their primary key (ID).
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def create_user(
        self, full_name: str, email: str, hashed_password: str
    ) -> User:
        """
        Creates and persists a new user record in the database.
        Returns the newly created User instance.
        """
        db_user = User(
            full_name=full_name,
            email=email,
            hashed_password=hashed_password,
        )
        self.db.add(db_user)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise

        await self.db.refresh(db_user)
        return db_user


def _hash_token(token: str) -> str:
    """Returns a SHA-256 hash of the token string for secure storage and comparison."""
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user_id: int, expires_in_days: int = 30) -> str:
        """Creates a new refresh token, saves the hash, and returns the raw token."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        for attempt in range(3):
            raw_token = secrets.token_urlsafe(48)
            hashed_token = _hash_token(raw_token)

            refresh_token = RefreshToken(
                token=hashed_token,
                user_id=user_id,
                expires_at=expires_at,
            )
            self.db.add(refresh_token)
            try:
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                if attempt == 2:
                    raise
            else:
                return raw_token

        raise RuntimeError("Failed to create refresh token after retries")

    async def get_valid_token(self, raw_token_value: str) -> RefreshToken | None:
        """Returns the token only if it exists, is not revoked, and has not expired."""

        hashed_token = _hash_token(raw_token_value)

        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == hashed_token,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        """Marks a refresh token as revoked (used during logout or rotation)."""
        token.is_revoked = True
        await self.db.commit()

    async def consume_atomically(self, raw_token_value: str) -> RefreshToken | None:
        """
        Atomically checks if the token is valid and revokes it in a single database transaction.
        """
        hashed_token = _hash_token(raw_token_value)

        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.token == hashed_token,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .values(is_revoked=True)
            .returning(RefreshToken)
        )

        result = await self.db.execute(stmt)
        token = result.scalar_one_or_none()

        if token:
            await self.db.commit()

        return token
