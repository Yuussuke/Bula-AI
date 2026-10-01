"""Build cautious patient answers from verified excerpts of one selected bula."""

import json
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from langchain_core.documents import Document
from pydantic import ValidationError

from app.modules.rag.context_assessment import (
    ContextAssessment,
    EvidenceAssessmentDecoder,
    EvidenceLimitation,
    EvidenceSupport,
)

from app.modules.rag.evidence_units import EvidenceUnit, build_evidence_units


ALLERGY_TARGET_PATTERN = re.compile(
    r"\b(?:alerg\w*|hipersensib\w*)\s+(?:a|as|ao|aos|de)\s+"
    r"([\w-]+(?:\s+[\w-]+){0,2})(?=[.,;?!]|$)"
)
FOLLOW_UP_TARGET_PATTERN = re.compile(r"^(?:e|mas e)\s+(?:a|as|ao|aos)\s+(\w+)")
EXPLICIT_RESTRICTION_PATTERN = re.compile(
    r"\b(?:nao\s+(?:(?:e|sao)\s+)?(?:utiliz\w*|us\w*|tom\w*|"
    r"recomend\w*|indicad\w*)|"
    r"contraindic\w*|proibid\w*)\b"
)
NEGATED_RESTRICTION_PATTERN = re.compile(
    r"\bnao\s+(?:e|sao)\s+(?:contraindic\w*|proibid\w*)\b"
)
PERMISSION_QUESTION_PATTERN = re.compile(
    r"\b(?:posso|pode|podem|devo|deve|proibid\w*|segur\w*)\b"
)
CAUTION_ONLY_PATTERN = re.compile(
    r"\b(?:inform\w*|consult\w*|convers\w*|cautel\w*|"
    r"avali\w*|pesquisa cuidadosa|pode causar)\b"
)


@dataclass(frozen=True)
class ExtractiveSafetyAnswer:
    answer: str
    documents: list[Document]
    support: EvidenceSupport


class EvidenceRejectionReason(StrEnum):
    INVALID_JSON = "invalid_json"
    INVALID_SELECTION_SCHEMA = "invalid_selection_schema"
    UNKNOWN_EVIDENCE_ID = "unknown_evidence_id"
    ALLERGY_TARGET_MISMATCH = "allergy_target_mismatch"
    EMPTY_VERIFIED_EVIDENCE = "empty_verified_evidence"


@dataclass(frozen=True)
class EvidenceValidationResult:
    answer: ExtractiveSafetyAnswer | None = None
    rejection_reason: EvidenceRejectionReason | None = None
    assessment: ContextAssessment | None = None
    validation_error: json.JSONDecodeError | ValidationError | None = None

    def error_details(self) -> dict[str, object]:
        """Describe original failures without logging input or exception prose."""
        if isinstance(self.validation_error, json.JSONDecodeError):
            return {
                "error_type": "JSONDecodeError",
                "json_line": self.validation_error.lineno,
                "json_column": self.validation_error.colno,
                "json_reason": self.validation_error.msg,
            }
        if isinstance(self.validation_error, ValidationError):
            issues = []
            for issue in self.validation_error.errors(include_input=False):
                # Unknown keys may contain arbitrary provider output.
                location = [
                    part
                    if part in {"unit_ids", "limitation"} or isinstance(part, int)
                    else "<unknown_field>"
                    for part in issue["loc"]
                ]
                issues.append({"location": location, "type": issue["type"]})
            return {"error_type": "ValidationError", "issues": issues}
        return {}


def has_specific_allergy_target(
    *, question: str, previous_question: str | None
) -> bool:
    return (
        _get_allergy_target(question=question, previous_question=previous_question)
        is not None
    )


