from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableLambda

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.bm25_retriever import BM25Retriever, BM25RetrieverFactory
from app.modules.rag.schemas import BM25SearchResult


class StubSearchIndex:
    """Replace external persistence, not the retriever under test."""

    def __init__(self, results: list[BM25SearchResult]) -> None:
        self.results = results
        self.received_query: str | None = None
        self.received_scope: tuple[UUID | None, Sequence[BulaCorpus] | None] | None = (
            None
        )
        self.error: Exception | None = None

    async def search(
        self,
        query: str,
        *,
        k: int = 10,
        bula_id: UUID | None = None,
        corpus: Sequence[BulaCorpus] | None = None,
    ) -> list[BM25SearchResult]:
        if self.error is not None:
            raise self.error
        self.received_query = query
        self.received_scope = (bula_id, corpus)
        return self.results[:k]


def make_result(*, score: float = 2.5) -> BM25SearchResult:
    bula_id = uuid4()
    return BM25SearchResult(
        chunk_id=f"{bula_id}:0",
        doc_id=str(bula_id),
        bula_id=bula_id,
        corpus=BulaCorpus.PRIVATE,
        drug_name="Dipirona",
        section_title="Composição",
        chunk_text="## Composição\n\nDipirona sódica: 500 mg.\n",
        bm25_score=score,
    )


@pytest.mark.anyio
async def test_ainvoke_preserves_source_identity_metadata_and_score() -> None:
    result = make_result()
    index = StubSearchIndex([result])
    retriever = BM25Retriever(index=index, bula_id=result.bula_id)

    documents = await retriever.ainvoke("DIPIRONA SÓDICA")

    assert isinstance(retriever, BaseRetriever)
    assert documents == [
        Document(
            id=result.chunk_id,
            page_content=result.chunk_text,
            metadata={
                "chunk_id": result.chunk_id,
                "doc_id": result.doc_id,
                "bula_id": str(result.bula_id),
                "corpus": "private",
                "drug_name": "Dipirona",
                "section_title": "Composição",
                "score": 2.5,
                "bm25_score": 2.5,
            },
        )
    ]
    assert index.received_query == "DIPIRONA SÓDICA"


@pytest.mark.anyio
async def test_retriever_preserves_ranking_and_requests_configured_top_k() -> None:
    results = [make_result(score=score) for score in (4.5, 2.3, 0.8)]
    retriever = BM25Retriever(index=StubSearchIndex(results), k=2)

    documents = await retriever.ainvoke("dipirona")

    assert [document.id for document in documents] == [
        result.chunk_id for result in results[:2]
    ]
    assert [document.metadata["score"] for document in documents] == [4.5, 2.3]


@pytest.mark.anyio
async def test_factory_keeps_scopes_independent_and_copies_mutable_filters() -> None:
    index = StubSearchIndex([])
    factory = BM25RetrieverFactory(index)
    selected_bula_id = uuid4()
    corpus = [BulaCorpus.PRIVATE]
    private_retriever = factory.build(bula_id=selected_bula_id, corpus=corpus, k=3)
    system_retriever = factory.build(bula_id=None, corpus=[BulaCorpus.SYSTEM])
    corpus.append(BulaCorpus.SYSTEM)

    await private_retriever.ainvoke("dipirona")
    assert index.received_scope == (selected_bula_id, (BulaCorpus.PRIVATE,))
    await system_retriever.ainvoke("dipirona")
    assert index.received_scope == (None, (BulaCorpus.SYSTEM,))


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["", "  \n\t"])
async def test_blank_query_returns_no_documents_without_accessing_database(
    query: str,
) -> None:
    index = StubSearchIndex([])
    index.error = RuntimeError("Database should not be needed")
    assert await BM25Retriever(index=index).ainvoke(query) == []


@pytest.mark.anyio
async def test_empty_corpus_does_not_broaden_to_unfiltered_search() -> None:
    index = StubSearchIndex([make_result()])
    index.error = RuntimeError("Database should not be needed")
    assert await BM25Retriever(index=index, corpus=()).ainvoke("dipirona") == []


@pytest.mark.anyio
async def test_no_matches_return_empty_documents() -> None:
    assert await BM25Retriever(index=StubSearchIndex([])).ainvoke("missing") == []


@pytest.mark.anyio
async def test_database_failure_is_not_disguised_as_no_evidence() -> None:
    index = StubSearchIndex([])
    index.error = TimeoutError("Database unavailable")
    with pytest.raises(TimeoutError, match="Database unavailable"):
        await BM25Retriever(index=index).ainvoke("dipirona")


def test_sync_invoke_explains_required_async_path() -> None:
    with pytest.raises(RuntimeError, match="async ainvoke"):
        BM25Retriever(index=StubSearchIndex([])).invoke("dipirona")


@pytest.mark.anyio
async def test_retriever_composes_with_lcel_without_model_calls() -> None:
    result = make_result()
    retriever = BM25Retriever(index=StubSearchIndex([result]))

    def extract_question(payload: dict[str, str]) -> str:
        return payload["question"]

    def extract_sources(documents: list[Document]) -> list[str]:
        return [document.page_content for document in documents]

    chain = (
        RunnableLambda(extract_question) | retriever | RunnableLambda(extract_sources)
    )
    assert await chain.ainvoke({"question": "dipirona"}) == [result.chunk_text]
