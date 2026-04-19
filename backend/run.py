"""Application entry point with structured logging configured before server startup."""

import sys

from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging(
    log_level=settings.log_level,
    json_logs=settings.json_logs,
    app_version="0.1.0",
    environment=settings.environment,
)

import uvicorn


def main() -> int:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_config=None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
