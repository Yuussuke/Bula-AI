import asyncio
from dataclasses import dataclass
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


@dataclass(frozen=True)
class FakeCompletionResponse:
    content: str
    finish_reason: str = "stop"
    delay_seconds: float = 0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None


class FakeCompletions:
    def __init__(
        self,
        responses: list[str | Exception | FakeCompletionResponse],
    ) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []
        self.active_request_count = 0
        self.max_active_request_count = 0

    async def create(self, **kwargs: object) -> object:
        self.requests.append(kwargs)
        self.active_request_count += 1
        self.max_active_request_count = max(
            self.max_active_request_count,
            self.active_request_count,
        )
        try:
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response

            if isinstance(response, FakeCompletionResponse):
                if response.delay_seconds:
                    await asyncio.sleep(response.delay_seconds)
                usage = SimpleNamespace(
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_tokens=(
                        response.prompt_tokens + response.completion_tokens
                        if response.prompt_tokens is not None
                        and response.completion_tokens is not None
                        else None
                    ),
                    cost=response.cost_usd,
                )
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content=response.content),
                            finish_reason=response.finish_reason,
                        )
                    ],
                    usage=usage,
                )

            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=response),
                        finish_reason="stop",
                    )
                ]
            )
        finally:
            self.active_request_count -= 1


class FakeChat:
    def __init__(self, completions: FakeCompletions) -> None:
        self.completions = completions


class FakeOpenAIClient:
    def __init__(
        self,
        responses: list[str | Exception | FakeCompletionResponse],
    ) -> None:
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
        "model": "primary-model",
        "is_llm_enabled": True,
    }
    config_values.update(overrides)
    return ChunkingConfig(**config_values)


def build_chunk_response(*, chunk_text: str) -> str:
    return json.dumps(
        {
            "chunks": [
                {
                    "chunk_text": chunk_text,
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
                }
                for section_index, chunk_text, _chunk_title in proposals
            ]
        }
    )


