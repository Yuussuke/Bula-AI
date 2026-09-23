"""Request-scoped construction of the hybrid retrieval strategy."""

from uuid import UUID

from app.modules.rag.bm25_retriever import BM25RetrieverFactory
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.enriching_retriever import EnrichingRetriever
from app.modules.rag.hybrid_retriever import HybridRetriever
from app.modules.rag.qdrant_store import QdrantVectorStore
from app.modules.rag.retriever import DenseBulaRetriever


HYBRID_CANDIDATE_MULTIPLIER = 2
MAX_HYBRID_RESULTS = 50


class HybridRetrieverFactory:
    """Build one authorized bula-scoped hybrid retriever per request."""

    def __init__(
        self,
        *,
        qdrant_store: QdrantVectorStore,
        embeddings: EmbeddingAdapter,
        bm25_retriever_factory: BM25RetrieverFactory,
    ) -> None:
        self.qdrant_store = qdrant_store
        self.embeddings = embeddings
        self.bm25_retriever_factory = bm25_retriever_factory

    def build(
        self,
        *,
        bula_id: UUID,
        k: int = 4,
    ) -> EnrichingRetriever:
        if k < 1 or k > MAX_HYBRID_RESULTS:
            raise ValueError(f"k must be between 1 and {MAX_HYBRID_RESULTS}.")

        candidate_k = k * HYBRID_CANDIDATE_MULTIPLIER
        dense_retriever = DenseBulaRetriever(
            bula_id=str(bula_id),
            k=candidate_k,
            qdrant_store=self.qdrant_store,
            embeddings=self.embeddings,
        )
        bm25_retriever = self.bm25_retriever_factory.build(
            bula_id=bula_id,
            k=candidate_k,
        )
        hybrid_retriever = HybridRetriever.from_retrievers(
            dense_retriever=dense_retriever,
            bm25_retriever=bm25_retriever,
            k=k,
        )
        return EnrichingRetriever(
            wrapped_retriever=hybrid_retriever,
            payload_store=self.qdrant_store,
        )
