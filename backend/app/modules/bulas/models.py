from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class SystemBulaPublicationState(str, enum.Enum):
    STAGED = "staged"
    VETTED = "vetted"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"
    REJECTED = "rejected"


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
    system_publication: Mapped["SystemBulaPublication | None"] = relationship(
        "SystemBulaPublication",
        back_populates="bula",
        cascade="all, delete-orphan",
        foreign_keys="SystemBulaPublication.bula_id",
        uselist=False,
    )


class SystemBulaPublication(Base, TimestampMixin):
    """Immutable ANVISA provenance plus the local publication lifecycle."""

    __tablename__ = "system_bula_publications"

    bula_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bulas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    state: Mapped[SystemBulaPublicationState] = mapped_column(
        SqlEnum(
            SystemBulaPublicationState,
            name="systembulapublicationstate",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=SystemBulaPublicationState.STAGED,
        server_default=SystemBulaPublicationState.STAGED.value,
        index=True,
    )

    target_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    active_ingredient: Mapped[str] = mapped_column(String(500), nullable=False)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    strength: Mapped[str] = mapped_column(String(255), nullable=False)
    pharmaceutical_form: Mapped[str] = mapped_column(String(500), nullable=False)
    presentation: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(20), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(500), nullable=False)
    company_tax_id: Mapped[str] = mapped_column(String(32), nullable=False)
    anvisa_product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    process_number: Mapped[str] = mapped_column(String(100), nullable=False)
    expedition_number: Mapped[str] = mapped_column(String(100), nullable=False)
    transaction_number: Mapped[str] = mapped_column(String(100), nullable=False)
    source_record_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    canonical_source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    search_query: Mapped[str] = mapped_column(String(500), nullable=False)
    downloader_version: Mapped[str] = mapped_column(String(100), nullable=False)
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    withdrawal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    supersedes_bula_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bulas.id", ondelete="SET NULL"),
        nullable=True,
    )

    bula: Mapped["Bula"] = relationship(
        "Bula",
        back_populates="system_publication",
        foreign_keys=[bula_id],
    )
