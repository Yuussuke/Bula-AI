from typing import Literal

from pydantic import BaseModel, Field


ChunkingMethod = Literal["primary", "fallback", "heuristic"]


class ChunkingConfig(BaseModel):
    target_tokens: int = Field(default=600, gt=0)
    min_tokens: int = Field(default=200, gt=0)
    max_tokens: int = Field(default=850, gt=0)
    overlap_ratio: float = Field(default=0.12, ge=0, lt=1)
    max_concurrency: int = Field(default=4, gt=0)
    model: str
    fallback_model: str
    is_llm_enabled: bool = True


class ChunkProposal(BaseModel):
    chunk_text: str
    chunk_title: str
    reason: str | None = None


class ChunkProposals(BaseModel):
    chunks: list[ChunkProposal]


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    index: int
    text: str
    chunk_title: str
    section_title: str
    token_estimate: int
    method: ChunkingMethod
    metadata: dict[str, object] = Field(default_factory=dict)


class ChunkResult(BaseModel):
    doc_id: str
    chunks: list[DocumentChunk]
    metadata: dict[str, object] = Field(default_factory=dict)
