from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Float, case, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.models import ChunkMetadata
from app.modules.rag.schemas import BM25SearchResult, ChunkMetadataInput
from app.modules.rag.section_titles import (
    ADMINISTRATIVE_SECTION_PATTERN,
    NUMBERED_SECTION_PREFIX_PATTERN,
    normalize_section_title,
)


class ChunkIndexPersistenceError(RuntimeError):
    """Safe worker/operator error; never includes SQL parameters or source text."""


class ChunkMetadataRepository:
    """PostgreSQL persistence only. Access authorization belongs to the caller."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_chunks(
        self,
        chunks: Sequence[ChunkMetadataInput],
        *,
        replace_bula_id: UUID | None = None,
    ) -> int:
        try:
            # Bounded statements stay below asyncpg's bind-parameter limit.
            for offset in range(0, len(chunks), 100):
                batch = chunks[offset : offset + 100]
                values = [chunk.model_dump() for chunk in batch]
                statement = insert(ChunkMetadata).values(values)
                upsert_statement = statement.on_conflict_do_update(
                    index_elements=[ChunkMetadata.chunk_id],
                    set_={
                        name: getattr(statement.excluded, name)
                        for name in (
                            "doc_id",
                            "corpus",
                            "drug_name",
                            "section_title",
                            "chunk_text",
                        )
                    },
                    # A collision must never move an existing chunk to another bula.
                    where=ChunkMetadata.bula_id == statement.excluded.bula_id,
                ).returning(ChunkMetadata.chunk_id)
                result = await self.db.execute(upsert_statement)
                if len(result.scalars().all()) != len(batch):
                    raise ValueError("Chunk identity belongs to another bula.")

            if replace_bula_id is not None:
                # Remove stale chunks in the SAME transaction as the replacement.
                await self.db.execute(
                    delete(ChunkMetadata).where(
                        ChunkMetadata.bula_id == replace_bula_id,
                        ChunkMetadata.chunk_id.not_in(
                            [chunk.chunk_id for chunk in chunks]
                        ),
                    )
                )
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise ChunkIndexPersistenceError(
                "PostgreSQL BM25 index write failed."
            ) from None
        except Exception:
            await self.db.rollback()
            raise
        return len(chunks)

    async def search(
        self,
        *,
        query: str,
        k: int,
        bula_id: UUID | None,
        corpus: Sequence[BulaCorpus] | None,
        include_administrative_sections: bool = True,
    ) -> list[BM25SearchResult]:
        # ATX headings alone are navigation, not answer evidence. Filter before
        # top-k so even many short heading-only matches cannot consume slots.
        # Only the eligibility expression is cleaned; source text stays intact.
        text_without_headings = func.regexp_replace(
            ChunkMetadata.chunk_text,
            r"^[ \t]{0,3}#{1,6}([ \t]+[^\r\n]*|[ \t]*$)",
            "",
            "gn",
        )
        has_body = (
            func.regexp_replace(text_without_headings, r"[[:space:]]", "", "g") != ""
        )
        candidates = select(ChunkMetadata).where(has_body)
        if not include_administrative_sections:
            # Eligibility precedes the lexical top-k; filtering afterwards
            # cannot recover a valid chunk displaced by administrative matches.
            candidates = candidates.where(
                ~self._section_title_key().regexp_match(ADMINISTRATIVE_SECTION_PATTERN)
            )
        if bula_id is not None:
            candidates = candidates.where(ChunkMetadata.bula_id == bula_id)
        if corpus is not None:
            candidates = candidates.where(ChunkMetadata.corpus.in_(corpus))

        # pg_textsearch 1.1 can post-filter an index top-k scan. Materialize the
        # scope FIRST so unrelated bulas cannot crowd out eligible results.
        scoped_chunks = candidates.cte("scoped_chunks").prefix_with("MATERIALIZED")
        # An uncorrelated scalar subquery avoids normalizing for every candidate.
        normalized_query = select(
            func.public.bula_bm25_normalize_v2(query)
        ).scalar_subquery()
        bm25_query = func.to_bm25query(normalized_query, "public.ix_chunk_meta_bm25")
        distance = scoped_chunks.c.search_text.op("<@>", return_type=Float)(bm25_query)
        # The extension returns NEGATIVE BM25 scores (lower is better).
        score = (-distance).label("bm25_score")
        statement = (
            select(
                scoped_chunks.c.chunk_id,
                scoped_chunks.c.doc_id,
                scoped_chunks.c.bula_id,
                scoped_chunks.c.corpus,
                scoped_chunks.c.drug_name,
                scoped_chunks.c.section_title,
                scoped_chunks.c.chunk_text,
                score,
            )
            .where(distance < 0)
            .order_by(distance.asc(), scoped_chunks.c.chunk_id.asc())
            .limit(k)
        )
        result = await self.db.execute(statement)
        return [BM25SearchResult.model_validate(row) for row in result.mappings()]

    async def find_section_evidence(
        self,
        *,
        bula_id: UUID,
        section_titles: Sequence[str],
        limit: int,
    ) -> list[ChunkMetadataInput]:
        """Read bounded source chunks from named sections of one authorized bula."""
        if not section_titles or limit < 1:
            return []

        normalized_titles = [normalize_section_title(title) for title in section_titles]
        normalized_section = self._section_title_key()
        text_without_headings = func.regexp_replace(
            ChunkMetadata.chunk_text,
            r"^[ \t]{0,3}#{1,6}([ \t]+[^\r\n]*|[ \t]*$)",
            "",
            "gn",
        )
        has_body = (
            func.regexp_replace(text_without_headings, r"[[:space:]]", "", "g") != ""
        )
        section_priority = case(
            *(
                (normalized_section == title, priority)
                for priority, title in enumerate(normalized_titles)
            ),
            else_=len(normalized_titles),
        )
        statement = (
            select(ChunkMetadata)
            .where(ChunkMetadata.bula_id == bula_id)
            .where(normalized_section.in_(normalized_titles))
            .where(has_body)
            .order_by(section_priority, ChunkMetadata.chunk_id)
            .limit(limit)
        )
        result = await self.db.execute(statement)
        return [
            ChunkMetadataInput.model_validate(chunk, from_attributes=True)
            for chunk in result.scalars()
            if chunk.chunk_text.strip()
        ]

    def _section_title_key(self) -> ColumnElement[str]:
        """Match normalized identity without changing stored/source headings."""
        title_without_number = func.regexp_replace(
            func.btrim(ChunkMetadata.section_title),
            NUMBERED_SECTION_PREFIX_PATTERN,
            "",
        )
        collapsed_title = func.regexp_replace(
            title_without_number, "[[:space:]]+", " ", "g"
        )
        return func.lower(func.public.unaccent(func.btrim(collapsed_title)))

    async def update_corpus(self, *, bula_id: UUID, corpus: BulaCorpus) -> None:
        try:
            await self.db.execute(
                update(ChunkMetadata)
                .where(ChunkMetadata.bula_id == bula_id)
                .values(corpus=corpus.value)
            )
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise ChunkIndexPersistenceError(
                "PostgreSQL BM25 corpus update failed."
            ) from None
        except Exception:
            await self.db.rollback()
            raise
