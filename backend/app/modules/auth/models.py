from __future__ import annotations

import enum
from typing import TYPE_CHECKING

# Database representation (SQLAlchemy)
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    UniqueConstraint,
)
from app.core.base import Base, UUIDMixin
from datetime import UTC, datetime
from sqlalchemy.orm import relationship, Mapped

if TYPE_CHECKING:
    from app.modules.bulas.models import Bula
    from app.modules.chat.models import ChatSession


class UserRole(str, enum.Enum):
    USER = "user"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"
    REVIEWER = "reviewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role: Column[UserRole] = Column(
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


class UserRoleAssignment(Base, UUIDMixin):
    """Administrative designation, not automated verification of qualifications."""

    __tablename__ = "user_role_assignments"
    __table_args__ = (
        UniqueConstraint("actor_id", "operation_id", name="uq_role_actor_operation"),
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    actor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_name = Column(Text, nullable=True)
    actor_role = Column(String(20), nullable=True)
    operation_id = Column(Uuid, nullable=True)
    request_fingerprint = Column(String(64), nullable=True)
    previous_role = Column(String(20), nullable=False)
    assigned_role = Column(String(20), nullable=False)
    reason = Column(String(1000), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
