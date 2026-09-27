"""Build cautious patient answers from verified excerpts of one selected bula."""

import json
import re
import unicodedata
from dataclasses import dataclass

from langchain_core.documents import Document
from pydantic import BaseModel, ConfigDict, Field, ValidationError


HIGH_RISK_QUESTION_PATTERN = re.compile(
    r"\b(?:alerg\w*|hipersensib\w*|contraindic\w*|dose\w*|dosagem\w*|"
    r"posolog\w*|gravidez|gravid\w*|amament\w*|crianc\w*|pediatric\w*|"
    r"intera\w*|reac\w*|efeitos? adversos?|segur\w*)\b"
    r"|\b(?:quem|quando) nao (?:pode|deve|posso|devo) usar\b"
    r"|\b(?:posso|pode|devo|deve) (?:tomar|usar)\b"
)
ALLERGY_TARGET_PATTERN = re.compile(
    r"\b(?:alerg\w*|hipersensib\w*)\s+(?:a|as|ao|aos|de)\s+(\w+)"
)
FOLLOW_UP_TARGET_PATTERN = re.compile(r"^(?:e|mas e)\s+(?:a|as|ao|aos)\s+(\w+)")
MAX_EVIDENCE_ITEMS = 2


class SafetyEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_number: int = Field(strict=True, ge=1)
    quote: str = Field(min_length=8, max_length=600)


class SafetyEvidenceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: list[SafetyEvidenceItem] = Field(max_length=MAX_EVIDENCE_ITEMS)


@dataclass(frozen=True)
class ExtractiveSafetyAnswer:
    answer: str
    documents: list[Document]


def is_high_risk_question(question: str) -> bool:
    return HIGH_RISK_QUESTION_PATTERN.search(_without_accents(question)) is not None


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
    """Select a complete statement mentioning the named allergen, without an LLM."""
    allergy_target = _get_allergy_target(
        question=question, previous_question=previous_question
    )
    if allergy_target is None:
        return _encode_selection(source_number=None, quote=None)

    indexed_documents = list(enumerate(documents, start=1))
    indexed_documents.sort(key=lambda item: _allergy_section_priority(item[1]))

    for source_number, document in indexed_documents:
        for statement in _source_statements(document.page_content):
            if len(statement) < 8 or len(statement) > 600:
                continue
            if _contains_multiple_sentences(statement):
                continue
            if not _contains_target(statement, allergy_target):
                continue
            return _encode_selection(source_number=source_number, quote=statement)

    return _encode_selection(source_number=None, quote=None)


def build_extractive_safety_answer(
    *,
    raw_response: str,
    documents: list[Document],
    question: str,
    previous_question: str | None = None,
) -> ExtractiveSafetyAnswer | None:
    """Fail closed if the model's selected text is not in the cited chunk."""
    try:
        selection = SafetyEvidenceSelection.model_validate_json(raw_response)
    except ValidationError:
        return None

    if not selection.evidence:
        return None

    allergy_target = _get_allergy_target(
        question=question, previous_question=previous_question
    )
    verified_evidence: list[tuple[int, str, Document]] = []
    seen_quotes: set[tuple[int, str]] = set()

    for evidence in selection.evidence:
        if evidence.source_number > len(documents):
            return None

        document = documents[evidence.source_number - 1]
        quote = _collapse_whitespace(evidence.quote)
        section_title = str(document.metadata.get("section_title", "")).strip()

        if not _is_complete_source_statement(
            quote=quote, source_text=document.page_content
        ):
            return None
        if _contains_multiple_sentences(quote):
            return None
        if _without_accents(quote.lstrip("# ")) == _without_accents(section_title):
            return None
        if allergy_target and not _contains_target(quote, allergy_target):
            return None

        quote_identity = (evidence.source_number, quote)
        if quote_identity in seen_quotes:
            continue

        seen_quotes.add(quote_identity)
        verified_evidence.append((evidence.source_number, quote, document))

    if not verified_evidence:
        return None

    answer_lines: list[str] = []
    cited_documents: list[Document] = []
    displayed_numbers_by_source: dict[int, int] = {}
    for source_number, quote, document in verified_evidence:
        section_title = str(document.metadata.get("section_title", "")).strip()
        displayed_number = displayed_numbers_by_source.get(source_number)
        if displayed_number is None:
            displayed_number = len(cited_documents) + 1
            displayed_numbers_by_source[source_number] = displayed_number
            cited_documents.append(document)
        answer_lines.append(
            f'Na seção "{section_title}", a bula informa:\n\n'
            f'> "{quote}" [{displayed_number}]'
        )

    answer_lines.append(
        "Esses trechos não determinam, sozinhos, se o medicamento é adequado "
        "ao seu caso. Consulte um médico ou farmacêutico antes de usá-lo."
    )
    return ExtractiveSafetyAnswer(
        answer="\n\n".join(answer_lines), documents=cited_documents
    )


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
    normalized_target = target.rstrip("s")
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


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _contains_multiple_sentences(quote: str) -> bool:
    return re.search(r"[.!?]\s+\S", quote) is not None


def _is_complete_source_statement(*, quote: str, source_text: str) -> bool:
    return quote in _source_statements(source_text)


def _source_statements(source_text: str) -> list[str]:
    statements: list[str] = []
    for paragraph in re.split(r"\n\s*\n", source_text):
        content_lines = [
            line
            for line in paragraph.splitlines()
            if not re.match(r"^\s{0,3}#{1,6}\s", line)
        ]
        if not content_lines:
            continue

        for line in content_lines:
            is_structured_line = line.lstrip().startswith(("|", "- ", "* "))
            if is_structured_line:
                statements.append(_collapse_whitespace(line))

        paragraph_text = _collapse_whitespace(" ".join(content_lines))
        statements.extend(re.split(r"(?<=[.!?])\s+(?=\S)", paragraph_text))

    return statements


def _allergy_section_priority(document: Document) -> int:
    section_title = _without_accents(str(document.metadata.get("section_title", "")))
    if "contraindic" in section_title or "quando nao devo usar" in section_title:
        return 0
    return 1


def _encode_selection(*, source_number: int | None, quote: str | None) -> str:
    if source_number is None or quote is None:
        return json.dumps({"evidence": []})
    return json.dumps(
        {"evidence": [{"source_number": source_number, "quote": quote}]},
        ensure_ascii=False,
    )


def _without_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
