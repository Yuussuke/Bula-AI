from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from typing import cast
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough

from app.modules.rag.retrieval_mode import RetrievalMode
from app.modules.rag.retriever_factory import RetrieverStrategyFactory
from app.modules.rag.section_evidence_retriever import (
    is_contraindication_question,
    is_contraindication_section,
    is_direct_contraindication_question,
)


NO_CONTEXT_MESSAGE = (
    "Nenhum trecho relevante foi recuperado para esta pergunta. "
    "Informe que a bula disponivel nao trouxe contexto suficiente."
)
CITATION_PATTERN = re.compile(r"\[(\d+)\]")
CITATION_WITH_SPACING_PATTERN = re.compile(
    r"(?P<leading>[ \t]*)\[(?P<number>\d+)\](?P<trailing>[ \t]*)"
)
UNSUPPORTED_ALLERGY_ABSENCE_PATTERN = re.compile(
    r"(?:bula|trechos?)[^.!?]{0,120}nao (?:informa|menciona|contem)"
    r"[^.!?]{0,160}(?:alerg\w*|hipersensib\w*|penicilin\w*)"
)
UNSUPPORTED_BULA_ABSENCE_PATTERN = re.compile(
    r"\ba bula nao (?:informa|menciona|contem)\b"
)
ALLERGY_EVIDENCE_PATTERN = re.compile(r"alerg\w*|hipersensib\w*|penicilin\w*")

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
                "sustente a afirmacao. Diferencie contraindicacao de advertencia: "
                "so diga que alguem nao pode usar o medicamento quando o texto "
                "citado afirmar expressamente essa restricao. Uma orientacao para "
                "informar o medico sobre alergia ou para avaliar o caso exige "
                "cautela, mas nao equivale por si so a uma contraindicacao. "
                "Se ambas aparecerem, apresente-as separadamente. Os trechos "
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
        retriever_factory: RetrieverStrategyFactory,
        llm_builder: Callable[[], BaseChatModel],
    ) -> None:
        self.retriever_factory = retriever_factory
        self.llm_builder = llm_builder

    def build_chain(
        self,
        *,
        bula_id: UUID,
        mode: RetrievalMode,
    ) -> Runnable[dict[str, object], dict[str, object]]:
        retriever = self.retriever_factory.build(bula_id=bula_id, mode=mode)
        llm = self.llm_builder()
        return build_rag_chain(retriever=retriever, llm=llm)


def build_rag_chain(
    *,
    retriever: BaseRetriever,
    llm: BaseChatModel,
) -> Runnable[dict[str, object], dict[str, object]]:
    retrieve_documents = RunnableLambda(_build_retrieval_query) | retriever
    answer_chain = (
        RunnableLambda(_build_prompt_input) | RAG_PROMPT | llm | StrOutputParser()
    )
    chain = RunnablePassthrough.assign(documents=retrieve_documents).assign(
        documents=RunnableLambda(_select_answer_documents)
    ).assign(answer=answer_chain) | RunnableLambda(_build_chain_output)
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
    chat_history = cast(list[BaseMessage], inputs.get("chat_history", []))

    previous_user_question = _get_previous_user_question(chat_history)
    if previous_user_question and _looks_like_follow_up(question):
        return f"{previous_user_question} {question}"

    # The retriever is already scoped to the selected bula. Repeating its name
    # biases lexical ranking toward chunks with many mentions of that name.
    return question


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


def _select_answer_documents(inputs: dict[str, object]) -> list[Document]:
    documents = cast(list[Document], inputs["documents"])
    question = str(inputs["question"])
    if not is_direct_contraindication_question(question):
        return documents

    contraindication_documents = [
        document
        for document in documents
        if is_contraindication_section(str(document.metadata.get("section_title", "")))
    ]
    return contraindication_documents or documents


def _build_chain_output(inputs: dict[str, object]) -> dict[str, object]:
    documents = cast(list[Document], inputs["documents"])
    answer = str(inputs["answer"]).strip()
    answer = _correct_unsupported_allergy_absence(
        question=str(inputs["question"]), answer=answer, documents=documents
    )
    normalized_answer, cited_documents = _select_cited_documents(
        answer=answer,
        documents=documents,
    )
    return {
        "answer": normalized_answer,
        "source_chunks": build_source_chunks(cited_documents),
    }


def _correct_unsupported_allergy_absence(
    *, question: str, answer: str, documents: list[Document]
) -> str:
    """Use exact source wording if an answer denies allergy evidence we found."""
    if not is_contraindication_question(question):
        return answer

    normalized_answer = _without_accents(answer)
    if UNSUPPORTED_ALLERGY_ABSENCE_PATTERN.search(normalized_answer):
        for index, document in enumerate(documents, start=1):
            section_title = str(document.metadata.get("section_title", ""))
            if not is_contraindication_section(section_title):
                continue

            body = re.sub(
                r"(?m)^[ \t]{0,3}#{1,6}[ \t]+[^\r\n]*$", "", document.page_content
            )
            for sentence in re.split(r"(?<=[.!?])\s+", body.strip()):
                if ALLERGY_EVIDENCE_PATTERN.search(_without_accents(sentence)):
                    return (
                        f'A seção "{section_title}" da bula informa: "{sentence.strip()}" '
                        f"[{index}]. Confira esse trecho e consulte um profissional "
                        "de saúde para avaliar o seu caso."
                    )

    if UNSUPPORTED_BULA_ABSENCE_PATTERN.search(normalized_answer):
        return (
            "Os trechos recuperados não permitem confirmar que essa informação "
            "esteja ausente da bula. Consulte a bula completa ou um profissional "
            "de saúde para avaliar o seu caso."
        )

    return answer


def _without_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    )


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
        original_number = int(citation_match.group("number"))
        displayed_number = citation_number_mapping.get(original_number)
        if displayed_number is None:
            leading_spacing = citation_match.group("leading")
            trailing_spacing = citation_match.group("trailing")
            if leading_spacing and trailing_spacing:
                return " "

            return ""

        return (
            f"{citation_match.group('leading')}"
            f"[{displayed_number}]"
            f"{citation_match.group('trailing')}"
        )

    normalized_answer = CITATION_WITH_SPACING_PATTERN.sub(replace_citation, answer)
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
