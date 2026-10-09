import re
from types import SimpleNamespace

import pytest
from langchain_core.embeddings import Embeddings as LCEmbeddings
from qdrant_client.models import Filter, ScoredPoint

from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.qdrant_store import QdrantVectorStore
from app.modules.rag.retriever import DenseBulaRetriever, SYNC_RETRIEVER_ERROR


class FakeEmbeddings(LCEmbeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        _ = text
        return [1.0, 0.0, 0.0, 0.0]


class FakeQdrantStore(QdrantVectorStore):
    def __init__(self, *, points: list[ScoredPoint] | None = None) -> None:
        self.query_filter: Filter | None = None
        self.requested_limit: int | None = None
        self.collection_name = "fake_collection"
        self.vector_size = 4
        self.points = points or [build_scored_point()]

    async def search_similar(
        self,
        *,
        vector: list[float],
        limit: int = 5,
        query_filter: Filter | None = None,
    ) -> SimpleNamespace:
        _ = vector
        self.requested_limit = limit
        self.query_filter = query_filter
        return SimpleNamespace(points=self.points)


def build_scored_point(
    *,
    point_id: str = "point-1",
    chunk_id: str = "chunk-1",
    chunk_text: str = "Dose usual: 1 comprimido.",
    score: float = 0.93,
    section_title: str = "Posologia",
) -> ScoredPoint:
    return ScoredPoint(
        id=point_id,
        version=0,
        score=score,
        payload={
            "bula_id": "bula-123",
            "chunk_id": chunk_id,
            "chunk_text": chunk_text,
            "drug_name": "Dipirona",
            "section_title": section_title,
            "chunk_index": 0,
            "manufacturer": "Example Pharma",
            "corpus": "private",
            "embedding_profile": "unspecified;input=plain-v1",
        },
    )


def build_embedding_adapter() -> EmbeddingAdapter:
    return EmbeddingAdapter(
        embedder=FakeEmbeddings(),
        batch_size=1,
        dimension=4,
    )


@pytest.mark.anyio
async def test_metadata_does_not_displace_evidence_and_remains_discoverable() -> None:
    metadata = build_scored_point(
        chunk_id="identity", chunk_text='---\nproduct: "Produto"\n---', score=0.99
    )
    evidence = build_scored_point(
        chunk_id="evidence", chunk_text="Guarde na embalagem original.", score=0.8
    )
    store = FakeQdrantStore(points=[metadata, evidence])
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        k=1,
        qdrant_store=store,
        embeddings=build_embedding_adapter(),
    )
    assert [
        document.metadata["chunk_id"]
        for document in await retriever.ainvoke("Como guardar?")
    ] == ["evidence"]
    discovery = retriever.model_copy(update={"include_document_metadata": True})
    assert [
        document.metadata["chunk_id"] for document in await discovery.ainvoke("Produto")
    ] == ["identity"]
    assert metadata.payload["chunk_text"] == '---\nproduct: "Produto"\n---'


@pytest.mark.anyio
async def test_retriever_returns_section_metadata() -> None:
    qdrant_store = FakeQdrantStore()
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        qdrant_store=qdrant_store,
        embeddings=build_embedding_adapter(),
    )

    documents = await retriever.ainvoke("Como tomar?")

    assert len(documents) == 1
    assert documents[0].page_content == "Dose usual: 1 comprimido."
    assert documents[0].metadata == {
        "section_title": "Posologia",
        "chunk_id": "chunk-1",
        "drug_name": "Dipirona",
        "bula_id": "bula-123",
        "chunk_index": 0,
        "manufacturer": "Example Pharma",
        "corpus": "private",
        "score": 0.93,
    }
    assert qdrant_store.requested_limit == 12
    assert qdrant_store.query_filter is not None
    assert len(qdrant_store.query_filter.must or []) == 2


@pytest.mark.anyio
async def test_retriever_skips_heading_only_candidates() -> None:
    qdrant_store = FakeQdrantStore(
        points=[
            build_scored_point(
                point_id="heading-point",
                chunk_id="heading-chunk",
                chunk_text="## INFORMACOES AO PACIENTE",
                score=0.98,
            ),
            build_scored_point(
                point_id="evidence-point",
                chunk_id="evidence-chunk",
                chunk_text=(
                    "## ADVERTENCIAS\n"
                    "Este medicamento contem acucar e requer orientacao profissional."
                ),
                score=0.91,
            ),
        ]
    )
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        qdrant_store=qdrant_store,
        embeddings=build_embedding_adapter(),
    )

    documents = await retriever.ainvoke("Pode ser usado por pessoas com diabetes?")

    assert [document.metadata["chunk_id"] for document in documents] == [
        "evidence-chunk"
    ]


def test_retriever_rejects_invalid_candidate_multiplier() -> None:
    with pytest.raises(ValueError, match="candidate_multiplier must be >= 1"):
        DenseBulaRetriever(
            bula_id="bula-123",
            candidate_multiplier=0,
            qdrant_store=FakeQdrantStore(),
            embeddings=build_embedding_adapter(),
        )


