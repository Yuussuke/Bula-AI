"""Bounded, resident inference and a LangChain reranking decorator."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import monotonic
from typing import Protocol

import structlog
from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

logger = structlog.get_logger(__name__)


class RerankerError(RuntimeError):
    """Technical reranking failure; never documentary insufficiency."""


class PairScorer(Protocol):
    def score(
        self, query: str, passages: list[str], *, deadline: float
    ) -> list[float]: ...


class ResidentReranker:
    """One inference thread/model per API process, with bounded outstanding work.

    A timed-out running CUDA operation keeps its slot until it actually finishes.
    It cannot overlap another inference or silently fall back to CPU/RRF.
    """

    def __init__(
        self,
        *,
        load_scorer: Callable[[], PairScorer],
        capacity: int = 16,
        timeout_seconds: float = 15,
    ) -> None:
        if capacity < 1 or timeout_seconds <= 0:
            raise ValueError("Reranker capacity and timeout must be positive.")
        self._load_scorer = load_scorer
        self._scorer: PairScorer | None = None
        self._has_load_failed = False
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="bge")
        self._lock = Lock()
        self._pending = 0
        self._is_closed = False
        self._capacity = capacity
        self._timeout_seconds = timeout_seconds

    def _get_scorer(self) -> PairScorer:
        if self._has_load_failed:
            raise RerankerError(
                "BGE initialization previously failed; check the startup log and restart."
            )
        if self._scorer is None:
            try:
                self._scorer = self._load_scorer()
            except Exception as exc:
                self._has_load_failed = True
                raise RerankerError(
                    "BGE initialization failed; check local assets, CUDA and the reranker extra."
                ) from exc
        return self._scorer

    async def warmup(self) -> None:
        """Load once before serving, outside the per-query inference deadline."""
        await asyncio.wrap_future(self._executor.submit(self._get_scorer))

    async def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        started = monotonic()
        deadline = started + self._timeout_seconds
        with self._lock:
            if self._is_closed:
                raise RerankerError("Reranker is closed.")
            if self._pending >= self._capacity:
                raise RerankerError("Reranker queue is full.")
            self._pending += 1
            try:
                future = self._executor.submit(self._score, query, passages, deadline)
            except RuntimeError as exc:
                self._pending -= 1
                raise RerankerError("Reranker is unavailable.") from exc

        def release_slot(_: object) -> None:
            with self._lock:
                self._pending -= 1

        future.add_done_callback(release_slot)
        wrapped = asyncio.wrap_future(future)

        def consume_late_error(result: asyncio.Future[list[float]]) -> None:
            if not result.cancelled():
                result.exception()

        wrapped.add_done_callback(consume_late_error)
        try:
            # wait() leaves the worker future alive on deadline/cancellation.
            # Python 3.14 shield() reports late worker errors as unhandled even
            # when its inner Future is consumed, so do not use shield here.
            completed, _ = await asyncio.wait((wrapped,), timeout=self._timeout_seconds)
            if not completed:
                future.cancel()
                raise RerankerError("Reranker deadline exceeded.")
            scores = wrapped.result()
            logger.info(
                "rag_reranking",
                status="success",
                candidate_count=len(passages),
                duration_ms=round((monotonic() - started) * 1000, 3),
            )
            return scores
        except asyncio.CancelledError:
            # Cancellation succeeds only for work that has not started.
            future.cancel()
            raise

    def _score(self, query: str, passages: list[str], deadline: float) -> list[float]:
        if monotonic() >= deadline:
            raise RerankerError("Reranker deadline exceeded in queue.")
        try:
            scores = self._get_scorer().score(query, passages, deadline=deadline)
        except RerankerError:
            raise
        except Exception as exc:
            raise RerankerError("BGE inference failed.") from exc
        if len(scores) != len(passages) or not all(
            math.isfinite(score) for score in scores
        ):
            raise RerankerError("BGE returned invalid scores.")
        if monotonic() >= deadline:
            raise RerankerError("Reranker deadline exceeded during inference.")
        return scores

    async def close(self) -> None:
        with self._lock:
            self._is_closed = True
        await asyncio.to_thread(self._executor.shutdown, wait=True, cancel_futures=True)
        self._scorer = None


class RerankingRetriever(BaseRetriever):
    wrapped_retriever: BaseRetriever
    reranker: ResidentReranker = Field(exclude=True, repr=False)
    k: int = Field(default=10, ge=1, le=50)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun
    ) -> list[Document]:
        documents = await self.wrapped_retriever.ainvoke(
            query, config={"callbacks": run_manager.get_child()}
        )
        if not documents:
            return []
        chunk_ids = [document.metadata.get("chunk_id") for document in documents]
        if any(
            not isinstance(chunk_id, str) or not chunk_id.strip()
            for chunk_id in chunk_ids
        ) or len(set(chunk_ids)) != len(chunk_ids):
            raise RerankerError("Reranking requires unique canonical chunk IDs.")
        passages = []
        for document in documents:
            section = document.metadata.get("section_title", "")
            prefix = f"Seção: {section}\n\n" if section else ""
            passages.append(prefix + document.page_content)
        scores = await self.reranker.score(query, passages)
        ranked = []
        for document, score in zip(documents, scores, strict=True):
            enriched = document.model_copy(deep=True)
            enriched.metadata.update(score=score, reranker_score=score)
            ranked.append(enriched)
        ranked.sort(
            key=lambda document: (
                -document.metadata["reranker_score"],
                document.metadata["chunk_id"],
            )
        )
        return ranked[: self.k]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        raise RuntimeError("RerankingRetriever requires async ainvoke().")