def build_chunker(
    *,
    responses: list[str | Exception | FakeCompletionResponse] | None = None,
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


def test_semantic_chunking_defaults_match_retrieval_v3_contract() -> None:
    config = ChunkingConfig()

    assert config.model == "google/gemini-3.1-flash-lite"
    assert config.prompt_version == "retrieval_v3"
    assert config.temperature == 0
    assert config.seed == 17
    assert config.max_output_tokens == 5000
    assert config.provider_zdr is True
    assert config.provider_data_collection == "deny"
    assert config.provider_require_parameters is True


@pytest.mark.anyio
async def test_base_chunker_uses_subclass_user_prompt() -> None:
    section_text = "Use um comprimido ao dia apos as refeicoes."
    chunker, fake_client = build_chunker(
        responses=[build_chunk_response(chunk_text=f"## POSOLOGIA\n{section_text}")]
    )

    result = await chunker.chunk_markdown(
        markdown=f"## POSOLOGIA\n{section_text}",
        doc_id="bula-123",
    )

    request = fake_client.completions.requests[0]
    messages = cast(list[dict[str, str]], request["messages"])
    assert result.chunks[0].text == f"## POSOLOGIA\n{section_text}"
    assert result.chunks[0].chunk_title == "POSOLOGIA"
    assert result.chunks[0].metadata["validation_outcome"] == "passed"
    assert messages[0]["content"] == "Split the section into semantic chunks."
    assert messages[1]["content"] == (
        f"Custom chunking instruction for POSOLOGIA:\n## POSOLOGIA\n{section_text}"
    )
    assert request["temperature"] == 0
    assert request["seed"] == 17
    assert request["max_tokens"] == 5000
    assert request["extra_body"] == {
        "usage": {"include": True},
        "provider": {
            "zdr": True,
            "data_collection": "deny",
            "require_parameters": True,
            "allow_fallbacks": True,
        },
    }


@pytest.mark.anyio
async def test_semantic_requests_are_sequential_and_keep_source_order() -> None:
    chunker, fake_client = build_chunker(
        responses=[
            FakeCompletionResponse(
                content=build_chunk_response(chunk_text="## A\nTexto A."),
                delay_seconds=0.01,
            ),
            FakeCompletionResponse(
                content=build_chunk_response(chunk_text="## B\nTexto B."),
                delay_seconds=0.01,
            ),
            FakeCompletionResponse(
                content=build_chunk_response(chunk_text="## C\nTexto C."),
                delay_seconds=0.01,
            ),
        ],
        config=build_config(is_batching_enabled=False),
    )

    result = await chunker.chunk_markdown(
        markdown="## A\nTexto A.\n\n## B\nTexto B.\n\n## C\nTexto C.",
        doc_id="sequential-bula",
    )

    semantic_metadata = cast(
        dict[str, object],
        result.metadata["semantic_chunking"],
    )
    assert fake_client.completions.max_active_request_count == 1
    assert [chunk.section_title for chunk in result.chunks] == ["A", "B", "C"]
    assert semantic_metadata["inference_mode"] == "sequential"
    assert semantic_metadata["request_count"] == 3


@pytest.mark.anyio
async def test_semantic_diagnostics_record_usage_latency_and_validation() -> None:
    chunker, _ = build_chunker(
        responses=[
            FakeCompletionResponse(
                content=build_chunk_response(
                    chunk_text="## POSOLOGIA\nUse conforme orientacao."
                ),
                prompt_tokens=120,
                completion_tokens=30,
                cost_usd=0.00042,
            )
        ]
    )

    result = await chunker.chunk_markdown(
        markdown="## POSOLOGIA\nUse conforme orientacao.",
        doc_id="diagnostic-bula",
    )

    semantic_metadata = cast(
        dict[str, object],
        result.metadata["semantic_chunking"],
    )
    usage = cast(dict[str, object], semantic_metadata["usage"])
    requests = cast(list[dict[str, object]], semantic_metadata["requests"])
    assert usage == {
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "total_tokens": 150,
        "cost_usd": 0.00042,
    }
    assert cast(dict[str, float], semantic_metadata["latency_ms"])["total"] >= 0
    assert requests[0]["validation_outcome"] == "passed"
    assert requests[0]["fallback_reason"] is None


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

    assert "Divida somente a fonte abaixo em chunks para busca semantica." in prompt
    assert "Use apenas texto copiado da fonte" in prompt
    assert "Mantenha a ordem dos trechos e cubra todo o conteudo" in prompt
    assert "preserve listas, composicao e dosagem intactas" in prompt
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
    assert "Use apenas texto copiado" in prompt
    assert "cubra cada section_text por completo" in prompt
    assert "preserve listas, composicao e dosagem intactas" in prompt
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
                (2, "## POSOLOGIA\nUse uma dose.", "Dose"),
                (0, "## COMPOSICAO\nContem dipirona.", "Composicao"),
                (3, "## CUIDADOS\nSiga orientacao.", "Cuidados"),
                (1, "## INDICACOES\nAlivia a dor.", "Indicacoes"),
            )
        ],
        config=build_config(
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
        "## COMPOSICAO\nContem dipirona.",
        "## INDICACOES\nAlivia a dor.",
        "## POSOLOGIA\nUse uma dose.",
        "## CUIDADOS\nSiga orientacao.",
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
                (0, "## A\nTexto A.", "A"),
                (1, "## B\nTexto B.", "B"),
            ),
            build_batch_chunk_response(
                (2, "## C\nTexto C.", "C"),
                (3, "## D\nTexto D.", "D"),
            ),
            build_chunk_response(chunk_text="## E\nTexto E."),
        ],
        config=build_config(
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
                (0, "## A\nTexto A.", "A"),
                (1, "## B\nTexto B.", "B"),
            ),
            build_chunk_response(chunk_text="## C\nTexto C."),
        ],
        config=build_config(
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
                (0, "## A\nTexto A.", "A"),
                (1, "## B\nTexto B.", "B"),
                (2, "## C\nTexto C.", "C"),
            )
        ],
        config=build_config(),
    )
    legacy_chunker, legacy_client = build_chunker(
        responses=[
            build_chunk_response(chunk_text="## A\nTexto A."),
            build_chunk_response(chunk_text="## B\nTexto B."),
            build_chunk_response(chunk_text="## C\nTexto C."),
        ],
        config=build_config(
            is_batching_enabled=False,
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
                (1, "## CUIDADOS\nNao exceda a dose.", "Cuidados"),
            ),
        ],
        config=build_config(),
    )

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert [request["model"] for request in fake_client.completions.requests] == [
        "primary-model"
    ]
    assert all(chunk.method == "deterministic" for chunk in result.chunks)
    assert [chunk.section_title for chunk in result.chunks] == [
        "POSOLOGIA",
        "CUIDADOS",
    ]
    assert result.metadata["fallback"] == {
        "count": 2,
        "reasons": {"non_source_text": 2},
    }


