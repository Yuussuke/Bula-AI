import json
from types import SimpleNamespace
from typing import cast

import pytest
from openai import AsyncOpenAI

from app.modules.rag import base_chunker as base_chunker_module
from app.modules.rag.base_chunker import BaseChunker, MarkdownSection
from app.modules.rag.chunker import BulaChunker
from app.modules.rag.schemas import ChunkingConfig
from app.modules.rag.token_estimator import TiktokenTokenEstimator, TokenEstimator


PT_MEDICAL_SNIPPET = (
    "Não use este medicamento em caso de hipersensibilidade à dipirona, "
    "asma induzida por analgésicos ou reação alérgica prévia a pirazolonas."
)


class DummyChunker(BaseChunker):
    def system_prompt(self) -> str:
        return "Split the section into semantic chunks."

    def user_prompt(self, *, section: MarkdownSection) -> str:
        return f"Custom chunking instruction for {section.title}:\n{section.text}"


class FakeCompletions:
    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.requests.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response

        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=response))]
        )


class FakeChat:
    def __init__(self, completions: FakeCompletions) -> None:
        self.completions = completions


class FakeOpenAIClient:
    def __init__(self, responses: list[str | Exception]) -> None:
        self.completions = FakeCompletions(responses=responses)
        self.chat = FakeChat(completions=self.completions)


class WordTokenEstimator:
    def estimate(self, text: str) -> int:
        return max(1, len(text.split()))


def build_config(**overrides: object) -> ChunkingConfig:
    config_values = {
        "target_tokens": 20,
        "min_tokens": 1,
        "max_tokens": 50,
        "overlap_ratio": 0.0,
        "max_concurrency": 2,
        "model": "primary-model",
        "fallback_model": "fallback-model",
        "is_llm_enabled": True,
    }
    config_values.update(overrides)
    return ChunkingConfig(**config_values)


def build_chunk_response(*, chunk_text: str, chunk_title: str = "POSOLOGIA") -> str:
    return json.dumps(
        {
            "chunks": [
                {
                    "chunk_text": chunk_text,
                    "chunk_title": chunk_title,
                    "reason": None,
                }
            ]
        }
    )


def build_chunker(
    *,
    responses: list[str | Exception] | None = None,
    config: ChunkingConfig | None = None,
    token_estimator: TokenEstimator | None = None,
) -> tuple[DummyChunker, FakeOpenAIClient]:
    fake_client = FakeOpenAIClient(responses=responses or [])
    chunker = DummyChunker(
        llm=cast(AsyncOpenAI, fake_client),
        config=config or build_config(),
        token_estimator=token_estimator,
    )
    return chunker, fake_client


@pytest.mark.anyio
async def test_base_chunker_uses_subclass_user_prompt() -> None:
    section_text = "Use um comprimido ao dia apos as refeicoes."
    chunker, fake_client = build_chunker(
        responses=[build_chunk_response(chunk_text=section_text)]
    )

    result = await chunker.chunk_markdown(
        markdown=f"## POSOLOGIA\n{section_text}",
        doc_id="bula-123",
    )

    request = fake_client.completions.requests[0]
    messages = cast(list[dict[str, str]], request["messages"])
    assert result.chunks[0].text == section_text
    assert messages[0]["content"] == "Split the section into semantic chunks."
    assert messages[1]["content"] == (
        f"Custom chunking instruction for POSOLOGIA:\n## POSOLOGIA\n{section_text}"
    )


def test_bula_chunker_user_prompt_preserves_medical_safety_instructions() -> None:
    fake_client = FakeOpenAIClient(responses=[])
    chunker = BulaChunker(
        llm=cast(AsyncOpenAI, fake_client),
        config=build_config(),
    )
    section = MarkdownSection(
        index=0,
        title="CONTRAINDICACOES",
        text="## CONTRAINDICACOES\nNao use em caso de alergia conhecida.",
    )

    prompt = chunker.user_prompt(section=section)

    assert "Divida apenas o texto abaixo em chunks para RAG." in prompt
    assert "Use somente trechos copiados do texto de origem" in prompt
    assert "nao adicione" in prompt
    assert "corrija ou complete nenhuma informacao medica" in prompt
    assert section.text in prompt


