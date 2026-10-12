"""Real PDF layout/conversion tests; no providers, databases or indexes."""

from __future__ import annotations

import hashlib
import socket
from unittest.mock import patch

import pymupdf
import pytest

from app.modules.rag.parsers.pdf_parser import BulaParser


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_multipage_pdf(
    page_count: int, *, has_letterhead: bool = False, has_new_heading: bool = False
) -> bytes:
    with pymupdf.open() as document:
        for number in range(page_count):
            page = document.new_page()
            if has_letterhead:
                page.insert_text((350, 20), "EXAMPLE LETTERHEAD", fontsize=9)
            if has_new_heading and number == 1:
                page.insert_text((40, 25), "Unrelated new section", fontsize=9)
            edges = [
                (40, 140, 200, 260, 320),
                (20, 150, 205, 265, 340),
                (30, 140, 205, 270, 335),
            ][number]
            top = 580 if number == 0 else 40
            body_count = 2 if number == 0 else 15
            body_top = top + 110 if number == 0 else top
            bottom = body_top + body_count * 35
            if number == 0:
                page.insert_text(
                    (40, 60),
                    "COMPOSICAO\nInstructions for patients. Preserve original values and units.",
                )
                page.draw_line((edges[1], top + 30), (edges[3], top + 30))
                page.draw_line((edges[0], body_top), (edges[-1], body_top))
                page.insert_text((45, top + 25), "Source labels", fontsize=8)
                page.insert_text((edges[1] + 5, top + 20), "Composition", fontsize=8)
                for column, text in [
                    (1, "Amount (mg)"),
                    (2, "Component (mg)"),
                    (3, "Volume (mL)"),
                ]:
                    page.insert_text(
                        (edges[column] + 15, top + 100), text, fontsize=8, rotate=90
                    )
            page.draw_line((edges[0], top), (edges[-1], top))
            for column, position in enumerate(edges):
                start = top + 30 if number == 0 and column == 2 else top
                page.draw_line((position, start), (position, bottom))
            for row in range(body_count):
                row_top = body_top + row * 35
                page.draw_line((edges[0], row_top + 35), (edges[-1], row_top + 35))
                values = [
                    f"Example solution {number * 15 + row}",
                    "310",
                    "420",
                    str(800 + number * 100 + row),
                ]
                for column, value in enumerate(values):
                    page.insert_text(
                        (edges[column] + 4, row_top + 20), value, fontsize=8
                    )
        return document.tobytes()


@pytest.mark.anyio
@pytest.mark.parametrize("page_count", [2, 3])
async def test_real_reflow_keeps_hierarchy_units_source_cells_and_all_data(
    page_count: int,
) -> None:
    source = make_multipage_pdf(page_count)
    digest = hashlib.sha256(source).hexdigest()
    with patch.object(
        socket.socket, "connect", side_effect=AssertionError("No network allowed")
    ):
        parsed = await BulaParser().parse(source, "synthetic-multipage.pdf")
    assert parsed.success, parsed.error
    assert parsed.cleanup_summary is not None
    tables = parsed.cleanup_summary["table_extraction"]["tables"]
    assert len(tables) == page_count
    original = tables[0]
    assert any(
        cell["text"] == "Composition" and cell["column_end"] - cell["column_start"] == 2
        for cell in original["cells"]
    )
    assert any(
        cell["text"] == "Volume (mL)" and cell["text_direction"] == [0, -1]
        for cell in original["cells"]
    )
    for page_number, table in enumerate(tables[1:], start=2):
        assert table["continuation_of"] == "p1:t0"
        assert table["previous_fragment_page"] == page_number - 1
        assert table["continuation_method"] == "relative_schema_and_anchors"
        assert all(cell["page"] == page_number for cell in table["cells"])
        assert all(cell["page"] == 1 for cell in table["header_source_cells"])
        assert {
            cell["source_cell_id"] for cell in table["header_source_cells"]
        }.issubset({cell["source_cell_id"] for cell in original["cells"]})
    markdown_rows = [
        line for line in parsed.markdown.splitlines() if line.startswith("|")
    ]
    assert sum("---" in line for line in markdown_rows) == 1
    assert len(markdown_rows) == 3 + 2 + 15 * (page_count - 1)
    assert all(len(line.split("|")) == 6 for line in markdown_rows)
    assert "| Example solution 15 | 310 | 420 | 900 |" in parsed.markdown
    assert hashlib.sha256(source).hexdigest() == digest


@pytest.mark.anyio
async def test_repeated_source_letterhead_does_not_break_the_continuation() -> None:
    with patch.object(
        socket.socket, "connect", side_effect=AssertionError("No network allowed")
    ):
        parsed = await BulaParser().parse(
            make_multipage_pdf(2, has_letterhead=True), "repeated-letterhead.pdf"
        )
    assert parsed.success, parsed.error
    assert (
        parsed.cleanup_summary["table_extraction"]["tables"][1]["continuation_of"]
        == "p1:t0"
    )


@pytest.mark.anyio
async def test_new_heading_does_not_silently_inherit_the_old_header() -> None:
    with patch.object(
        socket.socket, "connect", side_effect=AssertionError("No network allowed")
    ):
        parsed = await BulaParser().parse(
            make_multipage_pdf(2, has_new_heading=True), "different-context.pdf"
        )
    assert not parsed.success
    assert parsed.extraction_decision == "table_structure_rejected"
    assert (
        parsed.metadata["quality_signals"]["table_failure_reason"]
        == "ambiguous_continuation_context"
    )
