from collections.abc import Sequence
from uuid import UUID

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.bm25_query_normalizer import BM25QueryNormalizer
from app.modules.rag.repository import ChunkMetadataRepository
from app.modules.rag.schemas import BM25SearchResult, ChunkMetadataInput


class PostgreSQLBM25Index:
    """Internal lexical index, not a user-facing authorization boundary.

    Future retrievers must authorize the bula before invoking search. A corpus
    filter alone does not enforce ownership or system publication state.
    """

    def __init__(self, repository: ChunkMetadataRepository) -> None:
        self.repository = repository
        self.query_normalizer = BM25QueryNormalizer()

    async def upsert_chunks(self, chunks: Sequence[ChunkMetadataInput]) -> int:
        self._validate_chunk_identities(chunks)
        if not chunks:
            return 0
        return await self.repository.upsert_chunks(chunks)

    async def replace_bula_chunks(
        self, *, bula_id: UUID, chunks: Sequence[ChunkMetadataInput]
    ) -> int:
        self._validate_chunk_identities(chunks)
        if not chunks:
            raise ValueError("Cannot replace a bula index with empty chunks.")
        if any(chunk.bula_id != bula_id for chunk in chunks):
            raise ValueError("Replacement chunks must belong to the selected bula.")
        return await self.repository.upsert_chunks(chunks, replace_bula_id=bula_id)

    async def search(
        self,
        query: str,
        *,
        k: int = 10,
        bula_id: UUID | None = None,
        corpus: Sequence[BulaCorpus] | None = None,
        include_administrative_sections: bool = True,
        include_document_metadata: bool = True,
    ) -> list[BM25SearchResult]:
        if k < 1 or k > 100:
            raise ValueError("k must be between 1 and 100.")
        if not query.strip() or corpus == [] or corpus == ():
            return []
        return await self.repository.search(
            query=self.query_normalizer.normalize(query),
            k=k,
            bula_id=bula_id,
            corpus=corpus,
            include_administrative_sections=include_administrative_sections,
            include_document_metadata=include_document_metadata,
        )

    async def find_section_evidence(
        self,
        *,
        bula_id: UUID,
        section_titles: Sequence[str],
        limit: int = 2,
    ) -> list[ChunkMetadataInput]:
        return await self.repository.find_section_evidence(
            bula_id=bula_id,
            section_titles=section_titles,
            limit=limit,
        )

    async def update_corpus(self, *, bula_id: UUID, corpus: BulaCorpus) -> None:
        await self.repository.update_corpus(bula_id=bula_id, corpus=corpus)

    def _validate_chunk_identities(self, chunks: Sequence[ChunkMetadataInput]) -> None:
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("Duplicate chunk identities in the same batch.")
        if any(chunk.doc_id != str(chunk.bula_id) for chunk in chunks):
            raise ValueError("Chunk document identity must match its bula.")
