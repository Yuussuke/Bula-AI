from datetime import datetime, timezone
from uuid import UUID
from typing import Literal

from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.models import ChatMessage, ChatRole, ChatSession, ChatScope
from app.modules.bulas.models import PublicCatalogScope
from app.modules.chat.schemas import SessionSortOrder
from app.modules.rag.retrieval_mode import RetrievalMode
from app.core.text_search import text_search_match

MAX_CHAT_SESSION_TITLE_LENGTH = 50
DEFAULT_CHAT_SESSION_TITLE = "New conversation"


class ChatPersistenceError(Exception):
    """Raised when chat data cannot be persisted."""


class ChatRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search_user_history(
        self,
        *,
        user_id: int,
        query: str,
        match: Literal["title_prefix", "message_prefix", "title_substring"],
        limit: int,
        offset: int,
    ) -> list[tuple[ChatSession, ChatMessage | None]]:
        title_prefix = text_search_match(ChatSession.title, query, word_prefix=True)
        message_prefix = text_search_match(ChatMessage.content, query, word_prefix=True)
        if match == "message_prefix":
            # Rank only the owner's messages, then keep the latest matching message per chat.
            matching_messages = (
                select(
                    ChatMessage.id,
                    func.row_number()
                    .over(
                        partition_by=ChatMessage.session_id,
                        order_by=(ChatMessage.created_at.desc(), ChatMessage.id.desc()),
                    )
                    .label("position"),
                )
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatMessage.role == ChatRole.USER,
                    message_prefix,
                )
                .subquery()
            )
            statement = (
                select(ChatSession, ChatMessage)
                .join(ChatMessage, ChatMessage.session_id == ChatSession.id)
                .join(matching_messages, matching_messages.c.id == ChatMessage.id)
                .where(
                    ChatSession.user_id == user_id,
                    ~title_prefix,
                    matching_messages.c.position == 1,
                )
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            )
            result = await self.db.execute(statement.limit(limit).offset(offset))
            return [(row[0], row[1]) for row in result.all()]
        session_statement = select(ChatSession).where(ChatSession.user_id == user_id)
        if match == "title_prefix":
            session_statement = session_statement.where(title_prefix)
        else:
            has_matching_message = (
                select(ChatMessage.id)
                .where(
                    ChatMessage.session_id == ChatSession.id,
                    ChatMessage.role == ChatRole.USER,
                    message_prefix,
                )
                .exists()
            )
            session_statement = session_statement.where(
                text_search_match(ChatSession.title, query, word_prefix=False),
                ~title_prefix,
                ~has_matching_message,
            )
        sessions = await self.db.execute(
            session_statement.order_by(
                ChatSession.updated_at.desc(), ChatSession.id.desc()
            )
            .limit(limit)
            .offset(offset)
        )
        return [(session, None) for session in sessions.scalars().all()]

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

    async def create_session_with_messages(
        self,
        *,
        user_id: int,
        bula_id: UUID | None,
        first_question: str,
        answer: str,
        retrieval_mode: RetrievalMode,
        source_chunks: list[dict[str, str | float]],
        scope: ChatScope = ChatScope.BULA,
        catalog_scope: PublicCatalogScope = PublicCatalogScope.ALL,
    ) -> tuple[ChatSession, ChatMessage, ChatMessage]:
        chat_session = ChatSession(
            user_id=user_id,
            bula_id=bula_id,
            scope=scope.value,
            catalog_scope=catalog_scope.value,
            title=self._extract_title(first_question),
        )
        self.db.add(chat_session)
        await self.db.flush()

        user_message = ChatMessage(
            session=chat_session,
            role=ChatRole.USER,
            content=first_question,
            retrieval_mode=retrieval_mode,
        )
        self.db.add(user_message)
        await self.db.flush()

        assistant_message = ChatMessage(
            session=chat_session,
            role=ChatRole.ASSISTANT,
            content=answer,
            retrieval_mode=retrieval_mode,
            source_chunks=source_chunks,
        )
        self.db.add(assistant_message)

        try:
            await self.db.commit()
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise ChatPersistenceError() from exc

        await self.db.refresh(chat_session)
        await self.db.refresh(user_message)
        await self.db.refresh(assistant_message)
        return chat_session, user_message, assistant_message

    async def add_message(
        self,
        *,
        session_id: UUID,
        role: ChatRole,
        content: str,
        retrieval_mode: RetrievalMode | None = None,
        source_chunks: list[dict[str, str | float]] | None = None,
    ) -> ChatMessage:
        chat_message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            retrieval_mode=retrieval_mode,
            source_chunks=source_chunks or [],
        )
        self.db.add(chat_message)

        try:
            await self.db.commit()
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise ChatPersistenceError() from exc

        await self.db.refresh(chat_message)
        return chat_message

    async def add_turn(
        self,
        *,
        session: ChatSession,
        question: str,
        answer: str,
        retrieval_mode: RetrievalMode,
        source_chunks: list[dict[str, str | float]],
    ) -> tuple[ChatMessage, ChatMessage]:
        user_message = ChatMessage(
            session=session,
            role=ChatRole.USER,
            content=question,
            retrieval_mode=retrieval_mode,
        )
        assistant_message = ChatMessage(
            session=session,
            role=ChatRole.ASSISTANT,
            content=answer,
            retrieval_mode=retrieval_mode,
            source_chunks=source_chunks,
        )
        self.db.add_all([user_message, assistant_message])
        session.updated_at = datetime.now(timezone.utc)

        try:
            await self.db.commit()
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise ChatPersistenceError() from exc

        await self.db.refresh(user_message)
        await self.db.refresh(assistant_message)
        return user_message, assistant_message

    async def get_session_for_user(
        self,
        *,
        session_id: UUID,
        user_id: int,
    ) -> ChatSession | None:
        statement = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def update_session_for_user(
        self,
        *,
        session_id: UUID,
        user_id: int,
        title: str | None = None,
        is_pinned: bool | None = None,
    ) -> ChatSession | None:
        statement = (
            update(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .values(
                title=title if title is not None else ChatSession.title,
                is_pinned=is_pinned if is_pinned is not None else ChatSession.is_pinned,
                # Pinning is an organizational preference, not a new conversation turn.
                updated_at=datetime.now(timezone.utc)
                if title is not None
                else ChatSession.updated_at,
            )
            .returning(ChatSession)
            .execution_options(populate_existing=True)
        )
        try:
            result = await self.db.execute(statement)
            session = result.scalar_one_or_none()
            await self.db.commit()
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise ChatPersistenceError() from exc
        return session

    async def delete_session_for_user(self, *, session_id: UUID, user_id: int) -> bool:
        # The existing FK cascade removes only this conversation's messages.
        statement = (
            delete(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .returning(ChatSession.id)
        )
        try:
            result = await self.db.execute(statement)
            deleted_session_id = result.scalar_one_or_none()
            await self.db.commit()
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise ChatPersistenceError() from exc
        return deleted_session_id is not None

    async def get_session_history(self, *, session_id: UUID) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_recent_session_history(
        self,
        *,
        session_id: UUID,
        message_limit: int,
    ) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(message_limit)
        )
        result = await self.db.execute(statement)
        newest_first_messages = list(result.scalars().all())
        return list(reversed(newest_first_messages))

    async def list_user_sessions(
        self,
        *,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        scope: ChatScope | None = None,
        bula_id: UUID | None = None,
        sort: SessionSortOrder = "created_at",
        is_pinned: bool | None = None,
        query: str = "",
    ) -> list[ChatSession]:
        filters = [ChatSession.user_id == user_id]
        if query:
            filters.append(ChatSession.title.icontains(query, autoescape=True))
        if scope is not None:
            filters.append(ChatSession.scope == scope.value)
        if bula_id is not None:
            filters.append(ChatSession.bula_id == bula_id)
        if is_pinned is not None:
            filters.append(ChatSession.is_pinned == is_pinned)
        order_column = (
            ChatSession.updated_at if sort == "updated_at" else ChatSession.created_at
        )
        statement = (
            select(ChatSession)
            .where(*filters)
            .order_by(order_column.desc(), ChatSession.id.desc())
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
