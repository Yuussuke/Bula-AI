"""Behavioral tests for source-owned evidence units."""

from langchain_core.documents import Document

from app.modules.rag.evidence_units import (
    EvidenceUnitKind,
    build_evidence_units,
    format_evidence_units,
)


def test_prose_units_keep_negation_with_the_medical_claim() -> None:
    document = Document(
        page_content=(
            "## Uso\nNão\né recomendado dobrar a dose. "
            "Se a febre persistir, procure seu médico."
        ),
        metadata={"section_title": "Uso"},
    )

    units = build_evidence_units([document])

    assert [unit.text for unit in units] == [
        "Não é recomendado dobrar a dose.",
        "Se a febre persistir, procure seu médico.",
    ]
    assert [unit.unit_id for unit in units] == ["E1", "E2"]
    assert "[E1] Fonte 1; seção: Uso" in format_evidence_units(units)


def test_multiline_list_item_remains_whole_but_next_bullet_is_separate() -> None:
    document = Document(
        page_content=(
            "- Não use se houver alergia a penicilinas ou\n"
            "  reações anteriores.\n"
            "- Informe seu médico sobre outra alergia."
        )
    )

    units = build_evidence_units([document])

    assert [unit.text for unit in units] == [
        "- Não use se houver alergia a penicilinas ou reações anteriores.",
        "- Informe seu médico sobre outra alergia.",
    ]
    assert all(unit.kind is EvidenceUnitKind.LIST_ITEM for unit in units)


def test_table_row_includes_header_and_preserves_column_relationship() -> None:
    document = Document(
        page_content=(
            "## Posologia\nTabela de doses\n"
            "| Peso | Dose única | Máximo diário |\n"
            "| --- | --- | --- |\n"
            "| 20 kg | 10 gotas | 40 gotas |\n"
            "| 30 kg | 15 gotas | 60 gotas |"
        ),
        metadata={"section_title": "Posologia"},
    )

    units = build_evidence_units([document])

    assert [unit.kind for unit in units] == [
        EvidenceUnitKind.PROSE,
        EvidenceUnitKind.TABLE_ROW,
        EvidenceUnitKind.TABLE_ROW,
    ]
    assert "| Peso | Dose única | Máximo diário |" in units[1].text
    assert "| 20 kg | 10 gotas | 40 gotas |" in units[1].text
    assert "30 kg" not in units[1].text
    assert "| 30 kg | 15 gotas | 60 gotas |" in units[2].text


def test_misaligned_table_does_not_supply_dosage_evidence() -> None:
    document = Document(
        page_content=(
            "| Peso | Dose | Máximo |\n| --- | --- | --- |\n| 20 kg | 10 gotas |"
        )
    )

    assert build_evidence_units([document]) == []


def test_pregnancy_paragraph_produces_complete_individual_guidance() -> None:
    document = Document(
        page_content=(
            "### Gravidez e amamentação\n\n"
            "Não utilizar dipirona durante os primeiros 3 meses da gravidez. "
            "O uso de dipirona durante o segundo trimestre da gravidez só deve "
            "ocorrer após cuidadosa avaliação do potencial risco/benefício pelo médico. "
            "Não usar dipirona durante os últimos 3 meses da gravidez."
        ),
        metadata={"section_title": "Gravidez e amamentação"},
    )

    units = build_evidence_units([document])

    assert len(units) == 3
    assert units[0].text.startswith("Não utilizar dipirona")
    assert units[1].text.endswith("pelo médico.")
    assert units[2].text.startswith("Não usar dipirona")


def test_front_matter_is_not_prose_and_does_not_change_the_document() -> None:
    source = (
        '\ufeff---\nproduct: "Produto"\nstrength: "500 mg + 125 mg"\n'
        'presentation: "Embalagem. Fracionável"\naudience: "ACIMA DE 12 ANOS"\n'
        "---\n\n## Uso\nNão use em menores de 12 anos."
    )
    document = Document(page_content=source)
    units = build_evidence_units([document])
    assert [unit.text for unit in units] == ["Não use em menores de 12 anos."]
    assert units[0].unit_id == "E1"
    assert document.page_content == source


def test_metadata_only_or_unterminated_front_matter_has_no_evidence() -> None:
    for source in ['---\nstrength: "500 mg"\n---', '---\nstrength: "500 mg"']:
        assert build_evidence_units([Document(page_content=source)]) == []


def test_horizontal_rule_inside_body_does_not_discard_source_text() -> None:
    units = build_evidence_units(
        [Document(page_content="Primeira frase.\n\n---\n\nSegunda frase.")]
    )
    assert units[0].text == "Primeira frase."
    assert units[-1].text == "Segunda frase."


