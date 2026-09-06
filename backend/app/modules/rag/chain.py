from __future__ import annotations

import re
from collections.abc import Callable
from typing import cast

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough


NO_CONTEXT_MESSAGE = (
    "Nenhum trecho relevante foi recuperado para esta pergunta. "
    "Informe que a bula disponivel nao trouxe contexto suficiente."
)
CITATION_PATTERN = re.compile(r"\[(\d+)\]")

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Voce e um farmaceutico que ajuda pacientes brasileiros a entender "
                "bulas de medicamentos. Responda em portugues brasileiro, com "
                "linguagem clara e cuidadosa. Use somente o contexto recuperado. "
                "Nao invente informacoes medicas, doses, contraindicacoes ou "
                "orientacoes que nao estejam no contexto. Cada trecho recuperado "
                "tem um numero. Cite somente os trechos efetivamente usados pelo "
                "numero exato, por exemplo: [1] ou [2]. Nao cite um trecho que nao "
                "sustente a afirmacao. Os trechos "
                "recuperados nao representam necessariamente a bula inteira. "
                "Nunca conclua que uma informacao nao existe na bula apenas porque "
                "ela nao aparece nesses trechos. Se o contexto nao for suficiente, "
                "diga especificamente que a informacao nao foi encontrada nos "
                "trechos recuperados e oriente o usuario a consultar a bula completa "
                "ou um profissional de saude."
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
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
    ) -> Runnable[dict[str, object], dict[str, object]]:
        retriever = self.dense_retriever_builder(bula_id)
        llm = self.llm_builder()
        return build_dense_rag_chain(retriever=retriever, llm=llm)


def build_dense_rag_chain(
    *,
    retriever: BaseRetriever,
    llm: BaseChatModel,
) -> Runnable[dict[str, object], dict[str, object]]:
    retrieve_documents = RunnableLambda(_build_retrieval_query) | retriever
    answer_chain = (
        RunnableLambda(_build_prompt_input) | RAG_PROMPT | llm | StrOutputParser()
    )
    chain = RunnablePassthrough.assign(documents=retrieve_documents).assign(
        answer=answer_chain
    ) | RunnableLambda(_build_chain_output)
    return cast(Runnable[dict[str, object], dict[str, object]], chain)


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


def _build_retrieval_query(inputs: dict[str, object]) -> str:
    question = str(inputs["question"]).strip()
    drug_name = str(inputs.get("drug_name", "")).strip()
    chat_history = cast(list[BaseMessage], inputs.get("chat_history", []))

    query_parts: list[str] = []
    if drug_name:
        query_parts.append(f"Medicamento: {drug_name}.")

    previous_user_question = _get_previous_user_question(chat_history)
    if previous_user_question and _looks_like_follow_up(question):
        query_parts.append(f"Pergunta anterior: {previous_user_question}")

    query_parts.append(f"Pergunta atual: {question}")
    return " ".join(query_parts)


def _get_previous_user_question(chat_history: list[BaseMessage]) -> str | None:
    for message in reversed(chat_history):
        if message.type != "human":
            continue

        content = str(message.content).strip()
        if content:
            return content

    return None


def _looks_like_follow_up(question: str) -> bool:
    normalized_question = question.casefold().lstrip()
    follow_up_prefixes = (
        "e ",
        "e para ",
        "e em ",
        "e se ",
        "tambem",
        "também",
        "isso",
        "esse",
        "essa",
        "este",
        "esta",
    )
    return normalized_question.startswith(follow_up_prefixes)


def _build_prompt_input(inputs: dict[str, object]) -> dict[str, object]:
    documents = cast(list[Document], inputs["documents"])
    chat_history = cast(list[BaseMessage], inputs.get("chat_history", []))
    return {
        "context": format_documents(documents),
        "question": str(inputs["question"]),
        "chat_history": chat_history,
    }


def _build_chain_output(inputs: dict[str, object]) -> dict[str, object]:
    documents = cast(list[Document], inputs["documents"])
    answer = str(inputs["answer"]).strip()
    normalized_answer, cited_documents = _select_cited_documents(
        answer=answer,
        documents=documents,
    )
    return {
        "answer": normalized_answer,
        "source_chunks": build_source_chunks(cited_documents),
    }


def _select_cited_documents(
    *,
    answer: str,
    documents: list[Document],
) -> tuple[str, list[Document]]:
    cited_document_numbers: list[int] = []
    for citation_match in CITATION_PATTERN.finditer(answer):
        document_number = int(citation_match.group(1))
        if document_number < 1 or document_number > len(documents):
            continue
        if document_number in cited_document_numbers:
            continue

        cited_document_numbers.append(document_number)

    cited_document_numbers.sort(
        key=lambda document_number: _get_relevance_score(
            document=documents[document_number - 1]
        ),
        reverse=True,
    )
    citation_number_mapping = {
        original_number: displayed_number
        for displayed_number, original_number in enumerate(
            cited_document_numbers,
            start=1,
        )
    }

    def replace_citation(citation_match: re.Match[str]) -> str:
        original_number = int(citation_match.group(1))
        displayed_number = citation_number_mapping.get(original_number)
        if displayed_number is None:
            return citation_match.group(0)

        return f"[{displayed_number}]"

    normalized_answer = CITATION_PATTERN.sub(replace_citation, answer)
    cited_documents = [
        documents[document_number - 1] for document_number in cited_document_numbers
    ]
    return normalized_answer, cited_documents


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
    except TypeError, ValueError:
        return 0.0
