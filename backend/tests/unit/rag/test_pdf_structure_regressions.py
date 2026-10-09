from __future__ import annotations

import pymupdf
import pytest

from app.modules.rag.parsers.document_cleaner import BulaDocumentCleaner
from app.modules.rag.parsers.geometric_tables import (
    GeometricTable,
    GeometricTableIntegrator,
    TableCell,
)
from app.modules.rag.parsers.handlers import (
    ExtractedLine,
    ExtractedPage,
    PdfTextLineEvidence,
    PyMuPDF4LLMHandler,
    strip_markdown_emphasis,
)
from app.modules.rag.parsers.section_detector import SectionDetector


def test_visual_list_continuation_does_not_become_new_bullet() -> None:
    native_lines = "- reação com lesões\n\n- esbranquiçadas na pele;\n\n- enjoo."
    physical_lines = [
        PdfTextLineEvidence("- reação com lesões", 85, 80, True),
        PdfTextLineEvidence("esbranquiçadas na pele;", 85, 92, False),
        PdfTextLineEvidence("- enjoo.", 85, 104, True),
    ]
    extracted_lines = PyMuPDF4LLMHandler()._build_markdown_lines(
        text=native_lines,
        page_number=1,
        physical_lines=physical_lines,
    )
    result = BulaDocumentCleaner().clean(
        [ExtractedPage(1, native_lines, extracted_lines)]
    )

    assert [line.text for line in result.lines if line.text] == [
        "- reação com lesões esbranquiçadas na pele;",
        "- enjoo.",
    ]


def test_converter_bullet_without_physical_marker_becomes_prose() -> None:
    lines = PyMuPDF4LLMHandler()._build_markdown_lines(
        text="- Isto é uma frase contínua.",
        page_number=1,
        physical_lines=[
            PdfTextLineEvidence("Isto é uma frase contínua.", 85, 80, False)
        ],
    )

    assert [line.text for line in lines] == ["Isto é uma frase contínua."]


def test_numbered_inline_headings_keep_hierarchy_and_body() -> None:
    source_lines = [
        ExtractedLine("COMPOSIÇÃO", 1),
        ExtractedLine(
            "**5. ONDE DEVO GUARDAR?** Guarde na embalagem.", 1, is_bold=True
        ),
        ExtractedLine(
            "**7. O QUE FAZER SE ESQUECER?** Consulte a bula.", 1, is_bold=True
        ),
        ExtractedLine(
            "8. QUAIS SÃO OS EFEITOS? Podem ocorrer reações.", 1, is_bold=True
        ),
    ]
    result = BulaDocumentCleaner().clean([ExtractedPage(1, "", source_lines)])
    sections = SectionDetector().detect(result.lines)

    assert [section.title for section in sections[1:]] == [
        "5. ONDE DEVO GUARDAR?",
        "7. O QUE FAZER SE ESQUECER?",
        "8. QUAIS SÃO OS EFEITOS?",
    ]
    assert all(section.level == 2 for section in sections[1:])
    assert "Guarde na embalagem." in [line.text for line in result.lines]


def test_continuous_paragraph_crosses_page_without_new_paragraph() -> None:
    pages = [
        ExtractedPage(1, "", [ExtractedLine("Pode resultar em", 1)]),
        ExtractedPage(2, "", [ExtractedLine("crescimento excessivo.", 2)]),
    ]
    result = BulaDocumentCleaner().clean(pages)

    assert [line.text for line in result.lines] == [
        "Pode resultar em crescimento excessivo."
    ]


def test_native_blank_line_is_reconciled_only_with_physical_continuity() -> None:
    source = "**A orientação depende da avaliação do**\n\n**profissional responsável.**"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text(
            (80, 100),
            "A orientação depende da avaliação do\nprofissional responsável.",
            fontsize=10,
        )
        handler = PyMuPDF4LLMHandler()
        lines = handler._build_markdown_lines(
            text=source,
            page_number=1,
            physical_lines=handler._get_physical_lines(page),
        )

    result = BulaDocumentCleaner().clean([ExtractedPage(1, source, lines)])

    assert [line.text for line in result.lines] == [
        "A orientação depende da avaliação do profissional responsável."
    ]


