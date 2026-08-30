from typing import cast

from fastapi import Depends, Request
from langchain_core.embeddings import Embeddings as LCEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from openai import AsyncOpenAI
from pydantic import SecretStr
from qdrant_client import AsyncQdrantClient

from app.core.config import Settings, get_settings
from app.modules.bulas.dependencies import get_bula_repository
from app.modules.bulas.repository import BulaRepository
from app.modules.rag.base_chunker import BaseChunker
from app.modules.rag.chain import RAGChainFactory
from app.modules.rag.chunker import BulaChunker
from app.modules.rag.debug_artifacts import RAGIngestionDebugArtifacts
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.llm import OPENROUTER_BASE_URL, get_llm
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.qdrant_client import QDRANT_CLIENT_STATE_KEY
from app.modules.rag.qdrant_store import QdrantVectorStore
from app.modules.rag.retriever import DenseBulaRetriever
from app.modules.rag.schemas import ChunkingConfig
from app.modules.rag.service import RAGIngestionService
from app.modules.rag.token_estimator import build_token_estimator
from app.modules.storage.client import ObjectStoreClient
from app.modules.storage.dependencies import get_object_store_client


MISSING_OPENROUTER_API_KEY = "missing-openrouter-api-key"
OPENROUTER_EMBEDDING_MODEL_HINT = "intfloat/multilingual-e5-large"


def get_parser() -> BulaParser:
    return BulaParser(ocr_enabled=False)


def get_ingestion_debug_artifacts(
    settings: Settings = Depends(get_settings),
) -> RAGIngestionDebugArtifacts:
    return RAGIngestionDebugArtifacts(
        enabled=settings.rag_ingestion.debug,
        root_path=settings.rag_ingestion.debug_path,
    )


def get_embeddings(settings: Settings = Depends(get_settings)) -> EmbeddingAdapter:
    embedder: LCEmbeddings
    if settings.embedding.provider == "ollama":
        embedder = OllamaEmbeddings(
            model=settings.embedding.model,
            base_url=_build_ollama_base_url(settings=settings),
        )
    else:
        api_key = _get_openrouter_api_key_for_embeddings(settings=settings)
        _validate_openrouter_embedding_model(settings=settings)
        embedder = OpenAIEmbeddings(
            model=settings.embedding.model,
            api_key=SecretStr(api_key),
            base_url=OPENROUTER_BASE_URL,
            check_embedding_ctx_length=False,
            tiktoken_enabled=False,
            chunk_size=max(1, settings.embedding.batch_size),
            timeout=settings.embedding.timeout_seconds,
        )

    return EmbeddingAdapter(
        embedder=embedder,
        batch_size=settings.embedding.batch_size,
        dimension=settings.embedding.dimension,
    )


def get_qdrant_client(request: Request) -> AsyncQdrantClient:
    client = getattr(request.app.state, QDRANT_CLIENT_STATE_KEY, None)
    if client is None:
        raise RuntimeError("Qdrant client was not initialized.")

    return cast(AsyncQdrantClient, client)


def get_qdrant_store(
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant_client),
    settings: Settings = Depends(get_settings),
) -> QdrantVectorStore:
    return QdrantVectorStore(
        client=qdrant_client,
        vector_size=settings.embedding.dimension,
    )


def get_dense_retriever(
    bula_id: str,
    k: int = 4,
    qdrant_store: QdrantVectorStore = Depends(get_qdrant_store),
    embeddings: EmbeddingAdapter = Depends(get_embeddings),
) -> BaseRetriever:
    return DenseBulaRetriever(
        bula_id=bula_id,
        k=k,
        qdrant_store=qdrant_store,
        embeddings=embeddings,
    )


def get_chat_llm(settings: Settings = Depends(get_settings)) -> BaseChatModel:
    return get_llm(settings=settings)


def get_rag_chain_factory(
    settings: Settings = Depends(get_settings),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant_client),
) -> RAGChainFactory:
    def build_dense_retriever(bula_id: str) -> BaseRetriever:
        return DenseBulaRetriever(
            bula_id=bula_id,
            qdrant_store=get_qdrant_store(
                qdrant_client=qdrant_client,
                settings=settings,
            ),
            embeddings=get_embeddings(settings=settings),
        )

    def build_chat_llm() -> BaseChatModel:
        return get_llm(settings=settings)

    return RAGChainFactory(
        dense_retriever_builder=build_dense_retriever,
        llm_builder=build_chat_llm,
    )


