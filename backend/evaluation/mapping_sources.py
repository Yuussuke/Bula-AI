"""Read-only, hash-bound inputs for documentary mapping; no application imports."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from evaluation.artifacts import (
    digest_file,
    digest_value,
    read_json,
    read_jsonl,
    source_path,
)
from evaluation.contracts import SnapshotChunk
from evaluation.dataset import FrozenCollection


def checked_manifest(
    path: Path, fingerprint_field: str = "fingerprint_sha256"
) -> dict[str, Any]:
    manifest = read_json(path)
    body = dict(manifest)
    if (
        digest_value(
            {key: value for key, value in body.items() if key != fingerprint_field}
        )
        != body[fingerprint_field]
    ):
        raise ValueError("Manifest fingerprint mismatch")
    return manifest


class FrozenMappingSources:
    """Verified frozen questions and the exact previously verified index export."""

    def __init__(
        self,
        root: Path,
        derived_manifest: Path,
        ingestion_snapshot: Path,
        expected_snapshot: str,
    ) -> None:
        self.root = root.resolve()
        self.derived_path = derived_manifest.resolve()
        self.snapshot_path = ingestion_snapshot.resolve()
        self.source = FrozenCollection(
            self.root, self.root / "docs/evaluation/golden_set/frozen/v1/manifest.json"
        )
        self.source.verify_pdf_hashes()
        self.documents = {document.key: document for document in self.source.documents}
        self.files: dict[str, str] = {}
        self._pin(self.source.manifest_path)
        for item in self.source.manifest["effective_inputs"]:
            self._pin(source_path(self.root, item["path"]))
        self._pin(source_path(self.root, self.source.manifest["record_bindings_path"]))
        self.release = checked_manifest(self.derived_path)
        if self.release["status"] != "human_reviewed_methodologically_accepted_frozen":
            raise ValueError("A frozen derived release is required")
        if self.release["source_golden_manifest_sha256"] != digest_file(
            self.source.manifest_path
        ):
            raise ValueError("Derived source identity mismatch")
        self._pin(self.derived_path)
        for name, expected in self.release["inputs"].items():
            path = source_path(self.derived_path.parent, name)
            if digest_file(path) != expected:
                raise ValueError("Frozen derived input changed")
            self._pin(path)
        wording = checked_manifest(self.derived_path.parent / "questions.manifest.json")
        if (
            wording["fingerprint_sha256"] != self.release["dataset_fingerprint_sha256"]
            or wording["source_fingerprint_sha256"]
            != self.source.manifest["manifest_fingerprint_sha256"]
        ):
            raise ValueError("Derived wording belongs to another release")
        annotations = read_jsonl(self.derived_path.parent / "human_annotations.jsonl")
        self.annotations = {row["question_id"]: row for row in annotations}
        if len(self.annotations) != len(annotations):
            raise ValueError("Duplicated frozen human annotation")
        self.records: dict[str, dict[str, Any]] = {}
        self.record_hashes: dict[str, str] = {}
        for entry in wording["entries"]:
            identifier = entry["question_id"]
            if identifier in self.records or identifier not in self.source.records:
                raise ValueError("Unknown or duplicated derived question")
            original = self.source.records[identifier]
            fingerprint = digest_value({"source": original, "derived": entry})
            if (
                entry["source_record_sha256"] != digest_value(original)
                or entry["source_revision"] != original["draft_revision"]
            ):
                raise ValueError("Derived source revision changed")
            annotation = self.annotations.get(identifier, {})
            if (
                annotation.get("record_sha256") != fingerprint
                or annotation.get("decision") != "approved"
            ):
                raise ValueError("Frozen question approval/version mismatch")
            record = deepcopy(original)
            record.update(
                {key: entry[key] for key in ("question_scoped", "question_cross_bula")}
            )
            record["derived_revision"] = entry["derived_revision"]
            self.records[identifier] = record
            self.record_hashes[identifier] = fingerprint
        if set(self.annotations) != set(self.records) or len(self.records) != 200:
            raise ValueError("Expected 200 question/annotation bindings")
        for corpus in ("A", "B"):
            if Counter(
                record["answerable"]
                for record in self.records.values()
                if record["corpus_id"] == corpus
            ) != Counter({True: 80, False: 20}):
                raise ValueError("Derived positive/negative distribution changed")
        for key in self.documents:
            if (
                sum(
                    f"{record['corpus_id']}/{record['document_id']}" == key
                    for record in self.records.values()
                )
                != 2
            ):
                raise ValueError("Expected two questions per PDF")
        declared_pdfs = {
            (row["corpus_id"], row["document_id"], row["sha256"])
            for row in self.release["pdf_identities"]
        }
        if len(self.release["pdf_identities"]) != 100 or declared_pdfs != {
            (document.corpus_id, document.document_id, document.pdf_sha256)
            for document in self.documents.values()
        }:
            raise ValueError("Derived PDF universe changed")
        self.snapshot = checked_manifest(self.snapshot_path)
        if (
            self.snapshot["fingerprint_sha256"] != expected_snapshot
            or self.snapshot["golden_manifest_sha256"]
            != digest_file(self.source.manifest_path)
            or self.snapshot["derived_manifest_sha256"]
            != digest_file(self.derived_path)
        ):
            raise ValueError("Ingestion snapshot does not bind the approved release")
        self._pin(self.snapshot_path)
        for entry in self.snapshot["verification_files"].values():
            path = source_path(self.root, entry["path"])
            if digest_file(path) != entry["sha256"]:
                raise ValueError("Index verification artifact changed")
            verification = checked_manifest(path)
            if verification["successful_count"] != 50 or verification["failed_count"]:
                raise ValueError("Incomplete index verification")
            self._pin(path)
        self.chunks: dict[str, tuple[SnapshotChunk, ...]] = {}
        self.details: dict[str, dict[str, Any]] = {}
        self.checkpoints: dict[str, dict[str, Any]] = {}
        self.markdown: dict[str, str] = {}
        for entry in self.snapshot["effective_documents"]:
            key = f"{entry['corpus']}/{entry['document_id']}"
            if (
                key not in self.documents
                or key in self.chunks
                or entry["pdf_sha256"] != self.documents[key].pdf_sha256
            ):
                raise ValueError("Unexpected or duplicated ingestion PDF")
            path = source_path(self.root, entry["checkpoint"])
            if digest_file(path) != entry["checkpoint_sha256"]:
                raise ValueError("Ingestion checkpoint changed")
            checkpoint = read_json(path)
            if (
                checkpoint.get("status")
                != "ingested_integrity_verified_not_mapping_approved"
            ):
                raise ValueError("Only verified ingestion checkpoints may be mapped")
            for name in (
                "bula_id",
                "pdf_sha256",
                "parser_version",
                "chunk_count",
                "chunks_sha256",
                "markdown_sha256",
            ):
                if checkpoint[name] != entry[name]:
                    raise ValueError("Snapshot/checkpoint binding mismatch")
            chunks_path = source_path(path.parent.parent, checkpoint["chunks_path"])
            markdown_path = chunks_path.parent / "parsed_markdown.md"
            if (
                digest_file(chunks_path) != checkpoint["chunks_sha256"]
                or digest_file(markdown_path) != checkpoint["markdown_sha256"]
            ):
                raise ValueError("Indexed export or parsed Markdown changed")
            exported = read_json(chunks_path)
            if (
                exported["doc_id"] != checkpoint["bula_id"]
                or len(exported["chunks"]) != entry["chunk_count"]
            ):
                raise ValueError("Chunk count/document mismatch")
            values = sorted(exported["chunks"], key=lambda row: row["index"])
            if [row["index"] for row in values] != list(range(len(values))):
                raise ValueError("Chunk order must be unique and contiguous")
            mapped = []
            for row in values:
                if (
                    row["chunk_id"] in self.details
                    or row["doc_id"] != checkpoint["bula_id"]
                ):
                    raise ValueError("Duplicate or foreign indexed chunk")
                chunk = SnapshotChunk(
                    row["chunk_id"],
                    self.documents[key],
                    row["text"],
                    row.get("section_title", ""),
                )
                mapped.append(chunk)
                self.details[chunk.chunk_id] = {
                    **row,
                    "document_key": key,
                    "pdf_sha256": entry["pdf_sha256"],
                    "parser_version": entry["parser_version"],
                    "text_sha256": hashlib.sha256(
                        chunk.text.encode("utf-8")
                    ).hexdigest(),
                    "page_provenance": "not_recorded_in_index_export",
                    "document_fallback": checkpoint.get("fallback", {}),
                }
            self.chunks[key] = tuple(mapped)
            self.checkpoints[key] = checkpoint
            self.markdown[key] = markdown_path.read_text(encoding="utf-8")
            for pinned in (path, chunks_path, markdown_path):
                self._pin(pinned)
        declared_chunk_count = self.snapshot.get(
            "effective_chunk_count", self.snapshot.get("verified_chunks")
        )
        if (
            set(self.chunks) != set(self.documents)
            or not isinstance(declared_chunk_count, int)
            or declared_chunk_count <= 0
            or declared_chunk_count != len(self.details)
            or sum(
                entry["chunk_count"] for entry in self.snapshot["effective_documents"]
            )
            != len(self.details)
        ):
            raise ValueError("Indexed chunks differ from the declared 100-PDF snapshot")
        distribution = Counter(
            checkpoint["parser_version"] for checkpoint in self.checkpoints.values()
        )
        if dict(distribution) != self.snapshot["parser_version_distribution"]:
            raise ValueError("Parser version distribution changed")

    def _pin(self, path: Path) -> None:
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("Input escapes the source repository")
        self.files[path.relative_to(self.root).as_posix()] = digest_file(path)

    def verify_unchanged(self) -> None:
        for relative, expected in self.files.items():
            if digest_file(source_path(self.root, relative)) != expected:
                raise ValueError("Mapping input changed during the offline run")
        self.source.verify_pdf_hashes()
