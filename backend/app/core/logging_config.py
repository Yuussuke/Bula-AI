import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import add_log_level, ProcessorFormatter
from structlog.types import EventDict, Processor


class AppInfoProcessor:
    def __init__(self, app_version: str, environment: str) -> None:
        self.app_version = app_version
        self.environment = environment

    def __call__(
        self, logger: Any, method_name: str, event_dict: EventDict
    ) -> EventDict:
        _ = logger, method_name
        event_dict["app_version"] = self.app_version
        event_dict["environment"] = self.environment
        return event_dict


def add_app_info(app_version: str, environment: str) -> Processor:
    """Add application-level context to every log entry."""
    return AppInfoProcessor(app_version=app_version, environment=environment)


def build_processors(
    *, use_json: bool, app_version: str, environment: str
) -> list[Processor]:
    """Build the processor pipeline used by structlog."""
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_app_info(app_version, environment),
    ]

    if use_json:
        # Production: JSON output for log aggregation.
        import orjson

        def orjson_serializer(obj: Any, *args: Any, **kwargs: Any) -> str:
            return orjson.dumps(obj, default=str).decode("utf-8")

        processors.append(
            structlog.processors.JSONRenderer(serializer=orjson_serializer)
        )
    else:
        # Development: colored console output.
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    return processors


def configure_stdlib_logging(
    *, log_level: str, shared_processors: list[Processor]
) -> None:
    """Configure stdlib logging to use the same structlog processor pipeline."""
    pre_processors = shared_processors[:-1]
    renderer = shared_processors[-1]

    formatter = ProcessorFormatter(
        foreign_pre_chain=pre_processors,
        processors=[
            ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))

    for logger_name in [
        "sqlalchemy.engine",
        "sqlalchemy.engine.base",
        "uvicorn.access",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def should_use_json_logs(*, json_logs: bool, is_tty: bool) -> bool:
    """
    Decide if logs should be rendered as JSON.
    """
    _ = is_tty
    return json_logs


def configure_logging(
    *,
    log_level: str = "INFO",
    json_logs: bool = True,
    app_version: str = "0.1.0",
    environment: str = "development",
) -> None:
    """
    Configure structlog for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output JSON. If False, output colored console logs.
        app_version: Application version for log context
        environment: Environment name (development, staging, production)
    """
    # Respect explicit configuration for log format.
    use_json = should_use_json_logs(
        json_logs=json_logs,
        is_tty=sys.stdout.isatty(),
    )

    processors = build_processors(
        use_json=use_json,
        app_version=app_version,
        environment=environment,
    )

    structlog.configure(
        processors=processors[:-1] + [ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    configure_stdlib_logging(log_level=log_level, shared_processors=processors)
