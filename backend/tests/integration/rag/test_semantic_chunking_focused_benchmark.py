import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from langchain_core.embeddings import Embeddings as LCEmbeddings
from openai import AsyncOpenAI

from app.modules.rag.chunker import BulaChunker
from app.modules.rag.embeddings import EmbeddingAdapter
from app.modules.rag.parsers.pdf_parser import BulaParser
from app.modules.rag.schemas import ChunkingConfig
from scripts.benchmark_semantic_chunking import (
    FOCUSED_SECTION_SPECS,
    _find_focused_section,
    critical_content_preservation,
    has_complete_source_line_coverage,
    split_h2_sections,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "rag" / "bulas"
PDF_PATHS = {
    "dipirona": FIXTURE_ROOT / "dipirona_sanofi_medley_solucao_oral.pdf",
    "amoxicilina": FIXTURE_ROOT / "amoxicilina_cimed_suspensao_oral.pdf",
}


class SourceEchoCompletions:
    def __init__(self) -> None:
        self.request_count = 0
        self.active_request_count = 0
        self.max_active_request_count = 0

    async def create(self, **request: object) -> object:
        self.request_count += 1
        self.active_request_count += 1
        self.max_active_request_count = max(
            self.max_active_request_count,
            self.active_request_count,
        )
        try:
            messages = cast(list[dict[str, str]], request["messages"])
            response_format = cast(dict[str, Any], request["response_format"])
            schema_name = response_format["json_schema"]["name"]
            user_content = messages[-1]["content"]

            if schema_name == "batch_chunk_proposals":
                source_payload = user_content.split("Fontes em JSON:\n\n", maxsplit=1)[
                    1
                ]
                sections = json.loads(source_payload)
                response_payload = {
                    "chunks": [
                        {
                            "section_index": section["section_index"],
                            "chunk_text": section["section_text"],
                        }
                        for section in sections
                    ]
                }
            else:
                source_payload = user_content.split("Fonte da secao:\n\n", maxsplit=1)[
                    1
                ]
                response_payload = {"chunks": [{"chunk_text": source_payload}]}

            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=json.dumps(response_payload, ensure_ascii=False)
                        ),
                        finish_reason="stop",
                    )
                ],
                usage=SimpleNamespace(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    cost=0.0001,
                ),
            )
        finally:
            self.active_request_count -= 1


class SourceEchoClient:
    def __init__(self) -> None:
        self.completions = SourceEchoCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


class RecordingEmbeddings:
    def __init__(self) -> None:
        self.documents: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.documents.extend(texts)
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        _ = text
        return [0.1, 0.2, 0.3, 0.4]


@pytest.mark.anyio
async def test_six_focused_sections_validate_and_reach_embeddings_sequentially() -> (
    None
):
    parser = BulaParser(ocr_enabled=False)
    sections_by_document: dict[str, list[tuple[str, str]]] = {}
    for document, pdf_path in PDF_PATHS.items():
        parse_result = await parser.parse(
            pdf_bytes=pdf_path.read_bytes(),
            filename=pdf_path.name,
        )
        assert parse_result.success
        sections_by_document[document] = split_h2_sections(parse_result.markdown)

    focused_sections = [
        _find_focused_section(
            spec=spec,
            available_sections=sections_by_document[spec.document],
        )
        for spec in FOCUSED_SECTION_SPECS
    ]
    fake_client = SourceEchoClient()
    chunker = BulaChunker(
        llm=cast(AsyncOpenAI, fake_client),
        config=ChunkingConfig(),
    )
    recording_embeddings = RecordingEmbeddings()
    embeddings = EmbeddingAdapter(
        embedder=cast(LCEmbeddings, recording_embeddings),
        batch_size=8,
        dimension=4,
    )

    embedded_chunk_count = 0
    for focused_section in focused_sections:
        chunk_result = await chunker.chunk_markdown(
            markdown=focused_section.text,
            doc_id=f"{focused_section.document}-{focused_section.label}",
        )
        chunk_texts = [chunk.text for chunk in chunk_result.chunks]
        vectors = embeddings.embed_documents(chunk_texts)
        embedded_chunk_count += len(vectors)

        assert has_complete_source_line_coverage(
            source_text=focused_section.text,
            chunk_texts=chunk_texts,
        )
        assert (
            critical_content_preservation(
                source_text=focused_section.text,
                chunk_texts=chunk_texts,
            )
            == 1.0
        )
        assert chunk_result.metadata["fallback"] == {"count": 0, "reasons": {}}
        assert all(chunk.method == "primary" for chunk in chunk_result.chunks)

    assert len(focused_sections) == 6
    assert fake_client.completions.max_active_request_count == 1
    assert len(recording_embeddings.documents) == embedded_chunk_count
