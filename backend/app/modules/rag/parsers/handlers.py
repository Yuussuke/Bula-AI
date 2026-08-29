from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
import importlib
import re
from typing import Any
import unicodedata


ANVISA_SECTION_KEYWORDS = (
    "COMPOSICAO",
    "INDICACOES",
    "POSOLOGIA",
    "CONTRAINDICACOES",
)

BOLD_FONT_MARKERS = (
    "BOLD",
    "BLACK",
    "HEAVY",
    "SEMIBOLD",
    "NEGRITO",
)


@dataclass
class ExtractedLine:
    text: str
    page_number: int
    average_font_size: float | None = None
    max_font_size: float | None = None
    is_bold: bool = False
    is_paragraph_break: bool = False
    markdown_heading_level: int | None = None


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    lines: list[ExtractedLine]


@dataclass
class ExtractionResult:
    text: str
    extraction_tier: str
    pages: list[ExtractedPage]
    quality_signals: dict[str, object]
    converter_name: str | None = None
    converter_version: str | None = None
    extraction_decision: str | None = None
    error: str | None = None


class ParserHandler(ABC):
    extraction_tier: str

    def __init__(self) -> None:
        self._next: ParserHandler | None = None

    def set_next(self, handler: ParserHandler) -> ParserHandler:
        self._next = handler
        return handler

    def handle(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        extraction_result = self._extract(pdf_bytes=pdf_bytes, filename=filename)

        should_try_next_handler = self._should_delegate(extraction_result)
        if should_try_next_handler:
            return self._delegate_or_return_result(
                extraction_result=extraction_result,
                pdf_bytes=pdf_bytes,
                filename=filename,
            )

        return extraction_result

    @abstractmethod
    def _extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        """Extract text from the PDF without deciding final parser failure."""
        raise NotImplementedError

    def _should_delegate(self, extraction_result: ExtractionResult) -> bool:
        has_next_handler = self._next is not None
        has_error = extraction_result.error is not None
        is_sparse = bool(extraction_result.quality_signals.get("is_sparse", True))
        return has_next_handler and (has_error or is_sparse)

    def _delegate_or_return_result(
        self,
        *,
        extraction_result: ExtractionResult,
        pdf_bytes: bytes,
        filename: str,
    ) -> ExtractionResult:
        if self._next is None:
            return extraction_result

        next_result = self._next.handle(pdf_bytes=pdf_bytes, filename=filename)
        delegated_from = self._build_delegated_from_signal(
            current_result=extraction_result,
            next_result=next_result,
        )
        next_result.quality_signals["delegated_from"] = delegated_from
        return next_result

    def _build_delegated_from_signal(
        self,
        *,
        current_result: ExtractionResult,
        next_result: ExtractionResult,
    ) -> list[dict[str, object]]:
        delegated_from_signal = next_result.quality_signals.get("delegated_from", [])
        delegated_from: list[dict[str, object]] = []

        if isinstance(delegated_from_signal, list):
            for previous_signal in delegated_from_signal:
                if isinstance(previous_signal, dict):
                    delegated_from.append(previous_signal)

        delegated_from.insert(
            0,
            {
                "extraction_tier": current_result.extraction_tier,
                "error": current_result.error,
                "is_sparse": current_result.quality_signals.get("is_sparse", True),
                "character_count": current_result.quality_signals.get(
                    "character_count", 0
                ),
            },
        )
        return delegated_from

    def _build_quality_signals(self, text: str) -> dict[str, object]:
        clean_text = text.strip()
        matched_section_keywords = self._find_matched_section_keywords(clean_text)
        is_text_too_short = len(clean_text) < 100
        has_section_keyword = len(matched_section_keywords) > 0

        return {
            "is_sparse": is_text_too_short or not has_section_keyword,
            "character_count": len(clean_text),
            "matched_section_keywords": matched_section_keywords,
        }

    def _find_matched_section_keywords(self, text: str) -> list[str]:
        normalized_text = normalize_for_matching(text)
        return [
            keyword for keyword in ANVISA_SECTION_KEYWORDS if keyword in normalized_text
        ]

    def _is_sparse(self, text: str) -> bool:
        quality_signals = self._build_quality_signals(text)
        return bool(quality_signals["is_sparse"])

    def _build_failure_result(
        self,
        error: str,
        *,
        converter_name: str | None = None,
        converter_version: str | None = None,
        extraction_decision: str | None = None,
    ) -> ExtractionResult:
        return ExtractionResult(
            text="",
            extraction_tier=self.extraction_tier,
            pages=[],
            quality_signals=self._build_quality_signals(""),
            converter_name=converter_name,
            converter_version=converter_version,
            extraction_decision=extraction_decision,
            error=error,
        )

    def _build_success_result(
        self,
        pages: list[ExtractedPage],
        *,
        converter_name: str | None = None,
        converter_version: str | None = None,
        extraction_decision: str | None = None,
    ) -> ExtractionResult:
        text = "\n".join(page.text for page in pages if page.text.strip())
        quality_signals = self._build_quality_signals(text)
        quality_signals.update(
            {
                "converter_name": converter_name,
                "converter_version": converter_version,
                "extraction_decision": extraction_decision,
            }
        )
        return ExtractionResult(
            text=text,
            extraction_tier=self.extraction_tier,
            pages=pages,
            quality_signals=quality_signals,
            converter_name=converter_name,
            converter_version=converter_version,
            extraction_decision=extraction_decision,
        )

    def _build_lines_from_text(
        self,
        *,
        text: str,
        page_number: int,
    ) -> list[ExtractedLine]:
        return [
            ExtractedLine(text=line.strip(), page_number=page_number)
            for line in text.splitlines()
            if line.strip()
        ]


class PdfplumberHandler(ParserHandler):
    extraction_tier = "pdfplumber"

    def _extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        try:
            pdfplumber_module = get_pdfplumber_module()
            with pdfplumber_module.open(BytesIO(pdf_bytes)) as pdf:
                pages = [
                    self._extract_page(page=page, page_number=page_number)
                    for page_number, page in enumerate(pdf.pages, start=1)
                ]
        except Exception as exc:
            return self._build_failure_result(
                error=f"pdfplumber failed to extract text from {filename}: {exc}"
            )

        return self._build_success_result(pages=pages)

    def _extract_page(self, *, page: Any, page_number: int) -> ExtractedPage:
        page_text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
        lines = self._extract_lines(page=page, page_number=page_number)

        if not lines:
            lines = self._build_lines_from_text(
                text=page_text,
                page_number=page_number,
            )

        return ExtractedPage(
            page_number=page_number,
            text=page_text,
            lines=lines,
        )

    def _extract_lines(self, *, page: Any, page_number: int) -> list[ExtractedLine]:
        words = page.extract_words(
            extra_attrs=["fontname", "size"],
            keep_blank_chars=False,
            use_text_flow=True,
        )
        lines_by_vertical_position: dict[float, list[dict[str, Any]]] = {}

        for word in words:
            top_position = float(word.get("top", 0.0))
            line_key = round(top_position, 1)
            lines_by_vertical_position.setdefault(line_key, []).append(word)

        extracted_lines: list[ExtractedLine] = []
        for words_in_line in lines_by_vertical_position.values():
            sorted_words = sorted(
                words_in_line,
                key=lambda word: float(word.get("x0", 0.0)),
            )
            line_text = " ".join(str(word.get("text", "")) for word in sorted_words)
            clean_line_text = line_text.strip()

            if not clean_line_text:
                continue

            font_sizes = [
                float(word["size"])
                for word in sorted_words
                if isinstance(word.get("size"), (int, float))
            ]
            font_names = [str(word.get("fontname", "")) for word in sorted_words]

            extracted_lines.append(
                ExtractedLine(
                    text=clean_line_text,
                    page_number=page_number,
                    average_font_size=calculate_average(font_sizes),
                    max_font_size=max(font_sizes) if font_sizes else None,
                    is_bold=has_bold_font(font_names=font_names),
                )
            )

        return extracted_lines


class PyMuPDF4LLMHandler(ParserHandler):
    """Extract selectable PDF text with PyMuPDF4LLM's modern layout engine."""

    extraction_tier = "pymupdf4llm_native"
    converter_name = "pymupdf4llm"
    extraction_decision = "native_text"

    def _extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        try:
            pymupdf4llm_module = get_pymupdf4llm_module()
            converter_version = str(pymupdf4llm_module.version)
        except Exception as exc:
            return self._build_failure_result(
                error=f"PyMuPDF4LLM is unavailable for {filename}: {exc}",
                converter_name=self.converter_name,
                extraction_decision=self.extraction_decision,
            )

        try:
            pymupdf_module = get_pymupdf_module()
            document = pymupdf_module.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            return self._build_failure_result(
                error=f"PyMuPDF4LLM failed to open {filename}: {exc}",
                converter_name=self.converter_name,
                converter_version=converter_version,
                extraction_decision=self.extraction_decision,
            )

        try:
            page_chunks = pymupdf4llm_module.to_markdown(
                document,
                page_chunks=True,
                use_ocr=False,
                force_ocr=False,
                show_progress=False,
                write_images=False,
                embed_images=False,
            )
            pages = self._build_pages(page_chunks=page_chunks)
        except Exception as exc:
            return self._build_failure_result(
                error=f"PyMuPDF4LLM failed to extract text from {filename}: {exc}",
                converter_name=self.converter_name,
                converter_version=converter_version,
                extraction_decision=self.extraction_decision,
            )
        finally:
            document.close()

        return self._build_success_result(
            pages=pages,
            converter_name=self.converter_name,
            converter_version=converter_version,
            extraction_decision=self.extraction_decision,
        )

    def _build_pages(self, *, page_chunks: object) -> list[ExtractedPage]:
        if not isinstance(page_chunks, list):
            raise TypeError("PyMuPDF4LLM page_chunks output must be a list.")

        pages: list[ExtractedPage] = []
        for page_index, page_chunk in enumerate(page_chunks):
            if not isinstance(page_chunk, dict):
                raise TypeError("PyMuPDF4LLM page chunk must be a mapping.")

            page_text = str(page_chunk.get("text", ""))
            page_number = self._get_page_number(
                page_chunk=page_chunk,
                fallback_page_number=page_index + 1,
            )
            pages.append(
                ExtractedPage(
                    page_number=page_number,
                    text=page_text,
                    lines=self._build_markdown_lines(
                        text=page_text,
                        page_number=page_number,
                    ),
                )
            )

        return pages

    def _get_page_number(
        self,
        *,
        page_chunk: dict[object, object],
        fallback_page_number: int,
    ) -> int:
        metadata = page_chunk.get("metadata")
        if not isinstance(metadata, dict):
            return fallback_page_number

        page_number = metadata.get("page_number")
        if not isinstance(page_number, int) or page_number < 1:
            return fallback_page_number

        return page_number

    def _build_markdown_lines(
        self,
        *,
        text: str,
        page_number: int,
    ) -> list[ExtractedLine]:
        extracted_lines: list[ExtractedLine] = []
        previous_line_was_break = False

        for raw_line in text.splitlines():
            clean_line = raw_line.strip()
            if not clean_line:
                if extracted_lines and not previous_line_was_break:
                    extracted_lines.append(
                        ExtractedLine(
                            text="",
                            page_number=page_number,
                            is_paragraph_break=True,
                        )
                    )
                previous_line_was_break = True
                continue

            heading_level, line_without_heading = extract_markdown_heading(clean_line)
            line_without_emphasis, is_bold = strip_markdown_emphasis(
                line_without_heading
            )
            extracted_lines.append(
                ExtractedLine(
                    text=line_without_emphasis,
                    page_number=page_number,
                    is_bold=is_bold or heading_level is not None,
                    markdown_heading_level=heading_level,
                )
            )
            previous_line_was_break = False

        while extracted_lines and extracted_lines[-1].is_paragraph_break:
            extracted_lines.pop()

        return extracted_lines


class PyMuPDFHandler(ParserHandler):
    extraction_tier = "pymupdf"

    def _extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        try:
            pymupdf_module = get_pymupdf_module()
            document = pymupdf_module.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            return self._build_failure_result(
                error=f"PyMuPDF failed to open {filename}: {exc}"
            )

        try:
            pages = [
                self._extract_page(
                    page=document.load_page(page_index),
                    page_number=page_index + 1,
                )
                for page_index in range(document.page_count)
            ]
        except Exception as exc:
            return self._build_failure_result(
                error=f"PyMuPDF failed to extract text from {filename}: {exc}"
            )
        finally:
            document.close()

        return self._build_success_result(pages=pages)

    def _extract_page(self, *, page: Any, page_number: int) -> ExtractedPage:
        page_text = page.get_text("text") or ""
        page_dictionary = page.get_text("dict") or {}
        lines = self._extract_lines(
            page_dictionary=page_dictionary,
            page_number=page_number,
        )

        if not lines:
            lines = self._build_lines_from_text(
                text=page_text,
                page_number=page_number,
            )

        return ExtractedPage(
            page_number=page_number,
            text=page_text,
            lines=lines,
        )

    def _extract_lines(
        self,
        *,
        page_dictionary: dict[str, Any],
        page_number: int,
    ) -> list[ExtractedLine]:
        extracted_lines: list[ExtractedLine] = []
        blocks = page_dictionary.get("blocks", [])

        if not isinstance(blocks, list):
            return extracted_lines

        for block in blocks:
            if not isinstance(block, dict):
                continue

            block_lines = block.get("lines", [])
            if not isinstance(block_lines, list):
                continue

            for line in block_lines:
                extracted_line = self._extract_line(
                    line=line,
                    page_number=page_number,
                )

                if extracted_line is not None:
                    extracted_lines.append(extracted_line)

        return extracted_lines

    def _extract_line(
        self,
        *,
        line: object,
        page_number: int,
    ) -> ExtractedLine | None:
        if not isinstance(line, dict):
            return None

        spans = line.get("spans", [])
        if not isinstance(spans, list):
            return None

        line_text_parts: list[str] = []
        font_sizes: list[float] = []
        font_names: list[str] = []
        has_bold_flag = False

        for span in spans:
            if not isinstance(span, dict):
                continue

            span_text = str(span.get("text", "")).strip()
            if span_text:
                line_text_parts.append(span_text)

            span_size = span.get("size")
            if isinstance(span_size, (int, float)):
                font_sizes.append(float(span_size))

            font_names.append(str(span.get("font", "")))
            span_flags = span.get("flags")
            if isinstance(span_flags, int) and span_flags & 16:
                has_bold_flag = True

        line_text = " ".join(line_text_parts).strip()
        if not line_text:
            return None

        return ExtractedLine(
            text=line_text,
            page_number=page_number,
            average_font_size=calculate_average(font_sizes),
            max_font_size=max(font_sizes) if font_sizes else None,
            is_bold=has_bold_flag or has_bold_font(font_names=font_names),
        )


def calculate_average(values: list[float]) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)


