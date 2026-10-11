"""Inspect source/configuration without importing the app or starting services."""

from __future__ import annotations

import ast
import os
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evaluation.artifacts import digest_file, digest_value, read_json
from evaluation.dataset import DocumentIdentity, FrozenCollection
from evaluation.runner import plan_retrieval_jobs

SETTING_FIELDS = {
    "MaritacaSettings": ("maritaca_model",),
    "LLMSettings": ("provider", "enable_fallback", "timeout_seconds"),
    "OpenRouterSettings": (
        "chat_model",
        "chunk_model",
        "chunk_timeout_seconds",
        "chunk_max_retries",
        "require_zdr",
    ),
    "ProcessingSettings": (
        "chunk_target_tokens",
        "chunk_min_tokens",
        "chunk_max_tokens",
        "chunk_overlap_ratio",
        "chunk_batch_enabled",
        "chunk_batch_max_tokens",
        "chunk_batch_max_sections",
        "tokenizer_encoding",
    ),
    "EmbeddingSettings": (
        "provider",
        "model",
        "dimension",
        "batch_size",
        "timeout_seconds",
    ),
}


def settings_override_evidence(root: Path) -> dict[str, dict[str, str]]:
    """Allowlisted declarations, not an alternative Pydantic settings loader."""
    prefixes = {
        "MaritacaSettings": "",
        "LLMSettings": "LLM_",
        "OpenRouterSettings": "OPENROUTER_",
        "ProcessingSettings": "PROCESSING_",
        "EmbeddingSettings": "EMBEDDING_",
    }
    allowed_names = {
        prefixes[class_name] + field.upper()
        for class_name, fields in SETTING_FIELDS.items()
        for field in fields
    }
    dotenv: dict[str, str] = {}
    path = root / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.partition("=")
            name = name.strip()
            if separator and name in allowed_names:
                dotenv[name] = value.strip()
    process = {
        name: os.environ[name] for name in sorted(allowed_names) if name in os.environ
    }
    return {
        "dotenv_declarations": dict(sorted(dotenv.items())),
        "tool_process_declarations": process,
    }


def git_read(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def literal_default(node: ast.expr) -> object:
    if isinstance(node, ast.Call):
        defaults = [
            keyword.value for keyword in node.keywords if keyword.arg == "default"
        ]
        if len(defaults) != 1:
            raise ValueError("A static Field default is required")
        node = defaults[0]
    return ast.literal_eval(node)


def read_declared_settings(path: Path) -> dict[str, dict[str, object]]:
    """Explicit allowlist; never execute settings or load credentials/.env."""
    result: dict[str, dict[str, object]] = {}
    for definition in ast.parse(path.read_text(encoding="utf-8")).body:
        if (
            not isinstance(definition, ast.ClassDef)
            or definition.name not in SETTING_FIELDS
        ):
            continue
        fields: dict[str, object] = {}
        for statement in definition.body:
            if (
                isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
                and statement.value is not None
                and statement.target.id in SETTING_FIELDS[definition.name]
            ):
                fields[statement.target.id] = literal_default(statement.value)
        if set(fields) != set(SETTING_FIELDS[definition.name]):
            raise ValueError(f"Unresolved static settings: {definition.name}")
        result[definition.name] = fields
    if set(result) != set(SETTING_FIELDS):
        raise ValueError("Missing settings class")
    return result


def read_module_constants(path: Path, names: tuple[str, ...]) -> dict[str, object]:
    if not path.exists():
        return {}
    values: dict[str, object] = {}
    for statement in ast.parse(path.read_text(encoding="utf-8")).body:
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id in names
        ):
            values[statement.targets[0].id] = literal_default(statement.value)
    return values


