import structlog

from app.core.logging_config import AppInfoProcessor, build_processors


def test_app_info_processor_adds_application_context() -> None:
    processor = AppInfoProcessor(app_version="1.2.3", environment="test")

    event_dict = {"event": "user_registration_attempt", "email": "test@bulaai.com"}
    result = processor(logger=None, method_name="info", event_dict=event_dict)

    assert result["event"] == "user_registration_attempt"
    assert result["email"] == "test@bulaai.com"
    assert result["app_version"] == "1.2.3"
    assert result["environment"] == "test"


def test_build_processors_appends_console_renderer_when_not_json() -> None:
    processors = build_processors(
        use_json=False,
        app_version="0.1.0",
        environment="development",
    )

    assert any(isinstance(proc, AppInfoProcessor) for proc in processors)
    assert isinstance(processors[-1], structlog.dev.ConsoleRenderer)


def test_build_processors_appends_json_renderer_when_json_enabled() -> None:
    processors = build_processors(
        use_json=True,
        app_version="0.1.0",
        environment="production",
    )

    assert any(isinstance(proc, AppInfoProcessor) for proc in processors)
    assert isinstance(processors[-1], structlog.processors.JSONRenderer)