@pytest.mark.anyio
async def test_primary_failure_falls_through_to_fallback_model() -> None:
    section_text = "Use um comprimido ao dia apos as refeicoes."
    chunker, fake_client = build_chunker(
        responses=[
            RuntimeError("primary failed"),
            build_chunk_response(chunk_text=section_text),
        ]
    )

    result = await chunker.chunk_markdown(
        markdown=f"## POSOLOGIA\n{section_text}",
        doc_id="bula-123",
    )

    assert len(result.chunks) == 1
    assert result.chunks[0].method == "fallback"
    assert result.chunks[0].text == section_text
    assert [request["model"] for request in fake_client.completions.requests] == [
        "primary-model",
        "fallback-model",
    ]
    assert (
        fake_client.completions.requests[1]["response_format"]["json_schema"]["strict"]
        is True
    )


@pytest.mark.anyio
async def test_primary_and_fallback_failure_fall_through_to_heuristic() -> None:
    chunker, fake_client = build_chunker(
        responses=[
            RuntimeError("primary failed"),
            RuntimeError("fallback failed"),
        ]
    )

    result = await chunker.chunk_markdown(
        markdown="## POSOLOGIA\nUse conforme orientacao medica.",
        doc_id="bula-123",
    )

    assert len(fake_client.completions.requests) == 2
    assert len(result.chunks) == 1
    assert result.chunks[0].method == "heuristic"
    assert "Use conforme orientacao medica." in result.chunks[0].text


@pytest.mark.anyio
async def test_heuristic_fallback_logs_safe_model_failure_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning_calls: list[dict[str, object]] = []
    info_calls: list[dict[str, object]] = []
    section_text = "Use conforme orientacao medica."

    def record_warning(event: str, **kwargs: object) -> None:
        warning_calls.append({"event": event, **kwargs})

    def record_info(event: str, **kwargs: object) -> None:
        info_calls.append({"event": event, **kwargs})

    monkeypatch.setattr(base_chunker_module.logger, "warning", record_warning)
    monkeypatch.setattr(base_chunker_module.logger, "info", record_info)

    chunker, _ = build_chunker(
        responses=[
            RuntimeError(f"primary leaked raw text: {section_text}"),
            RuntimeError(f"fallback leaked raw text: {section_text}"),
        ]
    )

    result = await chunker.chunk_markdown(
        markdown=f"## POSOLOGIA\n{section_text}",
        doc_id="bula-123",
    )

    heuristic_log = next(
        call
        for call in info_calls
        if call["event"] == "rag_section_chunked" and call["method"] == "heuristic"
    )
    assert result.chunks[0].method == "heuristic"
    assert len(warning_calls) == 2
    assert warning_calls[0] == {
        "event": "rag_section_chunking_model_failed",
        "doc_id": "bula-123",
        "section_index": 0,
        "section_title": "POSOLOGIA",
        "method": "primary",
        "error_type": "RuntimeError",
        "failure_reason": "model_call_failed",
    }
    assert warning_calls[1]["method"] == "fallback"
    assert warning_calls[1]["error_type"] == "RuntimeError"
    assert heuristic_log["primary_failed"] is True
    assert heuristic_log["fallback_failed"] is True
    assert heuristic_log["primary_error_type"] == "RuntimeError"
    assert heuristic_log["fallback_error_type"] == "RuntimeError"
    assert heuristic_log["primary_failure_reason"] == "model_call_failed"
    assert heuristic_log["fallback_failure_reason"] == "model_call_failed"
    logged_values = " ".join(
        str(value) for call in warning_calls + info_calls for value in call.values()
    )
    assert section_text not in logged_values
    assert "leaked raw text" not in logged_values


@pytest.mark.anyio
async def test_invalid_json_from_models_triggers_heuristic() -> None:
    chunker, fake_client = build_chunker(
        responses=[
            "not-json",
            '{"chunks": []}',
        ]
    )

    result = await chunker.chunk_markdown(
        markdown="## CONTRAINDICACOES\nNao use em caso de alergia conhecida.",
        doc_id="bula-123",
    )

    assert len(fake_client.completions.requests) == 2
    assert len(result.chunks) == 1
    assert result.chunks[0].method == "heuristic"
    assert "alergia conhecida" in result.chunks[0].text