@pytest.mark.anyio
async def test_failed_batch_uses_deterministic_sections_without_provider_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning_calls: list[dict[str, object]] = []

    def record_warning(event: str, **kwargs: object) -> None:
        warning_calls.append({"event": event, **kwargs})

    monkeypatch.setattr(base_chunker_module.logger, "warning", record_warning)
    chunker, fake_client = build_chunker(
        responses=[
            RuntimeError("batch primary leaked Dose diaria."),
        ],
        config=build_config(),
    )
    markdown = "## POSOLOGIA\nDose diaria.\n\n## CUIDADOS\nNao exceda."

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert [request["model"] for request in fake_client.completions.requests] == [
        "primary-model"
    ]
    assert result.metadata["model_call_count"] == 1
    assert result.metadata["batch_fallback_count"] == 1
    assert all(chunk.method == "deterministic" for chunk in result.chunks)
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
async def test_provider_failure_uses_deterministic_fallback() -> None:
    section_text = "Use um comprimido ao dia apos as refeicoes."
    chunker, fake_client = build_chunker(
        responses=[
            RuntimeError("primary failed"),
        ]
    )

    result = await chunker.chunk_markdown(
        markdown=f"## POSOLOGIA\n{section_text}",
        doc_id="bula-123",
    )

    assert len(result.chunks) == 1
    assert result.chunks[0].method == "deterministic"
    assert result.chunks[0].text == f"## POSOLOGIA\n{section_text}"
    assert result.chunks[0].metadata["fallback_reason"] == "provider_error"
    assert [request["model"] for request in fake_client.completions.requests] == [
        "primary-model"
    ]
    assert (
        fake_client.completions.requests[0]["response_format"]["json_schema"]["strict"]
        is True
    )


@pytest.mark.anyio
async def test_invalid_json_uses_deterministic_fallback_without_provider_retry() -> (
    None
):
    chunker, fake_client = build_chunker(responses=["not-json"])

    result = await chunker.chunk_markdown(
        markdown="## POSOLOGIA\nUse conforme orientacao medica.",
        doc_id="bula-123",
    )

    assert len(fake_client.completions.requests) == 1
    assert len(result.chunks) == 1
    assert result.chunks[0].method == "deterministic"
    assert result.chunks[0].metadata["fallback_reason"] == "invalid_json"
    assert "Use conforme orientacao medica." in result.chunks[0].text


@pytest.mark.anyio
async def test_extra_model_metadata_is_rejected_by_strict_json_contract() -> None:
    model_response = json.dumps(
        {
            "chunks": [
                {
                    "chunk_text": "## POSOLOGIA\nUse conforme orientacao.",
                    "chunk_title": "Titulo inventado",
                }
            ]
        }
    )
    chunker, _ = build_chunker(responses=[model_response])

    result = await chunker.chunk_markdown(
        markdown="## POSOLOGIA\nUse conforme orientacao.",
        doc_id="bula-123",
    )

    assert result.chunks[0].method == "deterministic"
    assert result.chunks[0].chunk_title == "POSOLOGIA"
    assert result.chunks[0].metadata["fallback_reason"] == "invalid_json"


@pytest.mark.anyio
async def test_deterministic_fallback_logs_safe_model_failure_context(
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
        ]
    )

    result = await chunker.chunk_markdown(
        markdown=f"## POSOLOGIA\n{section_text}",
        doc_id="bula-123",
    )

    fallback_log = next(
        call
        for call in debug_calls
        if call["event"] == "rag_section_chunked" and call["method"] == "deterministic"
    )
    assert result.chunks[0].method == "deterministic"
    assert len(warning_calls) == 1
    assert warning_calls[0] == {
        "event": "rag_section_chunking_model_failed",
        "doc_id": "bula-123",
        "section_index": 0,
        "section_title": "POSOLOGIA",
        "method": "primary",
        "error_type": "RuntimeError",
        "failure_reason": "provider_error",
    }
    assert fallback_log["primary_failed"] is True
    assert fallback_log["primary_error_type"] == "RuntimeError"
    assert fallback_log["primary_failure_reason"] == "provider_error"
    assert isinstance(fallback_log["duration_ms"], float)
    logged_values = " ".join(
        str(value) for call in warning_calls + debug_calls for value in call.values()
    )
    assert section_text not in logged_values
    assert "leaked raw text" not in logged_values


