"""Conservative legal-tail cutoff before repeated headings are deduplicated."""

from __future__ import annotations

import re

from app.modules.rag.parsers.handlers import ExtractedLine, normalize_for_matching
from app.modules.rag.parsers.section_detector import DetectedSection


LEGAL_SECTION_PATTERN = re.compile(
    r"^(?:(?:[0-9]{1,2}|[IVXLCDM]+)\s*[-.)]\s*)?DIZERES\s+LEGAIS\.?$"
)


def trim_lines_from_last_legal_section(
    lines: list[ExtractedLine], detected_sections: list[DetectedSection]
) -> tuple[list[ExtractedLine], list[DetectedSection]]:
    """Keep intermediate legal blocks; cut only at the last standalone legal title.

    A mention in prose or a table is not a legal-section boundary. If no exact
    legal title was detected, preserve the complete document.
    """
    legal_line_indices = [
        index for index, line in enumerate(lines) if is_legal_section_marker(line.text)
    ]
    if not legal_line_indices:
        return lines, detected_sections

    cutoff_line_index = legal_line_indices[-1]
    return lines[:cutoff_line_index], [
        section
        for section in detected_sections
        if section.line_index < cutoff_line_index
    ]


def is_legal_section_marker(text: str) -> bool:
    normalized_title = normalize_for_matching(text.strip("*_# "))
    return LEGAL_SECTION_PATTERN.fullmatch(normalized_title) is not None