def get_llm_client(settings: Settings = Depends(get_settings)) -> AsyncOpenAI:
    api_key = _clean_optional_api_key(settings.openrouter.api_key)
    return AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key or MISSING_OPENROUTER_API_KEY,
        timeout=settings.openrouter.chunk_timeout_seconds,
        max_retries=settings.openrouter.chunk_max_retries,
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
        is_batching_enabled=settings.processing.chunk_batch_enabled,
        batch_max_tokens=settings.processing.chunk_batch_max_tokens,
        batch_max_sections=settings.processing.chunk_batch_max_sections,
        model=settings.openrouter.chunk_model,
        provider_zdr=settings.openrouter.require_zdr,
        is_llm_enabled=openrouter_api_key is not None,
        request_timeout_seconds=settings.openrouter.chunk_timeout_seconds,
    )
    return BulaChunker(
        llm=llm,
        config=config,
        token_estimator=build_token_estimator(settings=settings),
    )


def get_ingestion_service(
    chunker: BaseChunker = Depends(get_chunker),
    parser: BulaParser = Depends(get_parser),
    embeddings: EmbeddingAdapter = Depends(get_embeddings),
    qdrant_store: QdrantVectorStore = Depends(get_qdrant_store),
    object_store: ObjectStoreClient = Depends(get_object_store_client),
    bula_repo: BulaRepository = Depends(get_bula_repository),
    debug_artifacts: RAGIngestionDebugArtifacts = Depends(
        get_ingestion_debug_artifacts
    ),
) -> RAGIngestionService:
    return RAGIngestionService(
        chunker=chunker,
        parser=parser,
        embeddings=embeddings,
        qdrant_store=qdrant_store,
        object_store=object_store,
        bula_repo=bula_repo,
        debug_artifacts=debug_artifacts,
    )


def _clean_optional_api_key(api_key: str | None) -> str | None:
    if api_key is None:
        return None

    clean_api_key = api_key.strip()
    if not clean_api_key:
        return None

    return clean_api_key


def _get_openrouter_api_key_for_embeddings(*, settings: Settings) -> str:
    api_key = _clean_optional_api_key(settings.openrouter.api_key)
    if api_key is None:
        raise ValueError(
            "OPENROUTER_API_KEY is required when EMBEDDING_PROVIDER=openrouter. "
            "Set EMBEDDING_PROVIDER=ollama to use local embeddings."
        )

    return api_key


def _validate_openrouter_embedding_model(*, settings: Settings) -> None:
    if not _looks_like_ollama_model_tag(settings.embedding.model):
        return

    raise ValueError(
        "EMBEDDING_MODEL looks like an Ollama model tag, but "
        "EMBEDDING_PROVIDER=openrouter. Use "
        f"EMBEDDING_MODEL={OPENROUTER_EMBEDDING_MODEL_HINT} or set "
        "EMBEDDING_PROVIDER=ollama."
    )


def _looks_like_ollama_model_tag(model_name: str) -> bool:
    clean_model_name = model_name.strip().lower()
    return clean_model_name.startswith("jeffh/") or ":q" in clean_model_name


def _build_ollama_base_url(*, settings: Settings) -> str:
    clean_host = settings.ollama.host.rstrip("/")
    host_without_scheme = clean_host.split("://", maxsplit=1)[-1]
    if ":" in host_without_scheme:
        return clean_host

    return f"{clean_host}:{settings.ollama.port}"


def _validate_zdr_model_policy(*, settings: Settings) -> None:
    if not settings.openrouter.require_zdr:
        raise ValueError("Semantic chunking requires OpenRouter ZDR routing")

    has_free_primary_model = _is_free_model(settings.openrouter.chunk_model)
    if has_free_primary_model:
        raise ValueError("Free model variants are not allowed when ZDR is required")


def _is_free_model(model_name: str) -> bool:
    return ":free" in model_name.lower()