def test_table_rows_keep_their_own_adjacent_labels_and_section() -> None:
    document = Document(
        page_content=(
            "## Ajustes\n\nGrupo A\n\n"
            "| Categoria | Orientação |\n| --- | --- |\n| Leve | Sem ajuste |\n\n"
            "Grupo B\n\n"
            "| Categoria | Orientação |\n| --- | --- |\n| Leve | Outra orientação |"
        ),
        metadata={"section_title": "Ajustes"},
    )

    units = build_evidence_units([document])
    rows = [unit for unit in units if unit.kind is EvidenceUnitKind.TABLE_ROW]

    assert rows[0].text.startswith("## Ajustes\nGrupo A\n| Categoria |")
    assert rows[1].text.startswith("## Ajustes\nGrupo B\n| Categoria |")
    assert "Grupo B" not in rows[0].text
    assert "Grupo A" not in rows[1].text
    assert all(unit.section_title == "Ajustes" for unit in rows)
    assert [unit.text for unit in units if unit.kind is EvidenceUnitKind.PROSE] == [
        "Grupo A",
        "Grupo B",
    ]


def test_table_context_keeps_heading_hierarchy_but_not_previous_siblings() -> None:
    units = build_evidence_units(
        [
            Document(
                page_content=(
                    "## Orientações\n\n### Grupo A\n\n"
                    "| Faixa | Conduta |\n| --- | --- |\n| A | X |\n\n"
                    "### Grupo B\nRótulo local\n"
                    "| Faixa | Conduta |\n| --- | --- |\n| B | Y |\n\n"
                    "## Outra seção\n\n"
                    "| Faixa | Conduta |\n| --- | --- |\n| C | Z |"
                )
            )
        ]
    )
    rows = [unit for unit in units if unit.kind is EvidenceUnitKind.TABLE_ROW]

    assert rows[0].text.startswith("## Orientações\n### Grupo A\n| Faixa |")
    assert rows[1].text.startswith(
        "## Orientações\n### Grupo B\nRótulo local\n| Faixa |"
    )
    assert "Grupo A" not in rows[1].text
    assert rows[2].text.startswith("## Outra seção\n| Faixa |")
    assert "Orientações" not in rows[2].text
    assert "Grupo B" not in rows[2].text
    assert "Rótulo local" not in rows[2].text


def test_table_does_not_inherit_labels_across_prose_lists_or_dividers() -> None:
    table = "| Faixa | Conduta |\n| --- | --- |\n| A | X |"
    for intervening_block in [
        "Uma observação independente. Outra frase explicativa.",
        "- Um item independente",
        "---",
        "Outro bloco\ncom mais de uma linha",
    ]:
        units = build_evidence_units(
            [
                Document(
                    page_content=f"Rótulo anterior\n\n{intervening_block}\n\n{table}"
                )
            ]
        )
        row = next(unit for unit in units if unit.kind is EvidenceUnitKind.TABLE_ROW)

        assert row.text == table


def test_table_context_never_crosses_document_boundaries() -> None:
    table = "| Faixa | Conduta |\n| --- | --- |\n| A | X |"
    units = build_evidence_units(
        [
            Document(page_content="## Outra origem\n\nRótulo distante"),
            Document(page_content=table),
        ]
    )
    row = next(unit for unit in units if unit.kind is EvidenceUnitKind.TABLE_ROW)

    assert row.text == table
    assert row.source_number == 2


def test_table_label_is_not_reused_by_a_following_unlabelled_table() -> None:
    first_table = "| Faixa | Conduta |\n| --- | --- |\n| A | X |"
    second_table = "| Faixa | Conduta |\n| --- | --- |\n| B | Y |"
    units = build_evidence_units(
        [Document(page_content=f"Rótulo local\n\n{first_table}\n\n{second_table}")]
    )
    rows = [unit for unit in units if unit.kind is EvidenceUnitKind.TABLE_ROW]

    assert rows[0].text == f"Rótulo local\n{first_table}"
    assert rows[1].text == second_table


def test_table_context_preserves_original_cells_spacing_and_source_document() -> None:
    header = "  | Faixa | Conduta |  "
    separator = "  | :--- | ---: |  "
    original_row = "  | A  | X<br>Y **nota** |  "
    source = f"### Rótulo\n\n{header}\n{separator}\n{original_row}"
    document = Document(page_content=source)

    row = build_evidence_units([document])[0]

    assert row.text == f"### Rótulo\n{header}\n{separator}\n{original_row}"
    assert row.text.splitlines()[-1] == original_row
    assert document.page_content == source


def test_table_context_does_not_merge_surrounding_prose_sentences() -> None:
    units = build_evidence_units(
        [
            Document(
                page_content=(
                    "## Uso\n\nPrimeira frase. Segunda frase.\n\n"
                    "Rótulo local\n\n"
                    "| Faixa | Conduta |\n| --- | --- |\n| A | X |\n\n"
                    "Terceira frase. Quarta frase."
                )
            )
        ]
    )

    assert [unit.text for unit in units if unit.kind is EvidenceUnitKind.PROSE] == [
        "Primeira frase.",
        "Segunda frase.",
        "Rótulo local",
        "Terceira frase.",
        "Quarta frase.",
    ]
    row = next(unit for unit in units if unit.kind is EvidenceUnitKind.TABLE_ROW)
    assert row.text.startswith("## Uso\nRótulo local\n")
    assert "frase" not in row.text