@pytest.mark.anyio
async def test_administrative_candidates_do_not_displace_answer_evidence() -> None:
    administrative_points = [
        build_scored_point(
            point_id=f"admin-point-{number}",
            chunk_id=f"admin-chunk-{number}",
            section_title=section_title,
            chunk_text="Registro documental com conteúdo, não apenas heading.",
        )
        for number, section_title in enumerate(
            (
                "Histórico de alteração para a bula",
                "9. DIZERES LEGAIS",
                "VENDA SOB PRESCRIÇÃO COM RETENÇÃO DA RECEITA",
            )
        )
    ]
    source_text = "A bula informa que a avaliação deve ser feita pelo médico."
    evidence_point = build_scored_point(
        chunk_id="evidence", section_title="4. Advertências", chunk_text=source_text
    )
    store = FakeQdrantStore(points=[*administrative_points, evidence_point])
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        k=2,
        qdrant_store=store,
        embeddings=build_embedding_adapter(),
    )

    documents = await retriever.ainvoke("O que a bula informa?")

    assert [document.metadata["chunk_id"] for document in documents] == ["evidence"]
    assert documents[0].metadata["section_title"] == "4. Advertências"
    assert documents[0].page_content == source_text
    assert store.requested_limit == 12


@pytest.mark.anyio
async def test_multiplier_mode_remains_an_explicit_candidate_budget_option() -> None:
    store = FakeQdrantStore()
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        k=2,
        candidate_limit=None,
        candidate_multiplier=3,
        qdrant_store=store,
        embeddings=build_embedding_adapter(),
    )
    documents = await retriever.ainvoke("Pergunta documental")
    assert documents[0].metadata["chunk_id"] == "chunk-1"
    assert store.requested_limit == 6


@pytest.mark.anyio
async def test_administrative_sources_remain_available_when_explicitly_requested() -> (
    None
):
    store = FakeQdrantStore(
        points=[
            build_scored_point(
                section_title="Histórico de alteração para a bula",
                chunk_text="Registro da submissão eletrônica.",
            )
        ]
    )
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        qdrant_store=store,
        embeddings=build_embedding_adapter(),
    )

    assert await retriever.ainvoke("submissão") == []
    documents = await retriever.model_copy(
        update={"include_administrative_sections": True}
    ).ainvoke("submissão")
    assert (
        documents[0].metadata["section_title"] == "Histórico de alteração para a bula"
    )
    assert documents[0].page_content == "Registro da submissão eletrônica."


def test_retriever_rejects_invalid_k() -> None:
    with pytest.raises(ValueError, match="k must be >= 1"):
        DenseBulaRetriever(
            bula_id="bula-123",
            k=0,
            qdrant_store=FakeQdrantStore(),
            embeddings=build_embedding_adapter(),
        )


def test_dense_retriever_rejects_an_unscoped_search() -> None:
    with pytest.raises(ValueError, match="explicit corpus scope"):
        DenseBulaRetriever(
            qdrant_store=FakeQdrantStore(),
            embeddings=build_embedding_adapter(),
        )


@pytest.mark.anyio
async def test_empty_corpus_does_not_query_qdrant() -> None:
    store = FakeQdrantStore()
    adapter = build_embedding_adapter()
    retriever = DenseBulaRetriever(corpus=(), qdrant_store=store, embeddings=adapter)

    assert await retriever.ainvoke("Como tomar?") == []
    assert store.query_filter is None
    assert store.requested_limit is None


def test_retriever_sync_path_rejects_direct_use() -> None:
    retriever = DenseBulaRetriever(
        bula_id="bula-123",
        qdrant_store=FakeQdrantStore(),
        embeddings=build_embedding_adapter(),
    )

    with pytest.raises(RuntimeError, match=re.escape(SYNC_RETRIEVER_ERROR)):
        retriever.invoke("Como tomar?")


def test_raw_candidate_limit_cannot_be_smaller_than_final_cut() -> None:
    with pytest.raises(ValueError, match="candidate_limit must be >= k"):
        DenseBulaRetriever(
            bula_id="bula-123",
            candidate_limit=9,
            qdrant_store=FakeQdrantStore(),
            embeddings=build_embedding_adapter(),
        )


@pytest.mark.anyio
async def test_default_dense_cut_returns_ten_sources_without_expanding_raw_pool() -> (
    None
):
    points = [build_scored_point(chunk_id=f"chunk-{index}") for index in range(12)]
    store = FakeQdrantStore(points=points)
    retriever = DenseBulaRetriever(
        bula_id="bula-123", qdrant_store=store, embeddings=build_embedding_adapter()
    )
    documents = await retriever.ainvoke("Pergunta documental")
    assert [document.metadata["chunk_id"] for document in documents] == [
        f"chunk-{index}" for index in range(10)
    ]
    assert store.requested_limit == 12