def select_allergy_evidence(
    *, documents: list[Document], question: str, previous_question: str | None
) -> str:
    """Select one source-derived unit mentioning the named allergen, without an LLM."""
    allergy_target = _get_allergy_target(
        question=question, previous_question=previous_question
    )
    if allergy_target is None:
        return _encode_selection(unit_id=None, support=EvidenceSupport.INSUFFICIENT)

    units = build_evidence_units(documents)
    units.sort(key=lambda unit: _allergy_section_priority(unit.document))

    candidates: list[tuple[int, EvidenceUnit]] = []
    for unit in units:
        if not _contains_target(unit.text, allergy_target):
            continue
        restriction_priority = int(_has_explicit_restriction(unit.text))
        candidates.append((restriction_priority, unit))

    if not candidates:
        return _encode_selection(unit_id=None, support=EvidenceSupport.INSUFFICIENT)

    # A direct restriction takes precedence over a cautionary mention of the
    # same allergen. Equal-ranked candidates retain source/section order.
    restriction_priority, selected_unit = max(
        candidates, key=lambda candidate: candidate[0]
    )
    support = (
        EvidenceSupport.SUPPORTED
        if restriction_priority
        else EvidenceSupport.PARTIALLY_SUPPORTED
    )
    return _encode_selection(unit_id=selected_unit.unit_id, support=support)


def validate_extractive_safety_answer(
    *,
    raw_response: str,
    documents: list[Document],
    question: str,
    previous_question: str | None = None,
) -> EvidenceValidationResult:
    """Resolve model-selected IDs to source-owned text, failing closed on invalid IDs."""
    try:
        selection = EvidenceAssessmentDecoder().decode(raw_response)
    except json.JSONDecodeError as error:
        return EvidenceValidationResult(
            rejection_reason=EvidenceRejectionReason.INVALID_JSON,
            validation_error=error,
        )
    except ValidationError as error:
        return EvidenceValidationResult(
            rejection_reason=EvidenceRejectionReason.INVALID_SELECTION_SCHEMA,
            validation_error=error,
        )

    if not selection.unit_ids:
        return EvidenceValidationResult(
            answer=ExtractiveSafetyAnswer(
                answer="", documents=[], support=EvidenceSupport.INSUFFICIENT
            ),
            assessment=selection,
        )

    units_by_id = {unit.unit_id: unit for unit in build_evidence_units(documents)}
    allergy_target = _get_allergy_target(
        question=question, previous_question=previous_question
    )
    verified_evidence: list[EvidenceUnit] = []
    seen_unit_ids: set[str] = set()

    for unit_id in selection.unit_ids:
        unit = units_by_id.get(unit_id)
        if unit is None:
            return EvidenceValidationResult(
                rejection_reason=EvidenceRejectionReason.UNKNOWN_EVIDENCE_ID
            )
        if allergy_target and not _contains_target(unit.text, allergy_target):
            return EvidenceValidationResult(
                rejection_reason=EvidenceRejectionReason.ALLERGY_TARGET_MISMATCH
            )
        if unit_id in seen_unit_ids:
            continue
        seen_unit_ids.add(unit_id)
        verified_evidence.append(unit)

    if not verified_evidence:
        return EvidenceValidationResult(
            rejection_reason=EvidenceRejectionReason.EMPTY_VERIFIED_EVIDENCE
        )

    support = selection.support
    if (
        support is EvidenceSupport.SUPPORTED
        and PERMISSION_QUESTION_PATTERN.search(_without_accents(question))
        and any(_is_caution_only(unit.text) for unit in verified_evidence)
    ):
        has_explicit_restriction = any(
            _has_explicit_restriction(unit.text) for unit in verified_evidence
        )
        if not has_explicit_restriction:
            support = EvidenceSupport.PARTIALLY_SUPPORTED
            selection = selection.model_copy(
                update={"limitation": EvidenceLimitation.INDIVIDUAL}
            )

    answer_lines: list[str] = []
    selected_source_numbers = {unit.source_number for unit in verified_evidence}
    ranked_source_numbers = sorted(
        sorted(selected_source_numbers),
        key=lambda source_number: _get_relevance_score(documents[source_number - 1]),
        reverse=True,
    )
    cited_documents = [documents[number - 1] for number in ranked_source_numbers]
    displayed_numbers_by_source = {
        source_number: displayed_number
        for displayed_number, source_number in enumerate(ranked_source_numbers, start=1)
    }
    previous_source_number: int | None = None
    for unit in verified_evidence:
        displayed_number = displayed_numbers_by_source[unit.source_number]
        if unit.source_number != previous_source_number:
            section_title = unit.section_title or "Seção não identificada"
            answer_lines.append(f'Na seção "{section_title}", a bula informa:')
        previous_source_number = unit.source_number
        quoted_lines = "\n".join(f"> {line}" for line in unit.text.splitlines())
        answer_lines.append(f"{quoted_lines} [{displayed_number}]")

    if support is EvidenceSupport.PARTIALLY_SUPPORTED:
        if selection.limitation is EvidenceLimitation.INDIVIDUAL:
            answer_lines.append(
                "O trecho é relacionado à pergunta, mas não basta para concluir "
                "se esta apresentação é adequada ao seu caso. Consulte um médico "
                "ou farmacêutico antes de usá-la."
            )
        elif selection.limitation is EvidenceLimitation.SCOPE:
            answer_lines.append(
                "O trecho informa o que a bula descreve, mas não estabelece a "
                "finalidade ou conclusão sugerida na pergunta. Isso não constitui "
                "uma avaliação individual de uso do medicamento."
            )
        else:
            answer_lines.append(
                "Os trechos respondem parte da pergunta, mas não sustentam "
                "todas as conclusões solicitadas. Consulte a bula completa ou "
                "um profissional de saúde para esclarecer o que falta."
            )
    return EvidenceValidationResult(
        answer=ExtractiveSafetyAnswer(
            answer="\n\n".join(answer_lines), documents=cited_documents, support=support
        ),
        assessment=selection,
    )


