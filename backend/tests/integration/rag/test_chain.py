from typing import Any

import pytest
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForLLMRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from app.modules.rag.chain import (
    build_dense_rag_chain,
    build_source_chunks,
    format_documents,
)


class FakeRetriever(BaseRetriever):
    documents: list[Document]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = query
        _ = run_manager
        return self.documents

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        _ = query
        _ = run_manager
        return self.documents


class FakeChatModel(BaseChatModel):
    response: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def _llm_type(self) -> str:
        return "fake-chain-chat-model"

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
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self.response))]
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._generate(
            messages,
            stop=stop,
            run_manager=None,
            **kwargs,
        )


def build_document() -> Document:
    return Document(
        page_content="Dose usual: 1 comprimido apos as refeicoes.",
        metadata={"section_title": "Posologia", "score": 0.95},
    )


def test_format_documents_preserves_context_and_sections() -> None:
    context = format_documents([build_document()])

    assert "Secao: Posologia" in context
    assert "Dose usual: 1 comprimido" in context


def test_build_source_chunks_maps_relevance_score() -> None:
    source_chunks = build_source_chunks([build_document()])

    assert source_chunks == [
        {
            "section_title": "Posologia",
            "chunk_text": "Dose usual: 1 comprimido apos as refeicoes.",
            "relevance_score": 0.95,
        }
    ]


@pytest.mark.anyio
async def test_chain_with_mock_llm_produces_output() -> None:
    chain = build_dense_rag_chain(
        retriever=FakeRetriever(documents=[build_document()]),
        llm=FakeChatModel(response="Tome conforme indicado na secao [Posologia]."),
    )

    result = await chain.ainvoke({"question": "Como devo tomar?"})

    assert result["answer"] == "Tome conforme indicado na secao [Posologia]."
    assert result["source_chunks"] == [
        {
            "section_title": "Posologia",
            "chunk_text": "Dose usual: 1 comprimido apos as refeicoes.",
            "relevance_score": 0.95,
        }
    ]
