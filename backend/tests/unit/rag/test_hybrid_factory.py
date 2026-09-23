from typing import cast
from uuid import UUID

import pytest
from langchain_core.embeddings import Embeddings as LCEmbeddings
from qdrant_client import AsyncQdrantClient

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.bm25_retriever import (
    BM25Retriever,
    BM25RetrieverFactory,
    BM25SearchIndex,
)
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.enriching_retriever import EnrichingRetriever
from app.modules.rag.hybrid_factory import HybridRetrieverFactory
from app.modules.rag.hybrid_retriever import HybridRetriever
from app.modules.rag.qdrant_store import QdrantVectorStore
from app.modules.rag.retriever import DenseBulaRetriever
from app.modules.rag.schemas import BM25SearchResult


class FakeEmbeddings(LCEmbeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _text in texts]

    def embed_query(self, text: str) -> list[float]:
        _ = text
        return [1.0]


class StubBM25Index:
    async def search(
        self,
        query: str,
        *,
        k: int = 10,
        bula_id: UUID | None = None,
        corpus: tuple[BulaCorpus, ...] | None = None,
    ) -> list[BM25SearchResult]:
        _ = query
        _ = k
        _ = bula_id
        _ = corpus
        return []


def build_factory() -> tuple[
    HybridRetrieverFactory,
    QdrantVectorStore,
    EmbeddingAdapter,
]:
    qdrant_store = QdrantVectorStore(
        client=cast(AsyncQdrantClient, object()),
        vector_size=1,
    )
    embeddings = EmbeddingAdapter(
        embedder=FakeEmbeddings(),
        batch_size=1,
        dimension=1,
    )
    bm25_factory = BM25RetrieverFactory(cast(BM25SearchIndex, StubBM25Index()))
    return (
        HybridRetrieverFactory(
            qdrant_store=qdrant_store,
            embeddings=embeddings,
            bm25_retriever_factory=bm25_factory,
        ),
        qdrant_store,
        embeddings,
    )


def test_factory_builds_scoped_overfetching_retrievers_and_enricher() -> None:
    factory, qdrant_store, embeddings = build_factory()
    bula_id = UUID("11111111-1111-1111-1111-111111111111")

    enriched_retriever = factory.build(bula_id=bula_id, k=4)

    assert isinstance(enriched_retriever, EnrichingRetriever)
    assert enriched_retriever.payload_store is qdrant_store
    hybrid_retriever = enriched_retriever.wrapped_retriever
    assert isinstance(hybrid_retriever, HybridRetriever)
    assert hybrid_retriever.k == 4
    dense_retriever, bm25_retriever = hybrid_retriever.retrievers
    assert isinstance(dense_retriever, DenseBulaRetriever)
    assert dense_retriever.bula_id == str(bula_id)
    assert dense_retriever.k == 8
    assert dense_retriever.qdrant_store is qdrant_store
    assert dense_retriever.embeddings is embeddings
    assert isinstance(bm25_retriever, BM25Retriever)
    assert bm25_retriever.bula_id == bula_id
    assert bm25_retriever.k == 8


@pytest.mark.parametrize("k", [0, 51])
def test_factory_bounds_final_result_count(k: int) -> None:
    factory, _, _ = build_factory()

    with pytest.raises(ValueError, match="between 1 and 50"):
        factory.build(bula_id=UUID(int=1), k=k)