@pytest.mark.anyio
async def test_truncated_response_uses_explainable_deterministic_fallback() -> None:
    chunker, fake_client = build_chunker(
        responses=[
            FakeCompletionResponse(
                content='{"chunks": [{"chunk_text": "incompleto',
                finish_reason="length",
            )
        ]
    )

    result = await chunker.chunk_markdown(
        markdown="## CONTRAINDICACOES\nNao use em caso de alergia conhecida.",
        doc_id="bula-123",
    )

    assert len(fake_client.completions.requests) == 1
    assert len(result.chunks) == 1
    assert result.chunks[0].method == "deterministic"
    assert result.chunks[0].metadata["fallback_reason"] == "truncated_response"
    assert "alergia conhecida" in result.chunks[0].text


@pytest.mark.anyio
async def test_timeout_uses_deterministic_fallback_outside_provider_deadline() -> None:
    chunker, fake_client = build_chunker(
        responses=[
            FakeCompletionResponse(
                content=build_chunk_response(
                    chunk_text="## POSOLOGIA\nUse conforme orientacao."
                ),
                delay_seconds=0.05,
            )
        ],
        config=build_config(request_timeout_seconds=0.001),
    )

    result = await chunker.chunk_markdown(
        markdown="## POSOLOGIA\nUse conforme orientacao.",
        doc_id="bula-123",
    )

    assert len(fake_client.completions.requests) == 1
    assert result.chunks[0].method == "deterministic"
    assert result.chunks[0].metadata["fallback_reason"] == "timeout"
    assert "Use conforme orientacao." in result.chunks[0].text


@pytest.mark.anyio
async def test_disabled_llm_uses_deterministic_fallback_without_model_calls() -> None:
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
    assert result.chunks[0].method == "deterministic"
    assert result.chunks[0].metadata["validation_outcome"] == "not_attempted"


@pytest.mark.anyio
async def test_deterministic_fallback_only_splits_oversized_sections() -> None:
    config = build_config(is_llm_enabled=False, max_tokens=5)
    chunker, _ = build_chunker(config=config)

    markdown = f"## CURTO\nPequeno.\n\n## LONGO\n{'palavra ' * 40}"

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert result.chunks[0].text == "## CURTO\nPequeno."
    assert all(chunk.method == "deterministic" for chunk in result.chunks)
    assert len(result.chunks) > 2


@pytest.mark.anyio
async def test_deterministic_chunking_keeps_medical_chunks_within_hard_cap() -> None:
    config = build_config(is_llm_enabled=False, max_tokens=25, overlap_ratio=0.0)
    chunker, _ = build_chunker(
        config=config,
        token_estimator=TiktokenTokenEstimator(encoding_name="cl100k_base"),
    )
    markdown = "## CONTRAINDICACOES\n" + " ".join([PT_MEDICAL_SNIPPET] * 8)

    result = await chunker.chunk_markdown(markdown=markdown, doc_id="bula-123")

    assert len(result.chunks) > 1
    assert all(chunk.method == "deterministic" for chunk in result.chunks)
    assert all(chunk.token_estimate <= config.max_tokens for chunk in result.chunks)


@pytest.mark.anyio
async def test_valid_oversized_semantic_span_is_split_only_after_validation() -> None:
    config = build_config(max_tokens=8, overlap_ratio=0.0)
    section_text = f"{PT_MEDICAL_SNIPPET} {PT_MEDICAL_SNIPPET}"
    chunker, fake_client = build_chunker(
        responses=[
            build_chunk_response(chunk_text=f"## CONTRAINDICACOES\n{section_text}"),
        ],
        config=config,
        token_estimator=TiktokenTokenEstimator(encoding_name="cl100k_base"),
    )

    result = await chunker.chunk_markdown(
        markdown=f"## CONTRAINDICACOES\n{section_text}",
        doc_id="bula-123",
    )

    assert [request["model"] for request in fake_client.completions.requests] == [
        "primary-model"
    ]
    assert all(chunk.method == "primary" for chunk in result.chunks)
    assert all(
        chunk.metadata["validation_outcome"] == "passed" for chunk in result.chunks
    )
    assert all(chunk.token_estimate <= config.max_tokens for chunk in result.chunks)


@pytest.mark.anyio
async def test_document_chunk_token_estimate_uses_injected_estimator() -> None:
    section_text = "Use um comprimido ao dia apos as refeicoes."
    chunker, _ = build_chunker(
        responses=[build_chunk_response(chunk_text=f"## POSOLOGIA\n{section_text}")],
        token_estimator=WordTokenEstimator(),
    )

    result = await chunker.chunk_markdown(
        markdown=f"## POSOLOGIA\n{section_text}",
        doc_id="bula-123",
    )

    assert result.chunks[0].token_estimate == len(
        f"## POSOLOGIA\n{section_text}".split()
    )


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
