"""Deterministic cleanup for native Markdown extracted from medication PDFs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
import re

from app.modules.rag.parsers.handlers import (
    ExtractedLine,
    ExtractedPage,
    normalize_for_matching,
)
from app.modules.rag.parsers.markdown_renderer import normalize_spaces


PAGE_NUMBER_PATTERN = re.compile(r"^\s*(?:P[ÁA]GINA\s+)?\d{1,3}\s*$", re.IGNORECASE)
PICTURE_MARKER_PATTERN = re.compile(
    r"^\*{0,2}==>\s*picture\s*\[[^]]+]\s*intentionally omitted\s*<==\*{0,2}$",
    re.IGNORECASE,
)
PICTURE_TEXT_START_MARKER = "<!-- Start of picture text -->"
PICTURE_TEXT_END_MARKER = "<!-- End of picture text -->"
MARKDOWN_TABLE_SEPARATOR_PATTERN = re.compile(r"^\|(?:\s*:?-{3,}:?\s*\|)+$")
EMBEDDED_NUMBERED_HEADING_PATTERN = re.compile(
    r"^(.+[.!?])\s+((?:[0-9]{1,2})\.\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇ ]+)$"
)
STRENGTH_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mg|g|mcg|µg|mL|UI)"
    r"(?:\s*/\s*(?:\d+(?:[.,]\d+)?\s*)?(?:mg|g|mL))?\b",
    re.IGNORECASE,
)
CORPORATE_MARKERS = (
    "FARMACEUTICA",
    "LABORATORIO",
    "LTDA",
    "S/A",
    "SANOFI",
    "MEDLEY",
    "EMS",
    "CIMED",
    "COSMED",
)
DOSAGE_FORM_MARKERS = (
    "COMPRIMIDO",
    "CAPSULA",
    "CREME",
    "GEL",
    "GOTAS",
    "INJETAVEL",
    "POMADA",
    "PO PARA",
    "SOLUCAO",
    "SUSPENSAO",
    "XAROPE",
)
CORE_SECTION_MARKERS = (
    "COMPOSICAO",
    "PARA QUE ESTE MEDICAMENTO E INDICADO",
    "INDICACOES",
)
FRONT_MATTER_FIELD_ORDER = (
    "product",
    "manufacturer",
    "dosage_form",
    "strength",
    "presentation",
    "audience",
)


@dataclass(frozen=True)
class DocumentCleanupResult:
    lines: list[ExtractedLine]
    front_matter: dict[str, str]
    summary: dict[str, object]


class BulaDocumentCleaner:
    """Remove PDF noise without using an LLM or rewriting medical values."""

    def clean(self, pages: list[ExtractedPage]) -> DocumentCleanupResult:
        repeated_furniture = self._find_repeated_page_furniture(pages)
        clean_lines: list[ExtractedLine] = []
        removed_page_number_count = 0
        removed_picture_marker_count = 0
        removed_repeated_furniture_count = 0
        soft_hyphen_count = 0

        for page in pages:
            page_lines: list[ExtractedLine] = []
            is_inside_picture_text = False
            for extracted_line in page.lines:
                if extracted_line.is_paragraph_break:
                    self._append_paragraph_break(
                        lines=page_lines,
                        page_number=page.page_number,
                    )
                    continue

                clean_text, removed_soft_hyphens = self._normalize_line_text(
                    extracted_line.text
                )
                soft_hyphen_count += removed_soft_hyphens
                if not clean_text:
                    continue

                if PICTURE_TEXT_START_MARKER in clean_text:
                    is_inside_picture_text = True
                    removed_picture_marker_count += 1
                    continue

                if is_inside_picture_text:
                    removed_picture_marker_count += 1
                    if PICTURE_TEXT_END_MARKER in clean_text:
                        is_inside_picture_text = False
                    continue

                if PAGE_NUMBER_PATTERN.fullmatch(clean_text):
                    removed_page_number_count += 1
                    continue

                if PICTURE_MARKER_PATTERN.fullmatch(clean_text):
                    removed_picture_marker_count += 1
                    continue

                furniture_key = self._build_furniture_key(clean_text)
                if furniture_key in repeated_furniture:
                    removed_repeated_furniture_count += 1
                    continue

                page_lines.append(
                    ExtractedLine(
                        text=clean_text,
                        page_number=extracted_line.page_number,
                        average_font_size=extracted_line.average_font_size,
                        max_font_size=extracted_line.max_font_size,
                        is_bold=extracted_line.is_bold,
                        markdown_heading_level=extracted_line.markdown_heading_level,
                    )
                )

            self._trim_paragraph_breaks(page_lines)
            if clean_lines and page_lines:
                self._append_paragraph_break(
                    lines=clean_lines,
                    page_number=page.page_number,
                )
            clean_lines.extend(page_lines)

        clean_lines, split_heading_count = self._split_embedded_numbered_headings(
            clean_lines
        )
        front_matter, body_lines, front_matter_line_count = self._extract_front_matter(
            clean_lines
        )
        repaired_table_count = self._repair_dosage_table_headers(body_lines)
        joined_lines, joined_line_count = self._join_wrapped_prose(body_lines)
        table_row_count = sum(
            1 for line in joined_lines if self._is_markdown_table_line(line.text)
        )

        return DocumentCleanupResult(
            lines=joined_lines,
            front_matter=front_matter,
            summary={
                "removed_page_number_count": removed_page_number_count,
                "removed_picture_marker_count": removed_picture_marker_count,
                "removed_repeated_furniture_count": removed_repeated_furniture_count,
                "removed_soft_hyphen_count": soft_hyphen_count,
                "joined_wrapped_line_count": joined_line_count,
                "split_embedded_heading_count": split_heading_count,
                "front_matter_line_count": front_matter_line_count,
                "front_matter_fields": list(front_matter),
                "repaired_table_count": repaired_table_count,
                "table_row_count": table_row_count,
            },
        )

    def _find_repeated_page_furniture(
        self,
        pages: list[ExtractedPage],
    ) -> set[str]:
        occurrences: Counter[str] = Counter()
        minimum_occurrences = max(2, math.ceil(len(pages) * 0.25))

        for page in pages:
            substantive_lines = [
                line
                for line in page.lines
                if not line.is_paragraph_break and line.text.strip()
            ]
            edge_lines = substantive_lines[:3] + substantive_lines[-3:]
            page_keys = {
                self._build_furniture_key(line.text)
                for line in edge_lines
                if self._can_be_page_furniture(line.text)
            }
            occurrences.update(page_keys)

        return {
            key for key, count in occurrences.items() if count >= minimum_occurrences
        }

    def _can_be_page_furniture(self, value: str) -> bool:
        clean_value = normalize_spaces(value)
        if not clean_value or len(clean_value) > 120:
            return False

        normalized_value = normalize_for_matching(clean_value)
        if any(marker in normalized_value for marker in CORE_SECTION_MARKERS):
            return False

        if self._is_markdown_table_line(clean_value):
            return False

        return not PAGE_NUMBER_PATTERN.fullmatch(clean_value)

    def _build_furniture_key(self, value: str) -> str:
        return normalize_for_matching(normalize_spaces(value)).strip("*_# ")

    def _normalize_line_text(self, value: str) -> tuple[str, int]:
        soft_hyphen_count = value.count("\u00ad")
        without_soft_hyphens = value.replace("\u00ad", "")

        if self._is_markdown_table_line(without_soft_hyphens):
            return without_soft_hyphens.strip(), soft_hyphen_count

        clean_text = normalize_spaces(without_soft_hyphens)
        clean_text = re.sub(
            r"^((?:[0-9]{1,2}\.\s+)?POSOLOGIA E MODO DE USAR)\s+MODO DE USAR$",
            r"\1",
            clean_text,
            flags=re.IGNORECASE,
        )
        return clean_text, soft_hyphen_count

    def _split_embedded_numbered_headings(
        self,
        lines: list[ExtractedLine],
    ) -> tuple[list[ExtractedLine], int]:
        expanded_lines: list[ExtractedLine] = []
        split_heading_count = 0

        for line in lines:
            if line.is_paragraph_break:
                expanded_lines.append(line)
                continue

            heading_match = EMBEDDED_NUMBERED_HEADING_PATTERN.fullmatch(line.text)
            if heading_match is None:
                expanded_lines.append(line)
                continue

            expanded_lines.append(
                ExtractedLine(
                    text=heading_match.group(1),
                    page_number=line.page_number,
                    average_font_size=line.average_font_size,
                    max_font_size=line.max_font_size,
                )
            )
            self._append_paragraph_break(
                lines=expanded_lines,
                page_number=line.page_number,
            )
            expanded_lines.append(
                ExtractedLine(
                    text=heading_match.group(2),
                    page_number=line.page_number,
                    is_bold=True,
                    markdown_heading_level=2,
                )
            )
            split_heading_count += 1

        return expanded_lines, split_heading_count

    def _extract_front_matter(
        self,
        lines: list[ExtractedLine],
    ) -> tuple[dict[str, str], list[ExtractedLine], int]:
        core_section_index = self._find_core_section_index(lines)
        if core_section_index is None or core_section_index == 0:
            return {}, lines, 0

        identity_lines = [
            line
            for line in lines[:core_section_index]
            if not line.is_paragraph_break and line.text.strip()
        ]
        front_matter = self._build_front_matter(identity_lines)
        if not front_matter:
            return {}, lines, 0

        body_lines = lines[core_section_index:]
        self._trim_paragraph_breaks(body_lines)
        return front_matter, body_lines, len(identity_lines)

    def _find_core_section_index(self, lines: list[ExtractedLine]) -> int | None:
        for index, line in enumerate(lines):
            normalized_text = normalize_for_matching(line.text)
            normalized_text = re.sub(
                r"^(?:[0-9]{1,2}|[IVXLCDM]+)\s*[.\-)]+\s*",
                "",
                normalized_text,
            )
            if any(
                normalized_text.startswith(marker) for marker in CORE_SECTION_MARKERS
            ):
                return index

        return None

    def _build_front_matter(
        self,
        identity_lines: list[ExtractedLine],
    ) -> dict[str, str]:
        values = [normalize_spaces(line.text).strip("*_# ") for line in identity_lines]
        values = [value for value in values if value]
        front_matter: dict[str, str] = {}

        product = self._find_product(values)
        if product is not None:
            front_matter["product"] = product

        manufacturer = self._find_manufacturer(values)
        if manufacturer is not None:
            front_matter["manufacturer"] = manufacturer

        dosage_form, strength = self._find_form_and_strength(values)
        if dosage_form is not None:
            front_matter["dosage_form"] = dosage_form
        if strength is not None:
            front_matter["strength"] = strength

        presentation = self._find_values_after_marker(
            values=values,
            markers=("APRESENTACAO", "APRESENTACOES"),
        )
        if presentation is not None:
            front_matter["presentation"] = presentation

        audience_values = [
            value
            for value in values
            if normalize_for_matching(value).startswith("USO ")
        ]
        if audience_values:
            front_matter["audience"] = " ".join(audience_values)

        return {
            field: front_matter[field]
            for field in FRONT_MATTER_FIELD_ORDER
            if field in front_matter
        }

    def _find_product(self, values: list[str]) -> str | None:
        ignored_markers = (
            "APRESENTACAO",
            "BULA",
            "IDENTIFICACAO DO MEDICAMENTO",
            "MEDICAMENTO GENERICO",
            "USO ",
        )
        product_candidates: list[str] = []
        for value in values:
            normalized_value = normalize_for_matching(value)
            if any(marker in normalized_value for marker in ignored_markers):
                continue
            if any(marker in normalized_value for marker in CORPORATE_MARKERS):
                break
            if STRENGTH_PATTERN.search(value):
                break
            if 2 <= len(value) <= 100 and any(
                character.isalpha() for character in value
            ):
                product_candidates.append(value)

        if not product_candidates:
            return None

        if (
            len(product_candidates) >= 2
            and product_candidates[0] == product_candidates[0].lower()
            and product_candidates[1] == product_candidates[1].lower()
        ):
            return normalize_spaces(f"{product_candidates[0]} {product_candidates[1]}")

        return product_candidates[0]

    def _find_manufacturer(self, values: list[str]) -> str | None:
        for value in values:
            normalized_value = normalize_for_matching(value)
            if any(marker in normalized_value for marker in CORPORATE_MARKERS):
                value_after_colon = value.split(":", maxsplit=1)[-1].strip()
                return value_after_colon or value

        return None

    def _find_form_and_strength(
        self,
        values: list[str],
    ) -> tuple[str | None, str | None]:
        dosage_form: str | None = None
        strength: str | None = None

        for value in values:
            normalized_value = normalize_for_matching(value)
            has_dosage_form = any(
                marker in normalized_value for marker in DOSAGE_FORM_MARKERS
            )
            strength_match = STRENGTH_PATTERN.search(value)
            if dosage_form is None and has_dosage_form:
                dosage_form_candidate = value
                if strength_match is not None:
                    dosage_form_candidate = normalize_spaces(
                        f"{value[: strength_match.start()]} "
                        f"{value[strength_match.end() :]}"
                    )
                dosage_form = dosage_form_candidate.strip(" :-") or None

            if strength is None and strength_match is not None:
                strength = strength_match.group(0)

            if dosage_form is not None and strength is not None:
                break

        return dosage_form, strength

    def _find_values_after_marker(
        self,
        *,
        values: list[str],
        markers: tuple[str, ...],
    ) -> str | None:
        for index, value in enumerate(values):
            normalized_value = normalize_for_matching(value).strip(":")
            if normalized_value not in markers:
                continue

            presentation_values: list[str] = []
            for possible_value in values[index + 1 :]:
                normalized_possible_value = normalize_for_matching(possible_value)
                if normalized_possible_value.startswith("USO "):
                    break
                if normalized_possible_value in markers:
                    continue
                presentation_values.append(possible_value)

            if presentation_values:
                return " ".join(presentation_values)

        return None

    def _repair_dosage_table_headers(self, lines: list[ExtractedLine]) -> int:
        first_table_index = next(
            (
                index
                for index, line in enumerate(lines)
                if self._is_markdown_table_row(line.text)
                and not self._is_markdown_table_separator(line.text)
            ),
            None,
        )
        if first_table_index is None:
            return 0

        preceding_indices = [
            index
            for index in range(first_table_index - 1, -1, -1)
            if not lines[index].is_paragraph_break
        ][:6]
        preceding_indices.reverse()

        combined_header_index = next(
            (
                index
                for index in preceding_indices
                if all(
                    fragment in normalize_for_matching(lines[index].text)
                    for fragment in ("PESO", "DOSE", "SOLUCAO")
                )
            ),
            None,
        )
        milligram_header_index = next(
            (
                index
                for index in preceding_indices
                if normalize_for_matching(lines[index].text) == "MG"
            ),
            None,
        )
        if combined_header_index is not None and milligram_header_index is not None:
            header_indices = [combined_header_index, milligram_header_index]
            header_labels = (
                "Peso (média de idade)",
                "Dose",
                "Solução oral (em mL)*",
                lines[milligram_header_index].text,
            )
        else:
            header_indices = preceding_indices[-4:]
            if len(header_indices) != 4:
                return 0

            labels = [lines[index].text for index in header_indices]
            normalized_labels = [normalize_for_matching(label) for label in labels]
            required_fragments = ("PESO", "SOLUCAO", "DOSE", "MG")
            if not all(
                any(fragment in label for label in normalized_labels)
                for fragment in required_fragments
            ):
                return 0

            label_by_fragment = {
                fragment: next(
                    label
                    for label, normalized_label in zip(
                        labels, normalized_labels, strict=True
                    )
                    if fragment in normalized_label
                )
                for fragment in required_fragments
            }
            header_labels = (
                label_by_fragment["PESO"],
                label_by_fragment["DOSE"],
                label_by_fragment["SOLUCAO"],
                label_by_fragment["MG"],
            )

        page_number = lines[header_indices[0]].page_number
        header_line = ExtractedLine(
            text=f"| {' | '.join(header_labels)} |",
            page_number=page_number,
        )
        separator_line = ExtractedLine(
            text="|---|---|---|---|",
            page_number=page_number,
        )
        first_header_index = header_indices[0]
        lines[first_header_index:first_table_index] = [header_line, separator_line]
        duplicate_separator_index = first_header_index + 3
        if duplicate_separator_index < len(lines) and self._is_markdown_table_separator(
            lines[duplicate_separator_index].text
        ):
            lines.pop(duplicate_separator_index)

        self._repeat_split_weight_context(lines)
        return 1

    def _repeat_split_weight_context(self, lines: list[ExtractedLine]) -> None:
        previous_row_index: int | None = None

        for row_index, line in enumerate(lines):
            if not self._is_markdown_table_row(line.text):
                continue
            if self._is_markdown_table_separator(line.text):
                continue

            cells = self._parse_markdown_table_cells(line.text)
            if len(cells) != 4:
                previous_row_index = row_index
                continue

            if previous_row_index is None:
                previous_row_index = row_index
                continue

            previous_cells = self._parse_markdown_table_cells(
                lines[previous_row_index].text
            )
            if len(previous_cells) != 4:
                previous_row_index = row_index
                continue

            reconstructed_weight = self._reconstruct_split_weight(
                first_fragment=previous_cells[0],
                second_fragment=cells[0],
            )
            is_split_age_suffix = re.fullmatch(
                r"(?:meses|anos)\)",
                cells[0],
                flags=re.IGNORECASE,
            )
            if reconstructed_weight is None and is_split_age_suffix is None:
                previous_row_index = row_index
                continue

            completed_weight = reconstructed_weight
            if completed_weight is None:
                completed_weight = f"{previous_cells[0]} {cells[0]}"
            previous_cells[0] = completed_weight
            cells[0] = completed_weight
            lines[previous_row_index] = ExtractedLine(
                text=self._render_markdown_table_cells(previous_cells),
                page_number=lines[previous_row_index].page_number,
            )
            lines[row_index] = ExtractedLine(
                text=self._render_markdown_table_cells(cells),
                page_number=line.page_number,
            )
            previous_row_index = row_index

    def _parse_markdown_table_cells(self, value: str) -> list[str]:
        return [
            re.sub(r"</?sup>", "", cell.strip(), flags=re.IGNORECASE)
            for cell in value.strip().strip("|").split("|")
        ]

    def _reconstruct_split_weight(
        self,
        *,
        first_fragment: str,
        second_fragment: str,
    ) -> str | None:
        first_match = re.fullmatch(
            r"(\d+)\s+(\d+)\s+k\s+(\d+)\s+(\d+)",
            normalize_spaces(first_fragment),
            flags=re.IGNORECASE,
        )
        second_match = re.fullmatch(
            r"a\s+g\s+\(\s*a\s+anos\)",
            normalize_spaces(second_fragment),
            flags=re.IGNORECASE,
        )
        if first_match is None or second_match is None:
            return None

        minimum_weight, maximum_weight, minimum_age, maximum_age = first_match.groups()
        return (
            f"{minimum_weight} a {maximum_weight} kg "
            f"({minimum_age} a {maximum_age} anos)"
        )

    def _render_markdown_table_cells(self, cells: list[str]) -> str:
        return f"| {' | '.join(cells)} |"

    def _join_wrapped_prose(
        self,
        lines: list[ExtractedLine],
    ) -> tuple[list[ExtractedLine], int]:
        joined_lines: list[ExtractedLine] = []
        joined_line_count = 0

        for line in lines:
            if line.is_paragraph_break:
                self._append_paragraph_break(
                    lines=joined_lines,
                    page_number=line.page_number,
                )
                continue

            if joined_lines and self._should_join_lines(
                current_line=joined_lines[-1],
                next_line=line,
            ):
                current_line = joined_lines[-1]
                current_text = current_line.text
                if current_text.endswith("-") and line.text[:1].islower():
                    joined_text = f"{current_text[:-1]}{line.text}"
                else:
                    joined_text = f"{current_text} {line.text}"
                joined_lines[-1] = ExtractedLine(
                    text=joined_text,
                    page_number=current_line.page_number,
                    average_font_size=current_line.average_font_size,
                    max_font_size=current_line.max_font_size,
                    is_bold=current_line.is_bold,
                    markdown_heading_level=current_line.markdown_heading_level,
                )
                joined_line_count += 1
                continue

            joined_lines.append(line)

        self._trim_paragraph_breaks(joined_lines)
        return joined_lines, joined_line_count

    def _should_join_lines(
        self,
        *,
        current_line: ExtractedLine,
        next_line: ExtractedLine,
    ) -> bool:
        if current_line.is_paragraph_break or next_line.is_paragraph_break:
            return False
        if current_line.page_number != next_line.page_number:
            return False
        if self._is_structural_line(current_line) or self._is_structural_line(
            next_line
        ):
            return False
        if current_line.text.endswith((".", "?", "!", ":", ";")):
            return False

        return current_line.text.endswith("-") or next_line.text[:1].islower()

    def _is_structural_line(self, line: ExtractedLine) -> bool:
        clean_text = line.text.lstrip()
        return (
            line.markdown_heading_level is not None
            or self._is_markdown_table_line(clean_text)
            or re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)", clean_text) is not None
        )

    def _is_markdown_table_line(self, value: str) -> bool:
        return self._is_markdown_table_row(value) or self._is_markdown_table_separator(
            value
        )

    def _is_markdown_table_row(self, value: str) -> bool:
        clean_value = value.strip()
        return clean_value.startswith("|") and clean_value.endswith("|")

    def _is_markdown_table_separator(self, value: str) -> bool:
        return MARKDOWN_TABLE_SEPARATOR_PATTERN.fullmatch(value.strip()) is not None

    def _append_paragraph_break(
        self,
        *,
        lines: list[ExtractedLine],
        page_number: int,
    ) -> None:
        if not lines or lines[-1].is_paragraph_break:
            return

        lines.append(
            ExtractedLine(
                text="",
                page_number=page_number,
                is_paragraph_break=True,
            )
        )

    def _trim_paragraph_breaks(self, lines: list[ExtractedLine]) -> None:
        while lines and lines[0].is_paragraph_break:
            lines.pop(0)
        while lines and lines[-1].is_paragraph_break:
            lines.pop()


def render_front_matter(front_matter: dict[str, str]) -> str:
    if not front_matter:
        return ""

    lines = ["---"]
    for field in FRONT_MATTER_FIELD_ORDER:
        value = front_matter.get(field)
        if value is None:
            continue
        lines.append(f"{field}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)
