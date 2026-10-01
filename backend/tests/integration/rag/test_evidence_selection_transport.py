"""Exercise the real chat adapter/chain with only external HTTP replaced."""

import json
from typing import Any

import httpx
import pytest
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI
from openai import BadRequestError

from app.core.config import LLMSettings, OpenRouterSettings, Settings
from app.modules.rag import llm as rag_llm
from app.modules.rag.chain import build_rag_chain


class SourceRetriever(BaseRetriever):
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return [
            Document(
                page_content="Esta apresentação não é recomendada para menores de 12 anos.",
                metadata={"section_title": "Restrições"},
            )
        ]


@pytest.mark.anyio
@pytest.mark.parametrize("primary_status", [200, 503, 400])
async def test_selection_schema_reaches_primary_and_transient_fallback(
    monkeypatch: pytest.MonkeyPatch, primary_status: int
) -> None:
    contacted_hosts: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        contacted_hosts.append(request.url.host)
        payload = json.loads(request.content)
        response_format = payload.get("response_format", {})
        schema = response_format.get("json_schema", {})
        has_selection_schema = (
            response_format.get("type") == "json_schema"
            and schema.get("strict") is True
            and schema.get("schema", {}).get("additionalProperties") is False
            and set(schema.get("schema", {}).get("required", []))
            == {"unit_ids", "limitation"}
        )
        if request.url.host == "chat.maritaca.ai" and primary_status != 200:
            return httpx.Response(
                primary_status,
                json={
                    "error": {"message": "Test provider error", "type": "test_error"}
                },
            )
        if request.url.host == "openrouter.ai":
            assert payload["provider"]["require_parameters"] is True
        content = (
            '{"unit_ids":["E1"],"limitation":null}'
            if has_selection_schema
            else "unit_ids: [E1]"
        )
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(respond)
    real_chat_model = ChatOpenAI
    with httpx.Client(transport=transport) as sync_client:
        async with httpx.AsyncClient(transport=transport) as async_client:

            def build_http_model(**kwargs: Any) -> ChatOpenAI:
                return real_chat_model(
                    **kwargs, http_client=sync_client, http_async_client=async_client
                )

            monkeypatch.setattr(rag_llm, "ChatOpenAI", build_http_model)
            settings = Settings(
                secret_key="long_and_secure_secret_key_for_testing_purposes_only_1234567890",
                maritaca_api_key="maritaca-test-key",
                llm=LLMSettings(
                    provider="auto", enable_fallback=True, timeout_seconds=5
                ),
                openrouter=OpenRouterSettings(api_key="openrouter-test-key"),
            )
            chain = build_rag_chain(
                retriever=SourceRetriever(), llm=rag_llm.get_llm(settings=settings)
            )
            if primary_status == 400:
                with pytest.raises(BadRequestError):
                    await chain.ainvoke(
                        {"question": "Qual restrição a bula apresenta?"}
                    )
                assert contacted_hosts == ["chat.maritaca.ai"]
                return
            result = await chain.ainvoke(
                {"question": "Qual restrição a bula apresenta?"}
            )
            assert "não é recomendada para menores de 12 anos" in result["answer"]
            assert len(result["source_chunks"]) == 1
            assert contacted_hosts == (
                ["chat.maritaca.ai", "openrouter.ai"]
                if primary_status == 503
                else ["chat.maritaca.ai"]
            )
