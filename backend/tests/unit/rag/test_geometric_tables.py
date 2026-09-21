from __future__ import annotations

import pymupdf
import pytest

from app.modules.rag.parsers.geometric_tables import (
    GeometricTableExtractor,
    GeometricTableIntegrator,
    TableStructureError,
)


def make_table_pdf(
    *, columns: int = 3, rows: int = 3, has_caption: bool = False
) -> bytes:
    with pymupdf.open() as document:
        page = document.new_page()
        for row in range(rows + 1):
            page.draw_line((40, 80 + row * 30), (40 + columns * 80, 80 + row * 30))
        for column in range(columns + 1):
            top = 110 if has_caption and 0 < column < columns else 80
            page.draw_line((40 + column * 80, top), (40 + column * 80, 80 + rows * 30))
        for row in range(rows):
            for column in range(columns):
                if has_caption and row == 0 and column > 0:
                    continue
                # A real empty cell, with borders, not a merged cell.
                if row == rows - 1 and column == columns - 1:
                    continue
                value = "Caption" if has_caption and row == 0 else f"cell{row}{column}"
                page.insert_text((45 + column * 80, 99 + row * 30), value, fontsize=10)
        return document.tobytes()


@pytest.mark.parametrize(("columns", "rows"), [(2, 2), (3, 4), (5, 3)])
def test_geometry_detects_variable_dimensions_and_empty_cells(
    columns: int, rows: int
) -> None:
    with pymupdf.open(
        stream=make_table_pdf(columns=columns, rows=rows), filetype="pdf"
    ) as document:
        tables = GeometricTableExtractor().extract(document[0])
    assert len(tables) == 1
    table = tables[0]
    assert (table.row_count, table.column_count) == (rows, columns)
    assert len(table.cells) == rows * columns
    for cell in table.cells:
        assert cell.row_end == cell.row_start + 1
        assert cell.column_end == cell.column_start + 1
        expected = (
            ""
            if (cell.row_start, cell.column_start) == (rows - 1, columns - 1)
            else f"cell{cell.row_start}{cell.column_start}"
        )
        assert cell.text == expected


def test_merged_caption_keeps_span_without_inventing_empty_values() -> None:
    with pymupdf.open(
        stream=make_table_pdf(has_caption=True), filetype="pdf"
    ) as document:
        table = GeometricTableExtractor().extract(document[0])[0]
    caption = next(cell for cell in table.cells if cell.text == "Caption")
    assert caption.column_start == 0
    assert caption.column_end == 3
    markdown = table.to_markdown()
    assert markdown.count("Caption") == 1
    assert "| cell10 | cell11 | cell12 |" in markdown
    assert "| cell20 | cell21 |  |" in markdown


def test_geometry_does_not_treat_a_paragraph_box_as_a_table() -> None:
    with pymupdf.open() as document:
        page = document.new_page()
        page.draw_rect((40, 40, 300, 160))
        page.insert_text((50, 60), "A paragraph in a decorative box.")
        assert GeometricTableExtractor().extract(page) == []


def test_coordinate_replacement_preserves_surroundings_and_source_once() -> None:
    with pymupdf.open(stream=make_table_pdf(), filetype="pdf") as document:
        # Upstream converter result is external input. Intentionally malformed
        # table text proves replacement uses coordinates, not string matching.
        prefix, malformed, suffix = "Before\n\n", "bad table\n\n", "After\n"
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": prefix + malformed + suffix,
                "page_boxes": [
                    {
                        "class": "table",
                        "bbox": (40, 80, 280, 170),
                        "pos": (len(prefix), len(prefix + malformed)),
                    }
                ],
            }
        ]
        summary = GeometricTableIntegrator().repair(document, chunks)
    assert summary["geometric_table_count"] == 1
    assert chunks[0]["text"].startswith(prefix)
    assert chunks[0]["text"].endswith(suffix)
    assert "bad table" not in chunks[0]["text"]
    assert chunks[0]["text"].count("cell11") == 1


