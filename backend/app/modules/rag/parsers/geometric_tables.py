"""Coordinate-backed table repair; never infer medication values from prose."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import html
import re
from typing import Any
import unicodedata


Bounds = tuple[float, float, float, float]


class TableStructureError(ValueError):
    """A bounded diagnostic, without source text or provider payloads."""

    def __init__(self, reason: str, page_number: int) -> None:
        self.reason = reason
        self.page_number = page_number
        super().__init__(
            f"Table structure validation failed: {reason}; page={page_number}."
        )


@dataclass(frozen=True)
class TableCell:
    bounds: Bounds
    text: str
    row_start: int
    row_end: int
    column_start: int
    column_end: int


@dataclass(frozen=True)
class GeometricTable:
    page_number: int
    bounds: Bounds
    row_count: int
    column_count: int
    cells: tuple[TableCell, ...]

    def to_markdown(self) -> str:
        """Expand proven spans, not empty cells, into a rectangular view.

        The typed cells retain original spans. Repeated values in this view are
        inherited from the same physical cell, never generated or interpolated.
        Full-width leading caption rows are kept outside the header grid.
        """
        rows = [[""] * self.column_count for _ in range(self.row_count)]
        for cell in self.cells:
            value = html.escape(cell.text, quote=False).replace("|", "&#124;")
            value = value.replace("\n", "<br>")
            for row in range(cell.row_start, cell.row_end):
                for column in range(cell.column_start, cell.column_end):
                    rows[row][column] = value
        captions: list[str] = []
        while len(rows) > 1:
            row_index = len(captions)
            caption = next(
                (
                    cell
                    for cell in self.cells
                    if cell.row_start == row_index
                    and cell.row_end == row_index + 1
                    and cell.column_start == 0
                    and cell.column_end == self.column_count
                ),
                None,
            )
            if caption is None:
                break
            captions.append(rows.pop(0)[0])
        header = "| " + " | ".join(rows[0]) + " |"
        separator = "| " + " | ".join(["---"] * self.column_count) + " |"
        body = ["| " + " | ".join(row) + " |" for row in rows[1:]]
        return "\n".join([*captions, header, separator, *body])


class GeometricTableExtractor:
    """Use ruled cells of arbitrary dimensions and validate word ownership."""

    def extract(self, page: Any) -> list[GeometricTable]:
        tables: list[GeometricTable] = []
        words = page.get_text("words")
        # Explicit rules only. Borderless/native tables are not guessed here.
        # Do not reuse the learned layout boxes that caused merged columns.
        finder = page.find_tables(strategy="lines_strict", use_layout=False)
        for detected in finder.tables:
            if detected.row_count < 2 or detected.col_count < 2:
                continue  # A decorative box is not sufficient table evidence.
            bounds = tuple(detected.bbox)
            physical_cells = sorted(set(tuple(cell) for cell in detected.cells if cell))
            x_edges = self._edges(physical_cells, 0, 2)
            y_edges = self._edges(physical_cells, 1, 3)
            cells: list[TableCell] = []
            table_words = [word for word in words if self._contains(bounds, word)]
            for word in table_words:
                owners = sum(self._contains(cell, word) for cell in physical_cells)
                if owners != 1:
                    raise TableStructureError(
                        "ambiguous_cell_ownership", page.number + 1
                    )
            for cell_bounds in physical_cells:
                cell_words = [
                    word for word in table_words if self._contains(cell_bounds, word)
                ]
                cells.append(
                    TableCell(
                        bounds=cell_bounds,
                        text=self._words_to_text(cell_words),
                        row_start=self._edge_index(y_edges, cell_bounds[1]),
                        row_end=self._edge_index(y_edges, cell_bounds[3]),
                        column_start=self._edge_index(x_edges, cell_bounds[0]),
                        column_end=self._edge_index(x_edges, cell_bounds[2]),
                    )
                )
            occupancy: Counter[tuple[int, int]] = Counter()
            for cell in cells:
                occupancy.update(
                    (row, column)
                    for row in range(cell.row_start, cell.row_end)
                    for column in range(cell.column_start, cell.column_end)
                )
            if any(
                occupancy[(row, column)] != 1
                for row in range(len(y_edges) - 1)
                for column in range(len(x_edges) - 1)
            ):
                raise TableStructureError("incomplete_cell_grid", page.number + 1)
            tables.append(
                GeometricTable(
                    page_number=page.number + 1,
                    bounds=bounds,
                    row_count=len(y_edges) - 1,
                    column_count=len(x_edges) - 1,
                    cells=tuple(cells),
                )
            )
        return sorted(tables, key=lambda table: (table.bounds[1], table.bounds[0]))

    def _edges(self, cells: list[Bounds], first: int, second: int) -> list[float]:
        edges: list[float] = []
        for value in sorted(
            {cell[index] for cell in cells for index in (first, second)}
        ):
            if not edges or value - edges[-1] > 1:
                edges.append(value)
        return edges

    def _edge_index(self, edges: list[float], value: float) -> int:
        return min(range(len(edges)), key=lambda index: abs(edges[index] - value))

    def _contains(self, bounds: Bounds, word: Any) -> bool:
        x_center = (float(word[0]) + float(word[2])) / 2
        y_center = (float(word[1]) + float(word[3])) / 2
        return bounds[0] <= x_center < bounds[2] and bounds[1] <= y_center < bounds[3]

    def _words_to_text(self, words: list[Any]) -> str:
        lines: dict[tuple[int, int], list[Any]] = {}
        for word in words:
            lines.setdefault((word[5], word[6]), []).append(word)
        ordered_lines = sorted(
            lines.values(),
            key=lambda line: (min(w[1] for w in line), min(w[0] for w in line)),
        )
        return "\n".join(
            " ".join(str(word[4]) for word in sorted(line, key=lambda word: word[0]))
            for line in ordered_lines
        )


class GeometricTableIntegrator:
    """Replace native table offsets only when their page geometry agrees."""

    def __init__(self) -> None:
        self.extractor = GeometricTableExtractor()

    def repair(self, document: Any, page_chunks: Any) -> dict[str, object]:
        try:
            return self._repair(document, page_chunks)
        except TableStructureError:
            raise
        except Exception:
            # A geometry failure must not delegate to a plain-text fallback.
            raise TableStructureError("geometry_processing_failed", 0) from None

    def _repair(self, document: Any, page_chunks: Any) -> dict[str, object]:
        diagnostics: list[dict[str, object]] = []
        repaired_count = 0
        native_only_count = 0
        for chunk in page_chunks:
            page_number = chunk["metadata"]["page_number"]
            page = document[page_number - 1]
            tables = self.extractor.extract(page)
            boxes = [
                box for box in chunk.get("page_boxes", []) if box["class"] == "table"
            ]
            assignments: dict[int, list[GeometricTable]] = {}
            for table in tables:
                matches = [
                    index
                    for index, box in enumerate(boxes)
                    if self._covers(box["bbox"], table.bounds)
                ]
                if len(matches) != 1:
                    raise TableStructureError("unmapped_table_region", page_number)
                assignments.setdefault(matches[0], []).append(table)
            replacements: list[tuple[int, int, str]] = []
            for index, box in enumerate(boxes):
                selected = assignments.get(index, [])
                if not selected:
                    native_only_count += 1
                    start, end = box["pos"]
                    native_rows = [
                        line
                        for line in chunk["text"][start:end].splitlines()
                        if line.strip().startswith("|")
                    ]
                    widths = {len(re.split(r"(?<!\\)\|", line)) for line in native_rows}
                    if len(widths) > 1:
                        raise TableStructureError(
                            "inconsistent_native_columns", page_number
                        )
                    continue
                related_boxes = [
                    candidate
                    for candidate in chunk.get("page_boxes", [])
                    if candidate is box
                    or any(
                        self._covers(candidate["bbox"], table.bounds)
                        for table in selected
                    )
                ]
                start = min(candidate["pos"][0] for candidate in related_boxes)
                end = max(candidate["pos"][1] for candidate in related_boxes)
                if any(
                    start <= candidate["pos"][0] < end
                    and candidate not in related_boxes
                    for candidate in chunk.get("page_boxes", [])
                ):
                    raise TableStructureError(
                        "region_contains_unrelated_block", page_number
                    )
                if not 0 <= start < end <= len(chunk["text"]):
                    raise TableStructureError("invalid_native_offsets", page_number)
                region_bounds = (
                    min(candidate["bbox"][0] for candidate in related_boxes),
                    min(candidate["bbox"][1] for candidate in related_boxes),
                    max(candidate["bbox"][2] for candidate in related_boxes),
                    max(candidate["bbox"][3] for candidate in related_boxes),
                )
                replacement = self._render_region(page, region_bounds, selected)
                replacements.append((start, end, replacement + "\n\n"))
                for table in selected:
                    diagnostics.append(
                        {
                            "page": page_number,
                            "bounds": list(table.bounds),
                            "rows": table.row_count,
                            "columns": table.column_count,
                            "method": "geometric_lines_strict",
                            "merged_cells": sum(
                                cell.row_end - cell.row_start > 1
                                or cell.column_end - cell.column_start > 1
                                for cell in table.cells
                            ),
                        }
                    )
                    repaired_count += 1
            previous_end = -1
            for start, end, _ in sorted(replacements):
                if start < previous_end:
                    raise TableStructureError("overlapping_native_offsets", page_number)
                previous_end = end
            for start, end, replacement in sorted(replacements, reverse=True):
                chunk["text"] = (
                    chunk["text"][:start] + replacement + chunk["text"][end:]
                )
        return {
            "geometric_table_count": repaired_count,
            "native_only_table_count": native_only_count,
            "tables": diagnostics[:100],
            "diagnostics_truncated": len(diagnostics) > 100,
        }

    def _covers(self, outer: Any, inner: Bounds) -> bool:
        # Layout boxes follow text, while ruled grids include cell padding.
        width = max(0, min(outer[2], inner[2]) - max(outer[0], inner[0]))
        height = max(0, min(outer[3], inner[3]) - max(outer[1], inner[1]))
        area = min(
            (inner[2] - inner[0]) * (inner[3] - inner[1]),
            (outer[2] - outer[0]) * (outer[3] - outer[1]),
        )
        return bool(area > 0 and width * height / area >= 0.75)

    def _render_region(
        self, page: Any, bounds: Any, tables: list[GeometricTable]
    ) -> str:
        words = page.get_text("words")
        region_bounds: Bounds = (
            min(bounds[0], *(table.bounds[0] for table in tables)) - 1,
            min(bounds[1], *(table.bounds[1] for table in tables)) - 1,
            max(bounds[2], *(table.bounds[2] for table in tables)) + 1,
            max(bounds[3], *(table.bounds[3] for table in tables)) + 1,
        )
        region_words = [
            word for word in words if self.extractor._contains(region_bounds, word)
        ]
        leftover = [
            word
            for word in region_words
            if not any(self.extractor._contains(table.bounds, word) for table in tables)
        ]
        # Every physical table word must be covered by the native region too.
        table_text = "".join(cell.text for table in tables for cell in table.cells)
        accounted_text = table_text + "".join(str(word[4]) for word in leftover)
        source_text = "".join(str(word[4]) for word in region_words)
        if self._characters(accounted_text) != self._characters(source_text):
            raise TableStructureError("region_text_mismatch", page.number + 1)
        items: list[tuple[float, str]] = [
            (table.bounds[1], table.to_markdown()) for table in tables
        ]
        # Native boxes sometimes include section titles above/between tables.
        # Reinsert those physical lines in reading order, not into table cells.
        lines: dict[tuple[int, int], list[Any]] = {}
        for word in leftover:
            lines.setdefault((word[5], word[6]), []).append(word)
        for line in lines.values():
            value = self.extractor._words_to_text(line)
            items.append((min(word[1] for word in line), value))
        return "\n\n".join(
            value for _, value in sorted(items, key=lambda item: item[0])
        )

    def _characters(self, value: str) -> Counter[str]:
        normalized = unicodedata.normalize("NFKC", value)
        return Counter(re.sub(r"\s+", "", normalized))
