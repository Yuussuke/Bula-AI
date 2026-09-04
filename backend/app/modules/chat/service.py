from __future__ import annotations

from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import ValidationError

from app.modules.bulas.repository import BulaRepository
from app.modules.chat.models import ChatMessage, ChatRole, ChatSession, RetrievalMode
from app.modules.chat.repository import ChatRepository
from app.modules.chat.schemas import (
    AskRequest,
    AskResponse,
    DirectAskRequest,
    DirectAskResponse,
    SourceChunkResponse,
)
from app.modules.rag.chain import RAGChainFactory


class ChatChainOutputError(RuntimeError):
    """Raised when a RAG chain returns an invalid shape."""


class ChatSessionNotFoundError(Exception):
    """Raised when a chat session is unavailable to the current user."""


class QueryableBulaNotFoundError(Exception):
    """Raised when a bula cannot be queried by the current user."""


class UnsupportedRetrievalModeError(Exception):
    """Raised when a retrieval mode is not available in the current release."""


class DirectAskUnavailableError(Exception):
    """Raised while the legacy direct-ask endpoint remains unavailable."""


MAX_PRIOR_CHAT_TURNS = 10
MAX_PRIOR_CHAT_MESSAGES = MAX_PRIOR_CHAT_TURNS * 2


class ChatService:
    def __init__(
        self,
        *,
        chat_repository: ChatRepository,
        bula_repository: BulaRepository,
    ) -> None:
        self.chat_repository = chat_repository
        self.bula_repository = bula_repository

    async def ask_bula_question(
        self,
        *,
        bula_id: UUID,
        payload: AskRequest,
        user_id: int,
        chain_factory: RAGChainFactory,
    ) -> AskResponse:
        if payload.retrieval_mode != RetrievalMode.DENSE:
            raise UnsupportedRetrievalModeError()

        bula = await self.bula_repository.get_queryable_by_id_for_user(
            bula_id=bula_id,
            user_id=user_id,
        )
        if bula is None:
            raise QueryableBulaNotFoundError()

        chain = chain_factory.build_dense_chain(bula_id=str(bula_id))
        chain_result = await chain.ainvoke({"question": payload.question})
        answer, source_chunks = self._parse_chain_result(chain_result)

        chat_session, _, _ = await self.chat_repository.create_session_with_messages(
            user_id=user_id,
            bula_id=bula_id,
            first_question=payload.question,
            answer=answer,
            retrieval_mode=payload.retrieval_mode,
        )

        return AskResponse(
            session_id=chat_session.id,
            answer=answer,
            source_chunks=source_chunks,
        )

    async def continue_session(
        self,
        *,
        session_id: UUID,
        payload: AskRequest,
        user_id: int,
        chain_factory: RAGChainFactory,
    ) -> AskResponse:
        if payload.retrieval_mode != RetrievalMode.DENSE:
            raise UnsupportedRetrievalModeError()

        chat_session = await self.chat_repository.get_session_for_user(
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None or chat_session.bula_id is None:
            raise ChatSessionNotFoundError()

        bula = await self.bula_repository.get_queryable_by_id_for_user(
            bula_id=chat_session.bula_id,
            user_id=user_id,
        )
        if bula is None:
            raise ChatSessionNotFoundError()

        previous_messages = await self.chat_repository.get_recent_session_history(
            session_id=session_id,
            message_limit=MAX_PRIOR_CHAT_MESSAGES,
        )
        chat_history = self._build_chat_history(previous_messages)
        chain = chain_factory.build_dense_chain(bula_id=str(chat_session.bula_id))
        chain_result = await chain.ainvoke(
            {
                "question": payload.question,
                "chat_history": chat_history,
            }
        )
        answer, source_chunks = self._parse_chain_result(chain_result)

        await self.chat_repository.add_turn(
            session=chat_session,
            question=payload.question,
            answer=answer,
            retrieval_mode=payload.retrieval_mode,
        )
        return AskResponse(
            session_id=chat_session.id,
            answer=answer,
            source_chunks=source_chunks,
        )

    async def list_sessions_for_user(
        self,
        *,
        user_id: int,
        limit: int,
        offset: int,
    ) -> list[ChatSession]:
        return await self.chat_repository.list_user_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    async def get_session_with_history(
        self,
        *,
        session_id: UUID,
        user_id: int,
    ) -> tuple[ChatSession, list[ChatMessage]]:
        chat_session = await self.chat_repository.get_session_for_user(
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None:
            raise ChatSessionNotFoundError()

        messages = await self.chat_repository.get_session_history(
            session_id=session_id,
        )
        return chat_session, messages

    async def answer_question(
        self,
        payload: DirectAskRequest,
        user_id: int,
    ) -> DirectAskResponse:
        """
        Legacy placeholder kept while the first grounded endpoint is introduced.
        Medication answers must flow through the bula-scoped RAG endpoint.
        """
        _ = payload
        _ = user_id
        raise DirectAskUnavailableError()

    def _parse_chain_result(
        self,
        chain_result: dict[str, object],
    ) -> tuple[str, list[SourceChunkResponse]]:
        answer = str(chain_result.get("answer", "")).strip()
        if not answer:
            raise ChatChainOutputError("RAG chain returned an empty answer.")

        raw_source_chunks = chain_result.get("source_chunks", [])
        if not isinstance(raw_source_chunks, list):
            raise ChatChainOutputError("RAG chain returned invalid source_chunks.")

        try:
            source_chunks = [
                SourceChunkResponse.model_validate(source_chunk)
                for source_chunk in raw_source_chunks
            ]
        except ValidationError as exc:
            raise ChatChainOutputError(
                "RAG chain returned invalid source data."
            ) from exc

        return answer, source_chunks

    def _build_chat_history(
        self,
        messages: list[ChatMessage],
    ) -> list[BaseMessage]:
        chat_history: list[BaseMessage] = []
        for message in messages:
            if message.role == ChatRole.USER:
                chat_history.append(HumanMessage(content=message.content))
            else:
                chat_history.append(AIMessage(content=message.content))
        return chat_history
