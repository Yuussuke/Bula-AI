from __future__ import annotations

from typing import TYPE_CHECKING

# Database representation (SQLAlchemy)
from sqlalchemy import Column, Integer, String, Boolean
from app.core.base import Base
from sqlalchemy.orm import relationship, Mapped

if TYPE_CHECKING:
    from app.modules.bulas.models import Bula
    from app.modules.chat.models import ChatSession


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    bulas: Mapped[list["Bula"]] = relationship(
        "Bula", back_populates="user", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
