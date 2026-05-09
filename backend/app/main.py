from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.database import close_engine
from app.core.exceptions import global_exception_handler
from app.core.limiter import limiter
from app.core.middleware import CorrelationIdMiddleware
from app.core.pgqueuer import PGQ_QUERIES_STATE_KEY, create_pgq_queries
from app.core.request_logging import RequestLoggingMiddleware
from app.modules.auth.router import router as auth_router
from app.modules.bulas.router import router as bulas_router
from app.modules.chat.router import router as chat_router
from app.modules.rag.qdrant_client import (
    QDRANT_CLIENT_STATE_KEY,
    create_qdrant_client,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pgq_pool, pgq_queries = await create_pgq_queries(settings.database_url)
    setattr(app.state, PGQ_QUERIES_STATE_KEY, pgq_queries)
    qdrant_client = create_qdrant_client(settings=settings)
    setattr(app.state, QDRANT_CLIENT_STATE_KEY, qdrant_client)

    try:
        yield
    finally:
        # The FastAPI lifespan owns the shared Qdrant client and closes it on shutdown.
        await qdrant_client.close()
        await pgq_pool.close()
        await close_engine()


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    rate_limit_error = cast(RateLimitExceeded, exc)
    return _rate_limit_exceeded_handler(request, rate_limit_error)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Bula AI API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(bulas_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")

    return app


app = create_app()
