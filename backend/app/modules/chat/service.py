from fastapi import HTTPException, status

from app.modules.chat.schemas import DirectAskRequest, DirectAskResponse


class ChatService:
    async def answer_question(
        self,
        payload: DirectAskRequest,
        user_id: int,
    ) -> DirectAskResponse:
        """
        Entry point for future RAG-backed answers.

        A RetrieverService or RAGService should be called from here once the
        retrieval layer exists. Until then, this endpoint must not call the LLM
        directly because answers need to be grounded in uploaded bulas.
        """
        _ = payload
        _ = user_id
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "O chat RAG ainda não está disponível. "
                "A camada de retrieval ainda não foi implementada."
            ),
        )
