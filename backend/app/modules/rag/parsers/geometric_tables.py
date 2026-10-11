"""Coordinate-backed table repair; never infer medication values from prose."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any
import unicodedata

from pymupdf import TEXTFLAGS_WORDS


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
    reading_direction: tuple[int, int] = (1, 0)
    has_header: bool = True

    def to_markdown(self, *, is_continuation: bool = False) -> str:
        """Expand proven spans, not empty cells, into a rectangular view.

        The typed cells retain original spans. Repeated values in this view are
        inherited from the same physical cell, never generated or interpolated.
        Full-width leading caption rows are kept outside the header grid.
        """
        rows = [[""] * self.column_count for _ in range(self.row_count)]
        for cell in self.cells:
            value = re.sub(r"\s*\n\s*", " ", cell.text).replace("|", "&#124;")
            for row in range(cell.row_start, cell.row_end):
                for column in range(cell.column_start, cell.column_end):
                    rows[row][column] = value
        captions: list[str] = []
        while not is_continuation and len(rows) > 1:
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
        rendered_rows = ["| " + " | ".join(row) + " |" for row in rows]
        if is_continuation:
            return "\n".join(rendered_rows)
        separator = "| " + " | ".join(["---"] * self.column_count) + " |"
        if not self.has_header:
            empty_header = "| " + " | ".join([""] * self.column_count) + " |"
            return "\n".join([*captions, empty_header, separator, *rendered_rows])
        return "\n".join([*captions, rendered_rows[0], separator, *rendered_rows[1:]])


class GeometricTableExtractor:
    """Use ruled cells of arbitrary dimensions and validate word ownership."""

    def extract(self, page: Any) -> list[GeometricTable]:
        if page.rotation:
            raise TableStructureError("unnormalized_page_rotation", page.number + 1)
        tables: list[GeometricTable] = []
        words = page.get_text("words")
        # Explicit rules only. Borderless/native tables are not guessed here.
        # Do not reuse the learned layout boxes that caused merged columns.
        finder = page.find_tables(
            strategy="lines_strict", use_layout=False, add_lines=self._drawn_rules(page)
        )
        line_directions = self._line_directions(page)
        for detected in finder.tables:
            if detected.row_count < 2 or detected.col_count < 2:
                continue  # A decorative box is not sufficient table evidence.
            bounds = tuple(detected.bbox)
            physical_cells = sorted(set(tuple(cell) for cell in detected.cells if cell))
            direction = self._table_direction(physical_cells, words, line_directions)
            if direction == (0, 0):
                raise TableStructureError(
                    "unsupported_table_text_direction", page.number + 1
                )
            projected_cells = [
                self._project_bounds(cell, direction) for cell in physical_cells
            ]
            x_edges = self._edges(projected_cells, 0, 2)
            y_edges = self._edges(projected_cells, 1, 3)
            cells: list[TableCell] = []
            table_words = [word for word in words if self._contains(bounds, word)]
            for word in table_words:
                owners = sum(self._contains(cell, word) for cell in physical_cells)
                if owners != 1:
                    raise TableStructureError(
                        "ambiguous_cell_ownership", page.number + 1
                    )
            for cell_bounds in physical_cells:
                projected = self._project_bounds(cell_bounds, direction)
                cell_words = [
                    word for word in table_words if self._contains(cell_bounds, word)
                ]
                try:
                    cell_text = self._words_to_text(cell_words, line_directions)
                except ValueError:
                    raise TableStructureError(
                        "ambiguous_cell_reading_order", page.number + 1
                    ) from None
                cells.append(
                    TableCell(
                        bounds=cell_bounds,
                        text=cell_text,
                        row_start=self._edge_index(y_edges, projected[1]),
                        row_end=self._edge_index(y_edges, projected[3]),
                        column_start=self._edge_index(x_edges, projected[0]),
                        column_end=self._edge_index(x_edges, projected[2]),
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
                    reading_direction=direction,
                    has_header=not any(
                        self._intersects(bounds, tuple(image["bbox"]))
                        for image in page.get_image_info()
                    ),
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

    def _drawn_rules(
        self, page: Any
    ) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        """Expose thin filled borders, not filled backgrounds, to strict detection.

        Slightly tilted strokes use the converter's three-point snap tolerance.
        Every added segment originates in a physical path; no border is inferred.
        """
        rules: list[tuple[tuple[float, float], tuple[float, float]]] = []
        for drawing in page.get_drawings():
            items = drawing["items"]
            is_thin_outline = False
            if (
                drawing["type"] == "f"
                and items
                and all(item[0] == "l" for item in items)
            ):
                area = (
                    abs(
                        sum(
                            item[1].x * item[2].y - item[2].x * item[1].y
                            for item in items
                        )
                    )
                    / 2
                )
                rectangle = drawing["rect"]
                is_thin_outline = area <= 2 * (rectangle.width + rectangle.height)
            for item in items:
                if item[0] == "re" and drawing["type"] == "f":
                    rectangle = item[1]
                    if rectangle.width <= 1 and rectangle.height > 3:
                        x_center = (rectangle.x0 + rectangle.x1) / 2
                        rules.append(
                            ((x_center, rectangle.y0), (x_center, rectangle.y1))
                        )
                    elif rectangle.height <= 1 and rectangle.width > 3:
                        y_center = (rectangle.y0 + rectangle.y1) / 2
                        rules.append(
                            ((rectangle.x0, y_center), (rectangle.x1, y_center))
                        )
                elif item[0] == "l" and ("s" in drawing["type"] or is_thin_outline):
                    first, second = item[1:3]
                    if abs(first.x - second.x) <= 3 and abs(first.y - second.y) > 3:
                        x_center = (first.x + second.x) / 2
                        rules.append(((x_center, first.y), (x_center, second.y)))
                    elif abs(first.y - second.y) <= 3 and abs(first.x - second.x) > 3:
                        y_center = (first.y + second.y) / 2
                        rules.append(((first.x, y_center), (second.x, y_center)))
        return rules

    def _line_directions(self, page: Any) -> dict[tuple[int, int], tuple[int, int]]:
        directions: dict[tuple[int, int], tuple[int, int]] = {}
        # Match the word extraction flags: including images changes block IDs.
        for block in page.get_text("dict", flags=TEXTFLAGS_WORDS)["blocks"]:
            if block["type"] != 0:
                continue
            for line_index, line in enumerate(block["lines"]):
                direction = tuple(round(value) for value in line["dir"])
                if direction not in ((1, 0), (0, -1), (-1, 0), (0, 1)) or any(
                    abs(value - rounded) > 0.001
                    for value, rounded in zip(line["dir"], direction, strict=True)
                ):
                    directions[(block["number"], line_index)] = (0, 0)
                    continue
                directions[(block["number"], line_index)] = (direction[0], direction[1])
        return directions

    def _table_direction(
        self,
        cells: list[Bounds],
        words: list[Any],
        directions: dict[tuple[int, int], tuple[int, int]],
    ) -> tuple[int, int]:
        observed = {
            directions.get((word[5], word[6]), (1, 0))
            for word in words
            if any(self._contains(cell, word) for cell in cells)
        }
        if len(observed) == 1:
            return next(iter(observed))
        return (1, 0)  # Mixed vertical headers do not rotate the whole grid.

    def _project_bounds(self, bounds: Bounds, direction: tuple[int, int]) -> Bounds:
        dx, dy = direction
        corners = [
            (x * dx + y * dy, -x * dy + y * dx)
            for x in (bounds[0], bounds[2])
            for y in (bounds[1], bounds[3])
        ]
        return (
            min(point[0] for point in corners),
            min(point[1] for point in corners),
            max(point[0] for point in corners),
            max(point[1] for point in corners),
        )

    def _intersects(self, first: Bounds, second: Bounds) -> bool:
        return min(first[2], second[2]) > max(first[0], second[0]) and min(
            first[3], second[3]
        ) > max(first[1], second[1])

    def _words_to_text(
        self,
        words: list[Any],
        directions: dict[tuple[int, int], tuple[int, int]] | None = None,
    ) -> str:
        lines: dict[tuple[int, int], list[Any]] = {}
        for word in words:
            lines.setdefault((word[5], word[6]), []).append(word)
        directions = directions or {}
        observed = {directions.get(key, (1, 0)) for key in lines}
        if (0, 0) in observed:
            raise ValueError("Unsupported table text direction")
        if len(observed) > 1:
            raise ValueError("Mixed text directions within one cell")
        direction = next(iter(observed), (1, 0))
        ordered_lines = sorted(
            lines.values(),
            key=lambda line: self._project_bounds(
                (
                    min(w[0] for w in line),
                    min(w[1] for w in line),
                    max(w[2] for w in line),
                    max(w[3] for w in line),
                ),
                direction,
            )[1::-1],
        )
        return "\n".join(
            " ".join(str(word[4]) for word in sorted(line, key=lambda word: word[7]))
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
        previous_page_table: GeometricTable | None = None
        previous_page_height = 0.0
        for chunk in page_chunks:
            page_number = chunk["metadata"]["page_number"]
            page = document[page_number - 1]
            tables = self.extractor.extract(page)
            continuation_table: GeometricTable | None = None
            if (
                previous_page_table is not None
                and tables
                and self._is_multipage_continuation(
                    previous=previous_page_table,
                    current=tables[0],
                    previous_page_height=previous_page_height,
                    current_page_height=float(page.rect.height),
                )
            ):
                continuation_table = tables[0]
            boxes = chunk.get("page_boxes", [])
            for box in boxes:
                start, end = box["pos"]
                if not 0 <= start <= end <= len(chunk["text"]):
                    raise TableStructureError("invalid_native_offsets", page_number)
            # Connected regions support both one grid split into native fragments
            # and one native box containing multiple grids. Labels are not proof.
            regions = self._regions(tables, boxes, page_number)
            assigned_indices = {index for _, indices in regions for index in indices}
            replacements: list[tuple[int, int, str]] = []
            for index, box in enumerate(boxes):
                if box["class"] == "table" and index not in assigned_indices:
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
            for selected, indices in regions:
                related_boxes = [boxes[index] for index in indices]
                start = min(candidate["pos"][0] for candidate in related_boxes)
                end = max(candidate["pos"][1] for candidate in related_boxes)
                if any(
                    candidate["pos"][0] < candidate["pos"][1]
                    and max(start, candidate["pos"][0]) < min(end, candidate["pos"][1])
                    and index not in indices
                    for index, candidate in enumerate(boxes)
                ):
                    raise TableStructureError(
                        "region_contains_unrelated_block", page_number
                    )
                if not 0 <= start < end <= len(chunk["text"]):
                    raise TableStructureError("invalid_native_offsets", page_number)
                covered_end = start
                for interval_start, interval_end in sorted(
                    candidate["pos"] for candidate in related_boxes
                ):
                    if chunk["text"][covered_end:interval_start].strip():
                        raise TableStructureError("unmapped_native_text", page_number)
                    covered_end = max(covered_end, interval_end)
                region_bounds = (
                    min(candidate["bbox"][0] for candidate in related_boxes),
                    min(candidate["bbox"][1] for candidate in related_boxes),
                    max(candidate["bbox"][2] for candidate in related_boxes),
                    max(candidate["bbox"][3] for candidate in related_boxes),
                )
                replacement = self._render_region(
                    page, region_bounds, selected, continuation_table
                )
                replacements.append((start, end, replacement + "\n\n"))
                for table in selected:
                    diagnostics.append(
                        {
                            "page": page_number,
                            "bounds": list(table.bounds),
                            "rows": table.row_count,
                            "columns": table.column_count,
                            "method": "geometric_lines_strict",
                            "reading_direction": list(table.reading_direction),
                            "has_header": table.has_header,
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
            previous_page_table = tables[-1] if tables else None
            previous_page_height = float(page.rect.height)
        return {
            "geometric_table_count": repaired_count,
            "native_only_table_count": native_only_count,
            "tables": diagnostics[:100],
            "diagnostics_truncated": len(diagnostics) > 100,
        }

    def _regions(
        self, tables: list[GeometricTable], boxes: list[Any], page_number: int
    ) -> list[tuple[list[GeometricTable], set[int]]]:
        regions: list[tuple[list[GeometricTable], set[int]]] = []
        for table in tables:
            indices = {
                index
                for index, box in enumerate(boxes)
                if box["pos"][0] != box["pos"][1]
                and self._covers(box["bbox"], table.bounds)
            }
            if not indices:
                raise TableStructureError("unmapped_table_region", page_number)
            selected = [table]
            # Merge every connected component, not just the first matching box.
            for old_selected, old_indices in regions[:]:
                if indices & old_indices:
                    selected.extend(old_selected)
                    indices.update(old_indices)
                    regions.remove((old_selected, old_indices))
            regions.append((sorted(selected, key=lambda item: item.bounds[1]), indices))
        return regions

    def _covers(self, outer: Any, inner: Bounds) -> bool:
        # Layout boxes follow text, while ruled grids include cell padding.
        width = max(0, min(outer[2], inner[2]) - max(outer[0], inner[0]))
        height = max(0, min(outer[3], inner[3]) - max(outer[1], inner[1]))
        area = min(
            (inner[2] - inner[0]) * (inner[3] - inner[1]),
            (outer[2] - outer[0]) * (outer[3] - outer[1]),
        )
        return bool(area > 0 and width * height / area >= 0.75)

    def _is_multipage_continuation(
        self,
        *,
        previous: GeometricTable,
        current: GeometricTable,
        previous_page_height: float,
        current_page_height: float,
    ) -> bool:
        if not previous.has_header or not current.has_header:
            return False
        if current.page_number != previous.page_number + 1:
            return False
        if current.reading_direction != (1, 0) or previous.reading_direction != (1, 0):
            return False  # No cross-page inference across rotated logical grids.
        if current.column_count != previous.column_count:
            return False
        if previous.bounds[3] < previous_page_height * 0.60:
            return False
        if current.bounds[1] > current_page_height * 0.15:
            return False
        if self._has_repeated_grouped_header(previous, current):
            # An explicit repeated two-tier header anchors this page's columns;
            # retain it rather than inheriting labels across changed geometry.
            return False
        previous_edges = sorted(
            {
                edge
                for cell in previous.cells
                for edge in (cell.bounds[0], cell.bounds[2])
            }
        )
        current_edges = sorted(
            {
                edge
                for cell in current.cells
                for edge in (cell.bounds[0], cell.bounds[2])
            }
        )
        is_aligned = len(previous_edges) == len(current_edges) and all(
            abs(before - after) <= 2
            for before, after in zip(previous_edges, current_edges, strict=True)
        )
        if not is_aligned:
            # A likely continuation without a proven column correspondence must
            # not promote a data row to a new header or inherit guessed labels.
            raise TableStructureError(
                "ambiguous_table_continuation", current.page_number
            )
        return True

    def _has_repeated_grouped_header(
        self, previous: GeometricTable, current: GeometricTable
    ) -> bool:
        def signature(table: GeometricTable) -> list[tuple[int, int, int, int, str]]:
            return sorted(
                (
                    cell.row_start,
                    cell.row_end,
                    cell.column_start,
                    cell.column_end,
                    re.sub(r"\s+", " ", cell.text).strip(),
                )
                for cell in table.cells
                if cell.row_start < 2
            )

        has_grouped_first_row = any(
            cell.row_start == 0
            and cell.row_end == 1
            and cell.column_end - cell.column_start > 1
            and cell.text.strip()
            for cell in current.cells
        )
        has_named_second_row = any(
            cell.row_start == 1 and cell.text.strip() for cell in current.cells
        )
        return bool(
            has_grouped_first_row
            and has_named_second_row
            and signature(previous) == signature(current)
        )

    def _render_region(
        self,
        page: Any,
        bounds: Any,
        tables: list[GeometricTable],
        continuation_table: GeometricTable | None,
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
        items: list[tuple[Bounds, str]] = [
            (
                table.bounds,
                table.to_markdown(is_continuation=table is continuation_table),
            )
            for table in tables
        ]
        # Native boxes sometimes include section titles above/between tables.
        # Reinsert those physical lines in reading order, not into table cells.
        lines: dict[tuple[int, int], list[Any]] = {}
        for word in leftover:
            lines.setdefault((word[5], word[6]), []).append(word)
        for line in lines.values():
            value = self.extractor._words_to_text(
                line, self.extractor._line_directions(page)
            )
            items.append(
                (
                    (
                        min(word[0] for word in line),
                        min(word[1] for word in line),
                        max(word[2] for word in line),
                        max(word[3] for word in line),
                    ),
                    value,
                )
            )
        directions = {table.reading_direction for table in tables}
        direction = next(iter(directions)) if len(directions) == 1 else (1, 0)
        positioned = sorted(
            (
                self.extractor._project_bounds(bounds, direction)[1],
                self.extractor._project_bounds(bounds, direction)[0],
                value,
            )
            for bounds, value in items
        )
        values: list[str] = []
        while positioned:
            first_y = positioned[0][0]
            aligned = [item for item in positioned if item[0] - first_y <= 3]
            # Source borders of side-by-side grids may differ by sub-point noise.
            values.extend(
                value for _, _, value in sorted(aligned, key=lambda item: item[1])
            )
            positioned = positioned[len(aligned) :]
        return "\n\n".join(values)

    def _characters(self, value: str) -> Counter[str]:
        normalized = unicodedata.normalize("NFKC", value)
        return Counter(re.sub(r"\s+", "", normalized))
