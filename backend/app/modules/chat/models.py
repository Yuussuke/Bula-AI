from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
    Uuid,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, UUIDMixin, TimestampMixin
from app.modules.rag.retrieval_mode import RetrievalMode

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.bulas.models import Bula


class ChatRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatScope(str, enum.Enum):
    BULA = "bula"
    CROSS_BULA = "cross_bula"


class ChatSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        CheckConstraint("scope IN ('bula', 'cross_bula')", name="valid_chat_scope"),
        CheckConstraint(
            "catalog_scope IN ('all', 'system', 'shared')", name="valid_catalog_scope"
        ),
        CheckConstraint(
            "scope = 'cross_bula' OR catalog_scope = 'all'",
            name="individual_catalog_scope",
        ),
        CheckConstraint(
            "scope != 'cross_bula' OR bula_id IS NULL",
            name="cross_bula_without_document",
        ),
    )
    scope: Mapped[str] = mapped_column(
        String(20), default=ChatScope.BULA.value, server_default=ChatScope.BULA.value
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    catalog_scope: Mapped[str] = mapped_column(
        String(10), default="all", server_default="all"
    )
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )

    bula_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bulas.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")

    bula: Mapped["Bula"] = relationship("Bula", back_populates="chat_sessions")

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('USER', 'ASSISTANT')",
            name="role_user_assistant",
        ),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
    )

    role: Mapped[ChatRole] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    retrieval_mode: Mapped[RetrievalMode | None] = mapped_column(nullable=True)
    source_chunks: Mapped[list[dict[str, str | float]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )
