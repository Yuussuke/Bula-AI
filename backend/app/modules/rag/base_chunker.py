from __future__ import annotations

import asyncio
from collections import Counter
import hashlib
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Sequence

import structlog
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema
from pydantic import ValidationError

from app.modules.rag.chunk_validation import (
    SourceChunkValidationError,
    SourceChunkSpan,
    SourceChunkValidator,
)
from app.modules.rag.deterministic_chunker import DeterministicMarkdownSplitter
from app.modules.rag.schemas import (
    BatchChunkProposals,
    ChunkingConfig,
    ChunkingMethod,
    ChunkProposals,
    ChunkResult,
    DocumentChunk,
    ValidationOutcome,
)
from app.modules.rag.semantic_chunking import (
    SemanticChunkingRequestContract,
    SemanticRequestDiagnostic,
)
from app.modules.rag.token_estimator import HeuristicTokenEstimator, TokenEstimator


logger = structlog.get_logger(__name__)

SECTION_HEADING_PATTERN = re.compile(r"^(#{2,3})\s+(.+?)\s*$")

CHUNK_PROPOSALS_RESPONSE_FORMAT: ResponseFormatJSONSchema = {
    "type": "json_schema",
    "json_schema": {
        "name": "chunk_proposals",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "chunks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chunk_text": {"type": "string"},
                        },
                        "required": ["chunk_text"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["chunks"],
            "additionalProperties": False,
        },
    },
}

BATCH_CHUNK_PROPOSALS_RESPONSE_FORMAT: ResponseFormatJSONSchema = {
    "type": "json_schema",
    "json_schema": {
        "name": "batch_chunk_proposals",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "chunks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section_index": {"type": "integer", "minimum": 0},
                            "chunk_text": {"type": "string"},
                        },
                        "required": [
                            "section_index",
                            "chunk_text",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["chunks"],
            "additionalProperties": False,
        },
    },
}


class ChunkingModelError(Exception):
    """Raised when a model response cannot be trusted for chunking."""

    def __init__(self, failure_reason: str) -> None:
        super().__init__(failure_reason)
        self.failure_reason = failure_reason


@dataclass(frozen=True)
class MarkdownSection:
    index: int
    title: str
    text: str


@dataclass(frozen=True)
class MarkdownSectionBatch:
    index: int
    sections: tuple[MarkdownSection, ...]
    estimated_input_tokens: int


@dataclass(frozen=True)
class SectionChunkDraft:
    text: str
    chunk_title: str
    section_title: str
    method: ChunkingMethod
    reason: str | None = None
    validation_outcome: ValidationOutcome = "not_attempted"


@dataclass(frozen=True)
class ChunkingAttemptFailure:
    method: ChunkingMethod
    error_type: str
    failure_reason: str


@dataclass
class ChunkingRunMetrics:
    model_call_count: int = 0
    batch_fallback_count: int = 0
    validation_passed_section_count: int = 0
    validation_failed_section_count: int = 0
    deterministic_fallback_count: int = 0
    fallback_reasons: Counter[str] = dataclass_field(default_factory=Counter)
    semantic_requests: list[SemanticRequestDiagnostic] = dataclass_field(
        default_factory=list
    )


def make_chunk_id(doc_id: str, index: int, text: str) -> str:
    digest = hashlib.md5(f"{doc_id}:{index}:{text}".encode()).hexdigest()[:12]
    return f"{doc_id}_{index}_{digest}"


