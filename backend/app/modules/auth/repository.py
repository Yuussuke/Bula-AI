from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
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

class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user_id: int, expires_in_days: int = 30) -> RefreshToken:
        """Creates a new refresh token for the given user and persists it."""
        token_value = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        refresh_token = RefreshToken(
            token=token_value,
            user_id=user_id,
            expires_at=expires_at,
        )
        self.db.add(refresh_token)
        await self.db.commit()
        await self.db.refresh(refresh_token)
        return refresh_token

    async def get_valid_token(self, token_value: str) -> RefreshToken | None:
        """Returns the token only if it exists, is not revoked, and has not expired."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token_value,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        """Marks a refresh token as revoked (used during logout or rotation)."""
        token.is_revoked = True
        await self.db.commit()