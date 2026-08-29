"""Extracts best-effort leaflet metadata from parsed text and sections."""

from __future__ import annotations

from pathlib import Path
import re

from app.modules.rag.parsers.handlers import ExtractedLine, normalize_for_matching
from app.modules.rag.parsers.markdown_renderer import normalize_spaces
from app.modules.rag.parsers.section_detector import DetectedSection


class MetadataExtractor:
    def extract(
        self,
        lines: list[ExtractedLine],
        filename: str,
        markdown_sections: list[str],
        detected_sections: list[DetectedSection],
        quality_signals: dict[str, object],
        front_matter: dict[str, str] | None = None,
        parser_version: str | None = None,
        cleanup_summary: dict[str, object] | None = None,
    ) -> dict[str, object]:
        safe_front_matter = front_matter or {}
        front_matter_product = safe_front_matter.get("product")
        drug_name: str | None
        drug_name_source: str | None
        if front_matter_product is not None:
            drug_name = front_matter_product
            drug_name_source = "front_matter"
        else:
            drug_name, drug_name_source = self._extract_drug_name(
                extracted_lines=lines,
                filename=filename,
            )

        manufacturer = safe_front_matter.get("manufacturer")
        if manufacturer is None:
            manufacturer = self._extract_manufacturer(lines)

        return {
            "drug_name": drug_name,
            "drug_name_source": drug_name_source,
            "manufacturer": manufacturer,
            "front_matter": safe_front_matter,
            "parser_version": parser_version,
            "cleanup_summary": cleanup_summary or {},
            "sections_present": markdown_sections,
            "section_metadata": [
                {
                    "title": section.title,
                    "canonical_title": section.canonical_title,
                    "level": section.level,
                    "page_number": section.page_number,
                    "char_start": section.char_start,
                    "char_end": section.char_end,
                }
                for section in detected_sections
            ],
            "quality_signals": quality_signals,
        }

    def _extract_drug_name(
        self,
        *,
        extracted_lines: list[ExtractedLine],
        filename: str,
    ) -> tuple[str | None, str | None]:
        for extracted_line in extracted_lines[:30]:
            clean_line = normalize_spaces(extracted_line.text)
            if self._is_likely_drug_name(clean_line):
                return clean_line, "text"

        filename_stem = Path(filename).stem
        filename_candidate = normalize_spaces(re.sub(r"[_-]+", " ", filename_stem))
        if filename_candidate:
            return filename_candidate, "filename_best_effort"

        return None, None

    def _is_likely_drug_name(self, text: str) -> bool:
        if not text:
            return False

        normalized_text = normalize_for_matching(text)
        ignored_fragments = (
            "BULA",
            "PACIENTE",
            "PROFISSIONAL",
            "IDENTIFICACAO",
            "MEDICAMENTO",
            "COMPOSICAO",
            "INDICACOES",
            "POSOLOGIA",
        )
        has_ignored_fragment = any(
            ignored_fragment in normalized_text
            for ignored_fragment in ignored_fragments
        )
        if has_ignored_fragment:
            return False

        has_letter = any(character.isalpha() for character in text)
        return has_letter and 2 <= len(text) <= 80

    def _extract_manufacturer(
        self,
        extracted_lines: list[ExtractedLine],
    ) -> str | None:
        marker_fragments = (
            "REGISTRADO POR",
            "FABRICADO POR",
            "DETENTOR DO REGISTRO",
            "TITULAR DO REGISTRO",
            "IMPORTADO POR",
        )

        for index, extracted_line in enumerate(extracted_lines):
            clean_line = normalize_spaces(extracted_line.text)
            normalized_line = normalize_for_matching(clean_line)

            for marker in marker_fragments:
                if marker not in normalized_line:
                    continue

                manufacturer_after_colon = extract_value_after_colon(clean_line)
                if manufacturer_after_colon:
                    return manufacturer_after_colon

                next_line = get_next_non_empty_line(
                    extracted_lines=extracted_lines,
                    start_index=index + 1,
                )
                if next_line is not None:
                    return next_line

        return None


def extract_value_after_colon(value: str) -> str | None:
    if ":" not in value:
        return None

    possible_value = value.split(":", maxsplit=1)[1].strip()
    if not possible_value:
        return None

    return possible_value


def get_next_non_empty_line(
    *,
    extracted_lines: list[ExtractedLine],
    start_index: int,
) -> str | None:
    for extracted_line in extracted_lines[start_index:]:
        clean_line = normalize_spaces(extracted_line.text)
        if clean_line:
            return clean_line

    return None
