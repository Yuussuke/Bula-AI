from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    FetchedValue,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class ChunkMetadata(Base):
    """Source text for lexical retrieval; chunk_id is NOT the Qdrant point UUID."""

    __tablename__ = "chunk_meta"
    __table_args__ = (
        CheckConstraint(
            "corpus IN ('private', 'system', 'shared')", name="valid_corpus"
        ),
        Index("ix_chunk_meta_bula_id", "bula_id"),
        Index("ix_chunk_meta_corpus", "corpus"),
        Index(
            "ix_chunk_meta_bm25",
            "search_text",
            postgresql_using="bm25",
            postgresql_with={"text_config": "'pg_catalog.simple'"},
        ).ddl_if(dialect="postgresql"),
    )

    chunk_id: Mapped[str] = mapped_column(Text, primary_key=True)
    doc_id: Mapped[str] = mapped_column(Text)
    bula_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("bulas.id", ondelete="CASCADE"), nullable=False
    )
    corpus: Mapped[str] = mapped_column(String(20))
    drug_name: Mapped[str | None] = mapped_column(Text)
    section_title: Mapped[str] = mapped_column(Text)
    chunk_text: Mapped[str] = mapped_column(Text)
    # PostgreSQL trigger derives this from chunk_text; never exposed as a source.
    search_text: Mapped[str] = mapped_column(
        Text, server_default=FetchedValue(), server_onupdate=FetchedValue()
    )
