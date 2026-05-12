from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re

from app.modules.rag.parsers.handlers import (
    ExtractedLine,
    ExtractionResult,
    normalize_for_matching,
    ParserHandler,
    PdfplumberHandler,
    PyMuPDFHandler,
)
from app.modules.rag.parsers.markdown_renderer import MarkdownRenderer
from app.modules.rag.parsers.metadata_extractor import MetadataExtractor
from app.modules.rag.parsers.section_detector import SectionDetector


DEFAULT_FAILURE_ERROR = (
    "No text-based extraction tier produced enough content. "
    "OCR is not enabled in this parsing phase."
)
LEGAL_SECTION_PATTERN = re.compile(
    r"^(?:[0-9]{1,2}|[IVXLCDM]+)?\b\W*DIZERES\s+LEGAIS\b"
)


@dataclass
class ParseResult:
    markdown: str
    metadata: dict[str, object]
    sections: list[str]
    extraction_tier: str
    success: bool
    error: str | None = None


class BulaParser:
    """Assembles the parser chain and produces structured Markdown from a PDF."""

    def __init__(
        self,
        ocr_enabled: bool = False,
        first_handler: ParserHandler | None = None,
        section_detector: SectionDetector | None = None,
        markdown_renderer: MarkdownRenderer | None = None,
        metadata_extractor: MetadataExtractor | None = None,
    ) -> None:
        self.ocr_enabled = ocr_enabled
        self.first_handler = first_handler or self._build_default_handler_chain()
        self.section_detector = section_detector or SectionDetector()
        self.markdown_renderer = markdown_renderer or MarkdownRenderer()
        self.metadata_extractor = metadata_extractor or MetadataExtractor()

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

        extracted_lines = self._collect_lines(extraction_result=extraction_result)
        extracted_lines = self._trim_lines_from_legal_section(extracted_lines)
        detected_sections = self.section_detector.detect(extracted_lines)
        markdown_result = self.markdown_renderer.render(
            lines=extracted_lines,
            detected_sections=detected_sections,
        )
        metadata = self.metadata_extractor.extract(
            lines=extracted_lines,
            filename=filename,
            markdown_sections=markdown_result.sections,
            detected_sections=markdown_result.detected_sections,
            quality_signals=extraction_result.quality_signals,
        )

        return ParseResult(
            markdown=markdown_result.markdown,
            metadata=metadata,
            sections=markdown_result.sections,
            extraction_tier=extraction_result.extraction_tier,
            success=True,
        )

    def _build_default_handler_chain(self) -> ParserHandler:
        pdfplumber_handler = PdfplumberHandler()
        pymupdf_handler = PyMuPDFHandler()
        pdfplumber_handler.set_next(pymupdf_handler)
        return pdfplumber_handler

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

    def _trim_lines_from_legal_section(
        self,
        extracted_lines: list[ExtractedLine],
    ) -> list[ExtractedLine]:
        for line_index, extracted_line in enumerate(extracted_lines):
            normalized_line = normalize_for_matching(extracted_line.text)
            if LEGAL_SECTION_PATTERN.match(normalized_line):
                return extracted_lines[:line_index]

        return extracted_lines

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
