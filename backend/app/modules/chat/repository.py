from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.models import ChatMessage, ChatRole, ChatSession, RetrievalMode

MAX_CHAT_SESSION_TITLE_LENGTH = 50
DEFAULT_CHAT_SESSION_TITLE = "Nova conversa"


class ChatPersistenceError(Exception):
    """Raised when chat data cannot be persisted."""


class ChatRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_session(
        self,
        *,
        user_id: int,
        first_question: str,
        bula_id: UUID | None = None,
    ) -> ChatSession:
        chat_session = ChatSession(
            user_id=user_id,
            bula_id=bula_id,
            title=self._extract_title(first_question),
        )
        self.db.add(chat_session)

        try:
            await self.db.commit()
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise ChatPersistenceError() from exc

        await self.db.refresh(chat_session)
        return chat_session

    async def add_message(
        self,
        *,
        session_id: UUID,
        role: ChatRole,
        content: str,
        retrieval_mode: RetrievalMode | None = None,
    ) -> ChatMessage:
        chat_message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            retrieval_mode=retrieval_mode,
        )
        self.db.add(chat_message)

        try:
            await self.db.commit()
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise ChatPersistenceError() from exc

        await self.db.refresh(chat_message)
        return chat_message

    async def get_session_history(self, *, session_id: UUID) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def list_user_sessions(
        self,
        *,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ChatSession]:
        statement = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    def _extract_title(self, first_question: str) -> str:
        title = first_question.strip()[:MAX_CHAT_SESSION_TITLE_LENGTH]
        if not title:
            return DEFAULT_CHAT_SESSION_TITLE

        return title