@pytest.mark.parametrize(
    "next_line_position",
    [(80, 145), (300, 114), (95, 114)],
    ids=["paragraph-gap", "different-column", "indentation"],
)
def test_native_blank_line_is_preserved_for_separate_physical_blocks(
    next_line_position: tuple[int, int],
) -> None:
    source = "A orientação depende da avaliação do\n\nprofissional responsável."
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((80, 100), "A orientação depende da avaliação do", fontsize=10)
        page.insert_text(next_line_position, "profissional responsável.", fontsize=10)
        handler = PyMuPDF4LLMHandler()
        lines = handler._build_markdown_lines(
            text=source,
            page_number=1,
            physical_lines=handler._get_physical_lines(page),
        )

    assert any(line.is_paragraph_break for line in lines)


@pytest.mark.parametrize(
    "source",
    [
        "A orientação depende da avaliação do\n\nprofissional responsável.",
        "Uma orientação completa.\n\noutra orientação independente.",
        "A orientação depende de\n\n## nova seção",
        "A orientação depende de\n\n- uma lista independente.",
        "A orientação depende de\n\n| Coluna | Outra coluna |",
    ],
)
def test_paragraph_break_is_not_removed_without_documentary_geometry(
    source: str,
) -> None:
    lines = PyMuPDF4LLMHandler()._build_markdown_lines(text=source, page_number=1)

    assert any(line.is_paragraph_break for line in lines)


@pytest.mark.parametrize(
    ("first_text", "next_text"),
    [
        ("Uma orientação completa.", "outra orientação independente."),
        ("Uma condição necessária", "Nova orientação independente."),
        ("Uma condição necessária", "## nova seção"),
        ("Uma condição necessária", "- uma lista independente."),
        ("Uma condição necessária", "| Coluna | Outra coluna |"),
    ],
)
def test_physical_proximity_does_not_override_structural_boundaries(
    first_text: str,
    next_text: str,
) -> None:
    lines = PyMuPDF4LLMHandler()._build_markdown_lines(
        text=f"{first_text}\n\n{next_text}",
        page_number=1,
        physical_lines=[
            PdfTextLineEvidence(first_text, 80, 100, False, y1=110, block_index=0),
            PdfTextLineEvidence(
                next_text, 80, 113, next_text.startswith("- "), y1=123, block_index=0
            ),
        ],
    )

    assert any(line.is_paragraph_break for line in lines)


def test_explicit_blank_physical_line_preserves_paragraph_boundary() -> None:
    lines = PyMuPDF4LLMHandler()._build_markdown_lines(
        text="Uma condição necessária\n\noutra orientação independente.",
        page_number=1,
        physical_lines=[
            PdfTextLineEvidence(
                "Uma condição necessária", 80, 100, False, y1=110, block_index=0
            ),
            PdfTextLineEvidence("", 80, 113, False, y1=123, block_index=0),
            PdfTextLineEvidence(
                "outra orientação independente.", 80, 126, False, y1=136, block_index=0
            ),
        ],
    )

    assert any(line.is_paragraph_break for line in lines)


def test_geometry_requires_full_text_match_not_only_a_shared_prefix() -> None:
    lines = PyMuPDF4LLMHandler()._build_markdown_lines(
        text="Uma condição necessária de 10 mg\n\noutra orientação independente.",
        page_number=1,
        physical_lines=[
            PdfTextLineEvidence(
                "Uma condição necessária de 20 mg",
                80,
                100,
                False,
                y1=110,
                block_index=0,
            ),
            PdfTextLineEvidence(
                "outra orientação independente.", 80, 113, False, y1=123, block_index=0
            ),
        ],
    )

    assert any(line.is_paragraph_break for line in lines)


