from app.core.config import ProcessingSettings, Settings
from app.modules.rag.token_estimator import (
    HeuristicTokenEstimator,
    TiktokenTokenEstimator,
    build_token_estimator,
)


PT_MEDICAL_SNIPPET = (
    "Não use este medicamento em caso de hipersensibilidade à dipirona, "
    "asma induzida por analgésicos ou reação alérgica prévia a pirazolonas."
)


def test_tiktoken_estimator_counts_portuguese_medical_text() -> None:
    estimator = TiktokenTokenEstimator(encoding_name="cl100k_base")

    token_count = estimator.estimate(PT_MEDICAL_SNIPPET)

    assert token_count > 0
    assert token_count < len(PT_MEDICAL_SNIPPET)


def test_heuristic_estimator_keeps_documented_character_fallback() -> None:
    estimator = HeuristicTokenEstimator()

    assert estimator.estimate(PT_MEDICAL_SNIPPET) == max(
        1,
        len(PT_MEDICAL_SNIPPET) // 4,
    )
    assert estimator.estimate("") == 1


def test_build_token_estimator_uses_heuristic_when_encoding_is_blank() -> None:
    settings = Settings(
        secret_key="long_and_secure_secret_key_for_testing_purposes_only_1234567890",
        processing=ProcessingSettings(tokenizer_encoding=""),
    )

    estimator = build_token_estimator(settings=settings)

    assert isinstance(estimator, HeuristicTokenEstimator)
