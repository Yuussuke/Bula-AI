from pathlib import Path

import pytest

from scripts.benchmark_semantic_chunking import (
    FOCUSED_SECTION_SPECS,
    _find_focused_section,
    _validate_inputs,
    critical_content_preservation,
    has_complete_source_line_coverage,
    split_h2_sections,
)


REFERENCE_ROOT = Path("tests/fixtures/rag/references")
REFERENCE_PATHS = {
    "dipirona": REFERENCE_ROOT / "dipirona_sanofi_medley_solucao_oral.md",
    "amoxicilina": REFERENCE_ROOT / "amoxicilina_cimed_suspensao_oral.md",
}


def test_six_focused_benchmark_sections_exist_in_regression_markdown() -> None:
    sections_by_document = {
        document: split_h2_sections(path.read_text(encoding="utf-8"))
        for document, path in REFERENCE_PATHS.items()
    }

    selected_sections = [
        _find_focused_section(
            spec=spec,
            available_sections=sections_by_document[spec.document],
        )
        for spec in FOCUSED_SECTION_SPECS
    ]

    assert len(selected_sections) == 6
    assert {(section.document, section.label) for section in selected_sections} == {
        ("dipirona", "contraindications"),
        ("dipirona", "dosage"),
        ("dipirona", "adverse_effects"),
        ("amoxicilina", "composition"),
        ("amoxicilina", "dosage"),
        ("amoxicilina", "adverse_effects"),
    }


def test_source_coverage_allows_repeated_table_header_without_omission() -> None:
    source_text = (
        "## POSOLOGIA\n"
        "| Peso | Dose |\n"
        "| --- | --- |\n"
        "| 5 kg | 2,5 mL |\n"
        "| 10 kg | 5 mL |"
    )
    chunk_texts = [
        "## POSOLOGIA\n| Peso | Dose |\n| --- | --- |\n| 5 kg | 2,5 mL |",
        "| Peso | Dose |\n| --- | --- |\n| 10 kg | 5 mL |",
    ]

    assert has_complete_source_line_coverage(
        source_text=source_text,
        chunk_texts=chunk_texts,
    )
    assert (
        critical_content_preservation(
            source_text=source_text,
            chunk_texts=chunk_texts,
        )
        == 1.0
    )


def test_benchmark_rejects_missing_pdf_before_provider_calls(tmp_path: Path) -> None:
    missing_pdf = tmp_path / "missing.pdf"

    with pytest.raises(ValueError, match="Missing benchmark PDFs"):
        _validate_inputs(
            pdf_paths={"dipirona": missing_pdf},
            models=("baseline", "candidate"),
        )


def test_benchmark_requires_distinct_model_paths(tmp_path: Path) -> None:
    pdf_path = tmp_path / "fixture.pdf"
    pdf_path.write_bytes(b"%PDF fixture")

    with pytest.raises(ValueError, match="two distinct model"):
        _validate_inputs(
            pdf_paths={"dipirona": pdf_path},
            models=("same-model", "same-model"),
        )
