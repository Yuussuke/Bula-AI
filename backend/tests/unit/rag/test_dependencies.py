from typing import cast

import pytest
from fastapi import FastAPI, Request
from langchain_core.embeddings import Embeddings as LCEmbeddings
from openai import AsyncOpenAI
from pydantic import SecretStr

from app.core.config import (
    EmbeddingSettings,
    OllamaSettings,
    OpenRouterSettings,
    ProcessingSettings,
    QdrantSettings,
    RAGIngestionSettings,
    Settings,
)
from app.modules.rag.base_chunker import BaseChunker
from app.modules.rag.chunker import BulaChunker
from app.modules.rag.debug_artifacts import RAGIngestionDebugArtifacts
from app.modules.rag import dependencies as rag_dependencies
from app.modules.rag import qdrant_client as qdrant_client_module
from app.modules.rag.dependencies import (
    get_chunker,
    get_ingestion_debug_artifacts,
    get_ingestion_service,
    get_qdrant_client,
)
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.qdrant_client import QDRANT_CLIENT_STATE_KEY
from app.modules.rag.qdrant_store import QdrantVectorStore
from app.modules.rag.service import RAGIngestionService
from app.modules.rag.token_estimator import (
    HeuristicTokenEstimator,
    TiktokenTokenEstimator,
)


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
    assert created_kwargs["model"] == settings.embedding.model
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


def test_get_embeddings_rejects_local_quantized_model_tag_for_openrouter_provider() -> (
    None
):
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


def test_create_qdrant_client_uses_qdrant_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_kwargs: dict[str, object] = {}

    def fake_qdrant_client(**kwargs: object) -> FakeQdrantClient:
        created_kwargs.update(kwargs)
        return FakeQdrantClient(**kwargs)

    monkeypatch.setattr(
        qdrant_client_module,
        "AsyncQdrantClient",
        fake_qdrant_client,
    )
    settings = build_settings()
    settings.embedding = EmbeddingSettings(dimension=768)
    settings.qdrant = QdrantSettings(
        host="qdrant-test",
        port=6333,
        use_https=True,
        api_key="qdrant-key",
        timeout_seconds=30,
    )

    client = qdrant_client_module.create_qdrant_client(settings=settings)

    assert isinstance(client, FakeQdrantClient)
    assert created_kwargs == {
        "url": "https://qdrant-test:6333",
        "api_key": "qdrant-key",
        "timeout": 30,
    }


@pytest.mark.parametrize(
    ("qdrant_settings", "expected_url"),
    [
        (
            QdrantSettings(host="qdrant", port=6333, use_https=False),
            "http://qdrant:6333",
        ),
        (
            QdrantSettings(host="localhost", port=6333, use_https=False),
            "http://localhost:6333",
        ),
        (
            QdrantSettings(
                host="managed-qdrant.example.com",
                port=6333,
                use_https=True,
            ),
            "https://managed-qdrant.example.com:6333",
        ),
    ],
)
def test_build_qdrant_url_uses_configured_scheme(
    qdrant_settings: QdrantSettings,
    expected_url: str,
) -> None:
    qdrant_url = qdrant_client_module.build_qdrant_url(settings=qdrant_settings)

    assert qdrant_url == expected_url


def test_qdrant_settings_default_to_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("QDRANT_USE_HTTPS", raising=False)

    qdrant_settings = QdrantSettings(
        host="qdrant",
        port=6333,
        _env_file=None,
    )

    assert qdrant_settings.use_https is False
    assert (
        qdrant_client_module.build_qdrant_url(settings=qdrant_settings)
        == "http://qdrant:6333"
    )


def test_qdrant_settings_reads_use_https_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QDRANT_USE_HTTPS", "true")

    qdrant_settings = QdrantSettings(
        host="managed-qdrant.example.com",
        port=6333,
        _env_file=None,
    )

    assert qdrant_settings.use_https is True
    assert (
        qdrant_client_module.build_qdrant_url(settings=qdrant_settings)
        == "https://managed-qdrant.example.com:6333"
    )


def test_rag_ingestion_settings_defaults() -> None:
    settings = RAGIngestionSettings(_env_file=None)

    assert settings.debug is False
    assert settings.debug_path == "tmp/rag-ingestion-debug"
    assert settings.stale_job_retry_after_seconds == 300


