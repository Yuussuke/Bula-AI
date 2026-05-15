from qdrant_client import AsyncQdrantClient

from app.core.config import QdrantSettings, Settings


QDRANT_CLIENT_STATE_KEY = "qdrant_client"


def build_qdrant_url(*, settings: QdrantSettings) -> str:
    scheme = "https" if settings.use_https else "http"
    return f"{scheme}://{settings.host}:{settings.port}"


def create_qdrant_client(*, settings: Settings) -> AsyncQdrantClient:
    return AsyncQdrantClient(
        url=build_qdrant_url(settings=settings.qdrant),
        api_key=settings.qdrant.api_key,
        timeout=settings.qdrant.timeout_seconds,
    )
