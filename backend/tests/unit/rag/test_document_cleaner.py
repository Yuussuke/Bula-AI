from __future__ import annotations

from app.modules.rag.parsers.document_cleaner import (
    BulaDocumentCleaner,
    render_front_matter,
)
from app.modules.rag.parsers.handlers import ExtractedLine, ExtractedPage


def build_page(page_number: int, lines: list[ExtractedLine]) -> ExtractedPage:
    return ExtractedPage(
        page_number=page_number,
        text="\n".join(line.text for line in lines),
        lines=lines,
    )


def test_cleaner_extracts_identity_block_as_front_matter() -> None:
    pages = [
        build_page(
            1,
            [
                ExtractedLine(
                    text="dipirona monoidratada",
                    page_number=1,
                    is_bold=True,
                    markdown_heading_level=2,
                ),
                ExtractedLine(
                    text="Sanofi Medley Farmacêutica Ltda.",
                    page_number=1,
                ),
                ExtractedLine(text="Solução oral 50 mg/mL", page_number=1),
                ExtractedLine(text="APRESENTAÇÃO", page_number=1, is_bold=True),
                ExtractedLine(
                    text="Solução oral 50 mg/mL: frasco com 100 mL.",
                    page_number=1,
                ),
                ExtractedLine(text="USO ORAL.", page_number=1, is_bold=True),
                ExtractedLine(
                    text="USO ADULTO E PEDIÁTRICO ACIMA DE 3 MESES.",
                    page_number=1,
                    is_bold=True,
                ),
                ExtractedLine(text="COMPOSIÇÃO", page_number=1, is_bold=True),
                ExtractedLine(
                    text="Cada mL contém 50 mg de dipirona.",
                    page_number=1,
                ),
            ],
        )
    ]

    result = BulaDocumentCleaner().clean(pages)

    assert result.front_matter == {
        "product": "dipirona monoidratada",
        "manufacturer": "Sanofi Medley Farmacêutica Ltda.",
        "dosage_form": "Solução oral",
        "strength": "50 mg/mL",
        "presentation": "Solução oral 50 mg/mL: frasco com 100 mL.",
        "audience": "USO ORAL. USO ADULTO E PEDIÁTRICO ACIMA DE 3 MESES.",
    }
    assert [line.text for line in result.lines] == [
        "COMPOSIÇÃO",
        "Cada mL contém 50 mg de dipirona.",
    ]
    assert "## dipirona" not in render_front_matter(result.front_matter)
    assert 'product: "dipirona monoidratada"' in render_front_matter(
        result.front_matter
    )


def test_cleaner_removes_page_furniture_and_joins_only_wrapped_prose() -> None:
    pages = [
        build_page(
            1,
            [
                ExtractedLine(text="BULA DO PACIENTE", page_number=1),
                ExtractedLine(text="COMPOSIÇÃO", page_number=1, is_bold=True),
                ExtractedLine(text="O início de", page_number=1),
                ExtractedLine(text="ação ocorre em 30 minutos.", page_number=1),
                ExtractedLine(text="- Dose de 1,25 a 2,5 mL", page_number=1),
                ExtractedLine(text="2", page_number=1),
            ],
        ),
        build_page(
            2,
            [
                ExtractedLine(text="BULA DO PACIENTE", page_number=2),
                ExtractedLine(text="sistema imu-", page_number=2),
                ExtractedLine(text="nológico preservado.", page_number=2),
                ExtractedLine(text="3", page_number=2),
            ],
        ),
    ]

    result = BulaDocumentCleaner().clean(pages)
    clean_text = "\n".join(line.text for line in result.lines)

    assert "BULA DO PACIENTE" not in clean_text
    assert "\n2\n" not in f"\n{clean_text}\n"
    assert "\n3\n" not in f"\n{clean_text}\n"
    assert "O início de ação ocorre em 30 minutos." in clean_text
    assert "sistema imunológico preservado." in clean_text
    assert "- Dose de 1,25 a 2,5 mL" in clean_text
    assert result.summary["removed_page_number_count"] == 2
    assert result.summary["removed_repeated_furniture_count"] == 2
    assert result.summary["joined_wrapped_line_count"] == 2


