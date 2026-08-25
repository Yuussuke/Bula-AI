from __future__ import annotations

import asyncio
import hashlib
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence

import structlog
from langchain_text_splitters import (
    ExperimentalMarkdownSyntaxTextSplitter,
    RecursiveCharacterTextSplitter,
)
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema

from app.modules.rag.schemas import (
    BatchChunkProposals,
    ChunkingConfig,
    ChunkingMethod,
    ChunkProposals,
    ChunkResult,
    DocumentChunk,
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
                            "chunk_title": {"type": "string"},
                            "reason": {"type": ["string", "null"]},
                        },
                        "required": ["chunk_text", "chunk_title", "reason"],
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
                            "chunk_title": {"type": "string"},
                            "reason": {"type": ["string", "null"]},
                        },
                        "required": [
                            "section_index",
                            "chunk_text",
                            "chunk_title",
                            "reason",
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


@dataclass(frozen=True)
class ChunkingAttemptFailure:
    method: ChunkingMethod
    error_type: str
    failure_reason: str


@dataclass
class ChunkingRunMetrics:
    model_call_count: int = 0
    batch_fallback_count: int = 0


def make_chunk_id(doc_id: str, index: int, text: str) -> str:
    digest = hashlib.md5(f"{doc_id}:{index}:{text}".encode()).hexdigest()[:12]
    return f"{doc_id}_{index}_{digest}"


class BaseChunker(ABC):
    def __init__(
        self,
        llm: AsyncOpenAI,
        config: ChunkingConfig,
        token_estimator: TokenEstimator | None = None,
    ) -> None:
        self.llm = llm
        self.config = config
        self.token_estimator = token_estimator or HeuristicTokenEstimator()

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
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        metrics = ChunkingRunMetrics()

        batch_tasks = [
            self._chunk_batch_with_semaphore(
                semaphore=semaphore,
                section_batch=section_batch,
                doc_id=doc_id,
                metrics=metrics,
            )
            for section_batch in section_batches
        ]
        batch_results = await asyncio.gather(*batch_tasks)

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
                "chunk_count": len(chunks),
            },
        )

    async def _chunk_batch_with_semaphore(
        self,
        *,
        semaphore: asyncio.Semaphore,
        section_batch: MarkdownSectionBatch,
        doc_id: str,
        metrics: ChunkingRunMetrics,
    ) -> list[SectionChunkDraft]:
        async with semaphore:
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
        fallback_failure: ChunkingAttemptFailure | None = None

        if self.config.is_llm_enabled:
            primary_chunks, primary_failure = await self._try_model_chunking(
                section=section,
                doc_id=doc_id,
                model=self.config.model,
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

            fallback_chunks, fallback_failure = await self._try_model_chunking(
                section=section,
                doc_id=doc_id,
                model=self.config.fallback_model,
                method="fallback",
                metrics=metrics,
            )
            if fallback_chunks is not None:
                self._log_section_chunked(
                    doc_id=doc_id,
                    section=section,
                    method="fallback",
                    chunk_count=len(fallback_chunks),
                    duration_ms=self._elapsed_ms(section_started_at),
                )
                return fallback_chunks

        heuristic_chunks = self._chunk_section_heuristically(section=section)
        self._log_section_chunked(
            doc_id=doc_id,
            section=section,
            method="heuristic",
            chunk_count=len(heuristic_chunks),
            duration_ms=self._elapsed_ms(section_started_at),
            primary_failure=primary_failure,
            fallback_failure=fallback_failure,
        )
        return heuristic_chunks

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
            model=self.config.model,
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

        fallback_chunks, fallback_failure = await self._try_batch_model_chunking(
            section_batch=section_batch,
            doc_id=doc_id,
            model=self.config.fallback_model,
            method="fallback",
            metrics=metrics,
        )
        if fallback_chunks is not None:
            self._log_batch_chunked(
                doc_id=doc_id,
                section_batch=section_batch,
                method="fallback",
                chunk_count=len(fallback_chunks),
                duration_ms=self._elapsed_ms(batch_started_at),
            )
            return fallback_chunks

        assert primary_failure is not None
        assert fallback_failure is not None
        metrics.batch_fallback_count += 1
        logger.warning(
            "rag_chunking_batch_falling_back_to_sections",
            doc_id=doc_id,
            batch_index=section_batch.index,
            section_indices=[section.index for section in section_batch.sections],
            section_count=len(section_batch.sections),
            primary_error_type=primary_failure.error_type,
            fallback_error_type=fallback_failure.error_type,
            primary_failure_reason=primary_failure.failure_reason,
            fallback_failure_reason=fallback_failure.failure_reason,
        )

        chunk_drafts: list[SectionChunkDraft] = []
        for section in section_batch.sections:
            section_chunk_drafts = await self._chunk_section(
                section=section,
                doc_id=doc_id,
                metrics=metrics,
            )
            chunk_drafts.extend(section_chunk_drafts)

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
        model: str,
        method: ChunkingMethod,
        metrics: ChunkingRunMetrics,
    ) -> tuple[list[SectionChunkDraft] | None, ChunkingAttemptFailure | None]:
        try:
            metrics.model_call_count += 1
            chunks = await self._chunk_batch_with_model(
                section_batch=section_batch,
                model=model,
                method=method,
            )
            return chunks, None
        except Exception as exc:
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
        model: str,
        method: ChunkingMethod,
    ) -> list[SectionChunkDraft]:
        response = await self.llm.chat.completions.create(
            model=model,
            messages=self._build_batch_llm_messages(
                sections=section_batch.sections,
            ),
            temperature=0,
            response_format=BATCH_CHUNK_PROPOSALS_RESPONSE_FORMAT,
        )
        message_content = self._extract_message_content(response=response)
        proposals = BatchChunkProposals.model_validate_json(message_content)
        return self._validate_and_build_batch_model_chunks(
            proposals=proposals,
            sections=section_batch.sections,
            method=method,
        )

    async def _try_model_chunking(
        self,
        *,
        section: MarkdownSection,
        doc_id: str,
        model: str,
        method: ChunkingMethod,
        metrics: ChunkingRunMetrics,
    ) -> tuple[list[SectionChunkDraft] | None, ChunkingAttemptFailure | None]:
        try:
            metrics.model_call_count += 1
            chunks = await self._chunk_section_with_model(
                section=section, model=model, method=method
            )
            return chunks, None
        except Exception as exc:
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
        if isinstance(exc, ChunkingModelError):
            return "untrusted_model_response"

        return "model_call_failed"

    async def _chunk_section_with_model(
        self,
        *,
        section: MarkdownSection,
        model: str,
        method: ChunkingMethod,
    ) -> list[SectionChunkDraft]:
        response = await self.llm.chat.completions.create(
            model=model,
            messages=self._build_llm_messages(section=section),
            temperature=0,
            response_format=CHUNK_PROPOSALS_RESPONSE_FORMAT,
        )
        message_content = self._extract_message_content(response=response)
        proposals = ChunkProposals.model_validate_json(message_content)
        return self._validate_and_build_model_chunks(
            proposals=proposals,
            section=section,
            method=method,
        )

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
            raise ChunkingModelError("Model response did not include choices.")

        message = getattr(choices[0], "message", None)
        message_content = getattr(message, "content", None)
        if not isinstance(message_content, str) or not message_content.strip():
            raise ChunkingModelError("Model response did not include JSON content.")

        return message_content

    def _validate_and_build_model_chunks(
        self,
        *,
        proposals: ChunkProposals,
        section: MarkdownSection,
        method: ChunkingMethod,
    ) -> list[SectionChunkDraft]:
        if not proposals.chunks:
            raise ChunkingModelError("Model returned no chunk proposals.")

        chunk_drafts: list[SectionChunkDraft] = []
        for proposal in proposals.chunks:
            chunk_text = proposal.chunk_text.strip()
            if not chunk_text:
                raise ChunkingModelError("Model returned an empty chunk.")

            if not self._is_text_present_in_section(
                chunk_text=chunk_text,
                section_text=section.text,
            ):
                raise ChunkingModelError(
                    "Model returned text outside the source section."
                )

            estimated_tokens = self._estimate_tokens(chunk_text)
            if estimated_tokens > self.config.max_tokens:
                raise ChunkingModelError("Model returned an oversized chunk.")

            clean_chunk_title = proposal.chunk_title.strip() or section.title
            chunk_drafts.append(
                SectionChunkDraft(
                    text=chunk_text,
                    chunk_title=clean_chunk_title,
                    section_title=section.title,
                    method=method,
                    reason=proposal.reason,
                )
            )

        return chunk_drafts

    def _validate_and_build_batch_model_chunks(
        self,
        *,
        proposals: BatchChunkProposals,
        sections: Sequence[MarkdownSection],
        method: ChunkingMethod,
    ) -> list[SectionChunkDraft]:
        if not proposals.chunks:
            raise ChunkingModelError("Model returned no batch chunk proposals.")

        sections_by_index = {section.index: section for section in sections}
        chunk_drafts_by_section: dict[int, list[SectionChunkDraft]] = {
            section.index: [] for section in sections
        }

        for proposal in proposals.chunks:
            section = sections_by_index.get(proposal.section_index)
            if section is None:
                raise ChunkingModelError("Model returned an unknown section index.")

            chunk_text = proposal.chunk_text.strip()
            if not chunk_text:
                raise ChunkingModelError("Model returned an empty batch chunk.")

            if not self._is_text_present_in_section(
                chunk_text=chunk_text,
                section_text=section.text,
            ):
                raise ChunkingModelError(
                    "Model returned batch text outside the referenced section."
                )

            estimated_tokens = self._estimate_tokens(chunk_text)
            if estimated_tokens > self.config.max_tokens:
                raise ChunkingModelError("Model returned an oversized batch chunk.")

            clean_chunk_title = proposal.chunk_title.strip() or section.title
            chunk_drafts_by_section[section.index].append(
                SectionChunkDraft(
                    text=chunk_text,
                    chunk_title=clean_chunk_title,
                    section_title=section.title,
                    method=method,
                    reason=proposal.reason,
                )
            )

        missing_section_indices = [
            section.index
            for section in sections
            if not chunk_drafts_by_section[section.index]
        ]
        if missing_section_indices:
            raise ChunkingModelError(
                "Model did not return chunks for every section in the batch."
            )

        return [
            chunk_draft
            for section in sections
            for chunk_draft in chunk_drafts_by_section[section.index]
        ]

    def _chunk_section_heuristically(
        self,
        *,
        section: MarkdownSection,
    ) -> list[SectionChunkDraft]:
        first_pass_chunks = self._split_with_markdown_syntax(section.text)
        final_chunk_texts: list[str] = []

        for chunk_text in first_pass_chunks:
            if self._estimate_tokens(chunk_text) > self.config.max_tokens:
                final_chunk_texts.extend(self._split_oversized_chunk(chunk_text))
                continue

            final_chunk_texts.append(chunk_text)

        return [
            SectionChunkDraft(
                text=chunk_text,
                chunk_title=section.title,
                section_title=section.title,
                method="heuristic",
            )
            for chunk_text in final_chunk_texts
            if chunk_text.strip()
        ]

    def _split_with_markdown_syntax(self, text: str) -> list[str]:
        splitter = ExperimentalMarkdownSyntaxTextSplitter(
            headers_to_split_on=[
                ("##", "section"),
                ("###", "subsection"),
            ],
            strip_headers=False,
        )
        documents = splitter.split_text(text)
        chunks = [
            document.page_content.strip()
            for document in documents
            if document.page_content.strip()
        ]

        clean_text = text.strip()
        if chunks:
            return chunks

        if clean_text:
            return [clean_text]

        return []

    def _split_oversized_chunk(self, text: str) -> list[str]:
        max_tokens = self.config.max_tokens
        overlap_tokens = self._overlap_tokens(max_tokens=max_tokens)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens,
            chunk_overlap=overlap_tokens,
            length_function=self._estimate_tokens,
            separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
        )
        return [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]

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
            metadata["reason"] = chunk_draft.reason

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
        fallback_failure: ChunkingAttemptFailure | None = None,
    ) -> None:
        log_fields: dict[str, object] = {
            "doc_id": doc_id,
            "section_index": section.index,
            "section_title": section.title,
            "method": method,
            "chunk_count": chunk_count,
            "duration_ms": duration_ms,
        }
        if method == "heuristic":
            log_fields.update(
                {
                    "primary_failed": primary_failure is not None,
                    "fallback_failed": fallback_failure is not None,
                    "primary_error_type": (
                        primary_failure.error_type if primary_failure else None
                    ),
                    "fallback_error_type": (
                        fallback_failure.error_type if fallback_failure else None
                    ),
                    "primary_failure_reason": (
                        primary_failure.failure_reason if primary_failure else None
                    ),
                    "fallback_failure_reason": (
                        fallback_failure.failure_reason if fallback_failure else None
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

    def _is_text_present_in_section(
        self,
        *,
        chunk_text: str,
        section_text: str,
    ) -> bool:
        normalized_chunk_text = self._normalize_text_for_matching(chunk_text)
        normalized_section_text = self._normalize_text_for_matching(section_text)
        return normalized_chunk_text in normalized_section_text

    def _normalize_text_for_matching(self, text: str) -> str:
        return " ".join(text.split())

    def _estimate_tokens(self, text: str) -> int:
        return self.token_estimator.estimate(text)

    def _elapsed_ms(self, started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000, 2)

    def _overlap_tokens(self, *, max_tokens: int) -> int:
        if max_tokens <= 1:
            return 0

        overlap_tokens = int(max_tokens * self.config.overlap_ratio)
        return min(overlap_tokens, max_tokens - 1)
