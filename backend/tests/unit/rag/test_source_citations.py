"""Citation format is not documentary correctness; every referenced ID must exist."""

from langchain_core.language_models.fake_chat_models import FakeListChatModel
import pytest

from app.modules.rag.grounded_generation import (
    GroundedAnswerGenerator,
    GroundedGenerationError,
)


@pytest.mark.parametrize(
    "marker", ["[1]", "[1][2]", "[1,2]", "[1, 2]", "[2,\t1,2]", "[1] e [2, 1]"]
)
def test_existing_sources_accept_individual_and_grouped_references(marker: str) -> None:
    answer = f"Texto sintético {marker}."
    # Exercise the real answer validator, not only regex matching.
    generator = GroundedAnswerGenerator(FakeListChatModel(responses=[answer]))
    result = generator.build().invoke(
        {
            "generation_context": {
                "question": "Dúvida sintética?",
                "context": "[1] Fonte A\n[2] Fonte B",
                "limitation": "nenhuma",
                "chat_history": [],
            },
            "source_chunks": [{"chunk_text": "Fonte A"}, {"chunk_text": "Fonte B"}],
            "response_diagnostics": {},
        }
    )
    assert result["answer"] == answer  # Never rewrite the original model wording.
    assert result["response_diagnostics"]["citation_validation"] == "passed"
    assert len(result["source_chunks"]) == 2


@pytest.mark.parametrize(
    "marker", ["[3]", "[1,3]", "[1] [2,99]", "[0]", "[1,0]", "[1, 999999]"]
)
def test_any_unknown_source_rejects_the_whole_answer(marker: str) -> None:
    with pytest.raises(GroundedGenerationError, match="unknown_source_citation"):
        GroundedAnswerGenerator.validate_source_citations(f"Texto {marker}.", 2)


@pytest.mark.parametrize(
    "marker",
    ["[1,]", "[1,,2]", "[1;2]", "[1-2]", "[1,abc]", "[abc,2]", "[-1]", "[1,\n2]"],
)
def test_valid_reference_does_not_hide_malformed_numeric_marker(marker: str) -> None:
    with pytest.raises(GroundedGenerationError, match="malformed_source_citation"):
        GroundedAnswerGenerator.validate_source_citations(f"Texto [1] e {marker}.", 2)


@pytest.mark.parametrize(
    "answer", ["Texto sem referência.", "Texto [observação].", "Texto [E1]."]
)
def test_absence_of_numeric_source_reference_remains_a_failure(answer: str) -> None:
    with pytest.raises(GroundedGenerationError, match="missing_source_citation"):
        GroundedAnswerGenerator.validate_source_citations(answer, 2)


def test_bracketed_prose_does_not_invent_an_additional_source() -> None:
    GroundedAnswerGenerator.validate_source_citations("Texto [observação] [1].", 1)


def test_citation_cannot_succeed_without_sources() -> None:
    with pytest.raises(GroundedGenerationError, match="unknown_source_citation"):
        GroundedAnswerGenerator.validate_source_citations("Texto [1].", 0)
