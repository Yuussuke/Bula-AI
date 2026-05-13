from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pytest
from sacrebleu import corpus_bleu

from app.modules.rag.parsers.pdf_parser import BulaParser


FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "rag"


@dataclass(frozen=True)
class GoldenFixture:
    name: str
    minimum_bleu: float
    minimum_token_f1: float

    @property
    def pdf_path(self) -> Path:
        return FIXTURE_ROOT / "bulas" / f"{self.name}.pdf"

    @property
    def reference_path(self) -> Path:
        return FIXTURE_ROOT / "references" / f"{self.name}.md"


GOLDEN_FIXTURES = (
    GoldenFixture(
        name="dipirona_sanofi_medley_solucao_oral",
        minimum_bleu=75.0,
        minimum_token_f1=0.95,
    ),
    GoldenFixture(
        name="amoxicilina_cimed_suspensao_oral",
        minimum_bleu=75.0,
        minimum_token_f1=0.95,
    ),
    GoldenFixture(
        name="nesina_met_cosmed_comprimido_revestido",
        minimum_bleu=75.0,
        minimum_token_f1=0.95,
    ),
)


@pytest.mark.anyio
@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=lambda item: item.name)
async def test_bula_parser_matches_golden_markdown(fixture: GoldenFixture) -> None:
    parser = BulaParser()
    result = await parser.parse(
        pdf_bytes=fixture.pdf_path.read_bytes(),
        filename=fixture.pdf_path.name,
    )
    reference_markdown = fixture.reference_path.read_text(encoding="utf-8").strip()

    assert result.success is True

    hypothesis_markdown = result.markdown.strip()
    bleu_score = corpus_bleu(
        [hypothesis_markdown],
        [[reference_markdown]],
    ).score
    token_f1 = multiset_token_f1(
        hypothesis=hypothesis_markdown,
        reference=reference_markdown,
    )
    combined_score = (bleu_score / 100 + token_f1) / 2

    assert bleu_score >= fixture.minimum_bleu, (
        f"{fixture.name} BLEU={bleu_score:.2f}, "
        f"token_f1={token_f1:.4f}, combined={combined_score:.4f}. "
        "Thresholds are relaxed parser-regression baselines, not final quality "
        "targets; recalibrate them after intentional reference refreshes."
    )
    assert token_f1 >= fixture.minimum_token_f1, (
        f"{fixture.name} BLEU={bleu_score:.2f}, "
        f"token_f1={token_f1:.4f}, combined={combined_score:.4f}. "
        "Thresholds are relaxed parser-regression baselines, not final quality "
        "targets; recalibrate them after intentional reference refreshes."
    )


def multiset_token_f1(*, hypothesis: str, reference: str) -> float:
    hypothesis_tokens = hypothesis.split()
    reference_tokens = reference.split()

    if not hypothesis_tokens and not reference_tokens:
        return 1.0

    if not hypothesis_tokens or not reference_tokens:
        return 0.0

    hypothesis_counts = Counter(hypothesis_tokens)
    reference_counts = Counter(reference_tokens)
    overlap_count = sum(
        min(count, reference_counts[token])
        for token, count in hypothesis_counts.items()
    )

    precision = overlap_count / len(hypothesis_tokens)
    recall = overlap_count / len(reference_tokens)

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)
