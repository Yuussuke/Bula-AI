from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Literal

import structlog

from app.modules.rag.parsers.pdf_parser import ParseResult
from app.modules.rag.schemas import ChunkResult, ChunkingConfig


logger = structlog.get_logger(__name__)

RAG_DEBUG_ARTIFACTS_SCHEMA_VERSION = 4
MAX_DEBUG_ERROR_MESSAGE_LENGTH = 300
UNSUPPORTED_DEBUG_VALUE = "[unsupported_debug_value]"
SENSITIVE_METADATA_KEY_FRAGMENTS = (
    "api_key",
    "token",
    "secret",
    "password",
    "authorization",
    "payload",
    "prompt",
    "request_body",
    "response_body",
    "pdf_bytes",
    "file_bytes",
    "storage_address",
)

DebugArtifactStatus = Literal["success", "parse_failed", "chunking_failed"]
DebugMetadataValue = (
    str
    | int
    | float
    | bool
    | None
    | list["DebugMetadataValue"]
    | dict[str, "DebugMetadataValue"]
)


@dataclass(frozen=True)
class DebugArtifactWriteFailure:
    artifact: str
    path: str
    error: dict[str, str]


@dataclass(frozen=True)
class DebugArtifactWriteResult:
    artifacts_written: list[str]
    artifact_write_failures: list[DebugArtifactWriteFailure]


