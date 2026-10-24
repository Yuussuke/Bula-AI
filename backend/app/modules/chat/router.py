from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.chat.models import ChatScope
from app.modules.chat.dependencies import get_chat_service, require_chat_capacity
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
    PublishedSourcesChangedError,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
async def ask_cross_bula(
    payload: AskRequest,
    current_user: User = Depends(require_chat_capacity),
    chat_service: ChatService = Depends(get_chat_service),
) -> AskResponse:
    try:
        return await chat_service.ask_cross_bula_question(
            payload=payload, user_id=cast(int, current_user.id)
        )
    except PublishedSourcesChangedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="As fontes mudaram durante a consulta. Envie a pergunta novamente.",
        ) from exc


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
                "O chat RAG não está disponível neste endpoint. "
                "Utilize /api/v1/chat/ask ou /api/v1/chat/sessions/{bula_id}/ask."
            ),
        ) from exc


@router.post("/sessions/{bula_id}/ask", response_model=AskResponse)
async def ask_bula(
    bula_id: UUID,
    payload: AskRequest,
    current_user: User = Depends(require_chat_capacity),
    chat_service: ChatService = Depends(get_chat_service),
) -> AskResponse:
    try:
        return await chat_service.ask_bula_question(
            bula_id=bula_id,
            payload=payload,
            user_id=cast(int, current_user.id),
        )
    except QueryableBulaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bula não encontrada ou indisponível para consulta.",
        ) from exc


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    scope: ChatScope | None = Query(default=None),
    bula_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> list[ChatSessionResponse]:
    if scope == ChatScope.CROSS_BULA and bula_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Conversas gerais não podem ser filtradas por uma bula individual.",
        )
    sessions = await chat_service.list_sessions_for_user(
        user_id=cast(int, current_user.id),
        limit=limit,
        offset=offset,
        scope=scope,
        bula_id=bula_id,
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
            detail="Conversa não encontrada.",
        ) from exc
    return ChatSessionResponse.from_session(session, messages=messages)


@router.post("/sessions/{session_id}/messages", response_model=AskResponse)
async def continue_session(
    session_id: UUID,
    payload: AskRequest,
    current_user: User = Depends(require_chat_capacity),
    chat_service: ChatService = Depends(get_chat_service),
) -> AskResponse:
    try:
        return await chat_service.continue_session(
            session_id=session_id,
            payload=payload,
            user_id=cast(int, current_user.id),
        )
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada ou indisponível para consulta.",
        ) from exc
    except PublishedSourcesChangedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="As fontes mudaram durante a consulta. Envie a pergunta novamente.",
        ) from exc
