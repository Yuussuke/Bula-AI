"""
BulaGPT – Backend entry point.

Minimal FastAPI application that exposes a health-check endpoint.
Additional routes and modules will be added in future sprints.
"""

from fastapi import FastAPI
from pydantic import BaseModel


# Response model for the /health endpoint
class HealthResponse(BaseModel):
    status: str


def create_app() -> FastAPI:
    """Application factory – allows future configuration and middleware injection."""
    app = FastAPI(
        title="BulaGPT API",
        description="AI-powered assistant for Brazilian medication package inserts.",
        version="0.1.0",
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> dict:
        """Return a simple status to confirm the API is running."""
        return {"status": "ok"}

    return app


app = create_app()
