from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.chat.models import ChatSession


class BulaStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ERROR = "error"


class BulaCorpus(str, enum.Enum):
    PRIVATE = "private"
    SYSTEM = "system"
    SHARED = "shared"


def _enum_values(enum_class: type[enum.Enum]) -> list[str]:
    return [str(member.value) for member in enum_class]


class Bula(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bulas"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    drug_name: Mapped[str] = mapped_column(String, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String, nullable=True)
    file_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    qdrant_collection: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    status: Mapped[BulaStatus] = mapped_column(
        SqlEnum(BulaStatus, name="bulastatus"),
        nullable=False,
        default=BulaStatus.PENDING,
    )
    corpus: Mapped[BulaCorpus] = mapped_column(
        SqlEnum(
            BulaCorpus,
            name="bulacorpus",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=BulaCorpus.PRIVATE,
        server_default=BulaCorpus.PRIVATE.value,
    )

    user: Mapped["User"] = relationship("User", back_populates="bulas")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="bula"
    )
