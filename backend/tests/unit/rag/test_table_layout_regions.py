"""Source-derived layout regressions, independent of medication names."""

from __future__ import annotations

import pymupdf
import pytest

from app.modules.rag.parsers.geometric_tables import (
    GeometricTableExtractor,
    GeometricTableIntegrator,
    TableStructureError,
    GeometricTable,
    TableCell,
)


def make_grid(*, is_filled: bool = False, text_rotation: int = 0) -> bytes:
    with pymupdf.open() as document:
        page = document.new_page()
        for x_position in (40, 100, 160):
            if is_filled:
                page.draw_rect(
                    (x_position, 80, x_position + 0.5, 220), color=None, fill=(0, 0, 0)
                )
            else:
                page.draw_line((x_position, 80), (x_position, 220))
        for y_position in (80, 150, 220):
            if is_filled:
                page.draw_rect(
                    (40, y_position, 160, y_position + 0.5), color=None, fill=(0, 0, 0)
                )
            else:
                page.draw_line((40, y_position), (160, y_position))
        for row in range(2):
            for column in range(2):
                page.insert_text(
                    (65 + column * 60, 115 + row * 70),
                    chr(65 + row * 2 + column),
                    rotate=text_rotation,
                )
        return document.tobytes()


@pytest.mark.parametrize("native_class", ["table", "picture", "text"])
def test_native_class_is_not_required_for_proven_grid(native_class: str) -> None:
    with pymupdf.open(stream=make_grid(), filetype="pdf") as document:
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": "Before\nnative\nAfter",
                "page_boxes": [
                    {"class": native_class, "bbox": (40, 80, 160, 220), "pos": (7, 14)}
                ],
            }
        ]
        GeometricTableIntegrator().repair(document, chunks)
    assert chunks[0]["text"].startswith("Before\n")
    assert chunks[0]["text"].endswith("After")
    assert "| A | B |" in chunks[0]["text"]
    assert "| C | D |" in chunks[0]["text"]


def test_one_grid_can_replace_multiple_native_fragments_once() -> None:
    with pymupdf.open(stream=make_grid(), filetype="pdf") as document:
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": "header\nbody\n",
                "page_boxes": [
                    {"class": "table", "bbox": (40, 80, 160, 150), "pos": (0, 7)},
                    {"class": "picture", "bbox": (40, 150, 160, 220), "pos": (7, 12)},
                ],
            }
        ]
        summary = GeometricTableIntegrator().repair(document, chunks)
    assert summary["geometric_table_count"] == 1
    assert chunks[0]["text"].count("| A | B |") == 1
    assert chunks[0]["text"].count("| C | D |") == 1


@pytest.mark.parametrize("empty_position", [0, 3, 12])
def test_empty_offsets_do_not_consume_table_text(empty_position: int) -> None:
    with pymupdf.open(stream=make_grid(), filetype="pdf") as document:
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": "native table",
                "page_boxes": [
                    {
                        "class": "text",
                        "bbox": (0, 0, 10, 10),
                        "pos": (empty_position, empty_position),
                    },
                    {"class": "table", "bbox": (40, 80, 160, 220), "pos": (0, 12)},
                ],
            }
        ]
        GeometricTableIntegrator().repair(document, chunks)
    assert "| C | D |" in chunks[0]["text"]


def test_nonempty_unrelated_interval_still_rejects_the_replacement() -> None:
    with pymupdf.open(stream=make_grid(), filetype="pdf") as document:
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": "native table",
                "page_boxes": [
                    {"class": "text", "bbox": (0, 0, 10, 10), "pos": (3, 5)},
                    {"class": "table", "bbox": (40, 80, 160, 220), "pos": (0, 12)},
                ],
            }
        ]
        with pytest.raises(
            TableStructureError, match="region_contains_unrelated_block"
        ):
            GeometricTableIntegrator().repair(document, chunks)
    assert chunks[0]["text"] == "native table"


def test_thin_filled_borders_preserve_independent_columns() -> None:
    with pymupdf.open(stream=make_grid(is_filled=True), filetype="pdf") as document:
        table = GeometricTableExtractor().extract(document[0])[0]
    assert (table.row_count, table.column_count) == (2, 2)
    assert table.to_markdown() == "| A | B |\n| --- | --- |\n| C | D |"


