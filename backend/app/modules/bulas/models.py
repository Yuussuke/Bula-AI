import enum

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from app.core.base import Base, UUIDMixin, TimestampMixin

class BulaStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

class Bula(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bulas"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    
    drug_name: Mapped[str] = mapped_column(String, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String, nullable=True)
    file_url: Mapped[str] = mapped_column(String)
    qdrant_collection: Mapped[str | None] = mapped_column(String, nullable=True)
    
    status: Mapped[BulaStatus] = mapped_column(default=BulaStatus.PENDING)

    user: Mapped["User"] = relationship("User", back_populates="bulas")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="bula")