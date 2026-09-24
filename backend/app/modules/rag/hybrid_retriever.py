"""Deterministic Reciprocal Rank Fusion for dense and lexical retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field, model_validator


RRF_CONSTANT = 60
HYBRID_DOCUMENT_ID_KEY = "chunk_id"
HYBRID_RETRIEVER_NAMES = ("dense", "bm25")
HYBRID_RETRIEVER_WEIGHTS = (1.0, 1.0)


class HybridRetrieverContractError(RuntimeError):
    """Raised when retriever outputs cannot be fused safely."""


@dataclass
class _FusedDocumentState:
    document: Document
    first_seen: int
    rrf_score: float = 0.0
    ranks: dict[str, int] = field(default_factory=dict)


class HybridRetriever(EnsembleRetriever):
    """Fuse one dense and one BM25 ranking using equal-weight RRF.

    Child retrievers are invoked concurrently by ``EnsembleRetriever``. This
    specialization owns the Bula AI contracts that the generic implementation
    does not provide: strict chunk identity, metadata reconciliation, stable
    ties, source-specific diagnostics, and a bounded final result.
    """

    k: int = Field(default=10, ge=1, le=50)

    @classmethod
    def from_retrievers(
        cls,
        *,
        dense_retriever: BaseRetriever,
        bm25_retriever: BaseRetriever,
        k: int = 10,
    ) -> Self:
        return cls(
            retrievers=[dense_retriever, bm25_retriever],
            weights=list(HYBRID_RETRIEVER_WEIGHTS),
            c=RRF_CONSTANT,
            id_key=HYBRID_DOCUMENT_ID_KEY,
            k=k,
        )

    @model_validator(mode="after")
    def validate_hybrid_contract(self) -> Self:
        if len(self.retrievers) != len(HYBRID_RETRIEVER_NAMES):
            raise ValueError("Hybrid retrieval requires dense and BM25 retrievers.")
        if tuple(self.weights) != HYBRID_RETRIEVER_WEIGHTS:
            raise ValueError("Hybrid retrieval requires equal RRF weights.")
        if self.c != RRF_CONSTANT:
            raise ValueError(f"Hybrid retrieval requires RRF constant {RRF_CONSTANT}.")
        if self.id_key != HYBRID_DOCUMENT_ID_KEY:
            raise ValueError("Hybrid retrieval must deduplicate by chunk_id.")
        return self

    def weighted_reciprocal_rank(
        self,
        doc_lists: list[list[Document]],
    ) -> list[Document]:
        if len(doc_lists) != len(HYBRID_RETRIEVER_NAMES):
            raise HybridRetrieverContractError(
                "Hybrid retrieval received an unexpected number of rankings."
            )

        states_by_chunk_id: dict[str, _FusedDocumentState] = {}
        next_first_seen = 0
        for retriever_name, documents in zip(
            HYBRID_RETRIEVER_NAMES,
            doc_lists,
            strict=True,
        ):
            seen_chunk_ids: set[str] = set()
            for rank, document in enumerate(documents, start=1):
                chunk_id = self._get_chunk_id(document)
                if chunk_id in seen_chunk_ids:
                    raise HybridRetrieverContractError(
                        "A child retriever returned a duplicate chunk identity."
                    )
                seen_chunk_ids.add(chunk_id)

                state = states_by_chunk_id.get(chunk_id)
                if state is None:
                    state = _FusedDocumentState(
                        document=document.model_copy(deep=True),
                        first_seen=next_first_seen,
                    )
                    states_by_chunk_id[chunk_id] = state
                    next_first_seen += 1
                else:
                    self._validate_matching_source(state.document, document)
                    self._merge_metadata(state.document, document)

                state.rrf_score += 1.0 / (self.c + rank)
                state.ranks[retriever_name] = rank
                self._record_source_score(
                    target=state.document,
                    source=document,
                    retriever_name=retriever_name,
                )

        ranked_states = sorted(
            states_by_chunk_id.values(),
            key=self._ranking_key,
        )
        return [self._build_result_document(state) for state in ranked_states[: self.k]]

    def _get_chunk_id(self, document: Document) -> str:
        value = document.metadata.get(HYBRID_DOCUMENT_ID_KEY)
        if not isinstance(value, str) or not value.strip():
            raise HybridRetrieverContractError(
                "A retrieved document is missing a valid chunk identity."
            )
        return value

    def _validate_matching_source(
        self,
        existing_document: Document,
        candidate_document: Document,
    ) -> None:
        if existing_document.page_content != candidate_document.page_content:
            raise HybridRetrieverContractError(
                "Dense and BM25 indexes disagree on chunk source text."
            )

    def _merge_metadata(
        self,
        target: Document,
        source: Document,
    ) -> None:
        score_keys = {"score", "dense_score", "bm25_score", "rrf_score"}
        diagnostic_keys = {"dense_rank", "bm25_rank", "retrieval_sources"}
        for key, value in source.metadata.items():
            if key in score_keys or key in diagnostic_keys or value is None:
                continue

            existing_value = target.metadata.get(key)
            if self._is_missing_metadata(existing_value):
                target.metadata[key] = value
                continue
            if existing_value != value:
                raise HybridRetrieverContractError(
                    "Dense and BM25 indexes disagree on chunk metadata."
                )

    def _record_source_score(
        self,
        *,
        target: Document,
        source: Document,
        retriever_name: str,
    ) -> None:
        source_score_key = f"{retriever_name}_score"
        raw_score = source.metadata.get(source_score_key)
        if raw_score is None:
            raw_score = source.metadata.get("score")
        if raw_score is None:
            return

        try:
            target.metadata[source_score_key] = float(raw_score)
        except (TypeError, ValueError) as exc:
            raise HybridRetrieverContractError(
                "A child retriever returned an invalid score."
            ) from exc

    def _ranking_key(self, state: _FusedDocumentState) -> tuple[float, int, int, str]:
        best_rank = min(state.ranks.values())
        chunk_id = self._get_chunk_id(state.document)
        return (-state.rrf_score, best_rank, state.first_seen, chunk_id)

    def _build_result_document(self, state: _FusedDocumentState) -> Document:
        document = state.document.model_copy(deep=True)
        chunk_id = self._get_chunk_id(document)
        document.id = chunk_id
        document.metadata["score"] = state.rrf_score
        document.metadata["rrf_score"] = state.rrf_score
        document.metadata["retrieval_sources"] = [
            name for name in HYBRID_RETRIEVER_NAMES if name in state.ranks
        ]
        for retriever_name, rank in state.ranks.items():
            document.metadata[f"{retriever_name}_rank"] = rank
        return document

    def _is_missing_metadata(self, value: Any) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())
