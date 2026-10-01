import json

import pytest
from langchain_core.documents import Document
from pydantic import ValidationError

from app.modules.rag.context_assessment import (
    ContextAssessment,
    EvidenceAssessmentDecoder,
)
from app.modules.rag.extractive_safety_answer import (
    EvidenceRejectionReason,
    EvidenceSupport,
    validate_extractive_safety_answer,
)


SOURCE = "Este medicamento é indicado para infecções bacterianas."


def selection_response(
    *, unit_ids: list[str] | None = None, limitation: str | None = None
) -> str:
    return json.dumps(
        {"unit_ids": ["E1"] if unit_ids is None else unit_ids, "limitation": limitation}
    )


@pytest.mark.parametrize(
    "question",
    [
        "Esse medicamento trata virose?",
        "A indicação descrita é para infecções por vírus?",
        "A indicação apresentada é para aliviar dor de cabeça?",
    ],
)
def test_scope_clarification_returns_source_and_limitation(question: str) -> None:
    result = validate_extractive_safety_answer(
        raw_response=selection_response(limitation="scope"),
        documents=[Document(page_content=SOURCE)],
        question=question,
    )
    assert result.answer is not None
    assert result.answer.support is EvidenceSupport.PARTIALLY_SUPPORTED
    assert SOURCE in result.answer.answer
    assert "não estabelece" in result.answer.answer
    assert "Consulte um médico" not in result.answer.answer


@pytest.mark.parametrize(
    "source, question",
    [
        (
            "Os comprimidos não são recomendados para menores de 12 anos.",
            "Uma criança de 5 anos pode usar este comprimido?",
        ),
        (
            "O uso no segundo trimestre depende de avaliação médica.",
            "O que a bula informa sobre o segundo trimestre?",
        ),
    ],
)
def test_documentary_answer_does_not_require_unsolicited_individual_details(
    source: str, question: str
) -> None:
    result = validate_extractive_safety_answer(
        raw_response=selection_response(),
        documents=[Document(page_content=source)],
        question=question,
    )
    assert result.answer is not None
    assert result.answer.support is EvidenceSupport.SUPPORTED
    assert source in result.answer.answer
    assert "não basta" not in result.answer.answer


def test_requested_individual_authorization_keeps_limitation() -> None:
    result = validate_extractive_safety_answer(
        raw_response=selection_response(limitation="individual"),
        documents=[Document(page_content="O uso depende de avaliação médica.")],
        question="Está liberado usar?",
    )
    assert result.answer is not None
    assert result.answer.support is EvidenceSupport.PARTIALLY_SUPPORTED
    assert "não basta para concluir" in result.answer.answer


def test_missing_required_part_is_distinct_from_individual_authorization() -> None:
    result = validate_extractive_safety_answer(
        raw_response=selection_response(limitation="missing"),
        documents=[Document(page_content=SOURCE)],
        question="Qual a indicação e o prazo de tratamento?",
    )
    assert result.answer is not None
    assert "parte da pergunta" in result.answer.answer
    assert "adequada ao seu caso" not in result.answer.answer


@pytest.mark.parametrize("limitation", [None, "scope", "individual", "missing"])
def test_no_selected_evidence_abstains_without_contract_failure(
    limitation: str | None,
) -> None:
    result = validate_extractive_safety_answer(
        raw_response=selection_response(unit_ids=[], limitation=limitation),
        documents=[Document(page_content=SOURCE)],
        question="Sou diabético. Posso tomar?",
    )
    assert result.rejection_reason is None
    assert result.answer is not None
    assert result.answer.support is EvidenceSupport.INSUFFICIENT
    assert result.answer.documents == []


@pytest.mark.parametrize(
    "response",
    [
        '{"support":"supported","unit_ids":["E1"]}',
        '{"answerable":[],"missing":[]}',
        '{"unit_ids":["E1"]}',
        '{"unit_ids":["E1"],"limitation":null,"statement":"PRIVATE"}',
        selection_response(limitation="unsupported"),
    ],
)
def test_only_the_compact_contract_is_accepted(response: str) -> None:
    result = validate_extractive_safety_answer(
        raw_response=response,
        documents=[Document(page_content=SOURCE)],
        question="Qual indicação?",
    )
    assert result.answer is None
    assert result.rejection_reason is EvidenceRejectionReason.INVALID_SELECTION_SCHEMA


