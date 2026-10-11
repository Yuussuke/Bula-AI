"""Read the frozen release, not historical draft-status fields or RAG outputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation.artifacts import (
    digest_file,
    digest_value,
    read_json,
    read_jsonl,
    source_path,
)


@dataclass(frozen=True)
class DocumentIdentity:
    corpus_id: str
    document_id: str
    pdf_sha256: str
    relative_path: str

    @property
    def key(self) -> str:
        return f"{self.corpus_id}/{self.document_id}"


class FrozenCollection:
    def __init__(self, root: Path, manifest_path: Path) -> None:
        self.root = root.resolve()
        self.manifest_path = manifest_path.resolve()
        self.manifest = read_json(self.manifest_path)
        manifest_body = dict(self.manifest)
        declared_fingerprint = manifest_body.pop("manifest_fingerprint_sha256")
        if digest_value(manifest_body) != declared_fingerprint:
            raise ValueError("Frozen manifest fingerprint mismatch")
        if self.manifest["status"] != "methodologically_accepted_frozen":
            raise ValueError("A methodologically frozen collection is required")
        self.records: dict[str, dict[str, Any]] = {}
        record_paths: dict[str, str] = {}
        for entry in self.manifest["effective_inputs"]:
            path = source_path(self.root, entry["path"])
            if digest_file(path) != entry["sha256"]:
                raise ValueError(f"Changed frozen input: {entry['path']}")
            rows = read_jsonl(path)
            if len(rows) != entry["record_count"]:
                raise ValueError("Frozen input count mismatch")
            for record in rows:
                self.records[record["question_id"]] = record
                record_paths[record["question_id"]] = entry["path"]
        if (
            digest_value(list(self.records.values()))
            != self.manifest["effective_records_fingerprint_sha256"]
        ):
            raise ValueError("Effective collection mismatch")
        bindings = read_jsonl(
            source_path(self.root, self.manifest["record_bindings_path"])
        )
        if len(bindings) != len(self.records) or {
            row["question_id"] for row in bindings
        } != set(self.records):
            raise ValueError("Record binding membership mismatch")
        for binding in bindings:
            record = self.records[binding["question_id"]]
            if (
                digest_value(record) != binding["record_sha256"]
                or record["draft_revision"] != binding["draft_revision"]
                or record_paths[binding["question_id"]] != binding["effective_path"]
            ):
                raise ValueError("Record version binding mismatch")
        self.documents = tuple(
            DocumentIdentity(
                row["corpus_id"], row["document_id"], row["sha256"], row["path"]
            )
            for row in self.manifest["pdfs"]
        )
        if len({document.key for document in self.documents}) != len(self.documents):
            raise ValueError("Duplicate document identity")
        document_lookup = {document.key: document for document in self.documents}
        for record in self.records.values():
            key = f"{record['corpus_id']}/{record['document_id']}"
            if (
                key not in document_lookup
                or record["document_sha256"] != document_lookup[key].pdf_sha256
            ):
                raise ValueError("Question/PDF identity mismatch")
        counts = self.manifest["counts"]
        if (
            len(self.records) != counts["records"]
            or len(self.documents) != counts["pdfs"]
        ):
            raise ValueError("Collection count mismatch")
        for document in self.documents:
            document_records = [
                record
                for record in self.records.values()
                if f"{record['corpus_id']}/{record['document_id']}" == document.key
            ]
            if Counter(record["answerable"] for record in document_records) != Counter(
                {
                    True: counts["per_pdf"]["positive"],
                    False: counts["per_pdf"]["negative"],
                }
            ):
                raise ValueError("Per-document positive/negative count mismatch")

    def verify_pdf_hashes(self) -> None:
        for document in self.documents:
            if (
                digest_file(source_path(self.root, document.relative_path))
                != document.pdf_sha256
            ):
                raise ValueError(f"Changed PDF: {document.key}")

    def universe(self, corpus_id: str) -> tuple[DocumentIdentity, ...]:
        if corpus_id not in {"A", "B"}:
            raise ValueError("Unknown experimental corpus")
        return tuple(
            document for document in self.documents if document.corpus_id == corpus_id
        )

    def validate_index_universe(
        self, corpus_id: str, indexed_documents: tuple[DocumentIdentity, ...]
    ) -> None:
        """Future exports must enumerate exactly the frozen universe, before search."""
        expected = {
            (document.key, document.pdf_sha256) for document in self.universe(corpus_id)
        }
        actual = {(document.key, document.pdf_sha256) for document in indexed_documents}
        if len(indexed_documents) != len(actual) or actual != expected:
            raise ValueError(
                "Index universe contains missing, foreign, duplicate or changed PDFs"
            )
