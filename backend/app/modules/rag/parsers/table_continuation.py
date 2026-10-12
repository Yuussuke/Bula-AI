"""Conservative correspondence of ordered, source-backed column schemas."""

from __future__ import annotations

import re
from statistics import median
from typing import TYPE_CHECKING
import unicodedata

if TYPE_CHECKING:
    from app.modules.rag.parsers.geometric_tables import GeometricTable


class TableContinuationMatcher:
    """Relative geometry is corroborating evidence, not permission to guess.

    Reflow requires compatible ordered content types, a shared textual row-label
    vocabulary and at least two distinct constant-column anchors. Numeric values
    are compared literally, never interpreted as clinical quantities or converted.
    Tables without these signals keep the stricter absolute-coordinate path.
    """

    def column_edges(self, table: GeometricTable) -> list[float]:
        positions: list[list[float]] = [[] for _ in range(table.column_count + 1)]
        for cell in table.cells:
            positions[cell.column_start].append(cell.bounds[0])
            positions[cell.column_end].append(cell.bounds[2])
        if any(not values or max(values) - min(values) > 1 for values in positions):
            return []
        return [float(median(values)) for values in positions]

    def is_absolutely_aligned(
        self, previous: GeometricTable, current: GeometricTable
    ) -> bool:
        before, after = self.column_edges(previous), self.column_edges(current)
        return bool(
            before
            and len(before) == len(after)
            and all(
                abs(first - second) <= 2
                for first, second in zip(before, after, strict=True)
            )
        )

    def rows(self, table: GeometricTable) -> list[list[str]]:
        rows = [[""] * table.column_count for _ in range(table.row_count)]
        for cell in table.cells:
            for row in range(cell.row_start, cell.row_end):
                for column in range(cell.column_start, cell.column_end):
                    rows[row][column] = cell.text
        return rows

    def content_type(self, value: str) -> str:
        value = self.normalize(value)
        if value in {"", "-", "–", "—", "n/a", "na"}:
            return "empty"
        # A date-leading cell may contain a correction note. Classify its primary
        # lexical type without extracting, deleting or interpreting the note.
        if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}(?:\s|$)", value):
            return "date"
        quantity = re.fullmatch(r"[+−-]?\d+(?:[.,]\d+)*(?:\s*(%|[a-zµμ/²³]+))?", value)
        if quantity:
            return "number:" + (quantity.group(1) or "")
        return "text"

    def body_start(self, table: GeometricTable) -> int | None:
        # A numeric/date body is distinguished from named/rotated header tiers.
        # All-text bodies remain unresolved on the relative correspondence path.
        for index, row in enumerate(self.rows(table)):
            if (
                sum(self.content_type(value) not in {"text", "empty"} for value in row)
                >= 2
            ):
                return index
        return None

    def normalize(self, value: str) -> str:
        return (
            re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip().casefold()
        )

    def can_match_reflow(
        self,
        previous: GeometricTable,
        current: GeometricTable,
        header_source: GeometricTable,
    ) -> bool:
        before_edges, after_edges = (
            self.column_edges(previous),
            self.column_edges(current),
        )
        if not before_edges or len(before_edges) != len(after_edges):
            return False
        before_width, after_width = (
            before_edges[-1] - before_edges[0],
            after_edges[-1] - after_edges[0],
        )
        if before_width <= 0 or after_width <= 0:
            return False
        before = [(edge - before_edges[0]) / before_width for edge in before_edges]
        after = [(edge - after_edges[0]) / after_width for edge in after_edges]
        for index in range(previous.column_count):
            old_width, new_width = (
                before[index + 1] - before[index],
                after[index + 1] - after[index],
            )
            if old_width <= 0 or not 0.5 <= new_width / old_width <= 2:
                return False
            center_distance = abs(
                (before[index] + before[index + 1] - after[index] - after[index + 1])
                / 2
            )
            if center_distance > max(old_width, new_width):
                return False
        header_end = self.body_start(header_source)
        previous_start = self.body_start(previous)
        if header_end is None or header_end == 0 or previous_start is None:
            return False
        previous_rows = self.rows(previous)[previous_start:]
        current_rows = self.rows(current)
        if len(previous_rows) < 2 or len(current_rows) < 2:
            return False
        old_columns = [
            set(
                self.normalize(row[column])
                for row in previous_rows
                if row[column].strip()
            )
            for column in range(previous.column_count)
        ]
        new_columns = [
            set(
                self.normalize(row[column])
                for row in current_rows
                if row[column].strip()
            )
            for column in range(current.column_count)
        ]
        has_label_anchor = False
        stable_anchors = 0
        for column, (old_values, new_values) in enumerate(
            zip(old_columns, new_columns, strict=True)
        ):
            old_types = {self.content_type(value) for value in old_values}
            new_types = {self.content_type(value) for value in new_values}
            if (
                not old_values
                or not new_values
                or old_types != new_types
                or len(old_types) != 1
            ):
                return False
            if old_types == {"text"}:
                old_words = set.intersection(
                    *(set(re.findall(r"[^\W\d_]{3,}", value)) for value in old_values)
                )
                new_words = set.intersection(
                    *(set(re.findall(r"[^\W\d_]{3,}", value)) for value in new_values)
                )
                shared = old_words & new_words
                if (
                    len(shared) >= 2
                    and len(shared) / len(old_words | new_words) >= 0.75
                ):
                    has_label_anchor = True
            if len(old_values) == len(new_values) == 1 and old_values == new_values:
                value = next(iter(old_values))
                # Repeated placeholders in several columns cannot anchor identity.
                if not any(
                    value in values
                    for index, values in enumerate(old_columns)
                    if index != column
                ) and not any(
                    value in values
                    for index, values in enumerate(new_columns)
                    if index != column
                ):
                    stable_anchors += 1
            elif any(
                value in old_values
                and any(
                    value in values
                    for index, values in enumerate(new_columns)
                    if index != column
                )
                for value in old_values
            ):
                # The same distinctive old values appearing in another column are
                # evidence against propagation, not a reason to move those cells.
                if len(old_values) == 1 and not old_values & new_values:
                    return False
        return has_label_anchor and stable_anchors >= 2

    def can_match_frame_change(
        self,
        previous: GeometricTable,
        current: GeometricTable,
        header_source: GeometricTable,
    ) -> bool:
        """A drifting outer frame cannot move any anchored interior boundary."""
        before, after = self.column_edges(previous), self.column_edges(current)
        if len(before) < 4 or len(before) != len(after):
            return False
        if not all(
            abs(first - second) <= 2
            for first, second in zip(before[1:-1], after[1:-1], strict=True)
        ):
            return False
        for index in (0, len(before) - 2):
            old_width, new_width = (
                before[index + 1] - before[index],
                after[index + 1] - after[index],
            )
            if old_width <= 0 or not 0.5 <= new_width / old_width <= 2:
                return False
        header_end = self.body_start(header_source)
        previous_start = self.body_start(previous)
        if (
            header_end is None
            or header_end == 0
            or previous_start is None
            or self.body_start(current) != 0
        ):
            return False
        old_rows, new_rows = self.rows(previous)[previous_start:], self.rows(current)
        typed_anchors = 0
        for column in range(previous.column_count):
            old_types = {self.content_type(row[column]) for row in old_rows} - {"empty"}
            new_types = {self.content_type(row[column]) for row in new_rows} - {"empty"}
            if new_types - old_types:
                return False
            if old_types and new_types and "text" not in old_types:
                typed_anchors += 1
        return typed_anchors >= 2
