"""Renders extracted lines and detected sections into structured Markdown."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from app.modules.rag.parsers.handlers import ExtractedLine, normalize_for_matching

if TYPE_CHECKING:
    from app.modules.rag.parsers.section_detector import DetectedSection


@dataclass(frozen=True)
class MarkdownBuildResult:
    markdown: str
    sections: list[str]
    detected_sections: list["DetectedSection"]


class MarkdownRenderer:
    def render(
        self,
        lines: list[ExtractedLine],
        detected_sections: list["DetectedSection"],
    ) -> MarkdownBuildResult:
        sections_by_line_index = {
            section.line_index: section for section in detected_sections
        }
        markdown_lines: list[str] = []
        rendered_sections: list["DetectedSection"] = []
        seen_section_keys: set[str] = set()
        current_markdown_offset = 0

        for line_index, extracted_line in enumerate(lines):
            clean_line = normalize_spaces(extracted_line.text)
            if not clean_line:
                continue

            detected_section = sections_by_line_index.get(line_index)
            if detected_section is not None:
                section_key = normalize_for_matching(detected_section.canonical_title)
                is_repeated_section = section_key in seen_section_keys
                if not is_repeated_section:
                    if markdown_lines and markdown_lines[-1] != "":
                        current_markdown_offset = append_markdown_line(
                            markdown_lines=markdown_lines,
                            line="",
                            current_offset=current_markdown_offset,
                        )

                    heading_prefix = "#" * detected_section.level
                    heading_line = f"{heading_prefix} {detected_section.title}"
                    section_char_start = current_markdown_offset
                    current_markdown_offset = append_markdown_line(
                        markdown_lines=markdown_lines,
                        line=heading_line,
                        current_offset=current_markdown_offset,
                    )
                    rendered_sections.append(
                        self._copy_section_with_offsets(
                            detected_section=detected_section,
                            char_start=section_char_start,
                        )
                    )
                    seen_section_keys.add(section_key)
                continue

            current_markdown_offset = append_markdown_line(
                markdown_lines=markdown_lines,
                line=clean_line,
                current_offset=current_markdown_offset,
            )

        markdown = "\n".join(markdown_lines).strip()
        self._fill_section_end_offsets(
            detected_sections=rendered_sections,
            markdown_length=len(markdown),
        )

        return MarkdownBuildResult(
            markdown=markdown,
            sections=[section.title for section in rendered_sections],
            detected_sections=rendered_sections,
        )

    def _copy_section_with_offsets(
        self,
        *,
        detected_section: "DetectedSection",
        char_start: int,
    ) -> "DetectedSection":
        return type(detected_section)(
            title=detected_section.title,
            canonical_title=detected_section.canonical_title,
            level=detected_section.level,
            page_number=detected_section.page_number,
            line_index=detected_section.line_index,
            char_start=char_start,
        )

    def _fill_section_end_offsets(
        self,
        *,
        detected_sections: list["DetectedSection"],
        markdown_length: int,
    ) -> None:
        for index, detected_section in enumerate(detected_sections):
            has_next_section = index + 1 < len(detected_sections)
            if has_next_section:
                detected_section.char_end = detected_sections[index + 1].char_start
            else:
                detected_section.char_end = markdown_length


def append_markdown_line(
    *,
    markdown_lines: list[str],
    line: str,
    current_offset: int,
) -> int:
    markdown_lines.append(line)
    return current_offset + len(line) + 1


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def has_heading_numbering(value: str) -> bool:
    return re.match(r"^(?:[0-9]{1,2}|[IVXLCDM]+)[\.\)]\s+\S", value) is not None


def strip_leading_numbering(value: str) -> str:
    return re.sub(r"^(?:[0-9]{1,2}|[IVXLCDM]+)[\.\)]\s+", "", value).strip()
