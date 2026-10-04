"""Select an injected retrieval strategy after the caller authorizes the scope."""

from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from langchain_core.retrievers import BaseRetriever

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.retrieval_mode import RetrievalMode


class RetrieverBuilder(Protocol):
    def __call__(
        self, *, bula_id: UUID | None, corpus: tuple[BulaCorpus, ...] | None, k: int
    ) -> BaseRetriever: ...


class RetrieverStrategyFactory:
    def __init__(self, *, builders: Mapping[RetrievalMode, RetrieverBuilder]) -> None:
        if set(builders) != set(RetrievalMode):
            raise ValueError("Register exactly one builder for every retrieval mode.")
        self._builders = dict(builders)

    def build(
        self,
        *,
        mode: RetrievalMode,
        bula_id: UUID | None,
        corpus: Sequence[BulaCorpus] | None = None,
        k: int = 4,
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
        return self._builders[mode](bula_id=bula_id, corpus=corpus_scope, k=k)