class SourceSnapshot:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def capture(self) -> dict[str, Any]:
        paths = list((self.root / "backend/app").rglob("*.py"))
        paths.extend((self.root / "backend/alembic").rglob("*.py"))
        for relative in (
            "backend/pyproject.toml",
            "backend/uv.lock",
            "backend/Dockerfile",
            "backend/run.py",
            "backend/alembic.ini",
            "docker-compose.yml",
        ):
            path = self.root / relative
            if path.exists():
                paths.append(path)
        files = {
            path.relative_to(self.root).as_posix(): digest_file(path)
            for path in sorted(set(paths))
        }
        rag_path = self.root / "backend/app/modules/rag"
        return {
            "root": str(self.root),
            "commit": git_read(self.root, "rev-parse", "HEAD"),
            "pipeline_worktree_changes": git_read(
                self.root,
                "status",
                "--porcelain",
                "--",
                "backend/app",
                "backend/alembic",
                "backend/pyproject.toml",
                "backend/uv.lock",
                "backend/Dockerfile",
                "backend/run.py",
                "backend/alembic.ini",
                "docker-compose.yml",
            ),
            "file_sha256": files,
            "source_fingerprint_sha256": digest_value(files),
            "declared_settings_not_runtime": read_declared_settings(
                self.root / "backend/app/core/config.py"
            ),
            "override_evidence_not_runtime": settings_override_evidence(self.root),
            "parser": read_module_constants(
                rag_path / "parsers/pdf_parser.py", ("PARSER_VERSION",)
            ),
            "retrieval": read_module_constants(
                rag_path / "retrieval_limits.py",
                (
                    "DEFAULT_RETRIEVAL_K",
                    "DEFAULT_DENSE_CANDIDATE_LIMIT",
                    "DEFAULT_HYBRID_CANDIDATE_K",
                ),
            ),
            "runtime_verified": False,
        }

    @staticmethod
    def verify(snapshot: dict[str, Any]) -> None:
        root = Path(snapshot["root"])
        if git_read(root, "rev-parse", "HEAD") != snapshot["commit"]:
            raise ValueError("Source commit changed")
        current = SourceSnapshot(root).capture()
        if (
            current["file_sha256"] != snapshot["file_sha256"]
            or current["source_fingerprint_sha256"]
            != snapshot["source_fingerprint_sha256"]
        ):
            raise ValueError("Pipeline source/dependency files changed")
        if (
            current["pipeline_worktree_changes"]
            != snapshot["pipeline_worktree_changes"]
        ):
            raise ValueError("Pipeline working-tree state changed")
        if (
            current["override_evidence_not_runtime"]
            != snapshot["override_evidence_not_runtime"]
        ):
            raise ValueError("Allowlisted configuration declarations changed")