class RAGIngestionDebugArtifacts:
    def __init__(self, *, enabled: bool, root_path: str | Path) -> None:
        self.enabled = enabled
        self.root_path = Path(root_path)

    async def write_run_artifacts(
        self,
        *,
        run_id: str,
        doc_id: str,
        filename: str | None,
        status: DebugArtifactStatus,
        parse_result: ParseResult | None = None,
        markdown: str | None = None,
        chunk_result: ChunkResult | None = None,
        chunking_config: ChunkingConfig | None = None,
        error: BaseException | None = None,
    ) -> DebugArtifactWriteResult:
        if not self.enabled:
            return DebugArtifactWriteResult(
                artifacts_written=[],
                artifact_write_failures=[],
            )

        run_dir = self.root_path / doc_id / run_id
        artifacts_written: list[str] = []
        artifact_write_failures: list[DebugArtifactWriteFailure] = []
        artifacts = self._build_artifact_paths(
            has_markdown=markdown is not None,
            has_chunks=chunk_result is not None,
        )

        if markdown is not None:
            markdown_failure = self._write_text_artifact(
                run_id=run_id,
                doc_id=doc_id,
                artifact="parsed_markdown",
                path=run_dir / artifacts["parsed_markdown"],
                content=markdown,
            )
            self._record_artifact_write_result(
                artifact="parsed_markdown",
                failure=markdown_failure,
                artifacts_written=artifacts_written,
                artifact_write_failures=artifact_write_failures,
            )

        chunks_json_size_bytes: int | None = None
        if chunk_result is not None:
            chunks_json = self._serialize_json(chunk_result.model_dump(mode="json"))
            chunks_json_size_bytes = len(chunks_json.encode("utf-8"))
            chunks_failure = self._write_text_artifact(
                run_id=run_id,
                doc_id=doc_id,
                artifact="chunks",
                path=run_dir / artifacts["chunks"],
                content=chunks_json,
            )
            self._record_artifact_write_result(
                artifact="chunks",
                failure=chunks_failure,
                artifacts_written=artifacts_written,
                artifact_write_failures=artifact_write_failures,
            )

        manifest_artifacts_written = [*artifacts_written, "manifest"]
        manifest = self._build_manifest(
            run_id=run_id,
            doc_id=doc_id,
            filename=filename,
            status=status,
            parse_result=parse_result,
            chunk_result=chunk_result,
            chunking_config=chunking_config,
            error=error,
            artifacts=artifacts,
            artifacts_written=manifest_artifacts_written,
            artifact_write_failures=artifact_write_failures,
            chunks_json_size_bytes=chunks_json_size_bytes,
        )
        manifest_failure = self._write_text_artifact(
            run_id=run_id,
            doc_id=doc_id,
            artifact="manifest",
            path=run_dir / artifacts["manifest"],
            content=self._serialize_json(manifest),
        )
        self._record_artifact_write_result(
            artifact="manifest",
            failure=manifest_failure,
            artifacts_written=artifacts_written,
            artifact_write_failures=artifact_write_failures,
        )

        return DebugArtifactWriteResult(
            artifacts_written=artifacts_written,
            artifact_write_failures=artifact_write_failures,
        )

    def _build_artifact_paths(
        self,
        *,
        has_markdown: bool,
        has_chunks: bool,
    ) -> dict[str, str]:
        artifacts = {"manifest": "manifest.json"}
        if has_markdown:
            artifacts["parsed_markdown"] = "parsed_markdown.md"
        if has_chunks:
            artifacts["chunks"] = "chunks.json"
        return artifacts

    def _write_text_artifact(
        self,
        *,
        run_id: str,
        doc_id: str,
        artifact: str,
        path: Path,
        content: str,
    ) -> DebugArtifactWriteFailure | None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            return None
        except OSError as exc:
            sanitized_error = sanitize_debug_error(exc)
            logger.warning(
                "rag_ingestion_debug_artifacts_failed",
                run_id=run_id,
                bula_id=doc_id,
                doc_id=doc_id,
                path=str(path),
                error_type=sanitized_error["error_type"],
            )
            return DebugArtifactWriteFailure(
                artifact=artifact,
                path=path.name,
                error=sanitized_error,
            )

    def _record_artifact_write_result(
        self,
        *,
        artifact: str,
        failure: DebugArtifactWriteFailure | None,
        artifacts_written: list[str],
        artifact_write_failures: list[DebugArtifactWriteFailure],
    ) -> None:
        if failure is None:
            artifacts_written.append(artifact)
            return

        artifact_write_failures.append(failure)

    def _build_manifest(
        self,
        *,
        run_id: str,
        doc_id: str,
        filename: str | None,
        status: DebugArtifactStatus,
        parse_result: ParseResult | None,
        chunk_result: ChunkResult | None,
        chunking_config: ChunkingConfig | None,
        error: BaseException | None,
        artifacts: dict[str, str],
        artifacts_written: list[str],
        artifact_write_failures: list[DebugArtifactWriteFailure],
        chunks_json_size_bytes: int | None,
    ) -> dict[str, object]:
        manifest: dict[str, object] = {
            "schema_version": RAG_DEBUG_ARTIFACTS_SCHEMA_VERSION,
            "run_id": run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "bula_id": doc_id,
            "doc_id": doc_id,
            "filename": filename,
            "status": status,
            "extraction_tier": (
                parse_result.extraction_tier if parse_result is not None else None
            ),
            "parser_version": (
                parse_result.parser_version if parse_result is not None else None
            ),
            "converter": {
                "name": (
                    parse_result.converter_name if parse_result is not None else None
                ),
                "version": (
                    parse_result.converter_version if parse_result is not None else None
                ),
                "extraction_decision": (
                    parse_result.extraction_decision
                    if parse_result is not None
                    else None
                ),
            },
            "cleanup_summary": sanitize_debug_metadata(
                parse_result.cleanup_summary
                if parse_result is not None and parse_result.cleanup_summary is not None
                else {}
            ),
            "section_count": len(parse_result.sections) if parse_result else 0,
            "chunk_count": len(chunk_result.chunks) if chunk_result else 0,
            "chunk_methods": self._build_chunk_methods(chunk_result=chunk_result),
            "chunk_validation": self._build_chunk_diagnostic_metadata(
                chunk_result=chunk_result,
                metadata_key="validation",
            ),
            "chunk_fallback": self._build_chunk_diagnostic_metadata(
                chunk_result=chunk_result,
                metadata_key="fallback",
            ),
            "semantic_chunking": self._build_semantic_chunking_metadata(
                chunk_result=chunk_result,
            ),
            "artifacts_written": artifacts_written,
            "artifacts": artifacts,
            "parser_metadata": sanitize_debug_metadata(
                parse_result.metadata if parse_result is not None else {}
            ),
            "chunking_config": self._build_chunking_config_metadata(
                chunking_config=chunking_config,
            ),
        }
        if chunks_json_size_bytes is not None:
            manifest["chunks_json_size_bytes"] = chunks_json_size_bytes

        if error is not None:
            manifest["error"] = sanitize_debug_error(error)

        if artifact_write_failures:
            manifest["artifact_write_warning"] = {
                "failed_artifacts": [
                    {
                        "artifact": failure.artifact,
                        "path": failure.path,
                        "error": failure.error,
                    }
                    for failure in artifact_write_failures
                ]
            }

        return manifest

    def _build_chunk_methods(
        self,
        *,
        chunk_result: ChunkResult | None,
    ) -> list[str]:
        if chunk_result is None:
            return []

        return sorted({chunk.method for chunk in chunk_result.chunks})

    def _build_chunk_diagnostic_metadata(
        self,
        *,
        chunk_result: ChunkResult | None,
        metadata_key: str,
    ) -> dict[str, object]:
        if chunk_result is None:
            return {}

        metadata_value = chunk_result.metadata.get(metadata_key)
        if not isinstance(metadata_value, Mapping):
            return {}

        return sanitize_debug_metadata(metadata_value)

    def _build_chunking_config_metadata(
        self,
        *,
        chunking_config: ChunkingConfig | None,
    ) -> dict[str, object]:
        if chunking_config is None:
            return {}

        return {
            "target_tokens": chunking_config.target_tokens,
            "min_tokens": chunking_config.min_tokens,
            "max_tokens": chunking_config.max_tokens,
            "overlap_ratio": chunking_config.overlap_ratio,
            "is_batching_enabled": chunking_config.is_batching_enabled,
            "batch_max_tokens": chunking_config.batch_max_tokens,
            "batch_max_sections": chunking_config.batch_max_sections,
            "model": chunking_config.model,
            "prompt_version": chunking_config.prompt_version,
            "temperature": chunking_config.temperature,
            "seed": chunking_config.seed,
            "max_output_tokens": chunking_config.max_output_tokens,
            "provider": {
                "zdr": chunking_config.provider_zdr,
                "data_collection": chunking_config.provider_data_collection,
                "require_parameters": chunking_config.provider_require_parameters,
                "allow_fallbacks": chunking_config.provider_allow_fallbacks,
            },
            "inference_mode": "sequential",
            "is_llm_enabled": chunking_config.is_llm_enabled,
            "request_timeout_seconds": chunking_config.request_timeout_seconds,
        }

    def _build_semantic_chunking_metadata(
        self,
        *,
        chunk_result: ChunkResult | None,
    ) -> dict[str, object]:
        if chunk_result is None:
            return {}

        metadata = chunk_result.metadata.get("semantic_chunking")
        if not isinstance(metadata, Mapping):
            return {}

        return {
            "model": self._safe_scalar(metadata.get("model")),
            "prompt_version": self._safe_scalar(metadata.get("prompt_version")),
            "temperature": self._safe_scalar(metadata.get("temperature")),
            "seed": self._safe_scalar(metadata.get("seed")),
            "max_output_tokens": self._safe_scalar(metadata.get("max_output_tokens")),
            "provider": self._allowlisted_mapping(
                metadata.get("provider"),
                allowed_keys=(
                    "zdr",
                    "data_collection",
                    "require_parameters",
                    "allow_fallbacks",
                ),
            ),
            "inference_mode": self._safe_scalar(metadata.get("inference_mode")),
            "request_count": self._safe_scalar(metadata.get("request_count")),
            "latency_ms": self._allowlisted_mapping(
                metadata.get("latency_ms"),
                allowed_keys=("total", "average"),
            ),
            "usage": self._allowlisted_mapping(
                metadata.get("usage"),
                allowed_keys=(
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "cost_usd",
                ),
            ),
            "requests": self._allowlisted_request_diagnostics(metadata.get("requests")),
        }

    def _allowlisted_request_diagnostics(self, value: object) -> list[object]:
        if not isinstance(value, Sequence) or isinstance(
            value, str | bytes | bytearray
        ):
            return []

        request_diagnostics: list[object] = []
        for request in value:
            if not isinstance(request, Mapping):
                continue

            request_diagnostics.append(
                {
                    "model": self._safe_scalar(request.get("model")),
                    "prompt_version": self._safe_scalar(request.get("prompt_version")),
                    "temperature": self._safe_scalar(request.get("temperature")),
                    "seed": self._safe_scalar(request.get("seed")),
                    "max_output_tokens": self._safe_scalar(
                        request.get("max_output_tokens")
                    ),
                    "provider": self._allowlisted_mapping(
                        request.get("provider"),
                        allowed_keys=(
                            "zdr",
                            "data_collection",
                            "require_parameters",
                            "allow_fallbacks",
                        ),
                    ),
                    "latency_ms": self._safe_scalar(request.get("latency_ms")),
                    "usage": self._allowlisted_mapping(
                        request.get("usage"),
                        allowed_keys=(
                            "prompt_tokens",
                            "completion_tokens",
                            "total_tokens",
                            "cost_usd",
                        ),
                    ),
                    "validation_outcome": self._safe_scalar(
                        request.get("validation_outcome")
                    ),
                    "fallback_reason": self._safe_scalar(
                        request.get("fallback_reason")
                    ),
                }
            )
        return request_diagnostics

    def _allowlisted_mapping(
        self,
        value: object,
        *,
        allowed_keys: Sequence[str],
    ) -> dict[str, object]:
        if not isinstance(value, Mapping):
            return {}

        return {
            key: self._safe_scalar(value.get(key))
            for key in allowed_keys
            if key in value
        }

    def _safe_scalar(self, value: object) -> str | int | float | bool | None:
        if isinstance(value, str | int | float | bool) or value is None:
            return value
        return None

    def _serialize_json(self, payload: object) -> str:
        return json.dumps(payload, ensure_ascii=False, indent=2)


