from pathlib import Path
from typing import cast

import pytest
from langchain_core.embeddings import Embeddings as LCEmbeddings
from openai import AsyncOpenAI

from app.modules.rag.chunker import BulaChunker
from app.modules.rag.debug_artifacts import RAGIngestionDebugArtifacts
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.schemas import ChunkingConfig


FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "rag"
DIPIRONA_PDF = FIXTURE_ROOT / "bulas" / "dipirona_sanofi_medley_solucao_oral.pdf"


class UnusedOpenAIClient:
    pass


class RecordingEmbeddings:
    def __init__(self) -> None:
        self.documents: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.documents.extend(texts)
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        _ = text
        return [0.1, 0.2, 0.3, 0.4]


class WordTokenEstimator:
    def estimate(self, text: str) -> int:
        return max(1, len(text.split()))


@pytest.mark.anyio
async def test_real_dipirona_table_survives_deterministic_fallback_pipeline(
    tmp_path: Path,
) -> None:
    parser = BulaParser()
    parse_result = await parser.parse(
        pdf_bytes=DIPIRONA_PDF.read_bytes(),
        filename=DIPIRONA_PDF.name,
    )
    chunker = BulaChunker(
        llm=cast(AsyncOpenAI, UnusedOpenAIClient()),
        config=ChunkingConfig(
            target_tokens=120,
            min_tokens=20,
            max_tokens=200,
            overlap_ratio=0,
            model="unused-model",
            is_llm_enabled=False,
        ),
        token_estimator=WordTokenEstimator(),
    )

    chunk_result = await chunker.chunk_markdown(
        markdown=parse_result.markdown,
        doc_id="dipirona-real-fixture",
    )

    chunk_texts = [chunk.text for chunk in chunk_result.chunks]
    dosage_table_chunks = [
        chunk_text
        for chunk_text in chunk_texts
        if "Peso (média de idade)" in chunk_text
    ]
    assert dosage_table_chunks
    assert any(
        "| 5 a 8 kg (3 a 11 meses) | Dose única | 1,25 a 2,5 | 62,5 a 125 |"
        in chunk_text
        for chunk_text in dosage_table_chunks
    )
    assert any(
        "| 5 a 8 kg (3 a 11 meses) | Dose máxima diária | "
        "10(4 tomadas x 2,5 mL) | 500 |" in chunk_text
        for chunk_text in dosage_table_chunks
    )
    assert all(chunk.token_estimate <= 200 for chunk in chunk_result.chunks)
    assert all(chunk.method == "deterministic" for chunk in chunk_result.chunks)
    fallback_metadata = cast(dict[str, object], chunk_result.metadata["fallback"])
    assert fallback_metadata["count"] == chunk_result.metadata["section_count"]

    recording_embeddings = RecordingEmbeddings()
    embedding_adapter = EmbeddingAdapter(
        embedder=cast(LCEmbeddings, recording_embeddings),
        batch_size=8,
        dimension=4,
    )
    vectors = embedding_adapter.embed_documents(chunk_texts)
    assert len(vectors) == len(chunk_result.chunks)
    assert recording_embeddings.documents == chunk_texts

    debug_writer = RAGIngestionDebugArtifacts(
        enabled=True,
        root_path=tmp_path / "rag-debug",
    )
    await debug_writer.write_run_artifacts(
        run_id="run-1",
        doc_id="dipirona-real-fixture",
        filename=DIPIRONA_PDF.name,
        status="success",
        parse_result=parse_result,
        markdown=parse_result.markdown,
        chunk_result=chunk_result,
        chunking_config=chunker.config,
    )

    manifest_text = (
        tmp_path / "rag-debug" / "dipirona-real-fixture" / "run-1" / "manifest.json"
    ).read_text(encoding="utf-8")
    assert '"semantic_chunking_disabled"' in manifest_text
    assert "provider_payload" not in manifest_text
    assert "system_prompt" not in manifest_text