class ExperimentPreparer:
    def __init__(self, collection: FrozenCollection, candidate_root: Path) -> None:
        self.collection = collection
        self.candidate_root = candidate_root

    def prepare(self) -> dict[str, Any]:
        self.collection.verify_pdf_hashes()
        sources = {
            "main_checkout": SourceSnapshot(self.collection.root).capture(),
            "recommended_candidate": SourceSnapshot(self.candidate_root).capture(),
        }
        jobs = plan_retrieval_jobs(self.collection)
        distribution = Counter(
            f"{job.target.corpus_id}/{job.scenario}/{job.strategy}" for job in jobs
        )
        universes = {
            corpus_id: [
                asdict(document) for document in self.collection.universe(corpus_id)
            ]
            for corpus_id in ("A", "B")
        }
        if (
            any(len(universes[corpus_id]) != 50 for corpus_id in universes)
            or len(jobs) != 4800
            or any(value != 400 for value in distribution.values())
            or len(distribution) != 12
        ):
            raise ValueError("Unexpected frozen universe or retrieval plan composition")
        comparison_paths = set(sources["main_checkout"]["file_sha256"]) | set(
            sources["recommended_candidate"]["file_sha256"]
        )
        differences = [
            path
            for path in sorted(comparison_paths)
            if sources["main_checkout"]["file_sha256"].get(path)
            != sources["recommended_candidate"]["file_sha256"].get(path)
        ]
        result = {
            "schema_version": 1,
            "status": "offline_prepared_not_execution_authorized",
            "golden_set_manifest_path": str(self.collection.manifest_path),
            "golden_set_manifest_sha256": digest_file(self.collection.manifest_path),
            "golden_set_fingerprint_sha256": self.collection.manifest[
                "manifest_fingerprint_sha256"
            ],
            "evaluation_tool_file_sha256": {
                path.relative_to(self.collection.root).as_posix(): digest_file(path)
                for path in sorted(
                    (self.collection.root / "backend/evaluation").iterdir()
                )
                if path.is_file() and path.suffix in {".py", ".yaml"}
            },
            "sources": sources,
            "different_source_paths": differences,
            "universes": universes,
            "retrieval_plan": {
                "queries": len(jobs),
                "distribution": dict(sorted(distribution.items())),
                "jobs_sha256": digest_value([asdict(job) for job in jobs]),
                "selector_calls": 0,
                "generator_calls": 0,
            },
            "protocol": {
                "recall_cutoff": 10,
                "mrr_cutoff": 10,
                "relevance": "target_pdf_only",
                "ranking_stage": "strategy_output_before_safety_supplement_selection_generation",
                "cross_target_filter": False,
                "negative_abstention": "scoped_only",
                "unresolved_positive_policy": "pending_author_approval_no_scorer_implemented",
                "response_coverage": "pending_author_approval",
            },
            "layout": {
                "snapshots": "snapshots/<ingestion-id>/",
                "mapping": "mapping/<ingestion-id>/",
                "retrieval": "runs/retrieval/<run-id>/",
                "responses": "runs/responses/<run-id>/",
            },
            "runtime_requirements": [
                "approved canonical commit and clean source",
                "resolved non-secret settings including environment overrides",
                "image digests and installed versions",
                "migration and BM25 normalization/index configuration",
                "separate A/B databases and vector universes",
                "ingestion snapshot and chunk/PDF identity exports",
            ],
            "authorization": {
                "ingestion": False,
                "embeddings": False,
                "experimental_retrieval": False,
                "mapping": False,
                "selection": False,
                "generation": False,
                "judging": False,
                "metrics": False,
            },
        }
        result["fingerprint_sha256"] = digest_value(result)
        return result

    @staticmethod
    def verify(path: Path) -> None:
        manifest = read_json(path)
        body = dict(manifest)
        declared_fingerprint = body.pop("fingerprint_sha256")
        if digest_value(body) != declared_fingerprint:
            raise ValueError("Preparation manifest changed")
        golden_path = Path(manifest["golden_set_manifest_path"])
        if digest_file(golden_path) != manifest["golden_set_manifest_sha256"]:
            raise ValueError("Golden Set manifest changed")
        root = Path(manifest["sources"]["main_checkout"]["root"])
        collection = FrozenCollection(root, golden_path)
        collection.verify_pdf_hashes()
        tool_files = {
            tool_path.relative_to(root).as_posix(): digest_file(tool_path)
            for tool_path in sorted((root / "backend/evaluation").iterdir())
            if tool_path.is_file() and tool_path.suffix in {".py", ".yaml"}
        }
        if tool_files != manifest["evaluation_tool_file_sha256"]:
            raise ValueError("Evaluation infrastructure changed")
        for snapshot in manifest["sources"].values():
            SourceSnapshot.verify(snapshot)
        for corpus_id, rows in manifest["universes"].items():
            documents = tuple(DocumentIdentity(**row) for row in rows)
            collection.validate_index_universe(corpus_id, documents)
        if (
            digest_value([asdict(job) for job in plan_retrieval_jobs(collection)])
            != manifest["retrieval_plan"]["jobs_sha256"]
        ):
            raise ValueError("Retrieval jobs changed")
