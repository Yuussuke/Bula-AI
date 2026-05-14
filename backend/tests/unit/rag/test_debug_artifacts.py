from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.modules.rag import debug_artifacts as debug_artifacts_module
from app.modules.rag.debug_artifacts import (
    RAG_DEBUG_ARTIFACTS_SCHEMA_VERSION,
    UNSUPPORTED_DEBUG_VALUE,
    DebugArtifactWriteFailure,
    RAGIngestionDebugArtifacts,
    sanitize_debug_error,
    sanitize_debug_metadata,
)
from app.modules.rag.parsers.pdf_parser import ParseResult
from app.modules.rag.schemas import ChunkResult, ChunkingConfig, DocumentChunk


def build_parse_result() -> ParseResult:
    return ParseResult(
        markdown="## Posologia\nUse conforme orientacao medica.",
        metadata={
            "quality_signals": {
                "is_sparse": False,
                "character_count": 42,
            }
        },
        sections=["Posologia"],
        extraction_tier="fake",
        success=True,
    )


def build_chunk_result() -> ChunkResult:
    chunk = DocumentChunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        index=0,
        text="Use conforme orientacao medica.",
        chunk_title="Posologia",
        section_title="Posologia",
        token_estimate=8,
        method="heuristic",
    )
    return ChunkResult(doc_id="doc-1", chunks=[chunk])


def build_chunking_config() -> ChunkingConfig:
    return ChunkingConfig(
        target_tokens=600,
        min_tokens=200,
        max_tokens=850,
        overlap_ratio=0.12,
        max_concurrency=4,
        model="primary-model",
        fallback_model="fallback-model",
        is_llm_enabled=True,
    )


def make_debug_test_path() -> Path:
    return Path("tmp/rag-ingestion-debug/unit-tests") / uuid4().hex


@pytest.mark.anyio
async def test_disabled_debug_artifacts_do_not_write_files() -> None:
    debug_root = make_debug_test_path()
    writer = RAGIngestionDebugArtifacts(enabled=False, root_path=debug_root)

    result = await writer.write_run_artifacts(
        run_id="run-1",
        doc_id="doc-1",
        filename="leaflet.pdf",
        status="success",
        parse_result=build_parse_result(),
        markdown="## Posologia\nUse conforme orientacao medica.",
        chunk_result=build_chunk_result(),
        chunking_config=build_chunking_config(),
    )

    assert result.artifacts_written == []
    assert result.artifact_write_failures == []
    assert not debug_root.exists()


@pytest.mark.anyio
async def test_enabled_debug_artifacts_write_manifest_markdown_and_chunks() -> None:
    debug_root = make_debug_test_path()
    writer = RAGIngestionDebugArtifacts(enabled=True, root_path=debug_root)
    markdown = "## Posologia\nUse conforme orientacao medica."

    result = await writer.write_run_artifacts(
        run_id="run-1",
        doc_id="doc-1",
        filename="leaflet.pdf",
        status="success",
        parse_result=build_parse_result(),
        markdown=markdown,
        chunk_result=build_chunk_result(),
        chunking_config=build_chunking_config(),
    )

    run_dir = debug_root / "doc-1" / "run-1"
    manifest_path = run_dir / "manifest.json"
    chunks_path = run_dir / "chunks.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result.artifacts_written == ["parsed_markdown", "chunks", "manifest"]
    assert (run_dir / "parsed_markdown.md").read_text(encoding="utf-8") == markdown
    assert chunks_path.exists()
    assert manifest["schema_version"] == RAG_DEBUG_ARTIFACTS_SCHEMA_VERSION
    assert manifest["run_id"] == "run-1"
    assert datetime.fromisoformat(manifest["created_at"]).tzinfo is not None
    assert manifest["status"] == "success"
    assert manifest["artifacts"] == {
        "manifest": "manifest.json",
        "parsed_markdown": "parsed_markdown.md",
        "chunks": "chunks.json",
    }
    assert manifest["artifacts_written"] == [
        "parsed_markdown",
        "chunks",
        "manifest",
    ]
    assert manifest["chunks_json_size_bytes"] == len(chunks_path.read_bytes())
    assert manifest["chunk_methods"] == ["heuristic"]


