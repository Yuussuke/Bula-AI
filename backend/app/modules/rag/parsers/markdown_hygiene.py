"""Post-render Markdown cleanup rules for parsed medication leaflets."""

from __future__ import annotations

import re

from app.modules.rag.parsers.handlers import normalize_for_matching
from app.modules.rag.parsers.markdown_renderer import MarkdownBuildResult
from app.modules.rag.parsers.section_detector import DetectedSection


LEGAL_SECTION_PATTERN = re.compile(
    r"^(?:#+\s*)?(?:(?:[0-9]{1,2}|[IVXLCDM]+)\s*[-\.\)]\s*)?"
    r"DIZERES\s+LEGAIS\.?\s*$"
)


def trim_markdown_from_legal_section(
    markdown_result: MarkdownBuildResult,
) -> MarkdownBuildResult:
    """Drop low-signal legal boilerplate from the final Markdown output."""
    cutoff_index = find_legal_section_start(markdown_result.markdown)
    if cutoff_index is None:
        return markdown_result

    trimmed_markdown = markdown_result.markdown[:cutoff_index].rstrip()
    trimmed_sections = [
        _copy_section_with_offsets(
            section=section,
            markdown_length=len(trimmed_markdown),
        )
        for section in markdown_result.detected_sections
        if section.char_start < len(trimmed_markdown)
    ]
    _fill_section_end_offsets(
        detected_sections=trimmed_sections,
        markdown_length=len(trimmed_markdown),
    )

    return MarkdownBuildResult(
        markdown=trimmed_markdown,
        sections=[section.title for section in trimmed_sections],
        detected_sections=trimmed_sections,
    )


def find_legal_section_start(markdown: str) -> int | None:
    current_offset = 0
    for line in markdown.splitlines(keepends=True):
        clean_line = line.rstrip("\r\n")
        if is_legal_section_marker(clean_line):
            return current_offset

        current_offset += len(line)

    return None


def is_legal_section_marker(value: str) -> bool:
    normalized_value = normalize_for_matching(value.strip())
    return LEGAL_SECTION_PATTERN.match(normalized_value) is not None


def _copy_section_with_offsets(
    *,
    section: DetectedSection,
    markdown_length: int,
) -> DetectedSection:
    clipped_char_end = section.char_end
    if clipped_char_end is None or clipped_char_end > markdown_length:
        clipped_char_end = markdown_length

    return type(section)(
        title=section.title,
        canonical_title=section.canonical_title,
        level=section.level,
        page_number=section.page_number,
        line_index=section.line_index,
        consumed_line_indices=section.consumed_line_indices,
        char_start=section.char_start,
        char_end=clipped_char_end,
    )


def _fill_section_end_offsets(
    *,
    detected_sections: list[DetectedSection],
    markdown_length: int,
) -> None:
    for index, detected_section in enumerate(detected_sections):
        has_next_section = index + 1 < len(detected_sections)
        if has_next_section:
            detected_section.char_end = detected_sections[index + 1].char_start
        else:
            detected_section.char_end = markdown_length
