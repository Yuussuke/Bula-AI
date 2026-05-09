from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.bulas.dependencies import get_bula_repository
from app.modules.bulas.repository import BulaRepository
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService


def get_chat_repository(db: AsyncSession = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db=db)


def get_chat_service(
    chat_repository: ChatRepository = Depends(get_chat_repository),
    bula_repository: BulaRepository = Depends(get_bula_repository),
) -> ChatService:
    return ChatService(
        chat_repository=chat_repository,
        bula_repository=bula_repository,
    )
