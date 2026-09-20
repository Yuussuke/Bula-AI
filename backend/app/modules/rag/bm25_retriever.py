"""Async LangChain adapter for the persistent lexical index."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.schemas import BM25SearchResult


@runtime_checkable
class BM25SearchIndex(Protocol):
    """Read-only contract; SQL and normalization belong to the index."""

    async def search(
        self,
        query: str,
        *,
        k: int = 10,
        bula_id: UUID | None = None,
        corpus: Sequence[BulaCorpus] | None = None,
    ) -> list[BM25SearchResult]: ...


class BM25Retriever(BaseRetriever):
    """Retrieve original chunks without embeddings or LLM calls.

    Internal component, not an authorization boundary. Callers must authorize
    the selected bula/corpus before constructing a retriever. An omitted scope
    searches the whole index, including private chunks.

    Use ainvoke; like DenseBulaRetriever, synchronous invoke is unsupported.
    Instances backed by one AsyncSession must not run concurrent queries;
    batch callers should use max_concurrency=1 or separate scoped sessions.
    """

    index: BM25SearchIndex = Field(exclude=True, repr=False)
    k: int = Field(default=10, ge=1, le=100)
    bula_id: UUID | None = None
    corpus: tuple[BulaCorpus, ...] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        if not query.strip() or self.corpus == ():
            return []

        results = await self.index.search(
            query, k=self.k, bula_id=self.bula_id, corpus=self.corpus
        )
        # Preserve the index ranking, original source text, and chunk identities.
        return [self._to_document(result) for result in results]

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        raise RuntimeError("BM25Retriever requires async ainvoke().")

    def _to_document(self, result: BM25SearchResult) -> Document:
        return Document(
            id=result.chunk_id,
            page_content=result.chunk_text,
            metadata={
                "chunk_id": result.chunk_id,
                "doc_id": result.doc_id,
                "bula_id": str(result.bula_id),
                "corpus": result.corpus.value,
                "drug_name": result.drug_name,
                "section_title": result.section_title,
                # Existing chain consumers read score; retain the algorithm's
                # explicit name too. Neither value is a probability or cosine.
                "score": result.bm25_score,
                "bm25_score": result.bm25_score,
            },
        )


class BM25RetrieverFactory:
    """Request-scoped factory; does not cache the injected index/session."""

    def __init__(self, index: BM25SearchIndex) -> None:
        self.index = index

    def build(
        self,
        *,
        bula_id: UUID | None,
        corpus: Sequence[BulaCorpus] | None = None,
        k: int = 10,
    ) -> BM25Retriever:
        return BM25Retriever(
            index=self.index,
            bula_id=bula_id,
            corpus=tuple(corpus) if corpus is not None else None,
            k=k,
        )
