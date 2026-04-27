from __future__ import annotations

import enum
from typing import TYPE_CHECKING

# Database representation (SQLAlchemy)
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from app.core.base import Base
from sqlalchemy.orm import relationship, Mapped

if TYPE_CHECKING:
    from app.modules.bulas.models import Bula
    from app.modules.chat.models import ChatSession


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    REVIEWER = "reviewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(
        Enum(
            UserRole,
            name="userrole",
            values_callable=lambda user_roles: [role.value for role in user_roles],
        ),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )

    bulas: Mapped[list["Bula"]] = relationship(
        "Bula",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
