from typing import Any, Literal

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict, SecretStr

from app.core.config import LLMSettings, OpenRouterSettings, Settings
from app.modules.rag import llm as rag_llm
from app.modules.rag.llm import TransientFallbackChatModel, get_llm


class FakeChatModel(BaseChatModel):
    response: str = "ok"
    error: Exception | None = None
    calls: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        _ = messages
        _ = stop
        _ = run_manager
        _ = kwargs
        self.calls += 1
        if self.error is not None:
            raise self.error

        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self.response))]
        )


def build_settings(
    *,
    provider: Literal["auto", "maritaca", "openrouter"] = "auto",
    enable_fallback: bool = True,
) -> Settings:
    return Settings(
        secret_key="long_and_secure_secret_key_for_testing_purposes_only_1234567890",
        maritaca_api_key="maritaca-test-key",
        llm=LLMSettings(
            provider=provider,
            enable_fallback=enable_fallback,
            timeout_seconds=5,
        ),
        openrouter=OpenRouterSettings(api_key="openrouter-test-key"),
    )


def test_llm_factory_uses_maritaca_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_kwargs: dict[str, object] = {}

    def fake_maritaca(**kwargs: object) -> FakeChatModel:
        created_kwargs.update(kwargs)
        return FakeChatModel()

    monkeypatch.setattr(rag_llm, "ChatMaritalk", fake_maritaca)
    monkeypatch.setattr(rag_llm, "ChatOpenAI", lambda **kwargs: FakeChatModel())

    model = get_llm(settings=build_settings(enable_fallback=False))

    assert isinstance(model, FakeChatModel)
    assert created_kwargs["api_key"] == "maritaca-test-key"
    assert created_kwargs["model"] == "sabiazinho-4"


def test_llm_factory_uses_openrouter_fallback_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_kwargs: dict[str, object] = {}

    monkeypatch.setattr(rag_llm, "ChatMaritalk", lambda **kwargs: FakeChatModel())

    def fake_openrouter(**kwargs: object) -> FakeChatModel:
        created_kwargs.update(kwargs)
        return FakeChatModel()

    monkeypatch.setattr(rag_llm, "ChatOpenAI", fake_openrouter)

    model = get_llm(settings=build_settings())

    assert isinstance(model, TransientFallbackChatModel)
    assert created_kwargs["model"] == "openai/gpt-5.4-mini"
    assert created_kwargs["base_url"] == rag_llm.OPENROUTER_BASE_URL
    assert isinstance(created_kwargs["api_key"], SecretStr)


@pytest.mark.anyio
async def test_fallback_uses_secondary_for_transient_errors() -> None:
    primary = FakeChatModel(error=TimeoutError("provider timed out"))
    fallback = FakeChatModel(response="fallback answer")
    model = TransientFallbackChatModel(primary=primary, fallback=fallback)

    response = await model.ainvoke([HumanMessage(content="Como tomar?")])

    assert response.content == "fallback answer"
    assert primary.calls == 1
    assert fallback.calls == 1


@pytest.mark.anyio
async def test_fallback_does_not_mask_non_transient_errors() -> None:
    primary = FakeChatModel(error=ValueError("invalid request"))
    fallback = FakeChatModel(response="fallback answer")
    model = TransientFallbackChatModel(primary=primary, fallback=fallback)

    with pytest.raises(ValueError, match="invalid request"):
        await model.ainvoke([HumanMessage(content="Como tomar?")])

    assert primary.calls == 1
    assert fallback.calls == 0
