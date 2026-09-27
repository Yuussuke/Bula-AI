from uuid import UUID

import pytest
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.modules.rag.retrieval_mode import RetrievalMode
from app.modules.rag.retriever_factory import RetrieverStrategyFactory


class StrategyRetriever(BaseRetriever):
    mode: RetrievalMode
    bula_id: UUID
    k: int

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return [
            Document(
                page_content=f"{self.mode.value}: {query}",
                metadata={"bula_id": str(self.bula_id), "k": self.k},
            )
        ]


class RecordingBuilder:
    def __init__(self, mode: RetrievalMode) -> None:
        self.mode = mode
        self.is_built = False

    def __call__(self, *, bula_id: UUID, k: int) -> BaseRetriever:
        self.is_built = True
        return StrategyRetriever(mode=self.mode, bula_id=bula_id, k=k)


@pytest.mark.anyio
@pytest.mark.parametrize("mode", list(RetrievalMode))
async def test_selected_strategy_receives_scope_and_other_builders_stay_idle(
    mode: RetrievalMode,
) -> None:
    builders = {strategy: RecordingBuilder(strategy) for strategy in RetrievalMode}
    factory = RetrieverStrategyFactory(builders=builders)
    bula_id = UUID(int=1)

    retriever = factory.build(mode=mode, bula_id=bula_id, k=7)
    documents = await retriever.ainvoke("pergunta")

    assert documents[0].page_content == f"{mode.value}: pergunta"
    assert documents[0].metadata == {"bula_id": str(bula_id), "k": 7}
    assert [strategy for strategy, builder in builders.items() if builder.is_built] == [
        mode
    ]


def test_missing_strategy_fails_at_composition_time() -> None:
    with pytest.raises(ValueError, match="every retrieval mode"):
        RetrieverStrategyFactory(
            builders={RetrievalMode.DENSE: RecordingBuilder(RetrievalMode.DENSE)}
        )
