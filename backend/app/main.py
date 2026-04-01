from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.modules.bulas.router import router as bulas_router
from app.core.database import close_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown
    await close_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="BulaGPT API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(bulas_router, prefix="/api/v1")

    return app


app = create_app()