def sanitize_debug_error(exc: BaseException) -> dict[str, str]:
    raw_message = str(exc).strip() or exc.__class__.__name__
    if _contains_sensitive_text(raw_message):
        message = "Error message omitted because it may contain sensitive information."
    else:
        message = raw_message

    if len(message) > MAX_DEBUG_ERROR_MESSAGE_LENGTH:
        message = f"{message[:MAX_DEBUG_ERROR_MESSAGE_LENGTH]}..."

    return {
        "error_type": exc.__class__.__name__,
        "message": message,
    }


def sanitize_debug_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    sanitized_metadata: dict[str, object] = {}
    for key, value in metadata.items():
        if _is_sensitive_key(key):
            continue

        sanitized_metadata[key] = _sanitize_debug_value(value)

    return sanitized_metadata


def _sanitize_debug_value(value: object) -> DebugMetadataValue:
    if isinstance(value, str | int | float | bool) or value is None:
        return value

    if isinstance(value, Mapping):
        sanitized_mapping: dict[str, DebugMetadataValue] = {}
        for key, nested_value in value.items():
            if not isinstance(key, str) or _is_sensitive_key(key):
                continue

            sanitized_mapping[key] = _sanitize_debug_value(nested_value)
        return sanitized_mapping

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_sanitize_debug_value(item) for item in value]

    return UNSUPPORTED_DEBUG_VALUE


def _is_sensitive_key(key: str) -> bool:
    normalized_key = key.lower()
    return any(
        fragment in normalized_key for fragment in SENSITIVE_METADATA_KEY_FRAGMENTS
    )


def _contains_sensitive_text(value: str) -> bool:
    normalized_value = value.lower()
    return any(
        fragment in normalized_value for fragment in SENSITIVE_METADATA_KEY_FRAGMENTS
    )
