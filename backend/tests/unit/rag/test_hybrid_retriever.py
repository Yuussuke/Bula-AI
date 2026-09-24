from __future__ import annotations

from typing import Any

import pytest
from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from app.modules.rag.hybrid_retriever import (
    HybridRetriever,
    HybridRetrieverContractError,
    RRF_CONSTANT,
)


class StaticRetriever(BaseRetriever):
    documents: list[Document]
    received_queries: list[str] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = run_manager
        self.received_queries.append(query)
        return self.documents

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = query
        _ = run_manager
        raise RuntimeError("StaticRetriever requires async ainvoke().")


class FailingRetriever(BaseRetriever):
    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = query
        _ = run_manager
        raise TimeoutError("retriever timed out")

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = query
        _ = run_manager
        raise RuntimeError("FailingRetriever requires async ainvoke().")


def make_document(
    chunk_id: str | None,
    *,
    content: str | None = None,
    score: Any = None,
    **metadata: object,
) -> Document:
    document_metadata: dict[str, object] = dict(metadata)
    if chunk_id is not None:
        document_metadata["chunk_id"] = chunk_id
    if score is not None:
        document_metadata["score"] = score
    return Document(
        id=chunk_id,
        page_content=content or f"Conteudo de {chunk_id}",
        metadata=document_metadata,
    )


def build_hybrid(
    dense_documents: list[Document],
    bm25_documents: list[Document],
    *,
    k: int = 10,
) -> tuple[HybridRetriever, StaticRetriever, StaticRetriever]:
    dense_retriever = StaticRetriever(documents=dense_documents)
    bm25_retriever = StaticRetriever(documents=bm25_documents)
    hybrid = HybridRetriever.from_retrievers(
        dense_retriever=dense_retriever,
        bm25_retriever=bm25_retriever,
        k=k,
    )
    return hybrid, dense_retriever, bm25_retriever


@pytest.mark.anyio
async def test_rrf_combines_rankings_and_boosts_shared_chunks() -> None:
    dense_documents = [
        make_document("a", score=0.91, manufacturer="Sanofi"),
        make_document("b", score=0.82),
        make_document("c", score=0.73),
    ]
    bm25_documents = [
        make_document("b", score=4.2, doc_id="bula-1"),
        make_document("a", score=3.7, doc_id="bula-1"),
        make_document("d", score=2.1),
    ]
    hybrid, dense_retriever, bm25_retriever = build_hybrid(
        dense_documents,
        bm25_documents,
    )

    documents = await hybrid.ainvoke("qual a dose")

    expected_shared_score = (1.0 / (RRF_CONSTANT + 1)) + (1.0 / (RRF_CONSTANT + 2))
    expected_single_score = 1.0 / (RRF_CONSTANT + 3)
    assert [document.id for document in documents] == ["a", "b", "c", "d"]
    assert documents[0].metadata["rrf_score"] == pytest.approx(expected_shared_score)
    assert documents[1].metadata["rrf_score"] == pytest.approx(expected_shared_score)
    assert documents[2].metadata["rrf_score"] == pytest.approx(expected_single_score)
    assert documents[3].metadata["rrf_score"] == pytest.approx(expected_single_score)
    assert documents[0].metadata == {
        "chunk_id": "a",
        "manufacturer": "Sanofi",
        "doc_id": "bula-1",
        "dense_score": 0.91,
        "bm25_score": 3.7,
        "score": pytest.approx(expected_shared_score),
        "rrf_score": pytest.approx(expected_shared_score),
        "retrieval_sources": ["dense", "bm25"],
        "dense_rank": 1,
        "bm25_rank": 2,
    }
    assert dense_retriever.received_queries == ["qual a dose"]
    assert bm25_retriever.received_queries == ["qual a dose"]


@pytest.mark.anyio
async def test_rrf_deduplicates_and_limits_final_results() -> None:
    hybrid, _, _ = build_hybrid(
        [make_document("a"), make_document("b"), make_document("c")],
        [make_document("b"), make_document("d"), make_document("a")],
        k=2,
    )

    documents = await hybrid.ainvoke("pergunta")

    assert len(documents) == 2
    assert {document.id for document in documents} == {"a", "b"}


