from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.rag.parsers.geometric_tables import (
    GeometricTable,
    GeometricTableIntegrator,
    TableCell,
    TableStructureError,
)
from app.modules.rag.parsers.table_continuation import TableContinuationMatcher


def make_table(
    page: int,
    edges: tuple[float, ...],
    rows: list[list[str]],
) -> GeometricTable:
    top = 600.0 if page == 1 else 40.0
    cells = [
        TableCell(
            (edges[column], top + row * 40, edges[column + 1], top + (row + 1) * 40),
            text,
            row,
            row + 1,
            column,
            column + 1,
        )
        for row, values in enumerate(rows)
        for column, text in enumerate(values)
    ]
    return GeometricTable(
        page,
        (edges[0], top, edges[-1], top + len(rows) * 40),
        len(rows),
        len(edges) - 1,
        tuple(cells),
    )


@pytest.fixture
def source_pair() -> tuple[GeometricTable, GeometricTable]:
    previous = make_table(
        1,
        (40, 140, 200, 260, 320),
        [
            ["Example", "Amount (mg)", "Component (mg)", "Volume (mL)"],
            ["Example solution 1", "310", "420", "800"],
            ["Example solution 2", "310", "420", "900"],
        ],
    )
    current = make_table(
        2,
        (20, 150, 210, 265, 340),
        [
            ["Example solution 3", "310", "420", "1000"],
            ["Example solution 4", "310", "420", "1100"],
        ],
    )
    return previous, current


def test_shifted_and_resized_columns_keep_order_and_literal_values(
    source_pair: tuple[GeometricTable, GeometricTable],
) -> None:
    previous, current = source_pair
    matcher = TableContinuationMatcher()
    assert not matcher.is_absolutely_aligned(previous, current)
    assert matcher.can_match_reflow(previous, current, previous)
    assert GeometricTableIntegrator()._is_multipage_continuation(
        previous=previous,
        current=current,
        previous_page_height=842,
        current_page_height=842,
    )
    assert (
        current.to_markdown(is_continuation=True)
        == "| Example solution 3 | 310 | 420 | 1000 |\n| Example solution 4 | 310 | 420 | 1100 |"
    )


@pytest.mark.parametrize(
    "defect",
    [
        "unrelated_labels",
        "swapped_values",
        "different_units",
        "repeated_placeholders",
        "single_row",
        "new_header",
        "extreme_reflow",
    ],
)
def test_relative_geometry_and_column_count_are_not_sufficient(
    source_pair: tuple[GeometricTable, GeometricTable],
    defect: str,
) -> None:
    previous, current = source_pair
    matcher = TableContinuationMatcher()
    rows = matcher.rows(current)
    edges = (20, 150, 210, 265, 340)
    if defect == "unrelated_labels":
        for row in rows:
            row[0] = "Unrelated treatment"
    elif defect == "swapped_values":
        for row in rows:
            row[1], row[2] = row[2], row[1]
    elif defect == "different_units":
        for row in rows:
            row[1] = "310 mL"
    elif defect == "repeated_placeholders":
        previous = make_table(
            1,
            (40, 140, 200, 260, 320),
            [
                ["Example", "A", "B", "Volume"],
                ["Example solution 1", "1", "1", "800"],
                ["Example solution 2", "1", "1", "900"],
            ],
        )
        for row in rows:
            row[1] = row[2] = "1"
    elif defect == "single_row":
        rows = rows[:1]
    elif defect == "new_header":
        rows.insert(
            0, ["Different section", "Other amount", "Other component", "Volume"]
        )
    else:
        edges = (20, 260, 280, 300, 340)
    current = make_table(2, edges, rows)
    assert not matcher.can_match_reflow(previous, current, previous)
    with pytest.raises(TableStructureError, match="ambiguous_table_continuation"):
        GeometricTableIntegrator()._is_multipage_continuation(
            previous=previous,
            current=current,
            previous_page_height=842,
            current_page_height=842,
        )


def test_new_context_does_not_receive_previous_headers(
    source_pair: tuple[GeometricTable, GeometricTable],
) -> None:
    previous, current = source_pair
    with pytest.raises(TableStructureError, match="ambiguous_continuation_context"):
        GeometricTableIntegrator()._is_multipage_continuation(
            previous=previous,
            current=current,
            previous_page_height=842,
            current_page_height=842,
            has_context_break=True,
        )


