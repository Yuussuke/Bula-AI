from __future__ import annotations

from collections.abc import Callable
from typing import cast

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough


NO_CONTEXT_MESSAGE = (
    "Nenhum trecho relevante foi recuperado para esta pergunta. "
    "Informe que a bula disponivel nao trouxe contexto suficiente."
)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Voce e um farmaceutico que ajuda pacientes brasileiros a entender "
                "bulas de medicamentos. Responda em portugues brasileiro, com "
                "linguagem clara e cuidadosa. Use somente o contexto recuperado. "
                "Nao invente informacoes medicas, doses, contraindicacoes ou "
                "orientacoes que nao estejam no contexto. Cite as secoes usadas "
                "pelo titulo da secao, por exemplo: [Posologia]. Se o contexto "
                "nao for suficiente, diga isso explicitamente e oriente o usuario "
                "a consultar um profissional de saude."
            ),
        ),
        (
            "human",
            (
                "Contexto recuperado da bula:\n{context}\n\n"
                "Pergunta do paciente:\n{question}"
            ),
        ),
    ]
)


class RAGChainFactory:
    def __init__(
        self,
        *,
        dense_retriever_builder: Callable[[str], BaseRetriever],
        llm_builder: Callable[[], BaseChatModel],
    ) -> None:
        self.dense_retriever_builder = dense_retriever_builder
        self.llm_builder = llm_builder

    def build_dense_chain(
        self,
        *,
        bula_id: str,
    ) -> Runnable[dict[str, str], dict[str, object]]:
        retriever = self.dense_retriever_builder(bula_id)
        llm = self.llm_builder()
        return build_dense_rag_chain(retriever=retriever, llm=llm)


def build_dense_rag_chain(
    *,
    retriever: BaseRetriever,
    llm: BaseChatModel,
) -> Runnable[dict[str, str], dict[str, object]]:
    retrieve_documents = RunnableLambda(_extract_question) | retriever
    answer_chain = (
        RunnableLambda(_build_prompt_input) | RAG_PROMPT | llm | StrOutputParser()
    )
    chain = RunnablePassthrough.assign(documents=retrieve_documents).assign(
        answer=answer_chain
    ) | RunnableLambda(_build_chain_output)
    return cast(Runnable[dict[str, str], dict[str, object]], chain)


def format_documents(documents: list[Document]) -> str:
    if not documents:
        return NO_CONTEXT_MESSAGE

    formatted_documents: list[str] = []
    for index, document in enumerate(documents, start=1):
        section_title = _get_metadata_text(
            document=document,
            key="section_title",
            fallback="Secao nao identificada",
        )
        formatted_documents.append(
            f"[{index}] Secao: {section_title}\nTrecho: {document.page_content}"
        )

    return "\n\n".join(formatted_documents)


def build_source_chunks(documents: list[Document]) -> list[dict[str, object]]:
    return [
        {
            "section_title": _get_metadata_text(
                document=document,
                key="section_title",
                fallback="Secao nao identificada",
            ),
            "chunk_text": document.page_content,
            "relevance_score": _get_relevance_score(document=document),
        }
        for document in documents
    ]


def _extract_question(inputs: dict[str, str]) -> str:
    return inputs["question"]


def _build_prompt_input(inputs: dict[str, object]) -> dict[str, str]:
    documents = cast(list[Document], inputs["documents"])
    return {
        "context": format_documents(documents),
        "question": str(inputs["question"]),
    }


def _build_chain_output(inputs: dict[str, object]) -> dict[str, object]:
    documents = cast(list[Document], inputs["documents"])
    return {
        "answer": str(inputs["answer"]).strip(),
        "source_chunks": build_source_chunks(documents),
    }


def _get_metadata_text(*, document: Document, key: str, fallback: str) -> str:
    value = document.metadata.get(key)
    if value is None:
        return fallback

    text = str(value).strip()
    if not text:
        return fallback

    return text


def _get_relevance_score(*, document: Document) -> float:
    score = document.metadata.get("score", 0.0)
    try:
        return float(score)
    except (TypeError, ValueError):
        return 0.0