@pytest.mark.parametrize(
    ("rotation", "header", "data"),
    [
        (0, "| A | B |", "| C | D |"),
        (90, "| C | A |", "| D | B |"),
        (180, "| D | C |", "| B | A |"),
        (270, "| B | D |", "| A | C |"),
    ],
)
def test_grid_axes_follow_uniform_source_text_direction(
    rotation: int, header: str, data: str
) -> None:
    with pymupdf.open(
        stream=make_grid(text_rotation=rotation), filetype="pdf"
    ) as document:
        table = GeometricTableExtractor().extract(document[0])[0]
    assert table.to_markdown().splitlines() == [header, "| --- | --- |", data]


def test_rotated_multiline_cell_preserves_word_and_line_order() -> None:
    with pymupdf.open(stream=make_grid(text_rotation=90), filetype="pdf") as document:
        page = document[0]
        page.insert_text((45, 145), "first line", fontsize=8, rotate=90)
        page.insert_text((55, 145), "second line", fontsize=8, rotate=90)
        table = GeometricTableExtractor().extract(page)[0]
    matching = next(cell for cell in table.cells if "first" in cell.text)
    assert matching.text.startswith("first line\nsecond line")


def test_filled_background_alone_does_not_prove_a_table() -> None:
    with pymupdf.open() as document:
        page = document.new_page()
        page.draw_rect((40, 80, 300, 220), color=None, fill=(0.9, 0.9, 0.9))
        page.insert_text((50, 100), "Ordinary prose inside a shaded background.")
        assert GeometricTableExtractor().extract(page) == []


def test_rotated_page_requires_shared_coordinate_normalization() -> None:
    with pymupdf.open(stream=make_grid(), filetype="pdf") as document:
        page = document[0]
        page.set_rotation(90)
        with pytest.raises(TableStructureError, match="unnormalized_page_rotation"):
            GeometricTableExtractor().extract(page)
        page.remove_rotation()
        table = GeometricTableExtractor().extract(page)[0]
    assert {cell.text for cell in table.cells} == {"A", "B", "C", "D"}


def test_reversed_fragment_offsets_cannot_hide_inside_valid_region() -> None:
    with pymupdf.open(stream=make_grid(), filetype="pdf") as document:
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": "native table",
                "page_boxes": [
                    {"class": "table", "bbox": (40, 80, 160, 220), "pos": (0, 12)},
                    {"class": "text", "bbox": (40, 80, 100, 150), "pos": (8, 3)},
                ],
            }
        ]
        with pytest.raises(TableStructureError, match="invalid_native_offsets"):
            GeometricTableIntegrator().repair(document, chunks)


def test_unboxed_nonempty_text_between_fragments_is_not_discarded() -> None:
    with pymupdf.open(stream=make_grid(), filetype="pdf") as document:
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": "head EXTRA body",
                "page_boxes": [
                    {"class": "table", "bbox": (40, 80, 160, 150), "pos": (0, 4)},
                    {"class": "table", "bbox": (40, 150, 160, 220), "pos": (11, 15)},
                ],
            }
        ]
        with pytest.raises(TableStructureError, match="unmapped_native_text"):
            GeometricTableIntegrator().repair(document, chunks)
    assert chunks[0]["text"] == "head EXTRA body"


def test_illustrated_caption_is_preserved_without_inventing_headers() -> None:
    table = GeometricTable(
        1,
        (0, 0, 20, 20),
        2,
        2,
        (
            TableCell((0, 0, 20, 10), "Source caption", 0, 1, 0, 2),
            TableCell((0, 10, 10, 20), "First step", 1, 2, 0, 1),
            TableCell((10, 10, 20, 20), "Second step", 1, 2, 1, 2),
        ),
        has_header=False,
    )
    assert (
        table.to_markdown()
        == "Source caption\n|  |  |\n| --- | --- |\n| First step | Second step |"
    )


def test_unproven_continuation_is_rejected_instead_of_creating_false_header() -> None:
    with pymupdf.open() as document:
        chunks = []
        for page_number, top, middle in [(1, 650, 100), (2, 40, 120)]:
            page = document.new_page()
            for x_position in (40, middle, 200):
                page.draw_line((x_position, top), (x_position, top + 140))
            for y_position in (top, top + 70, top + 140):
                page.draw_line((40, y_position), (200, y_position))
            for row in range(2):
                page.insert_text((45, top + 30 + row * 70), "Left")
                page.insert_text((middle + 5, top + 30 + row * 70), "Right")
            chunks.append(
                {
                    "metadata": {"page_number": page_number},
                    "text": "native",
                    "page_boxes": [
                        {
                            "class": "table",
                            "bbox": (40, top, 200, top + 140),
                            "pos": (0, 6),
                        }
                    ],
                }
            )
        with pytest.raises(TableStructureError, match="ambiguous_table_continuation"):
            GeometricTableIntegrator().repair(document, chunks)


