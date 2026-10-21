"""Natural response flow using real chain composition and synthetic providers."""

from typing import Any

import pytest
from langchain_core.callbacks import (
    CallbackManagerForRetrieverRun,
    CallbackManagerForLLMRun,
)
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.modules.rag.chain import (
    build_grounded_rag_chain,
    INSUFFICIENT_SPECIFIC_EVIDENCE_MESSAGE,
)
from app.modules.rag.grounded_generation import GroundedGenerationError


class SourceRetriever(BaseRetriever):
    documents: list[Document]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return self.documents


class SyntheticChatModel(BaseChatModel):
    responses: list[str]
    requests: list[dict[str, Any]] = Field(default_factory=list)
    finish_reason: str = "stop"

    @property
    def _llm_type(self) -> str:
        return "synthetic-natural-answer"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.requests.append({"messages": messages, "options": kwargs})
        content = self.responses[min(len(self.requests) - 1, len(self.responses) - 1)]
        metadata = {
            "finish_reason": self.finish_reason if len(self.requests) > 1 else "stop"
        }
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content=content, response_metadata=metadata)
                )
            ]
        )


def source(text: str, score: float = 1) -> Document:
    return Document(
        page_content=text, metadata={"section_title": "Conservação", "score": score}
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "answer",
    [
        "Guarde entre 15 e 30 °C [2] e proteja da umidade [1].",
    ],
)
async def test_natural_answer_uses_only_validated_units_and_keeps_citation_mapping(
    answer: str,
) -> None:
    model = SyntheticChatModel(
        responses=[
            '{"unit_ids":["E2","E3"],"limitation":null}',
            answer,
        ]
    )
    first = source("Uma frase não selecionada. Conservar entre 15 e 30 °C.", 0.1)
    second = source("Proteger da umidade.", 0.9)
    result = await build_grounded_rag_chain(
        retriever=SourceRetriever(documents=[first, second]), llm=model
    ).ainvoke({"question": "Como guardar?"})
    assert result["answer"] == model.responses[1]
    assert result["source_chunks"][0]["chunk_text"] == second.page_content
    generation_input = str(model.requests[1]["messages"][-1].content)
    assert "Uma frase não selecionada" not in generation_input
    assert "[2] Seção" in generation_input
    assert "Conservar entre 15 e 30 °C" in generation_input
    assert "generation_context" not in result
    assert result["response_diagnostics"]["claim_verification"] == "not_implemented"
    assert result["response_diagnostics"]["generation_status"] == "success"
    assert model.requests[0]["options"]["response_format"]["type"] == "json_schema"
    assert "response_format" not in model.requests[1]["options"]


@pytest.mark.anyio
async def test_valid_empty_selection_abstains_without_generation() -> None:
    model = SyntheticChatModel(responses=['{"unit_ids":[],"limitation":null}'])
    result = await build_grounded_rag_chain(
        retriever=SourceRetriever(documents=[source("Conservar protegido da luz.")]),
        llm=model,
    ).ainvoke({"question": "Uma dúvida sem suporte?"})
    assert result["answer"] == INSUFFICIENT_SPECIFIC_EVIDENCE_MESSAGE
    assert len(model.requests) == 1
    assert result["response_diagnostics"]["abstention_reason"] == "insufficient_context"
    assert result["response_diagnostics"]["technical_failure"] is None


@pytest.mark.anyio
async def test_invalid_selection_is_technical_failure_not_documentary_insufficiency() -> (
    None
):
    model = SyntheticChatModel(responses=['{"unit_ids":["E99"],"limitation":null}'])
    result = await build_grounded_rag_chain(
        retriever=SourceRetriever(documents=[source("Conservar protegido da luz.")]),
        llm=model,
    ).ainvoke({"question": "Como guardar?"})
    assert len(model.requests) == 1
    assert result["response_diagnostics"]["technical_failure"] == "unknown_evidence_id"
    assert result["response_diagnostics"]["abstention_reason"] is None
    assert result["response_diagnostics"]["abstained"] is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        ("", "empty_generated_answer"),
        ("Guarde na embalagem.", "missing_source_citation"),
        ("Proteja da luz [2].", "unknown_source_citation"),
    ],
)
async def test_invalid_generation_is_not_a_successful_abstention(
    answer: str, reason: str
) -> None:
    model = SyntheticChatModel(
        responses=['{"unit_ids":["E1"],"limitation":null}', answer]
    )
    chain = build_grounded_rag_chain(
        retriever=SourceRetriever(documents=[source("Proteger da luz.")]), llm=model
    )
    with pytest.raises(GroundedGenerationError) as error:
        await chain.ainvoke({"question": "Como guardar?"})
    assert error.value.reason == reason


@pytest.mark.anyio
async def test_partial_evidence_keeps_actual_limitation_and_table_conditions() -> None:
    table = source(
        "## Adultos com insuficiência renal\n\n| Condição | Intervalo |\n| --- | --- |\n| Grave | 12 horas |"
    )
    model = SyntheticChatModel(
        responses=[
            '{"unit_ids":["E1"],"limitation":"individual"}',
            "A tabela para adultos com insuficiência renal grave informa intervalo de 12 horas [1]. A dose individual depende da avaliação profissional.",
        ]
    )
    result = await build_grounded_rag_chain(
        retriever=SourceRetriever(documents=[table]), llm=model
    ).ainvoke({"question": "Como ajustar no meu caso?"})
    assert "insuficiência renal" in str(model.requests[1]["messages"][-1].content)
    assert result["response_diagnostics"]["limitation"] == "individual"


@pytest.mark.anyio
async def test_truncated_generation_is_rejected_even_with_valid_citation() -> None:
    model = SyntheticChatModel(
        responses=['{"unit_ids":["E1"],"limitation":null}', "Proteger da luz [1]."],
        finish_reason="length",
    )
    with pytest.raises(GroundedGenerationError, match="incomplete_generated_answer"):
        await build_grounded_rag_chain(
            retriever=SourceRetriever(documents=[source("Proteger da luz.")]), llm=model
        ).ainvoke({"question": "Como guardar?"})