def test_cleaner_repairs_cross_page_dosage_table_context() -> None:
    pages = [
        build_page(
            1,
            [
                ExtractedLine(text="COMPOSIÇÃO", page_number=1),
                ExtractedLine(text="POSOLOGIA", page_number=1),
                ExtractedLine(text="Peso (média de idade)", page_number=1),
                ExtractedLine(text="Solução oral (em mL)*", page_number=1),
                ExtractedLine(text="Dose", page_number=1),
                ExtractedLine(text="mg", page_number=1),
                ExtractedLine(text="6", page_number=1),
            ],
        ),
        build_page(
            2,
            [
                ExtractedLine(
                    text="|5 a 8 kg (3 a 11|Dose única|1,25 a 2,5|62,5 a 125|",
                    page_number=2,
                ),
                ExtractedLine(text="|---|---|---|---|", page_number=2),
                ExtractedLine(
                    text="|meses)|Dose máxima diária|10 (4 tomadas x 2,5 mL)|500|",
                    page_number=2,
                ),
            ],
        ),
    ]

    result = BulaDocumentCleaner().clean(pages)
    clean_text = "\n".join(line.text for line in result.lines)

    assert "| Peso (média de idade) | Dose | Solução oral (em mL)* | mg |" in clean_text
    assert clean_text.count("|---|---|---|---|") == 1
    assert (
        "| 5 a 8 kg (3 a 11 meses) | Dose única | 1,25 a 2,5 | 62,5 a 125 |"
        in clean_text
    )
    assert (
        "| 5 a 8 kg (3 a 11 meses) | Dose máxima diária | "
        "10 (4 tomadas x 2,5 mL) | 500 |" in clean_text
    )
    assert result.summary["repaired_table_count"] == 1


def test_cleaner_repairs_combined_layout_header_and_fragmented_weight() -> None:
    pages = [
        build_page(
            1,
            [
                ExtractedLine(text="COMPOSIÇÃO", page_number=1),
                ExtractedLine(text="POSOLOGIA", page_number=1),
                ExtractedLine(
                    text=("Peso Dose Solução oral (em mL)* (média de idade)"),
                    page_number=1,
                ),
                ExtractedLine(text="mg", page_number=1),
                ExtractedLine(text="6", page_number=1),
                ExtractedLine(
                    text="<!-- Start of picture text -->",
                    page_number=1,
                ),
                ExtractedLine(
                    text="62,5 a 125<br><!-- End of picture text -->",
                    page_number=1,
                ),
                ExtractedLine(
                    text="|9 15 k 1 3|<sup>Dose única</sup>|2,5 a 5|125 a 250|",
                    page_number=1,
                ),
                ExtractedLine(text="|---|---|---|---|", page_number=1),
                ExtractedLine(
                    text="|a g ( a anos)|Dose máxima diária|20|1000|",
                    page_number=1,
                ),
            ],
        )
    ]

    result = BulaDocumentCleaner().clean(pages)
    clean_text = "\n".join(line.text for line in result.lines)

    assert "| Peso (média de idade) | Dose | Solução oral (em mL)* | mg |" in clean_text
    assert "| 9 a 15 kg (1 a 3 anos) | Dose única | 2,5 a 5 | 125 a 250 |" in clean_text
    assert "| 9 a 15 kg (1 a 3 anos) | Dose máxima diária | 20 | 1000 |" in clean_text
    assert "picture text" not in clean_text
    assert "62,5 a 125<br>" not in clean_text


def test_cleaner_splits_embedded_numbered_clinical_heading() -> None:
    pages = [
        build_page(
            1,
            [
                ExtractedLine(text="COMPOSIÇÃO", page_number=1),
                ExtractedLine(
                    text=(
                        "Em casos de eventos adversos, notifique a Anvisa. "
                        "10. SUPERDOSE"
                    ),
                    page_number=1,
                ),
                ExtractedLine(text="Após superdose aguda...", page_number=1),
            ],
        )
    ]

    result = BulaDocumentCleaner().clean(pages)

    assert [line.text for line in result.lines if line.text] == [
        "COMPOSIÇÃO",
        "Em casos de eventos adversos, notifique a Anvisa.",
        "10. SUPERDOSE",
        "Após superdose aguda...",
    ]
    assert result.summary["split_embedded_heading_count"] == 1
