from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.modules.bulas.repository import BulaRepository
from app.modules.chat.models import RetrievalMode
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
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=(
                    "This retrieval mode is part of the API contract, "
                    "but has not yet been implemented in this MVP."
                ),
            )

        bula = await self.bula_repository.get_queryable_by_id_for_user(
            bula_id=bula_id,
            user_id=user_id,
        )
        if bula is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bula not found or not ready for querying.",
            )

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
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "RAG chat is not yet available on this endpoint. "
                "Use /api/v1/chat/sessions/{bula_id}/ask."
            ),
        )

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
