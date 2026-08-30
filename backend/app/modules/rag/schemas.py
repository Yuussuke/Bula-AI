from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ChunkingMethod = Literal["primary", "fallback", "heuristic", "deterministic"]
ValidationOutcome = Literal["passed", "failed", "not_attempted"]


class ChunkingConfig(BaseModel):
    target_tokens: int = Field(default=600, gt=0)
    min_tokens: int = Field(default=200, gt=0)
    max_tokens: int = Field(default=850, gt=0)
    overlap_ratio: float = Field(default=0.0, ge=0, lt=1)
    is_batching_enabled: bool = True
    batch_max_tokens: int = Field(default=3000, gt=0)
    batch_max_sections: int = Field(default=8, gt=0)
    model: str = "google/gemini-3.1-flash-lite"
    prompt_version: Literal["retrieval_v3"] = "retrieval_v3"
    temperature: float = Field(default=0, ge=0, le=2)
    seed: int = 17
    max_output_tokens: int = Field(default=5000, gt=0)
    provider_zdr: bool = True
    provider_data_collection: Literal["deny"] = "deny"
    provider_require_parameters: bool = True
    provider_allow_fallbacks: bool = True
    is_llm_enabled: bool = True
    request_timeout_seconds: float = Field(default=60, gt=0)


class ChunkProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    chunk_text: str


class ChunkProposals(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    chunks: list[ChunkProposal]


class BatchChunkProposal(ChunkProposal):
    section_index: int = Field(ge=0)


class BatchChunkProposals(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    chunks: list[BatchChunkProposal]


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