class BaseChunker(ABC):
    def __init__(
        self,
        llm: AsyncOpenAI,
        config: ChunkingConfig,
        token_estimator: TokenEstimator | None = None,
        source_validator: SourceChunkValidator | None = None,
    ) -> None:
        self.llm = llm
        self.config = config
        self.token_estimator = token_estimator or HeuristicTokenEstimator()
        self.source_validator = source_validator or SourceChunkValidator()
        self.request_contract = SemanticChunkingRequestContract(config=self.config)
        self.deterministic_splitter = DeterministicMarkdownSplitter(
            token_estimator=self.token_estimator,
            target_tokens=self.config.target_tokens,
            max_tokens=self.config.max_tokens,
            overlap_ratio=self.config.overlap_ratio,
        )

    @abstractmethod
    def system_prompt(self) -> str:
        """Domain-specific instruction for the LLM chunking call."""

    @abstractmethod
    def user_prompt(self, *, section: MarkdownSection) -> str:
        """Domain-specific user instruction for the LLM chunking call."""

    @abstractmethod
    def batch_user_prompt(self, *, sections: Sequence[MarkdownSection]) -> str:
        """Domain-specific instruction for chunking multiple independent sections."""

    async def chunk_markdown(self, markdown: str, doc_id: str) -> ChunkResult:
        sections = self._split_markdown_sections(markdown)
        section_batches = self._build_section_batches(sections=sections)
        metrics = ChunkingRunMetrics()

        batch_results: list[list[SectionChunkDraft]] = []
        for section_batch in section_batches:
            batch_result = await self._chunk_batch_sequentially(
                section_batch=section_batch,
                doc_id=doc_id,
                metrics=metrics,
            )
            batch_results.append(batch_result)

        chunk_drafts = [
            chunk_draft
            for batch_chunk_drafts in batch_results
            for chunk_draft in batch_chunk_drafts
        ]

        chunks = [
            self._build_document_chunk(
                doc_id=doc_id,
                index=index,
                chunk_draft=chunk_draft,
            )
            for index, chunk_draft in enumerate(chunk_drafts)
        ]

        return ChunkResult(
            doc_id=doc_id,
            chunks=chunks,
            metadata={
                "section_count": len(sections),
                "batch_count": len(section_batches),
                "batched_section_count": sum(
                    len(section_batch.sections)
                    for section_batch in section_batches
                    if len(section_batch.sections) > 1
                ),
                "model_call_count": metrics.model_call_count,
                "batch_fallback_count": metrics.batch_fallback_count,
                "validation": {
                    "passed_section_count": metrics.validation_passed_section_count,
                    "failed_section_count": metrics.validation_failed_section_count,
                },
                "fallback": {
                    "count": metrics.deterministic_fallback_count,
                    "reasons": dict(sorted(metrics.fallback_reasons.items())),
                },
                "semantic_chunking": self._build_semantic_chunking_metadata(
                    metrics=metrics
                ),
                "chunk_count": len(chunks),
            },
        )

    async def _chunk_batch_sequentially(
        self,
        *,
        section_batch: MarkdownSectionBatch,
        doc_id: str,
        metrics: ChunkingRunMetrics,
    ) -> list[SectionChunkDraft]:
        if len(section_batch.sections) == 1:
            return await self._chunk_section(
                section=section_batch.sections[0],
                doc_id=doc_id,
                metrics=metrics,
            )

        return await self._chunk_batch(
            section_batch=section_batch,
            doc_id=doc_id,
            metrics=metrics,
        )

    async def _chunk_section(
        self,
        *,
        section: MarkdownSection,
        doc_id: str,
        metrics: ChunkingRunMetrics,
    ) -> list[SectionChunkDraft]:
        section_started_at = time.perf_counter()
        primary_failure: ChunkingAttemptFailure | None = None

        if self.config.is_llm_enabled:
            primary_chunks, primary_failure = await self._try_model_chunking(
                section=section,
                doc_id=doc_id,
                method="primary",
                metrics=metrics,
            )
            if primary_chunks is not None:
                self._log_section_chunked(
                    doc_id=doc_id,
                    section=section,
                    method="primary",
                    chunk_count=len(primary_chunks),
                    duration_ms=self._elapsed_ms(section_started_at),
                )
                return primary_chunks
        else:
            primary_failure = ChunkingAttemptFailure(
                method="primary",
                error_type="SemanticChunkingDisabled",
                failure_reason="semantic_chunking_disabled",
            )

        fallback_reason = (
            primary_failure.failure_reason
            if primary_failure is not None
            else "semantic_chunking_failed"
        )
        deterministic_chunks = self._chunk_section_deterministically(
            section=section,
            fallback_reason=fallback_reason,
        )
        metrics.deterministic_fallback_count += 1
        metrics.fallback_reasons[fallback_reason] += 1
        self._log_section_chunked(
            doc_id=doc_id,
            section=section,
            method="deterministic",
            chunk_count=len(deterministic_chunks),
            duration_ms=self._elapsed_ms(section_started_at),
            primary_failure=primary_failure,
        )
        return deterministic_chunks

    async def _chunk_batch(
        self,
        *,
        section_batch: MarkdownSectionBatch,
        doc_id: str,
        metrics: ChunkingRunMetrics,
    ) -> list[SectionChunkDraft]:
        batch_started_at = time.perf_counter()
        primary_chunks, primary_failure = await self._try_batch_model_chunking(
            section_batch=section_batch,
            doc_id=doc_id,
            method="primary",
            metrics=metrics,
        )
        if primary_chunks is not None:
            self._log_batch_chunked(
                doc_id=doc_id,
                section_batch=section_batch,
                method="primary",
                chunk_count=len(primary_chunks),
                duration_ms=self._elapsed_ms(batch_started_at),
            )
            return primary_chunks

        assert primary_failure is not None
        metrics.batch_fallback_count += 1
        logger.warning(
            "rag_chunking_batch_falling_back_to_sections",
            doc_id=doc_id,
            batch_index=section_batch.index,
            section_indices=[section.index for section in section_batch.sections],
            section_count=len(section_batch.sections),
            primary_error_type=primary_failure.error_type,
            primary_failure_reason=primary_failure.failure_reason,
        )

        chunk_drafts: list[SectionChunkDraft] = []
        for section in section_batch.sections:
            section_chunk_drafts = self._chunk_section_deterministically(
                section=section,
                fallback_reason=primary_failure.failure_reason,
            )
            chunk_drafts.extend(section_chunk_drafts)
            metrics.deterministic_fallback_count += 1
            metrics.fallback_reasons[primary_failure.failure_reason] += 1

        self._log_batch_chunked(
            doc_id=doc_id,
            section_batch=section_batch,
            method="section_fallback",
            chunk_count=len(chunk_drafts),
            duration_ms=self._elapsed_ms(batch_started_at),
        )
        return chunk_drafts

    async def _try_batch_model_chunking(
        self,
        *,
        section_batch: MarkdownSectionBatch,
        doc_id: str,
        method: ChunkingMethod,
        metrics: ChunkingRunMetrics,
    ) -> tuple[list[SectionChunkDraft] | None, ChunkingAttemptFailure | None]:
        try:
            metrics.model_call_count += 1
            chunks = await self._chunk_batch_with_model(
                section_batch=section_batch,
                method=method,
                metrics=metrics,
            )
            metrics.validation_passed_section_count += len(section_batch.sections)
            return chunks, None
        except Exception as exc:
            metrics.validation_failed_section_count += len(section_batch.sections)
            failure = self._build_chunking_attempt_failure(
                method=method,
                exc=exc,
            )
            logger.warning(
                "rag_chunking_batch_model_failed",
                doc_id=doc_id,
                batch_index=section_batch.index,
                section_indices=[section.index for section in section_batch.sections],
                section_count=len(section_batch.sections),
                estimated_input_tokens=section_batch.estimated_input_tokens,
                method=method,
                error_type=failure.error_type,
                failure_reason=failure.failure_reason,
            )
            return None, failure

    async def _chunk_batch_with_model(
        self,
        *,
        section_batch: MarkdownSectionBatch,
        method: ChunkingMethod,
        metrics: ChunkingRunMetrics,
    ) -> list[SectionChunkDraft]:
        request_started_at = time.perf_counter()
        response: Any | None = None
        try:
            async with asyncio.timeout(self.config.request_timeout_seconds):
                response = await self.llm.chat.completions.create(
                    **self.request_contract.build_request(
                        messages=self._build_batch_llm_messages(
                            sections=section_batch.sections,
                        ),
                        response_format=BATCH_CHUNK_PROPOSALS_RESPONSE_FORMAT,
                    )
                )
            message_content = self._extract_message_content(response=response)
            proposals = BatchChunkProposals.model_validate_json(message_content)
            chunks = self._validate_and_build_batch_model_chunks(
                proposals=proposals,
                sections=section_batch.sections,
                method=method,
            )
        except Exception as exc:
            self._record_semantic_request(
                metrics=metrics,
                response=response,
                request_started_at=request_started_at,
                validation_outcome="failed",
                fallback_reason=self._safe_failure_reason(exc),
            )
            raise

        self._record_semantic_request(
            metrics=metrics,
            response=response,
            request_started_at=request_started_at,
            validation_outcome="passed",
            fallback_reason=None,
        )
        return chunks

    async def _try_model_chunking(
        self,
        *,
        section: MarkdownSection,
        doc_id: str,
        method: ChunkingMethod,
        metrics: ChunkingRunMetrics,
    ) -> tuple[list[SectionChunkDraft] | None, ChunkingAttemptFailure | None]:
        try:
            metrics.model_call_count += 1
            chunks = await self._chunk_section_with_model(
                section=section,
                method=method,
                metrics=metrics,
            )
            metrics.validation_passed_section_count += 1
            return chunks, None
        except Exception as exc:
            metrics.validation_failed_section_count += 1
            failure = self._build_chunking_attempt_failure(
                method=method,
                exc=exc,
            )
            logger.warning(
                "rag_section_chunking_model_failed",
                doc_id=doc_id,
                section_index=section.index,
                section_title=section.title,
                method=method,
                error_type=failure.error_type,
                failure_reason=failure.failure_reason,
            )
            return None, failure

    def _build_chunking_attempt_failure(
        self,
        *,
        method: ChunkingMethod,
        exc: Exception,
    ) -> ChunkingAttemptFailure:
        return ChunkingAttemptFailure(
            method=method,
            error_type=exc.__class__.__name__,
            failure_reason=self._safe_failure_reason(exc),
        )

    def _safe_failure_reason(self, exc: Exception) -> str:
        if isinstance(exc, SourceChunkValidationError):
            return exc.reason

        if isinstance(exc, ChunkingModelError):
            return exc.failure_reason

        if isinstance(exc, TimeoutError):
            return "timeout"

        if isinstance(exc, ValidationError):
            return "invalid_json"

        return "provider_error"

    async def _chunk_section_with_model(
        self,
        *,
        section: MarkdownSection,
        method: ChunkingMethod,
        metrics: ChunkingRunMetrics,
    ) -> list[SectionChunkDraft]:
        request_started_at = time.perf_counter()
        response: Any | None = None
        try:
            async with asyncio.timeout(self.config.request_timeout_seconds):
                response = await self.llm.chat.completions.create(
                    **self.request_contract.build_request(
                        messages=self._build_llm_messages(section=section),
                        response_format=CHUNK_PROPOSALS_RESPONSE_FORMAT,
                    )
                )
            message_content = self._extract_message_content(response=response)
            proposals = ChunkProposals.model_validate_json(message_content)
            chunks = self._validate_and_build_model_chunks(
                proposals=proposals,
                section=section,
                method=method,
            )
        except Exception as exc:
            self._record_semantic_request(
                metrics=metrics,
                response=response,
                request_started_at=request_started_at,
                validation_outcome="failed",
                fallback_reason=self._safe_failure_reason(exc),
            )
            raise

        self._record_semantic_request(
            metrics=metrics,
            response=response,
            request_started_at=request_started_at,
            validation_outcome="passed",
            fallback_reason=None,
        )
        return chunks

    def _record_semantic_request(
        self,
        *,
        metrics: ChunkingRunMetrics,
        response: Any | None,
        request_started_at: float,
        validation_outcome: ValidationOutcome,
        fallback_reason: str | None,
    ) -> None:
        diagnostic = self.request_contract.build_diagnostic(
            response=response,
            latency_ms=self._elapsed_ms(request_started_at),
            validation_outcome=validation_outcome,
            fallback_reason=fallback_reason,
        )
        metrics.semantic_requests.append(diagnostic)

    def _build_semantic_chunking_metadata(
        self,
        *,
        metrics: ChunkingRunMetrics,
    ) -> dict[str, object]:
        requests = metrics.semantic_requests
        total_latency_ms = round(
            sum(request.latency_ms for request in requests),
            2,
        )
        average_latency_ms = (
            round(total_latency_ms / len(requests), 2) if requests else 0.0
        )

        prompt_tokens = self._sum_optional_usage(
            values=[request.prompt_tokens for request in requests]
        )
        completion_tokens = self._sum_optional_usage(
            values=[request.completion_tokens for request in requests]
        )
        total_tokens = self._sum_optional_usage(
            values=[request.total_tokens for request in requests]
        )
        cost_usd = self._sum_optional_cost(
            values=[request.cost_usd for request in requests]
        )

        return {
            "model": self.config.model,
            "prompt_version": self.config.prompt_version,
            "temperature": self.config.temperature,
            "seed": self.config.seed,
            "max_output_tokens": self.config.max_output_tokens,
            "provider": self.request_contract.provider_options(),
            "inference_mode": "sequential",
            "request_count": len(requests),
            "latency_ms": {
                "total": total_latency_ms,
                "average": average_latency_ms,
            },
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
            },
            "requests": [request.to_metadata() for request in requests],
        }

    def _sum_optional_usage(self, *, values: Sequence[int | None]) -> int | None:
        present_values = [value for value in values if value is not None]
        return sum(present_values) if present_values else None

    def _sum_optional_cost(self, *, values: Sequence[float | None]) -> float | None:
        present_values = [value for value in values if value is not None]
        return round(sum(present_values), 10) if present_values else None

    def _build_llm_messages(
        self,
        *,
        section: MarkdownSection,
    ) -> list[ChatCompletionMessageParam]:
        return [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": self.user_prompt(section=section)},
        ]

    def _build_batch_llm_messages(
        self,
        *,
        sections: Sequence[MarkdownSection],
    ) -> list[ChatCompletionMessageParam]:
        return [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": self.batch_user_prompt(sections=sections)},
        ]

    def _extract_message_content(self, *, response: Any) -> str:
        choices = getattr(response, "choices", [])
        if not choices:
            raise ChunkingModelError("invalid_response")

        finish_reason = getattr(choices[0], "finish_reason", None)
        if finish_reason == "length":
            raise ChunkingModelError("truncated_response")

        message = getattr(choices[0], "message", None)
        message_content = getattr(message, "content", None)
        if not isinstance(message_content, str) or not message_content.strip():
            raise ChunkingModelError("invalid_response")

        return message_content

    def _validate_and_build_model_chunks(
        self,
        *,
        proposals: ChunkProposals,
        section: MarkdownSection,
        method: ChunkingMethod,
    ) -> list[SectionChunkDraft]:
        source_spans = self.source_validator.validate_and_reconstruct(
            source_text=section.text,
            proposed_chunk_texts=[proposal.chunk_text for proposal in proposals.chunks],
            section_title=section.title,
        )
        return self._build_validated_span_drafts(
            source_spans=source_spans,
            section=section,
            method=method,
        )

    def _validate_and_build_batch_model_chunks(
        self,
        *,
        proposals: BatchChunkProposals,
        sections: Sequence[MarkdownSection],
        method: ChunkingMethod,
    ) -> list[SectionChunkDraft]:
        if not proposals.chunks:
            raise SourceChunkValidationError("missing_source_text")

        sections_by_index = {section.index: section for section in sections}
        proposal_texts_by_section: dict[int, list[str]] = {
            section.index: [] for section in sections
        }

        for proposal in proposals.chunks:
            section = sections_by_index.get(proposal.section_index)
            if section is None:
                raise SourceChunkValidationError("invalid_span")

            proposal_texts_by_section[section.index].append(proposal.chunk_text)

        chunk_drafts: list[SectionChunkDraft] = []
        for section in sections:
            source_spans = self.source_validator.validate_and_reconstruct(
                source_text=section.text,
                proposed_chunk_texts=proposal_texts_by_section[section.index],
                section_title=section.title,
            )
            chunk_drafts.extend(
                self._build_validated_span_drafts(
                    source_spans=source_spans,
                    section=section,
                    method=method,
                )
            )

        return chunk_drafts

    def _build_validated_span_drafts(
        self,
        *,
        source_spans: Sequence[SourceChunkSpan],
        section: MarkdownSection,
        method: ChunkingMethod,
    ) -> list[SectionChunkDraft]:
        chunk_drafts: list[SectionChunkDraft] = []

        for source_span in source_spans:
            chunk_drafts.extend(
                SectionChunkDraft(
                    text=deterministic_chunk.text,
                    chunk_title=deterministic_chunk.chunk_title,
                    section_title=section.title,
                    method=method,
                    validation_outcome="passed",
                )
                for deterministic_chunk in self.deterministic_splitter.split_validated_text(
                    source_text=source_span.text,
                    section_title=source_span.chunk_title,
                )
            )

        return chunk_drafts

    def _chunk_section_deterministically(
        self,
        *,
        section: MarkdownSection,
        fallback_reason: str,
    ) -> list[SectionChunkDraft]:
        return [
            SectionChunkDraft(
                text=deterministic_chunk.text,
                chunk_title=deterministic_chunk.chunk_title,
                section_title=section.title,
                method="deterministic",
                reason=fallback_reason,
                validation_outcome=(
                    "not_attempted"
                    if fallback_reason == "semantic_chunking_disabled"
                    else "failed"
                ),
            )
            for deterministic_chunk in self.deterministic_splitter.split(
                source_text=section.text,
                section_title=section.title,
            )
        ]

    def _build_section_batches(
        self,
        *,
        sections: Sequence[MarkdownSection],
    ) -> list[MarkdownSectionBatch]:
        is_batching_active = (
            self.config.is_batching_enabled and self.config.is_llm_enabled
        )
        if not is_batching_active:
            return [
                MarkdownSectionBatch(
                    index=batch_index,
                    sections=(section,),
                    estimated_input_tokens=self._estimate_tokens(section.text),
                )
                for batch_index, section in enumerate(sections)
            ]

        section_batches: list[MarkdownSectionBatch] = []
        current_sections: list[MarkdownSection] = []
        current_token_count = 0

        for section in sections:
            section_token_count = self._estimate_tokens(section.text)
            has_reached_section_limit = (
                len(current_sections) >= self.config.batch_max_sections
            )
            would_exceed_token_limit = (
                current_token_count + section_token_count > self.config.batch_max_tokens
            )

            if current_sections and (
                has_reached_section_limit or would_exceed_token_limit
            ):
                self._append_section_batch(
                    section_batches=section_batches,
                    sections=current_sections,
                    estimated_input_tokens=current_token_count,
                )
                current_sections = []
                current_token_count = 0

            current_sections.append(section)
            current_token_count += section_token_count

        if current_sections:
            self._append_section_batch(
                section_batches=section_batches,
                sections=current_sections,
                estimated_input_tokens=current_token_count,
            )

        return section_batches

    def _append_section_batch(
        self,
        *,
        section_batches: list[MarkdownSectionBatch],
        sections: Sequence[MarkdownSection],
        estimated_input_tokens: int,
    ) -> None:
        section_batches.append(
            MarkdownSectionBatch(
                index=len(section_batches),
                sections=tuple(sections),
                estimated_input_tokens=estimated_input_tokens,
            )
        )

    def _split_markdown_sections(self, markdown: str) -> list[MarkdownSection]:
        clean_markdown = markdown.strip()
        if not clean_markdown:
            return []

        sections: list[MarkdownSection] = []
        current_title = "Documento"
        current_lines: list[str] = []

        for line in clean_markdown.splitlines():
            heading_match = SECTION_HEADING_PATTERN.match(line.strip())
            if heading_match is not None:
                self._append_section(
                    sections=sections,
                    title=current_title,
                    lines=current_lines,
                )
                current_title = heading_match.group(2).strip()
                current_lines = [line]
                continue

            current_lines.append(line)

        self._append_section(
            sections=sections,
            title=current_title,
            lines=current_lines,
        )
        return sections

    def _append_section(
        self,
        *,
        sections: list[MarkdownSection],
        title: str,
        lines: list[str],
    ) -> None:
        section_text = "\n".join(lines).strip()
        if not section_text:
            return

        sections.append(
            MarkdownSection(
                index=len(sections),
                title=title,
                text=section_text,
            )
        )

    def _build_document_chunk(
        self,
        *,
        doc_id: str,
        index: int,
        chunk_draft: SectionChunkDraft,
    ) -> DocumentChunk:
        metadata: dict[str, object] = {
            "section_title": chunk_draft.section_title,
            "chunk_title": chunk_draft.chunk_title,
            "method": chunk_draft.method,
        }
        if chunk_draft.reason is not None:
            metadata["fallback_reason"] = chunk_draft.reason
        metadata["validation_outcome"] = chunk_draft.validation_outcome

        return DocumentChunk(
            chunk_id=make_chunk_id(doc_id=doc_id, index=index, text=chunk_draft.text),
            doc_id=doc_id,
            index=index,
            text=chunk_draft.text,
            chunk_title=chunk_draft.chunk_title,
            section_title=chunk_draft.section_title,
            token_estimate=self._estimate_tokens(chunk_draft.text),
            method=chunk_draft.method,
            metadata=metadata,
        )

    def _log_section_chunked(
        self,
        *,
        doc_id: str,
        section: MarkdownSection,
        method: ChunkingMethod,
        chunk_count: int,
        duration_ms: float,
        primary_failure: ChunkingAttemptFailure | None = None,
    ) -> None:
        log_fields: dict[str, object] = {
            "doc_id": doc_id,
            "section_index": section.index,
            "section_title": section.title,
            "method": method,
            "chunk_count": chunk_count,
            "duration_ms": duration_ms,
        }
        if method == "deterministic":
            log_fields.update(
                {
                    "primary_failed": primary_failure is not None,
                    "primary_error_type": (
                        primary_failure.error_type if primary_failure else None
                    ),
                    "primary_failure_reason": (
                        primary_failure.failure_reason if primary_failure else None
                    ),
                }
            )

        logger.debug("rag_section_chunked", **log_fields)

    def _log_batch_chunked(
        self,
        *,
        doc_id: str,
        section_batch: MarkdownSectionBatch,
        method: str,
        chunk_count: int,
        duration_ms: float,
    ) -> None:
        logger.debug(
            "rag_chunking_batch_completed",
            doc_id=doc_id,
            batch_index=section_batch.index,
            section_indices=[section.index for section in section_batch.sections],
            section_count=len(section_batch.sections),
            estimated_input_tokens=section_batch.estimated_input_tokens,
            method=method,
            chunk_count=chunk_count,
            duration_ms=duration_ms,
        )

    def _estimate_tokens(self, text: str) -> int:
        return self.token_estimator.estimate(text)

    def _elapsed_ms(self, started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000, 2)