def _get_relevance_score(document: Document) -> float:
    try:
        return float(document.metadata.get("score", 0.0))
    except TypeError, ValueError:
        return 0.0


def _get_allergy_target(*, question: str, previous_question: str | None) -> str | None:
    current_target = _get_explicit_allergy_target(question)
    if current_target is not None:
        return current_target

    if previous_question is None or not _get_explicit_allergy_target(previous_question):
        return None

    follow_up_match = FOLLOW_UP_TARGET_PATTERN.search(_without_accents(question))
    if follow_up_match is not None:
        return _normalize_target(follow_up_match.group(1))

    return _get_explicit_allergy_target(previous_question)


def _get_explicit_allergy_target(question: str) -> str | None:
    target_matches = list(ALLERGY_TARGET_PATTERN.finditer(_without_accents(question)))
    if not target_matches:
        return None
    return _normalize_target(target_matches[-1].group(1))


def _normalize_target(target: str) -> str | None:
    normalized_target = target.strip().rstrip("s")
    if len(normalized_target) < 5 or normalized_target in {
        "medicamento",
        "remedio",
        "substancia",
    }:
        return None
    return normalized_target


def _contains_target(quote: str, target: str) -> bool:
    normalized_quote = _without_accents(quote)
    return re.search(rf"\b{re.escape(target)}s?\b", normalized_quote) is not None


def _has_explicit_restriction(statement: str) -> bool:
    normalized_statement = _without_accents(statement)
    if NEGATED_RESTRICTION_PATTERN.search(normalized_statement):
        return False
    return EXPLICIT_RESTRICTION_PATTERN.search(normalized_statement) is not None


def _is_caution_only(statement: str) -> bool:
    return CAUTION_ONLY_PATTERN.search(_without_accents(statement)) is not None


def _allergy_section_priority(document: Document) -> int:
    section_title = _without_accents(str(document.metadata.get("section_title", "")))
    if "contraindic" in section_title or "quando nao devo usar" in section_title:
        return 0
    return 1


def _encode_selection(*, unit_id: str | None, support: EvidenceSupport) -> str:
    return ContextAssessment(
        unit_ids=[unit_id] if unit_id is not None else [],
        limitation=EvidenceLimitation.INDIVIDUAL
        if support is EvidenceSupport.PARTIALLY_SUPPORTED
        else None,
    ).model_dump_json()


def _without_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
