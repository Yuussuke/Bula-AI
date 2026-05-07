from typing import cast

import pytest
from langchain_core.embeddings import Embeddings as LCEmbeddings
from openai import AsyncOpenAI
from pydantic import SecretStr

from app.core.config import (
    EmbeddingSettings,
    OllamaSettings,
    OpenRouterSettings,
    ProcessingSettings,
    QdrantSettings,
    Settings,
)
from app.modules.rag.base_chunker import BaseChunker
from app.modules.rag.chunker import BulaChunker
from app.modules.rag import dependencies as rag_dependencies
from app.modules.rag.dependencies import get_chunker, get_ingestion_service
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.qdrant_store import QdrantVectorStore
from app.modules.rag.service import RAGIngestionService


class FakeOpenAIClient:
    pass


class FakeEmbeddings(LCEmbeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] * 1024 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        _ = text
        return [1.0] * 1024


class FakeQdrantClient:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class FakeQdrantStore:
    pass


class FakeObjectStore:
    pass


class FakeBulaRepository:
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


def test_get_embeddings_uses_openrouter_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_kwargs: dict[str, object] = {}

    def fake_openai_embeddings(**kwargs: object) -> FakeEmbeddings:
        created_kwargs.update(kwargs)
        return FakeEmbeddings()

    monkeypatch.setattr(
        rag_dependencies,
        "OpenAIEmbeddings",
        fake_openai_embeddings,
    )
    settings = build_settings(
        api_key="openrouter-embedding-key",
    )
    settings.embedding = EmbeddingSettings(
        provider="openrouter",
        model=rag_dependencies.OPENROUTER_EMBEDDING_MODEL_HINT,
        batch_size=8,
        dimension=1024,
        timeout_seconds=15,
    )

    adapter = rag_dependencies.get_embeddings(settings=settings)
    api_key = created_kwargs["api_key"]

    assert isinstance(adapter, EmbeddingAdapter)
    assert created_kwargs["model"] == "intfloat/multilingual-e5-large"
    assert isinstance(api_key, SecretStr)
    assert api_key.get_secret_value() == "openrouter-embedding-key"
    assert created_kwargs["base_url"] == rag_dependencies.OPENROUTER_BASE_URL
    assert created_kwargs["chunk_size"] == 8
    assert created_kwargs["timeout"] == 15


def test_get_embeddings_requires_openrouter_api_key_for_openrouter_provider() -> None:
    settings = build_settings(api_key=None)
    settings.embedding = EmbeddingSettings(provider="openrouter")

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY is required"):
        rag_dependencies.get_embeddings(settings=settings)


def test_get_embeddings_rejects_local_quantized_model_tag_for_openrouter_provider() -> None:
    settings = build_settings(api_key="openrouter-embedding-key")
    settings.embedding = EmbeddingSettings(
        provider="openrouter",
        model="local-ollama/example-embedding:q8_0",
    )

    with pytest.raises(ValueError, match="EMBEDDING_MODEL looks like an Ollama"):
        rag_dependencies.get_embeddings(settings=settings)


def test_get_embeddings_uses_ollama_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_kwargs: dict[str, object] = {}

    def fake_ollama_embeddings(**kwargs: object) -> FakeEmbeddings:
        created_kwargs.update(kwargs)
        return FakeEmbeddings()

    monkeypatch.setattr(
        rag_dependencies,
        "OllamaEmbeddings",
        fake_ollama_embeddings,
    )
    settings = build_settings()
    settings.embedding = EmbeddingSettings(provider="ollama")
    settings.ollama = OllamaSettings(host="http://ollama-test", port=11434)

    adapter = rag_dependencies.get_embeddings(settings=settings)

    assert isinstance(adapter, EmbeddingAdapter)
    assert created_kwargs["model"] == settings.embedding.model
    assert created_kwargs["base_url"] == "http://ollama-test:11434"


def test_get_qdrant_store_uses_qdrant_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_kwargs: dict[str, object] = {}

    def fake_qdrant_client(**kwargs: object) -> FakeQdrantClient:
        created_kwargs.update(kwargs)
        return FakeQdrantClient(**kwargs)

    monkeypatch.setattr(
        rag_dependencies,
        "AsyncQdrantClient",
        fake_qdrant_client,
    )
    settings = build_settings()
    settings.embedding = EmbeddingSettings(dimension=768)
    settings.qdrant = QdrantSettings(
        host="qdrant-test",
        port=6333,
        api_key="qdrant-key",
        timeout_seconds=30,
    )

    vector_store = rag_dependencies.get_qdrant_store(settings=settings)

    assert isinstance(vector_store, QdrantVectorStore)
    assert vector_store.vector_size == 768
    assert created_kwargs == {
        "host": "qdrant-test",
        "port": 6333,
        "api_key": "qdrant-key",
        "timeout": 30,
    }


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
    embeddings = EmbeddingAdapter(
        embedder=FakeEmbeddings(),
        batch_size=1,
        dimension=1024,
    )
    qdrant_store = cast(QdrantVectorStore, FakeQdrantStore())
    object_store = cast(object, FakeObjectStore())
    bula_repo = cast(object, FakeBulaRepository())

    service = get_ingestion_service(
        chunker=chunker,
        parser=parser,
        embeddings=embeddings,
        qdrant_store=qdrant_store,
        object_store=object_store,
        bula_repo=bula_repo,
    )

    assert isinstance(service, RAGIngestionService)
    assert service.chunker is chunker
    assert service.parser is parser
    assert service.embeddings is embeddings
    assert service.qdrant_store is qdrant_store
