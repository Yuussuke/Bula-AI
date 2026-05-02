from typing import cast

import pytest
from openai import AsyncOpenAI

from app.core.config import OpenRouterSettings, ProcessingSettings, Settings
from app.modules.rag.base_chunker import BaseChunker
from app.modules.rag.chunker import BulaChunker
from app.modules.rag.dependencies import get_chunker, get_ingestion_service
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.service import RAGIngestionService


class FakeOpenAIClient:
    pass


def build_settings(
    *,
    api_key: str | None = "openrouter-test-key",
    chunk_model: str = "primary-model",
    chunk_fallback_model: str = "fallback-model",
    require_zdr: bool = True,
) -> Settings:
    return Settings(
        secret_key="long_and_secure_secret_key_for_testing_purposes_only_1234567890",
        openrouter=OpenRouterSettings(
            api_key=api_key,
            chunk_model=chunk_model,
            chunk_fallback_model=chunk_fallback_model,
            require_zdr=require_zdr,
        ),
        processing=ProcessingSettings(
            chunk_target_tokens=20,
            chunk_min_tokens=1,
            chunk_max_tokens=50,
            chunk_overlap_ratio=0.0,
            chunk_max_concurrency=2,
        ),
    )


def test_get_chunker_returns_bula_chunker_as_base_chunker() -> None:
    fake_llm = cast(AsyncOpenAI, FakeOpenAIClient())
    settings = build_settings()

    chunker = get_chunker(llm=fake_llm, settings=settings)

    assert isinstance(chunker, BaseChunker)
    assert isinstance(chunker, BulaChunker)
    assert chunker.llm is fake_llm
    assert chunker.config.is_llm_enabled is True


def test_get_chunker_disables_llm_when_openrouter_key_is_missing() -> None:
    fake_llm = cast(AsyncOpenAI, FakeOpenAIClient())
    settings = build_settings(api_key=None)

    chunker = get_chunker(llm=fake_llm, settings=settings)

    assert chunker.config.is_llm_enabled is False


def test_get_chunker_rejects_free_primary_model_when_zdr_is_required() -> None:
    fake_llm = cast(AsyncOpenAI, FakeOpenAIClient())
    settings = build_settings(chunk_model="provider/model:free")

    with pytest.raises(ValueError, match="Free model variants"):
        get_chunker(llm=fake_llm, settings=settings)


def test_get_chunker_rejects_free_fallback_model_when_zdr_is_required() -> None:
    fake_llm = cast(AsyncOpenAI, FakeOpenAIClient())
    settings = build_settings(chunk_fallback_model="provider/fallback:free")

    with pytest.raises(ValueError, match="Free model variants"):
        get_chunker(llm=fake_llm, settings=settings)


def test_get_ingestion_service_receives_base_chunker() -> None:
    fake_llm = cast(AsyncOpenAI, FakeOpenAIClient())
    chunker = get_chunker(llm=fake_llm, settings=build_settings())
    parser = BulaParser(ocr_enabled=False)

    service = get_ingestion_service(chunker=chunker, parser=parser)

    assert isinstance(service, RAGIngestionService)
    assert service.chunker is chunker
    assert service.parser is parser
