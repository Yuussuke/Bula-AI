from fastapi import FastAPI
from pydantic import BaseModel
from app.routes.upload import router as upload_router


class HealthResponse(BaseModel):
    status: str


def create_app() -> FastAPI:
    app = FastAPI(
        title="BulaGPT API",
        description="AI-powered assistant for Brazilian medication package inserts.",
        version="0.1.0",
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(upload_router)

    return app


app = create_app()