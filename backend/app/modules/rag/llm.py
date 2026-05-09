from __future__ import annotations

import asyncio
from typing import Any

import httpx
from langchain_community.chat_models import ChatMaritalk
from langchain_community.chat_models.maritalk import MaritalkHTTPError
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)
from pydantic import ConfigDict, SecretStr

from app.core.config import Settings, settings


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
TRANSIENT_HTTP_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


class LLMConfigurationError(RuntimeError):
    """Raised when the configured chat LLM cannot be created."""


class TransientFallbackChatModel(BaseChatModel):
    primary: BaseChatModel
    fallback: BaseChatModel
    timeout_seconds: int | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def _llm_type(self) -> str:
        return "transient-fallback-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            return self.primary._generate(
                messages,
                stop=stop,
                run_manager=run_manager,
                **kwargs,
            )
        except Exception as exc:
            if is_transient_provider_error(exc):
                return self.fallback._generate(
                    messages,
                    stop=stop,
                    run_manager=run_manager,
                    **kwargs,
                )
            raise

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            primary_call = self.primary._agenerate(
                messages,
                stop=stop,
                run_manager=run_manager,
                **kwargs,
            )
            if self.timeout_seconds is None:
                return await primary_call

            return await asyncio.wait_for(primary_call, timeout=self.timeout_seconds)
        except Exception as exc:
            if is_transient_provider_error(exc):
                return await self.fallback._agenerate(
                    messages,
                    stop=stop,
                    run_manager=run_manager,
                    **kwargs,
                )
            raise


def get_llm(settings: Settings = settings) -> BaseChatModel:
    provider = settings.llm.provider

    if provider == "openrouter":
        return _build_openrouter_llm(settings=settings)

    primary_llm = _build_maritaca_llm(settings=settings)
    has_fallback = settings.llm.enable_fallback and provider in {"auto", "maritaca"}
    if not has_fallback:
        return primary_llm

    fallback_llm = _build_openrouter_llm(settings=settings)
    return TransientFallbackChatModel(
        primary=primary_llm,
        fallback=fallback_llm,
        timeout_seconds=settings.llm.timeout_seconds,
    )


def get_maritalk_llm(settings: Settings = settings) -> ChatMaritalk:
    return _build_maritaca_llm(settings=settings)


def is_transient_provider_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, APITimeoutError)):
        return True

    if isinstance(exc, httpx.TimeoutException):
        return True

    if isinstance(exc, RateLimitError):
        return True

    if isinstance(exc, (APIConnectionError, httpx.TransportError)):
        return True

    if isinstance(exc, APIStatusError):
        return exc.status_code in TRANSIENT_HTTP_STATUS_CODES

    if isinstance(exc, MaritalkHTTPError):
        return exc.status_code in TRANSIENT_HTTP_STATUS_CODES

    return False


def _build_maritaca_llm(*, settings: Settings) -> ChatMaritalk:
    api_key = _clean_optional_api_key(settings.maritaca_api_key)
    if api_key is None:
        raise LLMConfigurationError("MARITACA_API_KEY is required for Maritaca chat.")

    return ChatMaritalk(
        api_key=api_key,
        model=settings.maritaca_model,
        temperature=0.2,
    )


def _build_openrouter_llm(*, settings: Settings) -> ChatOpenAI:
    api_key = _clean_optional_api_key(settings.openrouter.api_key)
    if api_key is None:
        raise LLMConfigurationError("OPENROUTER_API_KEY is required for OpenRouter chat.")

    return ChatOpenAI(
        model=settings.openrouter.chat_model,
        api_key=SecretStr(api_key),
        base_url=OPENROUTER_BASE_URL,
        temperature=0.2,
        timeout=settings.llm.timeout_seconds,
        max_retries=0,
    )


def _clean_optional_api_key(api_key: str | None) -> str | None:
    if api_key is None:
        return None

    clean_api_key = api_key.strip()
    if not clean_api_key:
        return None

    return clean_api_key
