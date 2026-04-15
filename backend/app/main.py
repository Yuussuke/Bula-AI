from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.database import close_engine

from app.modules.bulas.router import router as bulas_router
from app.modules.auth.router import router as auth_router

from app.modules.chat import models as chat_models 

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown
    await close_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Bula AI API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(bulas_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    
    return app


app = create_app()