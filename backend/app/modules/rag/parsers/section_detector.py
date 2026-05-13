"""Detects structured leaflet sections from extracted PDF text lines."""

from __future__ import annotations

from dataclasses import dataclass
import re

from app.modules.rag.parsers.handlers import ExtractedLine, normalize_for_matching
from app.modules.rag.parsers.markdown_renderer import (
    has_heading_numbering,
    normalize_spaces,
    strip_leading_numbering,
)


SECTION_HEADER_MAX_LENGTH = 160
BOLD_SUBHEADING_MAX_LENGTH = 72
DISALLOWED_HEADING_PREFIXES = ("-", "–", "—", "•", "*", "(", "[", '"', "'", "“", "”")
CROSS_REFERENCE_WORD_PATTERN = r"\b(?:VIDE|VER)\b"
TABLE_FRAGMENT_TITLES = {
    "MG",
    "PESO",
    "VP",
    "VPS",
    "VP E VPS",
}


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
    consumed_line_indices: tuple[int, ...] = ()
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
            next_line = lines[line_index + 1] if line_index + 1 < len(lines) else None
            section_candidate = self._detect_section_candidate(
                extracted_line=extracted_line,
                next_line=next_line,
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

        return self._merge_adjacent_wrapped_heading_sections(detected_sections)

    def _merge_adjacent_wrapped_heading_sections(
        self,
        detected_sections: list[DetectedSection],
    ) -> list[DetectedSection]:
        merged_sections: list[DetectedSection] = []
        section_index = 0

        while section_index < len(detected_sections):
            current_section = detected_sections[section_index]
            next_index = section_index + 1

            while next_index < len(detected_sections):
                next_section = detected_sections[next_index]
                if not self._should_merge_wrapped_heading(
                    current_section=current_section,
                    next_section=next_section,
                ):
                    break

                current_section = DetectedSection(
                    title=normalize_spaces(
                        f"{current_section.title} {next_section.title}"
                    ),
                    canonical_title=self._merge_canonical_title(
                        current_section=current_section,
                        next_section=next_section,
                    ),
                    level=current_section.level,
                    page_number=current_section.page_number,
                    line_index=current_section.line_index,
                    consumed_line_indices=self._merge_consumed_line_indices(
                        current_section=current_section,
                        next_section=next_section,
                    ),
                )
                next_index += 1

            merged_sections.append(current_section)
            section_index = next_index

        return merged_sections

    def _should_merge_wrapped_heading(
        self,
        *,
        current_section: DetectedSection,
        next_section: DetectedSection,
    ) -> bool:
        if current_section.page_number != next_section.page_number:
            return False

        if (
            self._last_consumed_line_index(current_section) + 1
            != next_section.line_index
        ):
            return False

        if current_section.level not in {2, 3} or next_section.level != 3:
            return False

        current_title = normalize_spaces(current_section.title)
        next_title = normalize_spaces(next_section.title)
        combined_title = normalize_spaces(f"{current_title} {next_title}")

        if len(combined_title) > SECTION_HEADER_MAX_LENGTH:
            return False

        if current_title.endswith((".", "?", "!", ":")):
            return False

        if ":" in next_title:
            return False

        return self._is_all_caps_fragment(current_title) and self._is_all_caps_fragment(
            next_title
        )

    def _merge_canonical_title(
        self,
        *,
        current_section: DetectedSection,
        next_section: DetectedSection,
    ) -> str:
        if current_section.canonical_title != current_section.title:
            return current_section.canonical_title

        return normalize_spaces(
            f"{current_section.canonical_title} {next_section.canonical_title}"
        )

    def _merge_consumed_line_indices(
        self,
        *,
        current_section: DetectedSection,
        next_section: DetectedSection,
    ) -> tuple[int, ...]:
        current_line_indices = current_section.consumed_line_indices or (
            current_section.line_index,
        )
        next_line_indices = next_section.consumed_line_indices or (
            next_section.line_index,
        )
        return (*current_line_indices, *next_line_indices)

    def _last_consumed_line_index(self, section: DetectedSection) -> int:
        if section.consumed_line_indices:
            return section.consumed_line_indices[-1]

        return section.line_index

    def _is_all_caps_fragment(self, text: str) -> bool:
        has_letter = any(character.isalpha() for character in text)
        return has_letter and text == text.upper()

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
        next_line: ExtractedLine | None,
        baseline_font_size: float | None,
    ) -> SectionCandidate | None:
        clean_line = normalize_spaces(extracted_line.text)

        if len(clean_line) > SECTION_HEADER_MAX_LENGTH:
            return None

        if self._has_disallowed_heading_prefix(clean_line):
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
            heading_title = strip_leading_numbering(clean_line)
            if self._is_cross_reference_or_quoted_fragment(
                heading_title
            ) or self._looks_like_numbered_body_item(heading_title):
                return None

            return SectionCandidate(
                title=heading_title,
                canonical_title=heading_title,
                level=3,
            )

        is_visual_heading = self._is_visual_heading(
            extracted_line=extracted_line,
            next_line=next_line,
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
        if self._is_cross_reference_or_quoted_fragment(text):
            return None

        normalized_text = normalize_for_matching(strip_leading_numbering(text))
        for section_definition in SECTION_DEFINITIONS:
            has_matching_keyword = any(
                self._starts_with_section_keyword(
                    normalized_text=normalized_text,
                    keyword=keyword,
                )
                for keyword in section_definition.keywords
            )
            if has_matching_keyword:
                return section_definition

        return None

    def _is_visual_heading(
        self,
        *,
        extracted_line: ExtractedLine,
        next_line: ExtractedLine | None,
        baseline_font_size: float | None,
    ) -> bool:
        clean_line = normalize_spaces(extracted_line.text)
        if not any(character.isalnum() for character in clean_line):
            return False

        if self._is_cross_reference_or_quoted_fragment(clean_line):
            return False

        if clean_line.endswith((".", ",")):
            return False

        has_heading_case = clean_line == clean_line.upper()
        is_short_enough = len(clean_line) <= 80

        if extracted_line.is_bold and is_short_enough and has_heading_case:
            return True

        if self._is_bold_internal_subheading(
            extracted_line=extracted_line,
            next_line=next_line,
        ):
            return True

        if baseline_font_size is None or extracted_line.max_font_size is None:
            return False

        is_larger_than_body = extracted_line.max_font_size >= baseline_font_size + 1.5
        has_visual_emphasis = has_heading_case or extracted_line.is_bold
        return is_larger_than_body and is_short_enough and has_visual_emphasis

    def _starts_with_section_keyword(
        self,
        *,
        normalized_text: str,
        keyword: str,
    ) -> bool:
        return (
            normalized_text == keyword
            or normalized_text.startswith(f"{keyword} ")
            or normalized_text.startswith(f"{keyword}:")
            or normalized_text.startswith(f"{keyword}?")
        )

    def _has_disallowed_heading_prefix(self, text: str) -> bool:
        stripped_text = text.lstrip()
        return stripped_text.startswith(DISALLOWED_HEADING_PREFIXES)

    def _is_cross_reference_or_quoted_fragment(self, text: str) -> bool:
        stripped_text = text.lstrip()
        if self._has_disallowed_heading_prefix(stripped_text):
            return True

        normalized_text = normalize_for_matching(stripped_text)
        return re.search(CROSS_REFERENCE_WORD_PATTERN, normalized_text) is not None

    def _looks_like_numbered_body_item(self, text: str) -> bool:
        clean_text = normalize_spaces(text)
        if clean_text.endswith((".", ",")):
            return True

        is_long_mixed_case_sentence = (
            len(clean_text) > 90 and clean_text != clean_text.upper()
        )
        return is_long_mixed_case_sentence

    def _is_bold_internal_subheading(
        self,
        *,
        extracted_line: ExtractedLine,
        next_line: ExtractedLine | None,
    ) -> bool:
        if not extracted_line.is_bold:
            return False

        clean_line = normalize_spaces(extracted_line.text)
        if len(clean_line) > BOLD_SUBHEADING_MAX_LENGTH:
            return False

        normalized_line = normalize_for_matching(clean_line)
        if normalized_line in TABLE_FRAGMENT_TITLES:
            return False

        if not self._starts_with_uppercase(clean_line):
            return False

        if not self._has_title_like_shape(clean_line):
            return False

        return self._has_following_body_or_subheading(next_line)

    def _starts_with_uppercase(self, text: str) -> bool:
        if text.lstrip()[0].isdigit():
            return False

        first_letter = next(
            (character for character in text if character.isalpha()),
            "",
        )
        return bool(first_letter) and first_letter == first_letter.upper()

    def _has_title_like_shape(self, text: str) -> bool:
        clean_text = normalize_spaces(text)
        if clean_text.endswith(":"):
            return True

        word_count = len(clean_text.split())
        return word_count <= 6 and not clean_text.endswith(("?", "!", ".", ","))

    def _has_following_body_or_subheading(
        self, next_line: ExtractedLine | None
    ) -> bool:
        if next_line is None:
            return False

        next_text = normalize_spaces(next_line.text)
        if not next_text:
            return False

        normalized_next_text = normalize_for_matching(next_text)
        if normalized_next_text in TABLE_FRAGMENT_TITLES:
            return False

        if next_text.isdigit() or len(next_text) <= 3:
            return False

        return True