def test_rag_ingestion_settings_reads_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_INGESTION_DEBUG", "true")
    monkeypatch.setenv("RAG_INGESTION_DEBUG_PATH", "custom-debug")
    monkeypatch.setenv("RAG_INGESTION_STALE_JOB_RETRY_AFTER_SECONDS", "90")

    settings = RAGIngestionSettings(_env_file=None)

    assert settings.debug is True
    assert settings.debug_path == "custom-debug"
    assert settings.stale_job_retry_after_seconds == 90


def test_get_ingestion_debug_artifacts_uses_settings() -> None:
    settings = build_settings()
    settings.rag_ingestion = RAGIngestionSettings(
        debug=True,
        debug_path="custom-debug",
    )

    debug_artifacts = get_ingestion_debug_artifacts(settings=settings)

    assert isinstance(debug_artifacts, RAGIngestionDebugArtifacts)
    assert debug_artifacts.enabled is True
    assert str(debug_artifacts.root_path) == "custom-debug"


def test_get_qdrant_client_returns_lifespan_client() -> None:
    app = FastAPI()
    fake_client = cast(object, FakeQdrantClient())
    setattr(app.state, QDRANT_CLIENT_STATE_KEY, fake_client)
    request = Request({"type": "http", "app": app})

    client = get_qdrant_client(request=request)

    assert client is fake_client


def test_get_qdrant_client_requires_lifespan_initialization() -> None:
    app = FastAPI()
    request = Request({"type": "http", "app": app})

    with pytest.raises(RuntimeError, match="Qdrant client was not initialized"):
        get_qdrant_client(request=request)


def test_get_qdrant_store_reuses_shared_client() -> None:
    fake_client = cast(object, FakeQdrantClient())
    settings = build_settings()
    settings.embedding = EmbeddingSettings(dimension=768)

    vector_store = rag_dependencies.get_qdrant_store(
        qdrant_client=cast(object, fake_client),
        settings=settings,
    )

    assert isinstance(vector_store, QdrantVectorStore)
    assert vector_store.vector_size == 768
    assert vector_store._client is fake_client


def test_get_chunker_returns_bula_chunker_as_base_chunker() -> None:
    fake_llm = cast(AsyncOpenAI, FakeOpenAIClient())
    settings = build_settings()

    chunker = get_chunker(llm=fake_llm, settings=settings)

    assert isinstance(chunker, BaseChunker)
    assert isinstance(chunker, BulaChunker)
    assert chunker.llm is fake_llm
    assert chunker.config.is_llm_enabled is True
    assert isinstance(chunker.token_estimator, TiktokenTokenEstimator)


def test_get_chunker_uses_batch_processing_settings() -> None:
    fake_llm = cast(AsyncOpenAI, FakeOpenAIClient())
    settings = build_settings()
    settings.processing = ProcessingSettings(
        chunk_batch_enabled=False,
        chunk_batch_max_tokens=2400,
        chunk_batch_max_sections=6,
    )

    chunker = get_chunker(llm=fake_llm, settings=settings)

    assert chunker.config.is_batching_enabled is False
    assert chunker.config.batch_max_tokens == 2400
    assert chunker.config.batch_max_sections == 6


def test_get_chunker_uses_heuristic_token_estimator_when_encoding_is_blank() -> None:
    fake_llm = cast(AsyncOpenAI, FakeOpenAIClient())
    settings = build_settings()
    settings.processing = ProcessingSettings(tokenizer_encoding="")

    chunker = get_chunker(llm=fake_llm, settings=settings)

    assert isinstance(chunker.token_estimator, HeuristicTokenEstimator)


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
    debug_artifacts = RAGIngestionDebugArtifacts(
        enabled=False,
        root_path="tmp/rag-ingestion-debug",
    )

    service = get_ingestion_service(
        chunker=chunker,
        parser=parser,
        embeddings=embeddings,
        qdrant_store=qdrant_store,
        object_store=object_store,
        bula_repo=bula_repo,
        debug_artifacts=debug_artifacts,
    )

    assert isinstance(service, RAGIngestionService)
    assert service.chunker is chunker
    assert service.parser is parser
    assert service.embeddings is embeddings
    assert service.qdrant_store is qdrant_store
    assert service.debug_artifacts is debug_artifacts
