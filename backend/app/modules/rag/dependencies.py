from fastapi import Depends
from openai import AsyncOpenAI

from app.core.config import Settings, get_settings
from app.modules.rag.base_chunker import BaseChunker
from app.modules.rag.chunker import BulaChunker
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.schemas import ChunkingConfig
from app.modules.rag.service import RAGIngestionService


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MISSING_OPENROUTER_API_KEY = "missing-openrouter-api-key"


def get_parser() -> BulaParser:
    return BulaParser(ocr_enabled=False)


def get_llm_client(settings: Settings = Depends(get_settings)) -> AsyncOpenAI:
    api_key = _clean_optional_api_key(settings.openrouter.api_key)
    return AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key or MISSING_OPENROUTER_API_KEY,
    )


def get_chunker(
    llm: AsyncOpenAI = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
) -> BaseChunker:
    _validate_zdr_model_policy(settings=settings)
    openrouter_api_key = _clean_optional_api_key(settings.openrouter.api_key)
    config = ChunkingConfig(
        target_tokens=settings.processing.chunk_target_tokens,
        min_tokens=settings.processing.chunk_min_tokens,
        max_tokens=settings.processing.chunk_max_tokens,
        overlap_ratio=settings.processing.chunk_overlap_ratio,
        max_concurrency=settings.processing.chunk_max_concurrency,
        model=settings.openrouter.chunk_model,
        fallback_model=settings.openrouter.chunk_fallback_model,
        is_llm_enabled=openrouter_api_key is not None,
    )
    return BulaChunker(llm=llm, config=config)


def get_ingestion_service(
    chunker: BaseChunker = Depends(get_chunker),
    parser: BulaParser = Depends(get_parser),
) -> RAGIngestionService:
    return RAGIngestionService(chunker=chunker, parser=parser)


def _clean_optional_api_key(api_key: str | None) -> str | None:
    if api_key is None:
        return None

    clean_api_key = api_key.strip()
    if not clean_api_key:
        return None

    return clean_api_key


def _validate_zdr_model_policy(*, settings: Settings) -> None:
    if not settings.openrouter.require_zdr:
        return

    has_free_primary_model = _is_free_model(settings.openrouter.chunk_model)
    has_free_fallback_model = _is_free_model(settings.openrouter.chunk_fallback_model)
    if has_free_primary_model or has_free_fallback_model:
        raise ValueError("Free model variants are not allowed when ZDR is required")


def _is_free_model(model_name: str) -> bool:
    return ":free" in model_name.lower()
