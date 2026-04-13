from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Fetches a user from the database by their email address.
        Returns None if the user is not found.
        """
    
        result = await self.db.execute(select(User).where(User.email == email)) 
        return result.scalars().first()

    async def create_user(self, email: str, hashed_password: str) -> User:
        """
        Creates and persists a new user record in the database.
        Returns the newly created User instance.
        """
        db_user = User(
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