import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to each request for distributed tracing."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Get existing correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Add to context variables for structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id

        return response
