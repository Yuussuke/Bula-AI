import pytest
from langchain_core.documents import Document

from app.modules.rag.extractive_safety_answer import (
    EvidenceRejectionReason,
    EvidenceSupport,
    validate_extractive_safety_answer,
)


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        ("not JSON", EvidenceRejectionReason.INVALID_JSON),
        (
            '{"limitation":"magic","unit_ids":[]}',
            EvidenceRejectionReason.INVALID_SELECTION_SCHEMA,
        ),
        (
            '{"limitation":null,"unit_ids":"E1"}',
            EvidenceRejectionReason.INVALID_SELECTION_SCHEMA,
        ),
        (
            '{"support":"insufficient","unit_ids":["E1"]}',
            EvidenceRejectionReason.INVALID_SELECTION_SCHEMA,
        ),
        (
            '{"limitation":null,"unit_ids":["E99"]}',
            EvidenceRejectionReason.UNKNOWN_EVIDENCE_ID,
        ),
    ],
)
def test_rejected_selection_has_specific_reason(
    response: str, reason: EvidenceRejectionReason
) -> None:
    result = validate_extractive_safety_answer(
        raw_response=response,
        documents=[Document(page_content="Indicado para infecções bacterianas.")],
        question="Esse antibiótico trata virose, certo?",
    )
    assert result.answer is None
    assert result.rejection_reason is reason


def test_valid_insufficiency_is_not_a_contract_failure() -> None:
    result = validate_extractive_safety_answer(
        raw_response='{"limitation":null,"unit_ids":[]}',
        documents=[Document(page_content="Indicado para infecções bacterianas.")],
        question="Sou diabético. Posso usar?",
    )
    assert result.rejection_reason is None
    assert result.answer is not None
    assert result.answer.support is EvidenceSupport.INSUFFICIENT


def test_allergy_target_mismatch_has_its_own_reason() -> None:
    result = validate_extractive_safety_answer(
        raw_response='{"limitation":null,"unit_ids":["E1"]}',
        documents=[Document(page_content="Informe alergia a penicilinas.")],
        question="Tenho alergia a cefalosporinas.",
    )
    assert result.rejection_reason is EvidenceRejectionReason.ALLERGY_TARGET_MISMATCH
