"""Deterministic, request-scoped evidence units built from retrieved chunks.

The model selects unit IDs. Only this module supplies the displayed source text;
the model never needs to reproduce a medical sentence or a dosage value.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from langchain_core.documents import Document


HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+")
LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*+•−]|\d+[.)])\s+")
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+(?=\S)")
TABLE_SEPARATOR_CELL_PATTERN = re.compile(r"^:?-{3,}:?$")


class EvidenceUnitKind(StrEnum):
    PROSE = "prose"
    LIST_ITEM = "list_item"
    TABLE_ROW = "table_row"


@dataclass(frozen=True)
class EvidenceUnit:
    unit_id: str
    source_number: int
    section_title: str
    text: str
    kind: EvidenceUnitKind
    document: Document


def build_evidence_units(documents: list[Document]) -> list[EvidenceUnit]:
    """Enumerate source-derived units without changing the indexed documents."""
    units: list[EvidenceUnit] = []
    for source_number, document in enumerate(documents, start=1):
        section_title = str(document.metadata.get("section_title", "")).strip()
        for kind, text in _extract_document_units(document.page_content):
            units.append(
                EvidenceUnit(
                    unit_id=f"E{len(units) + 1}",
                    source_number=source_number,
                    section_title=section_title,
                    text=text,
                    kind=kind,
                    document=document,
                )
            )
    return units


def format_evidence_units(units: list[EvidenceUnit]) -> str:
    return "\n\n".join(
        f"[{unit.unit_id}] Fonte {unit.source_number}; "
        f"seção: {unit.section_title or 'Não identificada'}; "
        f"tipo: {unit.kind.value}\n{unit.text}"
        for unit in units
    )


def _extract_document_units(source_text: str) -> list[tuple[EvidenceUnitKind, str]]:
    extracted: list[tuple[EvidenceUnitKind, str]] = []
    source_text = _without_front_matter(source_text)
    active_headings: list[str] = []
    preceding_label: str | None = None
    for block in re.split(r"\n\s*\n", source_text):
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        text_lines: list[str] = []
        table_lines: list[str] = []
        table_context: list[str] = []
        for line in lines:
            if _is_table_line(line.strip()):
                if not table_lines:
                    local_label = (
                        _get_local_table_label(text_lines)
                        if text_lines
                        else preceding_label
                    )
                    table_context = list(active_headings)
                    if local_label is not None:
                        table_context.append(local_label)
                    preceding_label = None
                    _append_text_units(extracted, text_lines)
                table_lines.append(line)
                continue
            _append_table_units(extracted, table_lines, table_context)
            stripped_line = line.strip()
            if HEADING_PATTERN.match(stripped_line):
                heading_level = len(stripped_line.split(maxsplit=1)[0])
                while active_headings and (
                    len(active_headings[-1].split(maxsplit=1)[0]) >= heading_level
                ):
                    active_headings.pop()
                active_headings.append(stripped_line)
                preceding_label = None
            text_lines.append(stripped_line)
        _append_table_units(extracted, table_lines, table_context)
        preceding_label = _get_local_table_label(text_lines)
        _append_text_units(extracted, text_lines)
    return extracted


def _get_local_table_label(lines: list[str]) -> str | None:
    """Keep only an adjacent standalone fragment, never search prose for scope.

    Plain-text labels have no semantic type in Markdown. A single non-sentence
    line is retained verbatim as local context; no population or meaning is
    inferred. Headings establish a new boundary, and intervening prose/list
    blocks prevent carrying an earlier label into a table.
    """
    local_lines: list[str] = []
    for line in lines:
        if HEADING_PATTERN.match(line):
            local_lines.clear()
        else:
            local_lines.append(line)
    if len(local_lines) != 1:
        return None
    label = local_lines[0]
    if LIST_ITEM_PATTERN.match(label) or label.startswith(">"):
        return None
    if not label.strip("-*_ ") or label.rstrip("*_ ").endswith((".", "!", "?")):
        return None
    return label


def _without_front_matter(source_text: str) -> str:
    """Front matter is metadata, never a source-owned prose sentence."""
    lines = source_text.lstrip("\ufeff \t\r\n").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return source_text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() in {"---", "..."}:
            return "".join(lines[index + 1 :])
    # An unterminated envelope must not leak metadata as clinical evidence.
    return ""


def _append_text_units(
    extracted: list[tuple[EvidenceUnitKind, str]], lines: list[str]
) -> None:
    if not lines:
        return

    pending_prose: list[str] = []
    pending_list_item: list[str] = []
    for line in lines:
        if HEADING_PATTERN.match(line):
            _append_prose_units(extracted, pending_prose)
            _append_list_item(extracted, pending_list_item)
            continue
        if LIST_ITEM_PATTERN.match(line):
            _append_prose_units(extracted, pending_prose)
            _append_list_item(extracted, pending_list_item)
            pending_list_item.append(line)
            continue
        if pending_list_item:
            pending_list_item.append(line)
        else:
            pending_prose.append(line)

    _append_prose_units(extracted, pending_prose)
    _append_list_item(extracted, pending_list_item)
    lines.clear()


def _append_table_units(
    extracted: list[tuple[EvidenceUnitKind, str]],
    lines: list[str],
    context: list[str],
) -> None:
    if lines:
        extracted.extend(_extract_table_units(lines, context))
        lines.clear()


def _append_prose_units(
    extracted: list[tuple[EvidenceUnitKind, str]], lines: list[str]
) -> None:
    if not lines:
        return
    paragraph = " ".join(lines)
    for sentence in SENTENCE_BOUNDARY_PATTERN.split(paragraph):
        sentence = sentence.strip()
        if sentence:
            extracted.append((EvidenceUnitKind.PROSE, sentence))
    lines.clear()


def _append_list_item(
    extracted: list[tuple[EvidenceUnitKind, str]], lines: list[str]
) -> None:
    if not lines:
        return
    extracted.append((EvidenceUnitKind.LIST_ITEM, " ".join(lines)))
    lines.clear()


def _extract_table_units(
    lines: list[str], context: list[str]
) -> list[tuple[EvidenceUnitKind, str]]:
    if len(lines) < 3 or not _is_table_separator(lines[1]):
        return []

    expected_columns = _table_column_count(lines[0])
    if expected_columns < 2 or any(
        _table_column_count(line) != expected_columns for line in lines[1:]
    ):
        # An incomplete/misaligned row must not become dosage evidence.
        return []

    header, separator = lines[:2]
    return [
        (EvidenceUnitKind.TABLE_ROW, "\n".join([*context, header, separator, row]))
        for row in lines[2:]
    ]


def _is_table_line(line: str) -> bool:
    return line.startswith("|") and line.endswith("|")


def _is_table_separator(line: str) -> bool:
    return all(
        TABLE_SEPARATOR_CELL_PATTERN.fullmatch(cell.strip()) is not None
        for cell in line.strip().strip("|").split("|")
    )


def _table_column_count(line: str) -> int:
    return len(line.strip().strip("|").split("|"))
