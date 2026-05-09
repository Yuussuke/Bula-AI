from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.schemas import (
    AskRequest,
    AskResponse,
    DirectAskRequest,
    DirectAskResponse,
)
from app.modules.chat.service import ChatService
from app.modules.rag.chain import RAGChainFactory
from app.modules.rag.dependencies import get_rag_chain_factory

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/direct-ask", response_model=DirectAskResponse)
async def direct_ask(
    payload: DirectAskRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> DirectAskResponse:
    return await chat_service.answer_question(
        payload=payload,
        user_id=cast(int, current_user.id),
    )


@router.post("/sessions/{bula_id}/ask", response_model=AskResponse)
async def ask_bula(
    bula_id: UUID,
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    chain_factory: RAGChainFactory = Depends(get_rag_chain_factory),
    chat_service: ChatService = Depends(get_chat_service),
) -> AskResponse:
    return await chat_service.ask_bula_question(
        bula_id=bula_id,
        payload=payload,
        user_id=cast(int, current_user.id),
        chain_factory=chain_factory,
    )
