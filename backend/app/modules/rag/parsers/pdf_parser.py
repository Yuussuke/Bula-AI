from __future__ import annotations

import asyncio
from dataclasses import dataclass
from app.modules.rag.parsers.document_cleaner import (
    BulaDocumentCleaner,
    render_front_matter,
)
from app.modules.rag.parsers.handlers import (
    ExtractedLine,
    ExtractionResult,
    ParserHandler,
    PyMuPDF4LLMHandler,
    PyMuPDFHandler,
)
from app.modules.rag.parsers.markdown_hygiene import trim_markdown_from_legal_section
from app.modules.rag.parsers.markdown_renderer import (
    MarkdownBuildResult,
    MarkdownRenderer,
)
from app.modules.rag.parsers.metadata_extractor import MetadataExtractor
from app.modules.rag.parsers.section_detector import SectionDetector


DEFAULT_FAILURE_ERROR = (
    "No text-based extraction tier produced enough content. "
    "OCR is not enabled in this parsing phase."
)
PARSER_VERSION = "native_markdown_v1"


@dataclass
class ParseResult:
    markdown: str
    metadata: dict[str, object]
    sections: list[str]
    extraction_tier: str
    success: bool
    error: str | None = None
    parser_version: str = PARSER_VERSION
    converter_name: str | None = None
    converter_version: str | None = None
    extraction_decision: str | None = None
    cleanup_summary: dict[str, object] | None = None


class BulaParser:
    """Assembles the parser chain and produces structured Markdown from a PDF."""

    def __init__(
        self,
        ocr_enabled: bool = False,
        first_handler: ParserHandler | None = None,
        section_detector: SectionDetector | None = None,
        markdown_renderer: MarkdownRenderer | None = None,
        metadata_extractor: MetadataExtractor | None = None,
        document_cleaner: BulaDocumentCleaner | None = None,
    ) -> None:
        self.ocr_enabled = ocr_enabled
        self.first_handler = first_handler or self._build_default_handler_chain()
        self.section_detector = section_detector or SectionDetector()
        self.markdown_renderer = markdown_renderer or MarkdownRenderer()
        self.metadata_extractor = metadata_extractor or MetadataExtractor()
        self.document_cleaner = document_cleaner or BulaDocumentCleaner()

    async def parse(self, pdf_bytes: bytes, filename: str) -> ParseResult:
        if not pdf_bytes:
            return self._build_failure_parse_result(
                error="PDF content is empty.",
                extraction_tier="",
            )

        extraction_result = await asyncio.to_thread(
            self.first_handler.handle,
            pdf_bytes,
            filename,
        )

        is_extraction_sparse = bool(
            extraction_result.quality_signals.get("is_sparse", True)
        )
        if extraction_result.error is not None or is_extraction_sparse:
            return self._build_failure_parse_result(
                error=self._build_extraction_error(extraction_result),
                extraction_tier=extraction_result.extraction_tier,
            )

        cleanup_result = self.document_cleaner.clean(extraction_result.pages)
        extracted_lines = cleanup_result.lines
        if not extracted_lines:
            extracted_lines = self._collect_lines(extraction_result=extraction_result)
        detected_sections = self.section_detector.detect(extracted_lines)
        markdown_result = self.markdown_renderer.render(
            lines=extracted_lines,
            detected_sections=detected_sections,
        )
        markdown_result = self._prepend_front_matter(
            markdown_result=markdown_result,
            front_matter=cleanup_result.front_matter,
        )
        markdown_result = trim_markdown_from_legal_section(markdown_result)
        metadata = self.metadata_extractor.extract(
            lines=extracted_lines,
            filename=filename,
            markdown_sections=markdown_result.sections,
            detected_sections=markdown_result.detected_sections,
            quality_signals=extraction_result.quality_signals,
            front_matter=cleanup_result.front_matter,
            parser_version=PARSER_VERSION,
            cleanup_summary=cleanup_result.summary,
        )

        return ParseResult(
            markdown=markdown_result.markdown,
            metadata=metadata,
            sections=markdown_result.sections,
            extraction_tier=extraction_result.extraction_tier,
            success=True,
            converter_name=extraction_result.converter_name,
            converter_version=extraction_result.converter_version,
            extraction_decision=extraction_result.extraction_decision,
            cleanup_summary=cleanup_result.summary,
        )

    def _build_default_handler_chain(self) -> ParserHandler:
        pymupdf4llm_handler = PyMuPDF4LLMHandler()
        pymupdf_handler = PyMuPDFHandler()
        pymupdf4llm_handler.set_next(pymupdf_handler)
        return pymupdf4llm_handler

    def _prepend_front_matter(
        self,
        *,
        markdown_result: MarkdownBuildResult,
        front_matter: dict[str, str],
    ) -> MarkdownBuildResult:
        front_matter_markdown = render_front_matter(front_matter)
        if not front_matter_markdown:
            return markdown_result

        prefix = f"{front_matter_markdown}\n\n"
        for section in markdown_result.detected_sections:
            section.char_start += len(prefix)
            if section.char_end is not None:
                section.char_end += len(prefix)

        return MarkdownBuildResult(
            markdown=f"{prefix}{markdown_result.markdown}",
            sections=markdown_result.sections,
            detected_sections=markdown_result.detected_sections,
        )

    def _collect_lines(
        self,
        *,
        extraction_result: ExtractionResult,
    ) -> list[ExtractedLine]:
        extracted_lines: list[ExtractedLine] = []
        for page in extraction_result.pages:
            extracted_lines.extend(page.lines)

        if extracted_lines:
            return extracted_lines

        return [
            ExtractedLine(text=line.strip(), page_number=1)
            for line in extraction_result.text.splitlines()
            if line.strip()
        ]

    def _build_failure_parse_result(
        self,
        *,
        error: str,
        extraction_tier: str,
    ) -> ParseResult:
        return ParseResult(
            markdown="",
            metadata={},
            sections=[],
            extraction_tier=extraction_tier,
            success=False,
            error=error,
        )

    def _build_extraction_error(self, extraction_result: ExtractionResult) -> str:
        if extraction_result.error is not None:
            return extraction_result.error

        return DEFAULT_FAILURE_ERROR