def test_unmapped_ruled_table_is_not_silently_flattened() -> None:
    with pymupdf.open(stream=make_table_pdf(), filetype="pdf") as document:
        chunks = [
            {"metadata": {"page_number": 1}, "text": "unmapped", "page_boxes": []}
        ]
        with pytest.raises(TableStructureError, match="unmapped_table_region"):
            GeometricTableIntegrator().repair(document, chunks)


def test_borderless_native_table_is_retained_and_reported() -> None:
    with pymupdf.open() as document:
        document.new_page()
        native = "| A | B |\n| --- | --- |\n| 10 | 20 |"
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": native,
                "page_boxes": [
                    {
                        "class": "table",
                        "bbox": (40, 80, 280, 170),
                        "pos": (0, len(native)),
                    }
                ],
            }
        ]
        summary = GeometricTableIntegrator().repair(document, chunks)
    assert chunks[0]["text"] == native
    assert summary["native_only_table_count"] == 1


def test_borderless_table_with_inconsistent_columns_is_rejected() -> None:
    with pymupdf.open() as document:
        document.new_page()
        native = "| A | B |\n| --- | --- |\n| 10 | 20 | 30 |"
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": native,
                "page_boxes": [
                    {
                        "class": "table",
                        "bbox": (40, 80, 280, 170),
                        "pos": (0, len(native)),
                    }
                ],
            }
        ]
        with pytest.raises(TableStructureError, match="inconsistent_native_columns"):
            GeometricTableIntegrator().repair(document, chunks)


def test_bad_native_offsets_fail_without_source_in_error() -> None:
    with pymupdf.open(stream=make_table_pdf(), filetype="pdf") as document:
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": "private source",
                "page_boxes": [
                    {"class": "table", "bbox": (40, 80, 280, 170), "pos": (0, 999)}
                ],
            }
        ]
        with pytest.raises(
            TableStructureError, match="invalid_native_offsets"
        ) as caught:
            GeometricTableIntegrator().repair(document, chunks)
        assert "private source" not in str(caught.value)


def test_equal_width_tables_on_different_pages_are_not_automatically_joined() -> None:
    with pymupdf.open(stream=make_table_pdf(), filetype="pdf") as source:
        with pymupdf.open() as document:
            document.insert_pdf(source)
            document.insert_pdf(source)
            chunks = [
                {
                    "metadata": {"page_number": page},
                    "text": "native table",
                    "page_boxes": [
                        {"class": "table", "bbox": (40, 80, 280, 170), "pos": (0, 12)}
                    ],
                }
                for page in (1, 2)
            ]
            summary = GeometricTableIntegrator().repair(document, chunks)
    assert summary["geometric_table_count"] == 2
    for chunk in chunks:
        assert chunk["text"].count("cell00") == 1


def test_cell_spans_are_retained_for_vertical_and_horizontal_merges() -> None:
    from app.modules.rag.parsers.geometric_tables import GeometricTable, TableCell

    table = GeometricTable(
        1,
        (0, 0, 30, 30),
        3,
        3,
        (
            TableCell((0, 0, 10, 10), "Group", 0, 1, 0, 1),
            TableCell((10, 0, 20, 10), "Dose", 0, 1, 1, 2),
            TableCell((20, 0, 30, 10), "Limit", 0, 1, 2, 3),
            TableCell((0, 10, 10, 30), "Adult", 1, 3, 0, 1),
            TableCell((10, 10, 30, 20), "5 mg", 1, 2, 1, 3),
            TableCell((10, 20, 20, 30), "2 mg", 2, 3, 1, 2),
            TableCell((20, 20, 30, 30), "", 2, 3, 2, 3),
        ),
    )
    assert "| Adult | 5 mg | 5 mg |" in table.to_markdown()
    assert "| Adult | 2 mg |  |" in table.to_markdown()
    assert table.cells[3].row_end == 3