@pytest.mark.anyio
async def test_artifact_write_warning_does_not_replace_main_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    debug_root = make_debug_test_path()
    writer = RAGIngestionDebugArtifacts(enabled=True, root_path=debug_root)
    original_write_text_artifact = writer._write_text_artifact

    def fail_chunk_artifact_once(
        *,
        run_id: str,
        doc_id: str,
        artifact: str,
        path: Path,
        content: str,
    ) -> DebugArtifactWriteFailure | None:
        if artifact == "chunks":
            return DebugArtifactWriteFailure(
                artifact="chunks",
                path="chunks.json",
                error={"error_type": "OSError", "message": "disk full"},
            )

        return original_write_text_artifact(
            run_id=run_id,
            doc_id=doc_id,
            artifact=artifact,
            path=path,
            content=content,
        )

    monkeypatch.setattr(writer, "_write_text_artifact", fail_chunk_artifact_once)

    await writer.write_run_artifacts(
        run_id="run-1",
        doc_id="doc-1",
        filename="leaflet.pdf",
        status="success",
        parse_result=build_parse_result(),
        markdown="## Posologia\nUse conforme orientacao medica.",
        chunk_result=build_chunk_result(),
        chunking_config=build_chunking_config(),
    )

    manifest = json.loads(
        (debug_root / "doc-1" / "run-1" / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["status"] == "success"
    assert manifest["artifact_write_warning"] == {
        "failed_artifacts": [
            {
                "artifact": "chunks",
                "path": "chunks.json",
                "error": {"error_type": "OSError", "message": "disk full"},
            }
        ]
    }


@pytest.mark.anyio
async def test_io_failure_logs_warning_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning_calls: list[dict[str, object]] = []

    def record_warning(event: str, **kwargs: object) -> None:
        warning_calls.append({"event": event, **kwargs})

    monkeypatch.setattr(debug_artifacts_module.logger, "warning", record_warning)
    blocked_root = make_debug_test_path()
    blocked_root.parent.mkdir(parents=True, exist_ok=True)
    blocked_root.write_text("file blocks directory creation", encoding="utf-8")
    writer = RAGIngestionDebugArtifacts(enabled=True, root_path=blocked_root)

    result = await writer.write_run_artifacts(
        run_id="run-1",
        doc_id="doc-1",
        filename="leaflet.pdf",
        status="success",
        parse_result=build_parse_result(),
        markdown="## Posologia\nUse conforme orientacao medica.",
        chunk_result=build_chunk_result(),
        chunking_config=build_chunking_config(),
    )

    assert result.artifacts_written == []
    assert len(result.artifact_write_failures) == 3
    assert warning_calls
    assert warning_calls[0]["event"] == "rag_ingestion_debug_artifacts_failed"
    assert warning_calls[0]["run_id"] == "run-1"
    assert warning_calls[0]["bula_id"] == "doc-1"
    assert warning_calls[0]["doc_id"] == "doc-1"
    assert warning_calls[0]["error_type"] == "FileExistsError"


def test_sanitize_debug_error_omits_sensitive_messages() -> None:
    sanitized_error = sanitize_debug_error(
        RuntimeError("api_key leaked in exception message")
    )

    assert sanitized_error == {
        "error_type": "RuntimeError",
        "message": "Error message omitted because it may contain sensitive information.",
    }


def test_sanitize_debug_error_limits_message_length() -> None:
    sanitized_error = sanitize_debug_error(RuntimeError("x" * 400))

    assert sanitized_error["error_type"] == "RuntimeError"
    assert len(sanitized_error["message"]) == 303
    assert sanitized_error["message"].endswith("...")


def test_sanitize_debug_metadata_removes_sensitive_and_unsupported_values() -> None:
    raw_metadata = {
        "safe": "value",
        "token": "secret",
        "nested": {
            "password": "secret",
            "value": 1,
        },
        "items": [
            1,
            {
                "authorization": "Bearer secret",
                "ok": True,
            },
            object(),
        ],
        "unsupported": object(),
    }

    sanitized_metadata = sanitize_debug_metadata(raw_metadata)

    assert sanitized_metadata == {
        "safe": "value",
        "nested": {"value": 1},
        "items": [1, {"ok": True}, UNSUPPORTED_DEBUG_VALUE],
        "unsupported": UNSUPPORTED_DEBUG_VALUE,
    }