def test_compound_strength_is_not_truncated_to_first_component() -> None:
    lines = [
        ExtractedLine("Medicamento genérico", 1),
        ExtractedLine("Comprimido revestido 500 mg + 125 mg", 1),
        ExtractedLine("COMPOSIÇÃO", 1),
    ]
    result = BulaDocumentCleaner().clean([ExtractedPage(1, "", lines)])

    assert result.front_matter["strength"] == "500 mg + 125 mg"
    assert result.front_matter["dosage_form"] == "Comprimido revestido"


def test_escaped_html_is_removed_without_changing_source_words() -> None:
    lines = [ExtractedLine(r"Dose\<br>diária e \*\*acompanhamento\*\*", 1)]
    result = BulaDocumentCleaner().clean([ExtractedPage(1, "", lines)])

    assert result.lines[0].text == "Dose diária e acompanhamento"


@pytest.mark.parametrize(
    "source",
    ["25 mg**/kg e *dose usual", "ALFA_BETA", "Aviso com **marcador incompleto"],
)
def test_emphasis_cleanup_preserves_footnotes_and_unpaired_markers(source: str) -> None:
    plain_text, _ = strip_markdown_emphasis(source)

    assert plain_text == source


def test_literal_pipe_in_table_cell_remains_escaped() -> None:
    source = "| princípio A&#124;B | 5 mg |"
    result = BulaDocumentCleaner().clean(
        [ExtractedPage(1, "", [ExtractedLine(source, 1)])]
    )

    assert result.lines[0].text == source
    assert result.lines[0].text.count("|") == 3


def test_continued_rowspan_repeats_physical_value_without_shifting_columns() -> None:
    table = GeometricTable(
        page_number=2,
        bounds=(0, 0, 30, 30),
        row_count=2,
        column_count=3,
        cells=(
            TableCell((0, 0, 10, 30), "Grupo", 0, 2, 0, 1),
            TableCell((10, 0, 20, 15), "5 mg", 0, 1, 1, 2),
            TableCell((20, 0, 30, 15), "Diário", 0, 1, 2, 3),
            TableCell((10, 15, 20, 30), "2 mg", 1, 2, 1, 2),
            TableCell((20, 15, 30, 30), "Semanal", 1, 2, 2, 3),
        ),
    )

    markdown = table.to_markdown(is_continuation=True)
    assert markdown.splitlines() == [
        "| Grupo | 5 mg | Diário |",
        "| Grupo | 2 mg | Semanal |",
    ]


def test_adjacent_geometric_tables_share_one_header_not_false_page_headers() -> None:
    with pymupdf.open() as document:
        for y_edges, values in (
            ([140, 180, 220, 260], ["Heading", "first", "second"]),
            ([20, 60, 100], ["third", "fourth"]),
        ):
            page = document.new_page(width=300, height=300)
            for y in y_edges:
                page.draw_line((20, y), (180, y))
            for x in (20, 100, 180):
                page.draw_line((x, y_edges[0]), (x, y_edges[-1]))
            for row, value in enumerate(values):
                page.insert_text((25, y_edges[row] + 23), value)
                page.insert_text((105, y_edges[row] + 23), str(row + 1))
        chunks = [
            {
                "metadata": {"page_number": number},
                "text": "native table",
                "page_boxes": [
                    {
                        "class": "table",
                        "bbox": (20, bounds[0], 180, bounds[-1]),
                        "pos": (0, len("native table")),
                    }
                ],
            }
            for number, bounds in ((1, [140, 260]), (2, [20, 100]))
        ]
        GeometricTableIntegrator().repair(document, chunks)

    combined = "\n".join(str(chunk["text"]) for chunk in chunks)
    assert combined.count("| --- | --- |") == 1
    assert "| third | 1 |" in combined
    assert "| fourth | 2 |" in combined
    assert all(
        line.count("|") == 3 for line in combined.splitlines() if line.startswith("|")
    )
