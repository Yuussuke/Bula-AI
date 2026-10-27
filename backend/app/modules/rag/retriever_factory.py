"""Select an injected retrieval strategy after the caller authorizes the scope."""

from collections.abc import Callable, Mapping, Sequence
from typing import Protocol
from uuid import UUID

from langchain_core.retrievers import BaseRetriever

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.retrieval_mode import RetrievalMode
from app.modules.rag.retrieval_limits import DEFAULT_RETRIEVAL_K
from app.modules.rag.reranker import ResidentReranker, RerankingRetriever
from app.modules.rag.section_evidence_retriever import (
    SectionEvidenceIndex,
    SectionEvidenceRetriever,
)


class RetrieverBuilder(Protocol):
    def __call__(
        self,
        *,
        bula_id: UUID | None,
        corpus: tuple[BulaCorpus, ...] | None,
        k: int,
        allowed_bula_ids: tuple[UUID, ...] | None = None,
    ) -> BaseRetriever: ...


class RetrieverStrategyFactory:
    def __init__(
        self,
        *,
        builders: Mapping[RetrievalMode, RetrieverBuilder],
        hybrid_reranker: Callable[[], ResidentReranker] | None = None,
        section_index: SectionEvidenceIndex | None = None,
    ) -> None:
        if set(builders) != set(RetrievalMode):
            raise ValueError("Register exactly one builder for every retrieval mode.")
        self._builders = dict(builders)
        self._hybrid_reranker = hybrid_reranker
        self._section_index = section_index

    def build(
        self,
        *,
        mode: RetrievalMode,
        bula_id: UUID | None,
        corpus: Sequence[BulaCorpus] | None = None,
        allowed_bula_ids: tuple[UUID, ...] | None = None,
        k: int = DEFAULT_RETRIEVAL_K,
        validate_candidates: Callable[[BaseRetriever], BaseRetriever] | None = None,
    ) -> BaseRetriever:
        if bula_id is not None and not isinstance(bula_id, UUID):
            raise ValueError("A bula ID must be a UUID.")
        if bula_id is None and corpus is None:
            raise ValueError("A bula UUID or explicit corpus scope is required.")
        if k < 1 or k > 50:
            raise ValueError("k must be between 1 and 50.")
        corpus_scope = (
            tuple(BulaCorpus(value) for value in corpus) if corpus is not None else None
        )
        retriever = self._builders[mode](
            bula_id=bula_id, corpus=corpus_scope, k=k, allowed_bula_ids=allowed_bula_ids
        )
        if validate_candidates is not None:
            retriever = validate_candidates(retriever)
        if mode == RetrievalMode.HYBRID and self._hybrid_reranker is not None:
            retriever = RerankingRetriever(
                wrapped_retriever=retriever, reranker=self._hybrid_reranker(), k=k
            )
        if bula_id is not None and self._section_index is not None:
            retriever = SectionEvidenceRetriever(
                wrapped_retriever=retriever,
                index=self._section_index,
                bula_id=bula_id,
                corpus=corpus_scope,
            )
        return retriever
