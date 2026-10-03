import pytest

from app.modules.rag.section_titles import (
    is_administrative_section,
    normalize_section_title,
)


@pytest.mark.parametrize(
    "title",
    [
        "Advertências e precauções",
        "4. ADVERTÊNCIAS E PRECAUÇÕES",
        " 4) advertencias  e\tprecaucoes ",
        "4.2. Advertências e precauções",
    ],
)
def test_section_identity_ignores_number_case_accents_and_spacing(title: str) -> None:
    assert normalize_section_title(title) == "advertencias e precaucoes"


def test_normalization_does_not_remove_unrelated_numeric_text() -> None:
    assert normalize_section_title("500 mg + 125 mg") == "500 mg + 125 mg"
    assert normalize_section_title("12 anos") == "12 anos"


@pytest.mark.parametrize(
    "title",
    [
        "Histórico de alteração para a bula",
        "12. HISTÓRICO DE ALTERAÇÕES PARA A BULA",
        "III - DIZERES LEGAIS",
        "VENDA SOB PRESCRIÇÃO COM RETENÇÃO DA RECEITA",
    ],
)
def test_administrative_section_identity_is_recognized(title: str) -> None:
    assert is_administrative_section(title)


@pytest.mark.parametrize(
    "title",
    [
        "4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?",
        "Histórico de alergias",
        "Advertências da bula",
        "Documento",
    ],
)
def test_clinical_and_identification_sections_remain_eligible(title: str) -> None:
    assert not is_administrative_section(title)
