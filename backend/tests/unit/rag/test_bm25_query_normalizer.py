import pytest

from app.modules.rag.bm25_query_normalizer import BM25QueryNormalizer


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("contraindicacoes", "contraindicações"),
        ("CONTRAINDICACAO?", "contraindicação?"),
        ("indicacoes e interacoes", "indicações e interações"),
        ("composicao, informacoes", "composição, informações"),
        ("advertencias/precaucoes/reacoes", "advertências/precauções/reações"),
        ("contraindicações", "contraindicações"),
        ("amoxicilinna", "amoxicilinna"),
        (
            "precontraindicacoes contraindicacoes2 _contraindicacoes",
            "precontraindicacoes contraindicacoes2 _contraindicacoes",
        ),
        ("", ""),
    ],
)
def test_restores_only_complete_known_words(query: str, expected: str) -> None:
    normalizer = BM25QueryNormalizer()
    assert normalizer.normalize(query) == expected
    assert normalizer.normalize(expected) == expected


def test_preserves_drug_names_negation_doses_and_whitespace() -> None:
    query = "NAO usar Amoxicilina + Clavulanato: 500 mg + 125 mg; 0,5 mL\n10-20 kg.\tcontraindicacoes?"
    expected = "NAO usar Amoxicilina + Clavulanato: 500 mg + 125 mg; 0,5 mL\n10-20 kg.\tcontraindicações?"
    assert BM25QueryNormalizer().normalize(query) == expected
