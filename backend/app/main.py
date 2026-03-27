"""
BulaGPT – Backend entry point.

Minimal FastAPI application that exposes a health-check endpoint.
Additional routes and modules will be added in future sprints.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import UploadFile, File
from pypdf import PdfReader

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
    
    @app.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        reader = PdfReader(file.file)

        text = ""
        num_pages = len(reader.pages)

        for page in reader.pages:
            text += page.extract_text() or ""

        return {
            "filename": file.filename,
            "pages": num_pages,
            "characters": len(text)
        }

    return app



app = create_app()
