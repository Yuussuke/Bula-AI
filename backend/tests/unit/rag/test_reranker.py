import asyncio
from threading import Event

import pytest
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.modules.rag.reranker import ResidentReranker, RerankerError, RerankingRetriever


class FixedRetriever(BaseRetriever):
    documents: list[Document]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return self.documents


class FixedScorer:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.inputs: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages: list[str], *, deadline: float) -> list[float]:
        self.inputs.append((query, passages))
        return self.scores


def document(chunk_id: str, score: float = 1) -> Document:
    return Document(
        page_content=f"Texto original {chunk_id}",
        metadata={
            "chunk_id": chunk_id,
            "section_title": "Horários",
            "score": score,
            "rrf_score": score,
        },
    )


@pytest.mark.anyio
async def test_raw_logits_override_rrf_and_ties_use_chunk_id_without_changing_sources() -> (
    None
):
    sources = [document("c", 9), document("b", 2), document("a", 1)]
    scorer = FixedScorer([-3, 4, 4])
    service = ResidentReranker(load_scorer=lambda: scorer)
    try:
        retriever = RerankingRetriever(
            wrapped_retriever=FixedRetriever(documents=sources), reranker=service, k=2
        )
        ranked = await retriever.ainvoke("Qual o horário?")
        assert [row.metadata["chunk_id"] for row in ranked] == ["a", "b"]
        assert ranked[0].page_content == sources[2].page_content
        assert ranked[0].metadata["rrf_score"] == 1
        assert ranked[0].metadata["score"] == 4
        assert sources[2].metadata["score"] == 1
        assert scorer.inputs == [
            (
                "Qual o horário?",
                [f"Seção: Horários\n\nTexto original {key}" for key in ("c", "b", "a")],
            )
        ]
    finally:
        await service.close()


@pytest.mark.anyio
@pytest.mark.parametrize("scores", [[float("nan")], [], [1, 2]])
async def test_invalid_inference_is_a_technical_error_without_rrf_fallback(
    scores: list[float],
) -> None:
    service = ResidentReranker(load_scorer=lambda: FixedScorer(scores))
    try:
        retriever = RerankingRetriever(
            wrapped_retriever=FixedRetriever(documents=[document("a")]),
            reranker=service,
        )
        with pytest.raises(RerankerError, match="invalid scores"):
            await retriever.ainvoke("Horário?")
    finally:
        await service.close()


@pytest.mark.anyio
async def test_empty_retrieval_never_loads_the_gpu_model() -> None:
    def unavailable_scorer() -> FixedScorer:
        raise AssertionError("No model should be needed")

    service = ResidentReranker(load_scorer=unavailable_scorer)
    try:
        retriever = RerankingRetriever(
            wrapped_retriever=FixedRetriever(documents=[]), reranker=service
        )
        assert await retriever.ainvoke("Horário?") == []
    finally:
        await service.close()


@pytest.mark.anyio
async def test_timeout_keeps_running_slot_and_rejects_overload_until_worker_finishes() -> (
    None
):
    started = Event()
    release = Event()

    class BlockingScorer:
        def score(
            self, query: str, passages: list[str], *, deadline: float
        ) -> list[float]:
            started.set()
            if not release.wait(timeout=5):
                raise AssertionError("Test did not release the fake device")
            return [1.0]

    service = ResidentReranker(
        load_scorer=BlockingScorer, capacity=1, timeout_seconds=0.1
    )
    try:
        first = asyncio.create_task(service.score("q", ["p"]))
        assert await asyncio.to_thread(started.wait, 3)
        with pytest.raises(RerankerError, match="queue is full"):
            await service.score("q2", ["p2"])
        with pytest.raises(RerankerError, match="deadline exceeded"):
            await first
        with pytest.raises(RerankerError, match="queue is full"):
            await service.score("q3", ["p3"])
        release.set()
    finally:
        release.set()
        await service.close()
    with pytest.raises(RerankerError, match="closed"):
        await service.score("q", ["p"])


@pytest.mark.anyio
async def test_model_is_resident_across_sequential_requests() -> None:
    loaded: list[FixedScorer] = []

    def load_scorer() -> FixedScorer:
        scorer = FixedScorer([1.0])
        loaded.append(scorer)
        return scorer

    service = ResidentReranker(load_scorer=load_scorer)
    try:
        assert await service.score("a", ["b"]) == [1]
        assert await service.score("c", ["d"]) == [1]
        assert len(loaded) == 1
        assert loaded[0].inputs == [("a", ["b"]), ("c", ["d"])]
    finally:
        await service.close()


@pytest.mark.anyio
async def test_candidate_below_rrf_top_ten_can_be_promoted_by_bge() -> None:
    sources = [document(f"chunk-{index:02}") for index in range(40)]
    scorer = FixedScorer([-10.0] * 39 + [5.0])
    service = ResidentReranker(load_scorer=lambda: scorer)
    try:
        retriever = RerankingRetriever(
            wrapped_retriever=FixedRetriever(documents=sources), reranker=service, k=10
        )
        ranked = await retriever.ainvoke("Horário?")
        assert len(scorer.inputs[0][1]) == 40
        assert len(ranked) == 10
        assert ranked[0].metadata["chunk_id"] == "chunk-39"
    finally:
        await service.close()


@pytest.mark.anyio
async def test_initialization_failure_is_not_retried_on_every_question() -> None:
    attempts: list[str] = []

    def load_scorer() -> FixedScorer:
        attempts.append("load")
        raise RuntimeError("Device unavailable")

    service = ResidentReranker(load_scorer=load_scorer)
    try:
        with pytest.raises(RerankerError, match="initialization failed"):
            await service.warmup()
        with pytest.raises(RerankerError, match="previously failed"):
            await service.score("q", ["p"])
        assert attempts == ["load"]
    finally:
        await service.close()
