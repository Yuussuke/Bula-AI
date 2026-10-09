from uuid import UUID

import pytest
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.modules.bulas.models import BulaCorpus
from app.modules.rag.retrieval_mode import RetrievalMode
from app.modules.rag.retriever_factory import RetrieverStrategyFactory


class StrategyRetriever(BaseRetriever):
    mode: RetrievalMode
    bula_id: UUID | None
    corpus: tuple[BulaCorpus, ...] | None
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

    def __call__(
        self, *, bula_id: UUID | None, corpus: tuple[BulaCorpus, ...] | None, k: int
    ) -> BaseRetriever:
        self.is_built = True
        return StrategyRetriever(mode=self.mode, bula_id=bula_id, corpus=corpus, k=k)


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


@pytest.mark.parametrize("mode", list(RetrievalMode))
def test_strategy_accepts_corpus_scope_without_a_bula(mode: RetrievalMode) -> None:
    builders = {strategy: RecordingBuilder(strategy) for strategy in RetrievalMode}
    factory = RetrieverStrategyFactory(builders=builders)

    retriever = factory.build(
        mode=mode, bula_id=None, corpus=[BulaCorpus.SHARED, BulaCorpus.SYSTEM]
    )

    assert isinstance(retriever, StrategyRetriever)
    assert retriever.k == 10
    assert retriever.bula_id is None
    assert retriever.corpus == (BulaCorpus.SHARED, BulaCorpus.SYSTEM)
    assert [strategy for strategy, builder in builders.items() if builder.is_built] == [
        mode
    ]


def test_unscoped_strategy_is_rejected_before_initialization() -> None:
    builders = {strategy: RecordingBuilder(strategy) for strategy in RetrievalMode}
    factory = RetrieverStrategyFactory(builders=builders)

    with pytest.raises(ValueError, match="explicit corpus scope"):
        factory.build(mode=RetrievalMode.HYBRID, bula_id=None)

    assert not any(builder.is_built for builder in builders.values())


def test_missing_strategy_fails_at_composition_time() -> None:
    with pytest.raises(ValueError, match="every retrieval mode"):
        RetrieverStrategyFactory(
            builders={RetrievalMode.DENSE: RecordingBuilder(RetrievalMode.DENSE)}
        )
