import logging

import structlog

from app.core.logging_config import (
    AppInfoProcessor,
    build_processors,
    configure_stdlib_logging,
    should_use_json_logs,
)


def test_app_info_processor_adds_application_context() -> None:
    """Tests that the AppInfoProcessor correctly adds app_version and
    environment to log events."""
    processor = AppInfoProcessor(app_version="1.2.3", environment="test")

    event_dict = {"event": "user_registration_attempt", "email": "test@bulaai.com"}
    result = processor(None, "info", event_dict)

    assert result["event"] == "user_registration_attempt"
    assert result["email"] == "test@bulaai.com"
    assert result["app_version"] == "1.2.3"
    assert result["environment"] == "test"


def test_build_processors_appends_console_renderer_when_not_json() -> None:
    """Tests that the build_processors function appends a ConsoleRenderer
    when use_json is False."""
    processors = build_processors(
        use_json=False,
        app_version="0.1.0",
        environment="development",
    )

    assert any(isinstance(proc, AppInfoProcessor) for proc in processors)
    assert isinstance(processors[-1], structlog.dev.ConsoleRenderer)


def test_build_processors_appends_json_renderer_when_json_enabled() -> None:
    """Tests that the build_processors function appends a JSONRenderer
    when use_json is True."""
    processors = build_processors(
        use_json=True,
        app_version="0.1.0",
        environment="production",
    )

    assert any(isinstance(proc, AppInfoProcessor) for proc in processors)
    assert isinstance(processors[-1], structlog.processors.JSONRenderer)


def test_should_use_json_logs_respects_explicit_false_in_non_tty() -> None:
    """Ensures explicit JSON_LOGS=false is honored even in non-TTY runtimes."""
    assert should_use_json_logs(json_logs=False, is_tty=False) is False


def test_should_use_json_logs_respects_explicit_true_in_tty() -> None:
    """Ensures explicit JSON_LOGS=true is honored in interactive terminals."""
    assert should_use_json_logs(json_logs=True, is_tty=True) is True


def test_configure_stdlib_logging_sets_up_structlog_formatting() -> None:
    """Ensures stdlib logging uses structlog formatter and expected logger levels."""
    processors = build_processors(
        use_json=True,
        app_version="0.1.0",
        environment="test",
    )

    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    try:
        configure_stdlib_logging(log_level="INFO", shared_processors=processors)

        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1
        assert isinstance(
            root_logger.handlers[0].formatter,
            structlog.stdlib.ProcessorFormatter,
        )

        assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING
        assert logging.getLogger("sqlalchemy.engine.base").level == logging.WARNING
        assert logging.getLogger("uvicorn.access").level == logging.WARNING
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)