def test_one_native_region_orders_side_by_side_grids_left_to_right() -> None:
    with pymupdf.open() as document:
        page = document.new_page()
        for left, top, label in [(40, 80.2, "Left"), (220, 80, "Right")]:
            for x_position in (left, left + 60, left + 120):
                page.draw_line((x_position, top), (x_position, top + 140))
            for y_position in (top, top + 70, top + 140):
                page.draw_line((left, y_position), (left + 120, y_position))
            for row in range(2):
                for column in range(2):
                    page.insert_text(
                        (left + 5 + column * 60, top + 30 + row * 70), label
                    )
        chunks = [
            {
                "metadata": {"page_number": 1},
                "text": "native",
                "page_boxes": [
                    {"class": "picture", "bbox": (40, 80, 340, 220.2), "pos": (0, 6)}
                ],
            }
        ]
        summary = GeometricTableIntegrator().repair(document, chunks)
    assert summary["geometric_table_count"] == 2
    assert chunks[0]["text"].index("Left") < chunks[0]["text"].index("Right")


def test_mixed_reading_directions_in_one_cell_remain_rejected() -> None:
    with pymupdf.open(stream=make_grid(), filetype="pdf") as document:
        document[0].insert_text((80, 140), "Rotated", fontsize=8, rotate=90)
        with pytest.raises(TableStructureError, match="ambiguous_cell_reading_order"):
            GeometricTableExtractor().extract(document[0])


def test_repeated_grouped_header_anchors_changed_columns_on_its_own_page() -> None:
    with pymupdf.open() as document:
        chunks = []
        for number, top, shift in [(1, 650, 0), (2, 40, 10)]:
            page = document.new_page()
            edges = [40, 100 + shift, 160 + shift, 220 + shift, 300]
            for column, x_position in enumerate(edges):
                start = top + 40 if column in (1, 3) else top
                page.draw_line((x_position, start), (x_position, top + 140))
            for y_position in (top, top + 40, top + 80, top + 140):
                page.draw_line((40, y_position), (300, y_position))
            page.insert_text((45, top + 25), "Group A")
            page.insert_text((edges[2] + 5, top + 25), "Group B")
            for column in range(4):
                page.insert_text((edges[column] + 5, top + 65), f"Name{column}")
                page.insert_text(
                    (edges[column] + 5, top + 110), f"Value{number}{column}"
                )
            chunks.append(
                {
                    "metadata": {"page_number": number},
                    "text": "native",
                    "page_boxes": [
                        {
                            "class": "table",
                            "bbox": (40, top, 300, top + 140),
                            "pos": (0, 6),
                        }
                    ],
                }
            )
        GeometricTableIntegrator().repair(document, chunks)
    assert all(
        chunk["text"].count("| --- | --- | --- | --- |") == 1 for chunk in chunks
    )
    assert all(
        "Group A" in chunk["text"] and "Name0" in chunk["text"] for chunk in chunks
    )
    assert "Value20" in chunks[1]["text"]


def test_notes_between_pages_do_not_turn_continuation_data_into_headers() -> None:
    with pymupdf.open() as document:
        chunks = []
        for page_number, top in [(1, 650), (2, 40)]:
            page = document.new_page()
            for x_position in (40, 100, 200):
                page.draw_line((x_position, top), (x_position, top + 140))
            for y_position in (top, top + 70, top + 140):
                page.draw_line((40, y_position), (200, y_position))
            for row in range(2):
                page.insert_text((45, top + 30 + row * 70), f"Left{page_number}{row}")
                page.insert_text((105, top + 30 + row * 70), f"Right{page_number}{row}")
            page.insert_text((40, 820), "Source note")
            chunks.append(
                {
                    "metadata": {"page_number": page_number},
                    "text": "native\nSource note",
                    "page_boxes": [
                        {
                            "class": "table",
                            "bbox": (40, top, 200, top + 140),
                            "pos": (0, 6),
                        },
                        {"class": "text", "bbox": (40, 805, 140, 823), "pos": (7, 18)},
                    ],
                }
            )
        GeometricTableIntegrator().repair(document, chunks)
    assert "| --- | --- |" in chunks[0]["text"]
    assert "| --- | --- |" not in chunks[1]["text"]
    assert "| Left20 | Right20 |" in chunks[1]["text"]
    assert all("Source note" in chunk["text"] for chunk in chunks)
