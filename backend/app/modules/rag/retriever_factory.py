"""Select an injected retrieval strategy after the caller authorizes the bula."""

from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from langchain_core.retrievers import BaseRetriever

from app.modules.rag.retrieval_mode import RetrievalMode


class RetrieverBuilder(Protocol):
    def __call__(self, *, bula_id: UUID, k: int) -> BaseRetriever: ...


class RetrieverStrategyFactory:
    def __init__(self, *, builders: Mapping[RetrievalMode, RetrieverBuilder]) -> None:
        if set(builders) != set(RetrievalMode):
            raise ValueError("Register exactly one builder for every retrieval mode.")
        self._builders = dict(builders)

    def build(self, *, mode: RetrievalMode, bula_id: UUID, k: int = 4) -> BaseRetriever:
        if not isinstance(bula_id, UUID):
            raise ValueError("A bula UUID is required for retrieval.")
        if k < 1 or k > 50:
            raise ValueError("k must be between 1 and 50.")
        return self._builders[mode](bula_id=bula_id, k=k)
