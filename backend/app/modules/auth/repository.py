# Database operations (Select/Insert)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User

class UserRepository:
    async def get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        """
        Fetches a user from the database by their email address.
        Returns None if the user is not found.
        """
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def create_user(self, db: AsyncSession, email: str, hashed_password: str) -> User:
        """
        Creates and persists a new user record in the database.
        Returns the newly created User instance.
        """
        db_user = User(
            email=email,
            hashed_password=hashed_password,
        )
        db.add(db_user)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise

        await db.refresh(db_user)
        return db_user


USER_REPOSITORY = UserRepository()