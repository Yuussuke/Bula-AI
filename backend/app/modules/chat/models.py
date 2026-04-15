import uuid
import enum
from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, UUIDMixin, TimestampMixin

class RetrievalMode(str, enum.Enum):
    DENSE = "dense"
    BM25 = "bm25"
    HYBRID = "hybrid"

class ChatRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_sessions"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    bula_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bulas.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")

    bula: Mapped["Bula"] = relationship("Bula", back_populates="chat_sessions")
    
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
    )
    
    role: Mapped[ChatRole] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    retrieval_mode: Mapped[RetrievalMode | None] = mapped_column(nullable=True) 

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")