@pytest.mark.anyio
async def test_disabled_llm_uses_heuristic_without_model_calls() -> None:
    config = build_config(is_llm_enabled=False)
    chunker, fake_client = build_chunker(
        responses=[RuntimeError("should not be called")],
        config=config,
    )

    result = await chunker.chunk_markdown(
        markdown="## COMPOSICAO\nCada comprimido contem dipirona sodica.",
        doc_id="bula-123",
    )

    assert fake_client.completions.requests == []
    assert len(result.chunks) == 1
    assert result.chunks[0].method == "heuristic"


@pytest.mark.anyio
async def test_heuristic_second_pass_only_runs_for_oversized_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_config(is_llm_enabled=False, max_tokens=5)
    chunker, _ = build_chunker(config=config)
    oversized_chunks: list[str] = []
    original_split_oversized_chunk = chunker._split_oversized_chunk

    def tracking_split_oversized_chunk(text: str) -> list[str]:
        oversized_chunks.append(text)
        return original_split_oversized_chunk(text)

    monkeypatch.setattr(
        chunker,
        "_split_oversized_chunk",
        tracking_split_oversized_chunk,
    )

    markdown = f"## CURTO\nPequeno.\n\n## LONGO\n{'palavra ' * 40}"

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert len(oversized_chunks) == 1
    assert "LONGO" in oversized_chunks[0]
    assert all(chunk.method == "heuristic" for chunk in result.chunks)
    assert len(result.chunks) > 2


@pytest.mark.anyio
async def test_heuristic_chunking_keeps_pt_medical_chunks_within_token_bounds() -> None:
    config = build_config(is_llm_enabled=False, max_tokens=25, overlap_ratio=0.0)
    chunker, _ = build_chunker(
        config=config,
        token_estimator=TiktokenTokenEstimator(encoding_name="cl100k_base"),
    )
    markdown = "## CONTRAINDICACOES\n" + " ".join([PT_MEDICAL_SNIPPET] * 8)

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert len(result.chunks) > 1
    assert all(chunk.method == "heuristic" for chunk in result.chunks)
    assert all(chunk.token_estimate <= config.max_tokens for chunk in result.chunks)


@pytest.mark.anyio
async def test_model_chunk_over_token_limit_falls_back_to_heuristic() -> None:
    config = build_config(max_tokens=8, overlap_ratio=0.0)
    section_text = f"{PT_MEDICAL_SNIPPET} {PT_MEDICAL_SNIPPET}"
    chunker, fake_client = build_chunker(
        responses=[
            build_chunk_response(chunk_text=section_text),
            RuntimeError("fallback failed"),
        ],
        config=config,
        token_estimator=TiktokenTokenEstimator(encoding_name="cl100k_base"),
    )

    result = await chunker.chunk_markdown(
        markdown=f"## CONTRAINDICACOES\n{section_text}",
        doc_id="bula-123",
    )

    assert [request["model"] for request in fake_client.completions.requests] == [
        "primary-model",
        "fallback-model",
    ]
    assert all(chunk.method == "heuristic" for chunk in result.chunks)
    assert all(chunk.token_estimate <= config.max_tokens for chunk in result.chunks)


@pytest.mark.anyio
async def test_document_chunk_token_estimate_uses_injected_estimator() -> None:
    section_text = "Use um comprimido ao dia apos as refeicoes."
    chunker, _ = build_chunker(
        responses=[build_chunk_response(chunk_text=section_text)],
        token_estimator=WordTokenEstimator(),
    )

    result = await chunker.chunk_markdown(
        markdown=f"## POSOLOGIA\n{section_text}",
        doc_id="bula-123",
    )

    assert result.chunks[0].token_estimate == len(section_text.split())


@pytest.mark.anyio
async def test_chunk_ids_are_deterministic_for_same_input() -> None:
    config = build_config(is_llm_enabled=False)
    chunker, _ = build_chunker(config=config)
    markdown = "## POSOLOGIA\nUse um comprimido ao dia."

    first_result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")
    second_result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert [chunk.chunk_id for chunk in first_result.chunks] == [
        chunk.chunk_id for chunk in second_result.chunks
    ]
