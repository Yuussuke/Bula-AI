import json
from types import SimpleNamespace
from typing import Sequence, cast

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

    def batch_user_prompt(self, *, sections: Sequence[MarkdownSection]) -> str:
        section_identifiers = ", ".join(str(section.index) for section in sections)
        return f"Custom batch chunking instruction for: {section_identifiers}"


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


def build_batch_chunk_response(
    *proposals: tuple[int, str, str],
) -> str:
    return json.dumps(
        {
            "chunks": [
                {
                    "section_index": section_index,
                    "chunk_text": chunk_text,
                    "chunk_title": chunk_title,
                    "reason": None,
                }
                for section_index, chunk_text, chunk_title in proposals
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


def test_bula_chunker_batch_prompt_keeps_sections_independent() -> None:
    fake_client = FakeOpenAIClient(responses=[])
    chunker = BulaChunker(
        llm=cast(AsyncOpenAI, fake_client),
        config=build_config(),
    )
    sections = [
        MarkdownSection(index=0, title="POSOLOGIA", text="Dose diaria."),
        MarkdownSection(index=1, title="CONTRAINDICACOES", text="Nao utilizar."),
    ]

    prompt = chunker.batch_user_prompt(sections=sections)
    serialized_sections = json.loads(prompt.rsplit("\n\n", maxsplit=1)[1])

    assert "nunca misture conteudo de secoes diferentes" in prompt
    assert "Use somente trechos copiados" in prompt
    assert serialized_sections == [
        {
            "section_index": 0,
            "section_title": "POSOLOGIA",
            "section_text": "Dose diaria.",
        },
        {
            "section_index": 1,
            "section_title": "CONTRAINDICACOES",
            "section_text": "Nao utilizar.",
        },
    ]


@pytest.mark.anyio
async def test_small_adjacent_sections_share_one_model_request() -> None:
    markdown = (
        "## COMPOSICAO\nContem dipirona.\n\n"
        "## INDICACOES\nAlivia a dor.\n\n"
        "## POSOLOGIA\nUse uma dose.\n\n"
        "## CUIDADOS\nSiga orientacao."
    )
    chunker, fake_client = build_chunker(
        responses=[
            build_batch_chunk_response(
                (2, "Use uma dose.", "Dose"),
                (0, "Contem dipirona.", "Composicao"),
                (3, "Siga orientacao.", "Cuidados"),
                (1, "Alivia a dor.", "Indicacoes"),
            )
        ],
        config=build_config(
            max_concurrency=1,
            batch_max_tokens=100,
            batch_max_sections=8,
        ),
        token_estimator=WordTokenEstimator(),
    )

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert len(fake_client.completions.requests) == 1
    assert result.metadata["section_count"] == 4
    assert result.metadata["batch_count"] == 1
    assert result.metadata["batched_section_count"] == 4
    assert result.metadata["model_call_count"] == 1
    assert [chunk.section_title for chunk in result.chunks] == [
        "COMPOSICAO",
        "INDICACOES",
        "POSOLOGIA",
        "CUIDADOS",
    ]
    assert [chunk.text for chunk in result.chunks] == [
        "Contem dipirona.",
        "Alivia a dor.",
        "Use uma dose.",
        "Siga orientacao.",
    ]


@pytest.mark.anyio
async def test_batch_limits_split_sections_into_multiple_requests() -> None:
    markdown = (
        "## A\nTexto A.\n\n"
        "## B\nTexto B.\n\n"
        "## C\nTexto C.\n\n"
        "## D\nTexto D.\n\n"
        "## E\nTexto E."
    )
    chunker, fake_client = build_chunker(
        responses=[
            build_batch_chunk_response(
                (0, "Texto A.", "A"),
                (1, "Texto B.", "B"),
            ),
            build_batch_chunk_response(
                (2, "Texto C.", "C"),
                (3, "Texto D.", "D"),
            ),
            build_chunk_response(chunk_text="Texto E.", chunk_title="E"),
        ],
        config=build_config(
            max_concurrency=1,
            batch_max_tokens=100,
            batch_max_sections=2,
        ),
        token_estimator=WordTokenEstimator(),
    )

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert len(fake_client.completions.requests) == 3
    assert result.metadata["batch_count"] == 3
    assert result.metadata["model_call_count"] == 3
    assert [chunk.section_title for chunk in result.chunks] == ["A", "B", "C", "D", "E"]


@pytest.mark.anyio
async def test_batch_token_budget_splits_adjacent_sections() -> None:
    markdown = "## A\nTexto A.\n\n## B\nTexto B.\n\n## C\nTexto C."
    chunker, fake_client = build_chunker(
        responses=[
            build_batch_chunk_response(
                (0, "Texto A.", "A"),
                (1, "Texto B.", "B"),
            ),
            build_chunk_response(chunk_text="Texto C.", chunk_title="C"),
        ],
        config=build_config(
            max_concurrency=1,
            batch_max_tokens=8,
            batch_max_sections=8,
        ),
        token_estimator=WordTokenEstimator(),
    )

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert len(fake_client.completions.requests) == 2
    assert result.metadata["batch_count"] == 2
    assert [chunk.section_title for chunk in result.chunks] == ["A", "B", "C"]


@pytest.mark.anyio
async def test_batching_reduces_calls_for_same_document_without_changing_output() -> (
    None
):
    markdown = "## A\nTexto A.\n\n## B\nTexto B.\n\n## C\nTexto C."
    batched_chunker, batched_client = build_chunker(
        responses=[
            build_batch_chunk_response(
                (0, "Texto A.", "A"),
                (1, "Texto B.", "B"),
                (2, "Texto C.", "C"),
            )
        ],
        config=build_config(max_concurrency=1),
    )
    legacy_chunker, legacy_client = build_chunker(
        responses=[
            build_chunk_response(chunk_text="Texto A.", chunk_title="A"),
            build_chunk_response(chunk_text="Texto B.", chunk_title="B"),
            build_chunk_response(chunk_text="Texto C.", chunk_title="C"),
        ],
        config=build_config(
            is_batching_enabled=False,
            max_concurrency=1,
        ),
    )

    batched_result = await batched_chunker.chunk_markdown(
        markdown=markdown,
        doc_id="bula-123",
    )
    legacy_result = await legacy_chunker.chunk_markdown(
        markdown=markdown,
        doc_id="bula-123",
    )

    assert len(batched_client.completions.requests) == 1
    assert len(legacy_client.completions.requests) == 3
    assert batched_result.metadata["model_call_count"] == 1
    assert legacy_result.metadata["model_call_count"] == 3
    assert [(chunk.section_title, chunk.text) for chunk in batched_result.chunks] == [
        (chunk.section_title, chunk.text) for chunk in legacy_result.chunks
    ]


@pytest.mark.anyio
async def test_batch_response_cannot_mix_text_between_sections() -> None:
    markdown = "## POSOLOGIA\nDose diaria.\n\n## CUIDADOS\nNao exceda a dose."
    chunker, fake_client = build_chunker(
        responses=[
            build_batch_chunk_response(
                (0, "Nao exceda a dose.", "Resposta invalida"),
                (1, "Nao exceda a dose.", "Cuidados"),
            ),
            build_batch_chunk_response(
                (0, "Dose diaria.", "Posologia"),
                (1, "Nao exceda a dose.", "Cuidados"),
            ),
        ],
        config=build_config(max_concurrency=1),
    )

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert [request["model"] for request in fake_client.completions.requests] == [
        "primary-model",
        "fallback-model",
    ]
    assert all(chunk.method == "fallback" for chunk in result.chunks)
    assert [chunk.section_title for chunk in result.chunks] == [
        "POSOLOGIA",
        "CUIDADOS",
    ]


@pytest.mark.anyio
async def test_failed_batch_retries_each_section_individually(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning_calls: list[dict[str, object]] = []

    def record_warning(event: str, **kwargs: object) -> None:
        warning_calls.append({"event": event, **kwargs})

    monkeypatch.setattr(base_chunker_module.logger, "warning", record_warning)
    chunker, fake_client = build_chunker(
        responses=[
            RuntimeError("batch primary leaked Dose diaria."),
            RuntimeError("batch fallback leaked Dose diaria."),
            build_chunk_response(chunk_text="Dose diaria.", chunk_title="Posologia"),
            build_chunk_response(chunk_text="Nao exceda.", chunk_title="Cuidados"),
        ],
        config=build_config(max_concurrency=1),
    )
    markdown = "## POSOLOGIA\nDose diaria.\n\n## CUIDADOS\nNao exceda."

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert [request["model"] for request in fake_client.completions.requests] == [
        "primary-model",
        "fallback-model",
        "primary-model",
        "primary-model",
    ]
    assert result.metadata["model_call_count"] == 4
    assert result.metadata["batch_fallback_count"] == 1
    assert all(chunk.method == "primary" for chunk in result.chunks)
    split_log = next(
        call
        for call in warning_calls
        if call["event"] == "rag_chunking_batch_falling_back_to_sections"
    )
    assert split_log["batch_index"] == 0
    assert split_log["section_indices"] == [0, 1]
    assert split_log["section_count"] == 2
    logged_values = " ".join(
        str(value) for call in warning_calls for value in call.values()
    )
    assert "Dose diaria" not in logged_values
    assert "leaked" not in logged_values


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
    debug_calls: list[dict[str, object]] = []
    section_text = "Use conforme orientacao medica."

    def record_warning(event: str, **kwargs: object) -> None:
        warning_calls.append({"event": event, **kwargs})

    def record_debug(event: str, **kwargs: object) -> None:
        debug_calls.append({"event": event, **kwargs})

    monkeypatch.setattr(base_chunker_module.logger, "warning", record_warning)
    monkeypatch.setattr(base_chunker_module.logger, "debug", record_debug)

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
        for call in debug_calls
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
    assert isinstance(heuristic_log["duration_ms"], float)
    logged_values = " ".join(
        str(value) for call in warning_calls + debug_calls for value in call.values()
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
