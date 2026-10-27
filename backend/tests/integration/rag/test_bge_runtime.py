"""Opt-in infrastructure smoke: local weights/CUDA, synthetic non-medical text."""

import math
import os
from pathlib import Path

import pytest

from app.modules.rag.bge_engine import BGEEngine
from app.modules.rag.reranker import ResidentReranker, RerankerError


@pytest.mark.anyio
@pytest.mark.skipif(
    not os.environ.get("BGE_TEST_MODEL_PATH"),
    reason="Local BGE assets and CUDA required",
)
async def test_native_python_runtime_loads_once_and_scores_complete_pairs() -> None:
    service = ResidentReranker(
        load_scorer=lambda: BGEEngine(Path(os.environ["BGE_TEST_MODEL_PATH"]))
    )
    try:
        await service.warmup()
        scores = await service.score(
            "Qual o horário de funcionamento?",
            [
                "Seção: Horários\n\nO estabelecimento funciona das nove às dezoito horas.",
                "Seção: Endereço\n\nA biblioteca fica na rua central.",
            ],
        )
        assert len(scores) == 2
        assert all(math.isfinite(score) for score in scores)
        with pytest.raises(RerankerError, match="truncation is disabled"):
            await service.score("Horário?", ["palavra " * 9000])
    finally:
        await service.close()
