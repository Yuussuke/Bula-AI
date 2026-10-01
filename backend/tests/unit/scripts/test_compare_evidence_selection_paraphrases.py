"""Offline safeguards for a question-only experiment; no model calls."""

import json

import pytest

from scripts.benchmark_evidence_selection import (
    DEFAULT_FIXTURES,
    build_selector_messages,
    load_cases,
)
from scripts.compare_evidence_selection_paraphrases import prepare_pairs


def load_annotations() -> list[dict[str, str]]:
    return json.loads(
        DEFAULT_FIXTURES.with_name("evidence_selection_paraphrases.json").read_text(
            encoding="utf-8"
        )
    )


def test_only_question_changes_and_no_annotations_reach_model() -> None:
    cases = load_cases()
    before = [case.model_dump() for case in cases]
    annotations = load_annotations()
    for annotation in annotations:
        annotation["review"] = "PRIVATE_SEMANTIC_REVIEW"
    pairs = prepare_pairs(cases, annotations)
    assert len(pairs) == 12
    for (original, variant), annotation in zip(pairs, annotations, strict=True):
        assert original.model_dump(exclude={"question"}) == variant.model_dump(
            exclude={"question"}
        )
        messages = build_selector_messages(variant)
        text = "\n".join(str(message.content) for message in messages)
        assert annotation["paraphrase"] in text
        assert original.question not in text
        assert "PRIVATE_SEMANTIC_REVIEW" not in text
        assert original.annotation_notes not in text
    assert [case.model_dump() for case in cases] == before


@pytest.mark.parametrize("field", ["case_id", "original_question"])
def test_manifest_mismatch_stops_experiment(field: str) -> None:
    annotations = load_annotations()
    annotations[0][field] = "changed"
    with pytest.raises(ValueError, match="manifest"):
        prepare_pairs(load_cases(), annotations)


def test_missing_variant_is_rejected_instead_of_reducing_sample() -> None:
    with pytest.raises(ValueError, match="12"):
        prepare_pairs(load_cases(), load_annotations()[:-1])
