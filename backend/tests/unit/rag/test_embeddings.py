import pytest
from langchain_core.embeddings import Embeddings as LCEmbeddings

from app.modules.rag.embeddings import EmbeddingAdapter


class FakeEmbeddings(LCEmbeddings):
    def __init__(self, *, dimension: int = 1024) -> None:
        self.dimension = dimension
        self.document_batches: list[list[str]] = []
        self.query_texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_batches.append(list(texts))
        return [[1.0] * self.dimension for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_texts.append(text)
        return [1.0] * self.dimension


def test_embed_documents_respects_batch_size() -> None:
    fake_embedder = FakeEmbeddings(dimension=1024)
    adapter = EmbeddingAdapter(
        embedder=fake_embedder,
        batch_size=32,
        dimension=1024,
    )
    texts = [f"texto {index}" for index in range(100)]

    vectors = adapter.embed_documents(texts)

    assert len(fake_embedder.document_batches) == 4
    assert [len(batch) for batch in fake_embedder.document_batches] == [32, 32, 32, 4]
    assert len(vectors) == len(texts)
    assert all(len(vector) == 1024 for vector in vectors)


def test_embed_documents_rejects_wrong_vector_dimension() -> None:
    fake_embedder = FakeEmbeddings(dimension=3)
    adapter = EmbeddingAdapter(
        embedder=fake_embedder,
        batch_size=32,
        dimension=1024,
    )

    with pytest.raises(ValueError, match="expected 1024"):
        adapter.embed_documents(["texto com dimensao errada"])


def test_embed_query_rejects_wrong_vector_dimension() -> None:
    fake_embedder = FakeEmbeddings(dimension=3)
    adapter = EmbeddingAdapter(
        embedder=fake_embedder,
        batch_size=32,
        dimension=1024,
    )

    with pytest.raises(ValueError, match="expected 1024"):
        adapter.embed_query("texto com dimensao errada")
