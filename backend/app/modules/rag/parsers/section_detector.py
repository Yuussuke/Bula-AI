"""Detects structured leaflet sections from extracted PDF text lines."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.rag.parsers.handlers import ExtractedLine, normalize_for_matching
from app.modules.rag.parsers.markdown_renderer import (
    has_heading_numbering,
    normalize_spaces,
    strip_leading_numbering,
)


SECTION_HEADER_MAX_LENGTH = 160


@dataclass(frozen=True)
class SectionDefinition:
    canonical_title: str
    keywords: tuple[str, ...]


@dataclass
class DetectedSection:
    title: str
    canonical_title: str
    level: int
    page_number: int
    line_index: int
    char_start: int = 0
    char_end: int | None = None


@dataclass(frozen=True)
class SectionCandidate:
    title: str
    canonical_title: str
    level: int


SECTION_DEFINITIONS = (
    SectionDefinition(
        canonical_title="Identificacao do Medicamento",
        keywords=("IDENTIFICACAO DO MEDICAMENTO",),
    ),
    SectionDefinition(
        canonical_title="Composicao",
        keywords=("COMPOSICAO",),
    ),
    SectionDefinition(
        canonical_title="Indicacoes",
        keywords=(
            "INDICACOES",
            "PARA QUE ESTE MEDICAMENTO E INDICADO",
        ),
    ),
    SectionDefinition(
        canonical_title="Posologia e modo de usar",
        keywords=(
            "POSOLOGIA",
            "MODO DE USAR",
            "COMO DEVO USAR",
        ),
    ),
    SectionDefinition(
        canonical_title="Contraindicacoes",
        keywords=(
            "CONTRAINDICACOES",
            "QUANDO NAO DEVO USAR",
        ),
    ),
    SectionDefinition(
        canonical_title="Interacoes medicamentosas",
        keywords=("INTERACOES MEDICAMENTOSAS",),
    ),
    SectionDefinition(
        canonical_title="Reacoes adversas",
        keywords=(
            "EFEITOS COLATERAIS",
            "REACOES ADVERSAS",
            "QUAIS OS MALES",
        ),
    ),
    SectionDefinition(
        canonical_title="Advertencias e precaucoes",
        keywords=(
            "ADVERTENCIAS",
            "PRECAUCOES",
            "O QUE DEVO SABER",
        ),
    ),
    SectionDefinition(
        canonical_title="Armazenamento",
        keywords=(
            "ARMAZENAMENTO",
            "ONDE COMO E POR QUANTO TEMPO",
        ),
    ),
)


class SectionDetector:
    def detect(self, lines: list[ExtractedLine]) -> list[DetectedSection]:
        baseline_font_size = self._calculate_baseline_font_size(lines)
        detected_sections: list[DetectedSection] = []

        for line_index, extracted_line in enumerate(lines):
            section_candidate = self._detect_section_candidate(
                extracted_line=extracted_line,
                baseline_font_size=baseline_font_size,
            )

            if section_candidate is None:
                continue

            detected_sections.append(
                DetectedSection(
                    title=section_candidate.title,
                    canonical_title=section_candidate.canonical_title,
                    level=section_candidate.level,
                    page_number=extracted_line.page_number,
                    line_index=line_index,
                )
            )

        return detected_sections

    def _calculate_baseline_font_size(
        self,
        extracted_lines: list[ExtractedLine],
    ) -> float | None:
        font_sizes = [
            line.average_font_size
            for line in extracted_lines
            if line.average_font_size is not None
        ]

        if not font_sizes:
            return None

        sorted_font_sizes = sorted(font_sizes)
        middle_index = len(sorted_font_sizes) // 2
        return sorted_font_sizes[middle_index]

    def _detect_section_candidate(
        self,
        *,
        extracted_line: ExtractedLine,
        baseline_font_size: float | None,
    ) -> SectionCandidate | None:
        clean_line = normalize_spaces(extracted_line.text)

        if len(clean_line) > SECTION_HEADER_MAX_LENGTH:
            return None

        standard_section = self._match_standard_section(clean_line)
        if standard_section is not None:
            return SectionCandidate(
                title=strip_leading_numbering(clean_line),
                canonical_title=standard_section.canonical_title,
                level=2,
            )

        is_numbered_heading = has_heading_numbering(clean_line)
        if is_numbered_heading:
            return SectionCandidate(
                title=strip_leading_numbering(clean_line),
                canonical_title=strip_leading_numbering(clean_line),
                level=3,
            )

        is_visual_heading = self._is_visual_heading(
            extracted_line=extracted_line,
            baseline_font_size=baseline_font_size,
        )
        if is_visual_heading:
            return SectionCandidate(
                title=clean_line,
                canonical_title=clean_line,
                level=3,
            )

        return None

    def _match_standard_section(self, text: str) -> SectionDefinition | None:
        normalized_text = normalize_for_matching(text)
        for section_definition in SECTION_DEFINITIONS:
            has_matching_keyword = any(
                keyword in normalized_text for keyword in section_definition.keywords
            )
            if has_matching_keyword:
                return section_definition

        return None

    def _is_visual_heading(
        self,
        *,
        extracted_line: ExtractedLine,
        baseline_font_size: float | None,
    ) -> bool:
        clean_line = normalize_spaces(extracted_line.text)
        has_heading_case = clean_line == clean_line.upper()
        is_short_enough = len(clean_line) <= 80

        if extracted_line.is_bold and is_short_enough and has_heading_case:
            return True

        if baseline_font_size is None or extracted_line.max_font_size is None:
            return False

        is_larger_than_body = extracted_line.max_font_size >= baseline_font_size + 1.5
        return is_larger_than_body and is_short_enough
