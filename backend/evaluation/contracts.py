"""Evaluation-only contracts. No mapper, scorer, provider or production imports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from evaluation.artifacts import digest_value
from evaluation.dataset import DocumentIdentity

Scenario = Literal["scoped", "cross"]
Strategy = Literal["dense", "bm25", "hybrid"]
MappingStatus = Literal["complete", "partial", "ambiguous", "absent"]


@dataclass(frozen=True)
class RetrievalRequest:
    question: str
    corpus_id: str
    scoped_document_id: str | None
    k: int = 10


@dataclass(frozen=True)
class RetrievalJob:
    question_id: str
    record_sha256: str
    target: DocumentIdentity
    scenario: Scenario
    strategy: Strategy
    question: str

    @property
    def key(self) -> str:
        return f"{self.question_id}/{self.scenario}/{self.strategy}"

    def request(self) -> RetrievalRequest:
        # Gold identity is retained for later scoring, never passed in cross retrieval.
        return RetrievalRequest(
            self.question,
            self.target.corpus_id,
            self.target.document_id if self.scenario == "scoped" else None,
        )


@dataclass(frozen=True)
class RankedChunk:
    chunk_id: str
    document_id: str
    corpus_id: str
    pdf_sha256: str
    text_sha256: str
    rank: int
    score: float
    score_details: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SnapshotChunk:
    chunk_id: str
    document: DocumentIdentity
    text: str
    section: str
    local_context: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceReference:
    reference_id: str
    quote: str
    pdf_page: int
    section: str
    source_region: str | None = None


@dataclass(frozen=True)
class MappingInput:
    question_id: str
    record_sha256: str
    ingestion_snapshot_sha256: str
    target: DocumentIdentity
    question_scoped: str
    question_cross: str
    expected_information: str
    required_qualifiers: tuple[str, ...]
    references: tuple[EvidenceReference, ...]
    chunks: tuple[SnapshotChunk, ...]

    def validate(self) -> None:
        if len({chunk.chunk_id for chunk in self.chunks}) != len(self.chunks):
            raise ValueError("Duplicate snapshot chunk")
        if any(chunk.document != self.target for chunk in self.chunks):
            raise ValueError("Mapper received chunks from another PDF")
        if len({reference.reference_id for reference in self.references}) != len(
            self.references
        ):
            raise ValueError("Duplicate documentary reference")


@dataclass(frozen=True)
class ReferenceMatch:
    reference_id: str
    chunk_ids: tuple[str, ...]
    status: MappingStatus
    rationale: str


@dataclass(frozen=True)
class MappingOutput:
    input_sha256: str
    status: MappingStatus
    matches: tuple[ReferenceMatch, ...]
    semantic_review: Literal["pending", "confirmed", "disputed"] = "pending"

    def validate(self, mapping_input: MappingInput) -> None:
        mapping_input.validate()
        if self.input_sha256 != digest_value(asdict(mapping_input)):
            raise ValueError("Mapping belongs to another input/snapshot")
        if {match.reference_id for match in self.matches} != {
            reference.reference_id for reference in mapping_input.references
        } or len(self.matches) != len(mapping_input.references):
            raise ValueError("Mapping must account for every reference")
        chunk_ids = {chunk.chunk_id for chunk in mapping_input.chunks}
        for match in self.matches:
            if (
                len(set(match.chunk_ids)) != len(match.chunk_ids)
                or not set(match.chunk_ids) <= chunk_ids
            ):
                raise ValueError("Unknown or duplicate mapped chunk")
            if match.status == "absent" and match.chunk_ids:
                raise ValueError("Absent reference cannot have supporting chunks")
            if match.status in {"complete", "partial"} and not match.chunk_ids:
                raise ValueError("A correspondence requires chunks")
        if self.status == "complete" and any(
            match.status != "complete" for match in self.matches
        ):
            raise ValueError("Complete mapping cannot conceal unresolved references")
        # A literal complete match does NOT set semantic_review='confirmed'.
