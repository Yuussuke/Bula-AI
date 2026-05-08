from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService


def get_chat_repository(db: AsyncSession = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db=db)


def get_chat_service() -> ChatService:
    return ChatService()