def test_third_page_uses_original_header_source(
    source_pair: tuple[GeometricTable, GeometricTable],
) -> None:
    original, second = source_pair
    third = make_table(
        3,
        (30, 140, 205, 270, 335),
        [
            ["Example solution 5", "310", "420", "1200"],
            ["Example solution 6", "310", "420", "1300"],
        ],
    )
    assert TableContinuationMatcher().can_match_reflow(second, third, original)
    assert not TableContinuationMatcher().can_match_reflow(second, third, second)


def test_nonadjacent_page_and_different_column_count_do_not_propagate(
    source_pair: tuple[GeometricTable, GeometricTable],
) -> None:
    previous, current = source_pair
    integrator = GeometricTableIntegrator()
    assert not integrator._is_multipage_continuation(
        previous=previous,
        current=replace(current, page_number=3),
        previous_page_height=842,
        current_page_height=842,
    )
    other = make_table(2, (20, 150, 210), [["Other", "310"], ["Other", "420"]])
    assert not integrator._is_multipage_continuation(
        previous=previous,
        current=other,
        previous_page_height=842,
        current_page_height=842,
    )


def test_only_text_columns_keep_conservative_rejection() -> None:
    previous = make_table(
        1,
        (40, 140, 220),
        [["A", "B"], ["Same label", "Same value"], ["Same label", "Same value"]],
    )
    current = make_table(
        2, (20, 145, 230), [["Same label", "Same value"], ["Same label", "Same value"]]
    )
    assert not TableContinuationMatcher().can_match_reflow(previous, current, previous)


def test_units_are_classified_without_conversions() -> None:
    matcher = TableContinuationMatcher()
    assert matcher.content_type("12,5 mg") == "number:mg"
    assert matcher.content_type("12.5 mL") == "number:ml"
    assert matcher.content_type("12/10/2026") == "date"
    assert matcher.content_type("12/10/2026 Revised on 13/10/2026") == "date"
    assert matcher.normalize("12,5 mg") != matcher.normalize("0,0125 g")


def test_outer_frame_drift_keeps_anchored_internal_edges_and_nullable_dates() -> None:
    previous = make_table(
        1,
        (40, 140, 200, 260, 320),
        [
            ["Date", "Protocol", "Other date", "Description"],
            ["01/01/2020", "ABC", "02/01/2020", "Original description"],
            ["03/01/2020", "DEF", "04/01/2020", "Another description"],
        ],
    )
    current = make_table(
        2,
        (35, 140, 200, 260, 325),
        [
            ["05/01/2020", "NA", "06/01/2020", "New description"],
            ["07/01/2020", "GHI", "-", "Other description"],
        ],
    )
    matcher = TableContinuationMatcher()
    assert not matcher.can_match_reflow(previous, current, previous)
    assert matcher.can_match_frame_change(previous, current, previous)
    assert "| 05/01/2020 | NA | 06/01/2020 | New description |" in current.to_markdown(
        is_continuation=True
    )
    wrong_type = make_table(
        2,
        (35, 140, 200, 260, 325),
        [
            ["New description", "NA", "06/01/2020", "05/01/2020"],
            ["Other description", "GHI", "-", "07/01/2020"],
        ],
    )
    assert not matcher.can_match_frame_change(previous, wrong_type, previous)
    moved_inside = make_table(2, (35, 145, 200, 260, 325), matcher.rows(current))
    assert not matcher.can_match_frame_change(previous, moved_inside, previous)


def test_recurring_marginal_text_is_independent_of_markdown_emphasis() -> None:
    integrator = GeometricTableIntegrator()

    def chunk(text: str) -> dict[str, object]:
        return {
            "metadata": {"page_number": 1},
            "text": text,
            "page_boxes": [
                {
                    "class": "section-header",
                    "bbox": (30, 20, 100, 35),
                    "pos": (0, len(text)),
                }
            ],
        }

    assert integrator._top_context(
        chunk("**Example Letterhead**"), 600, 800
    ) == integrator._top_context(chunk("# Example Letterhead"), 600, 800)
