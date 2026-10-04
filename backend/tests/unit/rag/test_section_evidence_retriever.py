from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from langchain_core.callbacks import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.schemas import ChunkMetadataInput
from app.modules.rag.section_evidence_retriever import (
    SectionEvidenceIndex,
    SectionEvidenceRetriever,
)


class ExistingResultsRetriever(BaseRetriever):
    documents: list[Document]
    queries: list[str] = Field(default_factory=list)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun,
    ) -> list[Document]:
        self.queries.append(query)
        return self.documents

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        raise RuntimeError("Use the async path.")


def safety_chunk(bula_id: UUID, chunk_id: str = "contra") -> ChunkMetadataInput:
    return ChunkMetadataInput(
        chunk_id=chunk_id,
        doc_id=str(bula_id),
        bula_id=bula_id,
        corpus=BulaCorpus.SYSTEM,
        drug_name="Amoxicilina",
        section_title="QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?",
        chunk_text="A amoxicilina é contraindicada para pessoas com alergia a penicilinas.",
    )


@pytest.mark.anyio
async def test_safety_question_adds_missing_evidence_from_selected_bula() -> None:
    bula_id = UUID(int=1)
    existing_retriever = ExistingResultsRetriever(
        documents=[
            Document(
                page_content="Use com cautela se houver problemas no fígado.",
                metadata={"chunk_id": "warning", "section_title": "Advertências"},
            )
        ]
    )
    section_index = AsyncMock(spec=SectionEvidenceIndex)
    section_index.find_section_evidence.return_value = [safety_chunk(bula_id)]
    retriever = SectionEvidenceRetriever(
        wrapped_retriever=existing_retriever,
        index=section_index,
        bula_id=bula_id,
    )

    documents = await retriever.ainvoke("Quem não pode usar este medicamento?")

    assert [document.metadata["chunk_id"] for document in documents] == [
        "contra",
        "warning",
    ]
    assert "alergia a penicilinas" in documents[0].page_content
    assert documents[0].metadata["bula_id"] == str(bula_id)
    section_index.find_section_evidence.assert_awaited_once()
    assert section_index.find_section_evidence.call_args.kwargs["bula_id"] == bula_id


@pytest.mark.anyio
async def test_safety_evidence_deduplicates_existing_chunk() -> None:
    bula_id = UUID(int=1)
    existing_retriever = ExistingResultsRetriever(
        documents=[
            Document(
                page_content=safety_chunk(bula_id).chunk_text,
                metadata={"chunk_id": "contra"},
            )
        ]
    )
    section_index = AsyncMock(spec=SectionEvidenceIndex)
    section_index.find_section_evidence.return_value = [safety_chunk(bula_id)]
    retriever = SectionEvidenceRetriever(
        wrapped_retriever=existing_retriever,
        index=section_index,
        bula_id=bula_id,
    )

    documents = await retriever.ainvoke("Tenho alergia a penicilinas. Posso usar?")

    assert len(documents) == 1
    assert documents[0].metadata["chunk_id"] == "contra"


@pytest.mark.anyio
async def test_unrelated_question_does_not_expand_context() -> None:
    bula_id = UUID(int=1)
    existing_retriever = ExistingResultsRetriever(documents=[])
    section_index = AsyncMock(spec=SectionEvidenceIndex)
    retriever = SectionEvidenceRetriever(
        wrapped_retriever=existing_retriever,
        index=section_index,
        bula_id=bula_id,
    )

    assert await retriever.ainvoke("Como devo guardar o medicamento?") == []
    section_index.find_section_evidence.assert_not_awaited()


@pytest.mark.anyio
async def test_rejects_section_evidence_from_another_bula() -> None:
    section_index = AsyncMock(spec=SectionEvidenceIndex)
    section_index.find_section_evidence.return_value = [safety_chunk(UUID(int=2))]
    retriever = SectionEvidenceRetriever(
        wrapped_retriever=ExistingResultsRetriever(documents=[]),
        index=section_index,
        bula_id=UUID(int=1),
    )

    with pytest.raises(ValueError, match="another bula"):
        await retriever.ainvoke("Quais são as contraindicações?")


@pytest.mark.anyio
@pytest.mark.parametrize("corpus", [(BulaCorpus.SHARED,), (BulaCorpus.SYSTEM,), ()])
async def test_section_supplement_respects_corpus_scope(
    corpus: tuple[BulaCorpus, ...],
) -> None:
    bula_id = UUID(int=1)
    section_index = AsyncMock(spec=SectionEvidenceIndex)
    section_index.find_section_evidence.return_value = [safety_chunk(bula_id)]
    retriever = SectionEvidenceRetriever(
        wrapped_retriever=ExistingResultsRetriever(documents=[]),
        index=section_index,
        bula_id=bula_id,
        corpus=corpus,
    )

    documents = await retriever.ainvoke("Tenho alergia. Posso usar?")

    assert [document.metadata["chunk_id"] for document in documents] == (
        ["contra"] if BulaCorpus.SYSTEM in corpus else []
    )
    if not corpus:
        section_index.find_section_evidence.assert_not_awaited()
