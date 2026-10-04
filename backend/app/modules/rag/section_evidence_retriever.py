"""Add bounded safety-section evidence to a bula-scoped retrieval result."""

import re
import unicodedata
from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.schemas import ChunkMetadataInput


CONTRAINDICATION_SECTION_TITLES = (
    "QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?",
    "CONTRAINDICAÇÕES",
    "O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?",
)
SAFETY_QUESTION_PATTERN = re.compile(
    r"\b(?:contraindic\w*|alerg\w*|hipersensib\w*|penicilin\w*)\b"
    r"|\b(?:quem|quando) nao (?:deve|devo|pode|posso) usar\b"
)
DIRECT_CONTRAINDICATION_PATTERN = re.compile(
    r"\b(?:quem|quando) nao (?:deve|devo|pode|posso) usar\b"
    r"|\bquais(?: sao)?(?: as)? contraindic\w*\b"
    r"|^contraindic\w*\b"
)


def is_contraindication_question(question: str) -> bool:
    return SAFETY_QUESTION_PATTERN.search(_without_accents(question)) is not None


def is_direct_contraindication_question(question: str) -> bool:
    return (
        DIRECT_CONTRAINDICATION_PATTERN.search(_without_accents(question)) is not None
    )


def is_contraindication_section(section_title: str) -> bool:
    normalized = _without_accents(section_title)
    return "quando nao devo usar" in normalized or "contraindic" in normalized


def _without_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    )


@runtime_checkable
class SectionEvidenceIndex(Protocol):
    async def find_section_evidence(
        self,
        *,
        bula_id: UUID,
        section_titles: Sequence[str],
        limit: int = 2,
    ) -> list[ChunkMetadataInput]: ...


class SectionEvidenceRetriever(BaseRetriever):
    """Keep the selected strategy and supplement its result from the same bula.

    Authorization is performed by the chat service before this retriever is
    constructed. The repository query is independently scoped to the bula ID.
    """

    wrapped_retriever: BaseRetriever
    index: SectionEvidenceIndex = Field(exclude=True, repr=False)
    bula_id: UUID
    corpus: tuple[BulaCorpus, ...] | None = None
    section_limit: int = Field(default=2, ge=1, le=4)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        documents = await self.wrapped_retriever.ainvoke(query)
        if self.corpus == ():
            return []
        if not is_contraindication_question(query):
            return documents

        # The BM25 branch and this query can share one AsyncSession. Await the
        # wrapped retrieval first so the session is never used concurrently.
        section_chunks = await self.index.find_section_evidence(
            bula_id=self.bula_id,
            section_titles=CONTRAINDICATION_SECTION_TITLES,
            limit=self.section_limit,
        )
        seen_chunk_ids = {document.metadata.get("chunk_id") for document in documents}
        supplemental_documents: list[Document] = []
        for chunk in section_chunks:
            if chunk.bula_id != self.bula_id:
                raise ValueError("Section evidence belongs to another bula.")
            if self.corpus is not None and chunk.corpus not in self.corpus:
                continue
            if chunk.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk.chunk_id)
            supplemental_documents.append(
                Document(
                    id=chunk.chunk_id,
                    page_content=chunk.chunk_text,
                    metadata={
                        "chunk_id": chunk.chunk_id,
                        "doc_id": chunk.doc_id,
                        "bula_id": str(chunk.bula_id),
                        "corpus": chunk.corpus.value,
                        "drug_name": chunk.drug_name,
                        "section_title": chunk.section_title,
                        "score": 0.0,
                        "section_evidence": True,
                    },
                )
            )

        return supplemental_documents + documents

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        raise RuntimeError("SectionEvidenceRetriever requires async ainvoke().")
