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
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from app.modules.rag.chain import (
    build_dense_rag_chain,
    build_source_chunks,
    format_documents,
)


class FakeRetriever(BaseRetriever):
    documents: list[Document]
    queries: list[str] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        self.queries.append(query)
        _ = run_manager
        return self.documents

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        self.queries.append(query)
        _ = run_manager
        return self.documents


class FakeChatModel(BaseChatModel):
    response: str
    received_messages: list[BaseMessage] = Field(default_factory=list)

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
        self.received_messages = list(messages)
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


def build_document(
    *,
    section_title: str = "Posologia",
    content: str = "Dose usual: 1 comprimido apos as refeicoes.",
    score: float = 0.95,
) -> Document:
    return Document(
        page_content=content,
        metadata={"section_title": section_title, "score": score},
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
    retriever = FakeRetriever(documents=[build_document()])
    chain = build_dense_rag_chain(
        retriever=retriever,
        llm=FakeChatModel(response="Tome conforme indicado no trecho [1]."),
    )

    result = await chain.ainvoke(
        {
            "question": "Como devo tomar?",
            "drug_name": "Dipirona",
        }
    )

    assert result["answer"] == "Tome conforme indicado no trecho [1]."
    assert result["source_chunks"] == [
        {
            "section_title": "Posologia",
            "chunk_text": "Dose usual: 1 comprimido apos as refeicoes.",
            "relevance_score": 0.95,
        }
    ]
    assert retriever.queries == [
        "Medicamento: Dipirona. Pergunta atual: Como devo tomar?"
    ]


@pytest.mark.anyio
async def test_chain_returns_only_cited_documents_and_renumbers_sources() -> None:
    retriever = FakeRetriever(
        documents=[
            build_document(),
            build_document(
                section_title="Advertencias",
                content="O tratamento exige acompanhamento medico.",
                score=0.91,
            ),
        ]
    )
    chain = build_dense_rag_chain(
        retriever=retriever,
        llm=FakeChatModel(
            response="Consulte seu medico conforme o trecho [2]. Releia [2]."
        ),
    )

    result = await chain.ainvoke(
        {
            "question": "Preciso de acompanhamento?",
            "drug_name": "Dipirona",
        }
    )

    assert result["answer"] == "Consulte seu medico conforme o trecho [1]. Releia [1]."
    assert result["source_chunks"] == [
        {
            "section_title": "Advertencias",
            "chunk_text": "O tratamento exige acompanhamento medico.",
            "relevance_score": 0.91,
        }
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("invalid_citation", ["[0]", "[99]"])
async def test_chain_removes_invalid_citations_without_dropping_valid_sources(
    invalid_citation: str,
) -> None:
    chain = build_dense_rag_chain(
        retriever=FakeRetriever(documents=[build_document()]),
        llm=FakeChatModel(
            response=(
                "Orientacao sustentada pelo trecho [1]. "
                f"Referencia inexistente {invalid_citation}."
            )
        ),
    )

    result = await chain.ainvoke(
        {
            "question": "Qual e a orientacao?",
            "drug_name": "Dipirona",
        }
    )

    assert result["answer"] == (
        "Orientacao sustentada pelo trecho [1]. Referencia inexistente."
    )
    assert result["source_chunks"] == [
        {
            "section_title": "Posologia",
            "chunk_text": "Dose usual: 1 comprimido apos as refeicoes.",
            "relevance_score": 0.95,
        }
    ]


@pytest.mark.anyio
async def test_chain_numbers_cited_sources_by_relevance_not_mention_order() -> None:
    retriever = FakeRetriever(
        documents=[
            build_document(
                section_title="Mais relevante",
                content="Evidencia principal.",
                score=0.96,
            ),
            build_document(
                section_title="Menos relevante",
                content="Evidencia complementar.",
                score=0.82,
            ),
        ]
    )
    chain = build_dense_rag_chain(
        retriever=retriever,
        llm=FakeChatModel(response="Complemento [2]. Evidencia principal [1]."),
    )

    result = await chain.ainvoke(
        {
            "question": "Qual e a orientacao?",
            "drug_name": "Dipirona",
        }
    )

    assert result["answer"] == "Complemento [2]. Evidencia principal [1]."
    assert [
        source_chunk["section_title"] for source_chunk in result["source_chunks"]
    ] == ["Mais relevante", "Menos relevante"]


@pytest.mark.anyio
async def test_chain_returns_no_sources_when_answer_does_not_cite_context() -> None:
    chain = build_dense_rag_chain(
        retriever=FakeRetriever(documents=[build_document()]),
        llm=FakeChatModel(response="Os trechos recuperados nao sao suficientes."),
    )

    result = await chain.ainvoke(
        {
            "question": "Ha informacao suficiente?",
            "drug_name": "Dipirona",
        }
    )

    assert result["source_chunks"] == []


@pytest.mark.anyio
async def test_chain_includes_prior_messages_before_current_question() -> None:
    chat_model = FakeChatModel(response="Resposta contextual.")
    retriever = FakeRetriever(documents=[build_document()])
    chain = build_dense_rag_chain(
        retriever=retriever,
        llm=chat_model,
    )

    await chain.ainvoke(
        {
            "question": "E para criancas?",
            "drug_name": "Dipirona",
            "chat_history": [
                HumanMessage(content="Como devo usar este medicamento?"),
                AIMessage(content="Use conforme a secao [Posologia]."),
            ],
        }
    )

    assert [message.content for message in chat_model.received_messages[1:3]] == [
        "Como devo usar este medicamento?",
        "Use conforme a secao [Posologia].",
    ]
    assert "E para criancas?" in str(chat_model.received_messages[-1].content)
    assert retriever.queries == [
        "Medicamento: Dipirona. "
        "Pergunta anterior: Como devo usar este medicamento? "
        "Pergunta atual: E para criancas?"
    ]
    assert "Nunca conclua que uma informacao nao existe na bula" in str(
        chat_model.received_messages[0].content
    )