def test_original_schema_error_is_not_replaced_by_a_legacy_attempt() -> None:
    response = selection_response(limitation="unsupported")
    with pytest.raises(ValidationError) as original:
        EvidenceAssessmentDecoder().decode(response)
    assert [(issue["loc"], issue["type"]) for issue in original.value.errors()] == [
        (("limitation",), "enum")
    ]
    result = validate_extractive_safety_answer(
        raw_response=response, documents=[], question="Teste"
    )
    assert result.error_details() == {
        "error_type": "ValidationError",
        "issues": [{"location": ["limitation"], "type": "enum"}],
    }
    assert "unsupported" not in str(result.error_details())


def test_unquoted_selection_is_a_json_error_not_insufficient_evidence() -> None:
    result = validate_extractive_safety_answer(
        raw_response="unit_ids: [E1]\nlimitation: null",
        documents=[Document(page_content=SOURCE)],
        question="Qual a indicação?",
    )
    assert result.answer is None
    assert result.rejection_reason is EvidenceRejectionReason.INVALID_JSON
    assert isinstance(result.validation_error, json.JSONDecodeError)
    assert result.error_details()["json_reason"] == "Expecting value"


def test_provider_schema_subset_keeps_local_selection_bound() -> None:
    response_format = ContextAssessment.provider_response_format()
    assert response_format["type"] == "json_schema"
    # Only the wire schema omits an unsupported array keyword.
    assert "maxItems" not in str(response_format)
    assert (
        ContextAssessment.model_json_schema()["properties"]["unit_ids"]["maxItems"] == 6
    )


def test_unknown_id_rejects_the_whole_selection() -> None:
    result = validate_extractive_safety_answer(
        raw_response=selection_response(unit_ids=["E1", "E99"]),
        documents=[Document(page_content=SOURCE)],
        question="Qual indicação?",
    )
    assert result.answer is None
    assert result.rejection_reason is EvidenceRejectionReason.UNKNOWN_EVIDENCE_ID


def test_one_global_id_limit_has_no_second_conversion_limit() -> None:
    documents = [Document(page_content="Um. Dois. Três. Quatro. Cinco. Seis.")]
    valid = validate_extractive_safety_answer(
        raw_response=selection_response(
            unit_ids=[f"E{index}" for index in range(1, 7)]
        ),
        documents=documents,
        question="Resumo?",
    )
    assert valid.answer is not None
    invalid = validate_extractive_safety_answer(
        raw_response=selection_response(
            unit_ids=[f"E{index}" for index in range(1, 8)]
        ),
        documents=documents,
        question="Resumo?",
    )
    assert invalid.rejection_reason is EvidenceRejectionReason.INVALID_SELECTION_SCHEMA
    assert invalid.error_details()["issues"] == [
        {"location": ["unit_ids"], "type": "too_long"}
    ]


@pytest.mark.parametrize("fence", ["```json", "```"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_complete_envelope_is_equivalent_to_plain_json(
    fence: str, newline: str
) -> None:
    response = selection_response()
    documents = [Document(page_content=SOURCE)]
    plain = validate_extractive_safety_answer(
        raw_response=response, documents=documents, question="Indicação?"
    )
    fenced = validate_extractive_safety_answer(
        raw_response=f"  {newline}{fence}{newline}{response}{newline}```{newline} ",
        documents=documents,
        question="Indicação?",
    )
    assert plain.answer is not None
    assert fenced == plain


@pytest.mark.parametrize(
    "template",
    [
        "Explanation\n```json\n{response}\n```",
        "```json\n{response}\n```\nExplanation",
        "```json\n{response}\n```\n```json\n{response}\n```",
        "```json\n{response}",
        "```python\n{response}\n```",
        "```json {response} ```",
        "```json\n{response}\n{response}\n```",
        '```json\n{"unit_ids":',
    ],
)
def test_envelope_never_repairs_or_extracts_json_fragments(template: str) -> None:
    response = template.replace("{response}", selection_response())
    result = validate_extractive_safety_answer(
        raw_response=response,
        documents=[Document(page_content=SOURCE)],
        question="Indicação?",
    )
    assert result.answer is None
    assert result.rejection_reason is EvidenceRejectionReason.INVALID_JSON
    assert isinstance(result.validation_error, json.JSONDecodeError)
    assert result.error_details()["json_line"] >= 1
    assert result.error_details()["json_column"] >= 1
    assert isinstance(result.error_details()["json_reason"], str)