@pytest.mark.anyio
async def test_rrf_returns_empty_when_both_rankings_are_empty() -> None:
    hybrid, _, _ = build_hybrid([], [])

    documents = await hybrid.ainvoke("pergunta")

    assert documents == []


@pytest.mark.anyio
async def test_rrf_propagates_child_retriever_failures() -> None:
    hybrid = HybridRetriever.from_retrievers(
        dense_retriever=FailingRetriever(),
        bm25_retriever=StaticRetriever(documents=[]),
    )

    with pytest.raises(TimeoutError, match="retriever timed out"):
        await hybrid.ainvoke("pergunta")


@pytest.mark.anyio
async def test_rrf_ties_are_deterministic_and_prefer_dense_first_seen_order() -> None:
    hybrid, _, _ = build_hybrid(
        [make_document("dense-only")],
        [make_document("bm25-only")],
    )

    first_run = await hybrid.ainvoke("pergunta")
    second_run = await hybrid.ainvoke("pergunta")

    assert [document.id for document in first_run] == [
        "dense-only",
        "bm25-only",
    ]
    assert [document.id for document in second_run] == [
        "dense-only",
        "bm25-only",
    ]


@pytest.mark.anyio
async def test_rrf_does_not_mutate_child_documents() -> None:
    dense_document = make_document("shared", score=0.9)
    bm25_document = make_document("shared", score=2.5, doc_id="bula-1")
    original_dense_metadata = dense_document.metadata.copy()
    original_bm25_metadata = bm25_document.metadata.copy()
    hybrid, _, _ = build_hybrid([dense_document], [bm25_document])

    documents = await hybrid.ainvoke("pergunta")

    assert dense_document.metadata == original_dense_metadata
    assert bm25_document.metadata == original_bm25_metadata
    assert documents[0] is not dense_document
    assert documents[0] is not bm25_document


@pytest.mark.anyio
async def test_rrf_rejects_missing_chunk_identity() -> None:
    hybrid, _, _ = build_hybrid([make_document(None)], [])

    with pytest.raises(HybridRetrieverContractError, match="chunk identity"):
        await hybrid.ainvoke("pergunta")


@pytest.mark.anyio
async def test_rrf_rejects_duplicate_identity_inside_one_ranking() -> None:
    hybrid, _, _ = build_hybrid(
        [make_document("duplicate"), make_document("duplicate")],
        [],
    )

    with pytest.raises(HybridRetrieverContractError, match="duplicate"):
        await hybrid.ainvoke("pergunta")


@pytest.mark.anyio
async def test_rrf_rejects_disagreement_between_indexes() -> None:
    hybrid, _, _ = build_hybrid(
        [make_document("shared", content="Texto no Qdrant")],
        [make_document("shared", content="Texto diferente no PostgreSQL")],
    )

    with pytest.raises(HybridRetrieverContractError, match="source text"):
        await hybrid.ainvoke("pergunta")


@pytest.mark.anyio
async def test_rrf_rejects_conflicting_metadata() -> None:
    hybrid, _, _ = build_hybrid(
        [make_document("shared", bula_id="bula-a")],
        [make_document("shared", bula_id="bula-b")],
    )

    with pytest.raises(HybridRetrieverContractError, match="metadata"):
        await hybrid.ainvoke("pergunta")


@pytest.mark.anyio
async def test_rrf_rejects_invalid_child_score() -> None:
    hybrid, _, _ = build_hybrid([make_document("a", score="invalid")], [])

    with pytest.raises(HybridRetrieverContractError, match="invalid score"):
        await hybrid.ainvoke("pergunta")


def test_hybrid_retriever_rejects_nonstandard_fusion_contract() -> None:
    dense_retriever = StaticRetriever(documents=[])
    bm25_retriever = StaticRetriever(documents=[])

    with pytest.raises(ValueError, match="constant 60"):
        HybridRetriever(
            retrievers=[dense_retriever, bm25_retriever],
            weights=[1.0, 1.0],
            c=10,
            id_key="chunk_id",
        )

    with pytest.raises(ValueError, match="deduplicate by chunk_id"):
        HybridRetriever(
            retrievers=[dense_retriever, bm25_retriever],
            weights=[1.0, 1.0],
            c=60,
            id_key="doc_id",
        )
