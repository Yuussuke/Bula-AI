from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema
from pydantic import ValidationError

from app.modules.rag.schemas import ChunkingConfig, ValidationOutcome


RETRIEVAL_V3_SYSTEM_PROMPT = (
    "Voce cria unidades de recuperacao para RAG sobre bulas em portugues "
    "brasileiro. Crie chunks autoexplicativos e semanticamente atomicos: um "
    "chunk deve responder a uma unica intencao clinica proxima. Separe temas "
    "sem relacao, mas nao separe itens de uma mesma lista, passos de uso, "
    "tabelas/blocos de posologia, advertencias ou um subtitulo do seu contexto. "
    "Preserve literalmente todo o texto: nao resuma, corrija, reescreva, "
    "invente ou omita. Cada chunk_text precisa ser trecho contiguo da fonte. "
    "Meta: 200-850 tokens; evite chunks pequenos e headings vazios. Retorne "
    "somente JSON valido."
)

RETRIEVAL_V3_USER_PROMPT_TEMPLATE = (
    "Divida somente a fonte abaixo em chunks para busca semantica. Mantenha a "
    "ordem dos trechos e cubra todo o conteudo. Use apenas texto copiado da "
    "fonte. Prefira limites entre paragrafos ou subtemas completos; preserve "
    "listas, composicao e dosagem intactas. Fonte da secao:\n\n{section_text}"
)


@dataclass(frozen=True)
class SemanticRequestDiagnostic:
    model: str
    prompt_version: str
    temperature: float
    seed: int
    max_output_tokens: int
    provider: dict[str, object]
    latency_ms: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None
    validation_outcome: ValidationOutcome
    fallback_reason: str | None
    section_indices: tuple[int, ...]
    observed_model: str | None
    observed_provider: str | None
    finish_reason: str | None
    error_type: str | None
    validation_errors: tuple[dict[str, object], ...]

    def to_metadata(self) -> dict[str, object]:
        return {
            "model": self.model,
            "prompt_version": self.prompt_version,
            "temperature": self.temperature,
            "seed": self.seed,
            "max_output_tokens": self.max_output_tokens,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "usage": {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "cost_usd": self.cost_usd,
            },
            "validation_outcome": self.validation_outcome,
            "fallback_reason": self.fallback_reason,
            "section_indices": list(self.section_indices),
            "observed_model": self.observed_model,
            "observed_provider": self.observed_provider,
            "finish_reason": self.finish_reason,
            "error_type": self.error_type,
            "validation_errors": list(self.validation_errors),
        }


class SemanticChunkingRequestContract:
    """Builds the versioned OpenRouter request used by workers and benchmarks."""

    def __init__(self, *, config: ChunkingConfig) -> None:
        self.config = config

    def build_request(
        self,
        *,
        messages: list[ChatCompletionMessageParam],
        response_format: ResponseFormatJSONSchema,
    ) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "seed": self.config.seed,
            "max_tokens": self.config.max_output_tokens,
            "response_format": response_format,
            "extra_body": {
                "usage": {"include": True},
                "provider": self.provider_options(),
            },
        }

    def provider_options(self) -> dict[str, object]:
        return {
            "zdr": self.config.provider_zdr,
            "data_collection": self.config.provider_data_collection,
            "require_parameters": self.config.provider_require_parameters,
            "allow_fallbacks": self.config.provider_allow_fallbacks,
        }

    def build_diagnostic(
        self,
        *,
        response: Any | None,
        latency_ms: float,
        validation_outcome: ValidationOutcome,
        fallback_reason: str | None,
        section_indices: tuple[int, ...] = (),
        error: Exception | None = None,
    ) -> SemanticRequestDiagnostic:
        usage = getattr(response, "usage", None)
        choices = getattr(response, "choices", [])
        return SemanticRequestDiagnostic(
            model=self.config.model,
            prompt_version=self.config.prompt_version,
            temperature=self.config.temperature,
            seed=self.config.seed,
            max_output_tokens=self.config.max_output_tokens,
            provider=self.provider_options(),
            latency_ms=latency_ms,
            prompt_tokens=self._optional_int(usage, "prompt_tokens"),
            completion_tokens=self._optional_int(usage, "completion_tokens"),
            total_tokens=self._optional_int(usage, "total_tokens"),
            cost_usd=self._extract_cost(usage=usage),
            validation_outcome=validation_outcome,
            fallback_reason=fallback_reason,
            section_indices=section_indices,
            observed_model=self._optional_string(response, "model"),
            observed_provider=self._optional_string(response, "provider"),
            finish_reason=self._optional_string(choices[0], "finish_reason")
            if choices
            else None,
            error_type=type(error).__name__ if error is not None else None,
            validation_errors=self._safe_validation_errors(error),
        )

    def _optional_string(self, source: Any, attribute_name: str) -> str | None:
        value = getattr(source, attribute_name, None)
        return value if isinstance(value, str) else None

    def _safe_validation_errors(
        self, error: Exception | None
    ) -> tuple[dict[str, object], ...]:
        if not isinstance(error, ValidationError):
            return ()
        # Never serialize exception strings, input values, or custom contexts.
        # Unknown field names can originate in provider content; redact them.
        known_fields = {
            "chunks",
            "chunk_text",
            "section_index",
            "choices",
            "message",
            "content",
            "model",
            "usage",
        }
        details: list[dict[str, object]] = []
        for item in error.errors(
            include_input=False, include_context=False, include_url=False
        )[:5]:
            location = [
                part if isinstance(part, int) or part in known_fields else "<field>"
                for part in item["loc"]
            ]
            detail: dict[str, object] = {"type": item["type"], "location": location}
            position = re.search(r"line (\d+) column (\d+)", item["msg"])
            if position is not None:
                detail["line"] = int(position.group(1))
                detail["column"] = int(position.group(2))
            details.append(detail)
        return tuple(details)

    def _optional_int(self, source: Any, attribute_name: str) -> int | None:
        value = getattr(source, attribute_name, None)
        return value if isinstance(value, int) else None

    def _extract_cost(self, *, usage: Any) -> float | None:
        direct_cost = getattr(usage, "cost", None)
        if isinstance(direct_cost, int | float):
            return float(direct_cost)

        model_extra = getattr(usage, "model_extra", None)
        if not isinstance(model_extra, dict):
            return None

        extra_cost = model_extra.get("cost")
        if isinstance(extra_cost, int | float):
            return float(extra_cost)
        return None
