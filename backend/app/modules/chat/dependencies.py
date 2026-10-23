from fastapi import Depends, HTTPException
from functools import lru_cache
from collections.abc import AsyncIterator
from typing import cast
from app.core.config import get_settings
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.chat.usage_guard import ChatUsageGuard, ChatCapacityExceededError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.bulas.dependencies import get_bula_repository
from app.modules.bulas.repository import BulaRepository
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService
from app.modules.rag.chain import RAGChainFactory
from app.modules.rag.dependencies import get_rag_chain_factory


@lru_cache
def get_chat_usage_guard() -> ChatUsageGuard:
    settings = get_settings()
    return ChatUsageGuard(
        requests_per_minute=settings.chat_requests_per_minute,
        max_concurrent=settings.chat_max_concurrent_per_user,
    )


async def require_chat_capacity(
    current_user: User = Depends(get_current_user),
    guard: ChatUsageGuard = Depends(get_chat_usage_guard),
) -> AsyncIterator[User]:
    user_id = cast(int, current_user.id)
    try:
        guard.acquire(user_id)
    except ChatCapacityExceededError as exc:
        raise HTTPException(
            status_code=429,
            detail="Limite de consultas atingido ou outra resposta em andamento. Tente novamente em um minuto.",
            headers={"Retry-After": "60"},
        ) from exc
    try:
        yield current_user
    finally:
        guard.release(user_id)


def get_chat_repository(db: AsyncSession = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db=db)


def get_chat_service(
    chat_repository: ChatRepository = Depends(get_chat_repository),
    bula_repository: BulaRepository = Depends(get_bula_repository),
    chain_factory: RAGChainFactory = Depends(get_rag_chain_factory),
) -> ChatService:
    return ChatService(
        chat_repository=chat_repository,
        bula_repository=bula_repository,
        chain_factory=chain_factory,
    )
