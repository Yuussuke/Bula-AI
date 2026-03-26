"""
BulaGPT – Backend entry point.

Minimal FastAPI application that exposes a health-check endpoint.
Additional routes and modules will be added in future sprints.
"""

from fastapi import FastAPI

# Create the FastAPI application instance
app = FastAPI(
    title="BulaGPT API",
    description="AI-powered assistant for Brazilian medication package inserts.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Return a simple status to confirm the API is running."""
    return {"status": "ok"}
