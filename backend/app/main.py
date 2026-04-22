from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import global_exception_handler
from app.core.database import close_engine
from app.core.middleware import CorrelationIdMiddleware
from app.core.request_logging import RequestLoggingMiddleware
from app.modules.auth.router import router as auth_router
from app.modules.bulas.router import router as bulas_router
from app.modules.chat.router import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Bula AI API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(bulas_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")

    return app


app = create_app()
