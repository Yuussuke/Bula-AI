from qdrant_client import AsyncQdrantClient

from app.core.config import Settings


QDRANT_CLIENT_STATE_KEY = "qdrant_client"


def create_qdrant_client(*, settings: Settings) -> AsyncQdrantClient:
    return AsyncQdrantClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        api_key=settings.qdrant.api_key,
        timeout=settings.qdrant.timeout_seconds,
    )
