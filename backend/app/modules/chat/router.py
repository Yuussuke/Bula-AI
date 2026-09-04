from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.schemas import (
    AskRequest,
    AskResponse,
    ChatSessionResponse,
    DirectAskRequest,
    DirectAskResponse,
)
from app.modules.chat.service import (
    ChatService,
    ChatSessionNotFoundError,
    DirectAskUnavailableError,
    QueryableBulaNotFoundError,
    UnsupportedRetrievalModeError,
)
from app.modules.rag.chain import RAGChainFactory
from app.modules.rag.dependencies import get_rag_chain_factory

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/direct-ask", response_model=DirectAskResponse)
async def direct_ask(
    payload: DirectAskRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> DirectAskResponse:
    try:
        return await chat_service.answer_question(
            payload=payload,
            user_id=cast(int, current_user.id),
        )
    except DirectAskUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "RAG chat is not yet available on this endpoint. "
                "Use /api/v1/chat/sessions/{bula_id}/ask."
            ),
        ) from exc


@router.post("/sessions/{bula_id}/ask", response_model=AskResponse)
async def ask_bula(
    bula_id: UUID,
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    chain_factory: RAGChainFactory = Depends(get_rag_chain_factory),
    chat_service: ChatService = Depends(get_chat_service),
) -> AskResponse:
    try:
        return await chat_service.ask_bula_question(
            bula_id=bula_id,
            payload=payload,
            user_id=cast(int, current_user.id),
            chain_factory=chain_factory,
        )
    except UnsupportedRetrievalModeError as exc:
        raise _unsupported_retrieval_mode_http_exception() from exc
    except QueryableBulaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bula not found or not ready for querying.",
        ) from exc


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> list[ChatSessionResponse]:
    sessions = await chat_service.list_sessions_for_user(
        user_id=cast(int, current_user.id),
        limit=limit,
        offset=offset,
    )
    return [ChatSessionResponse.from_session(session) for session in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    try:
        session, messages = await chat_service.get_session_with_history(
            session_id=session_id,
            user_id=cast(int, current_user.id),
        )
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        ) from exc
    return ChatSessionResponse.from_session(session, messages=messages)


@router.post("/sessions/{session_id}/messages", response_model=AskResponse)
async def continue_session(
    session_id: UUID,
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    chain_factory: RAGChainFactory = Depends(get_rag_chain_factory),
    chat_service: ChatService = Depends(get_chat_service),
) -> AskResponse:
    try:
        return await chat_service.continue_session(
            session_id=session_id,
            payload=payload,
            user_id=cast(int, current_user.id),
            chain_factory=chain_factory,
        )
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or no longer queryable.",
        ) from exc
    except UnsupportedRetrievalModeError as exc:
        raise _unsupported_retrieval_mode_http_exception() from exc


def _unsupported_retrieval_mode_http_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "This retrieval mode is part of the API contract, "
            "but has not yet been implemented in this MVP."
        ),
    )