def get_pdfplumber_module() -> Any:
    return importlib.import_module("pdfplumber")


def get_pymupdf_module() -> Any:
    return importlib.import_module("pymupdf")


def get_pymupdf4llm_module() -> Any:
    return importlib.import_module("pymupdf4llm")


def extract_markdown_heading(value: str) -> tuple[int | None, str]:
    heading_match = re.match(r"^(#{1,6})\s+(.+)$", value)
    if heading_match is None:
        return None, value

    return len(heading_match.group(1)), heading_match.group(2).strip()


def strip_markdown_emphasis(value: str) -> tuple[str, bool]:
    clean_value = value.strip()
    is_bold = False

    while len(clean_value) >= 4 and (
        (clean_value.startswith("**") and clean_value.endswith("**"))
        or (clean_value.startswith("__") and clean_value.endswith("__"))
    ):
        clean_value = clean_value[2:-2].strip()
        is_bold = True

    return clean_value, is_bold


def has_bold_font(*, font_names: list[str]) -> bool:
    for font_name in font_names:
        normalized_font_name = normalize_for_matching(font_name)
        has_marker = any(marker in normalized_font_name for marker in BOLD_FONT_MARKERS)
        if has_marker:
            return True

    return False


def normalize_for_matching(value: str) -> str:
    normalized_value = unicodedata.normalize("NFD", value)
    without_accents = "".join(
        character
        for character in normalized_value
        if unicodedata.category(character) != "Mn"
    )
    return without_accents.upper()
