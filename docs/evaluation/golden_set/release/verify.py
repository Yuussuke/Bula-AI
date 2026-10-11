"""Verify the published collection without PDFs, private history or RAG calls."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, cast


def digest_value(value: object) -> str:
    serialized = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return cast(dict[str, Any], value)


def source_path(root: Path, relative_path: str) -> Path:
    resolved_path = (root / relative_path).resolve()
    if not resolved_path.is_relative_to(root.resolve()):
        raise ValueError("Publication path escapes the repository")
    return resolved_path


class PublicationVerifier:
    """Check byte identities and effective versions, not semantic correctness."""

    def __init__(self, root: Path, inventory: dict[str, Any]) -> None:
        self.root = root.resolve()
        self.inventory = inventory

    def read_records(self, relative_path: str) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in source_path(self.root, relative_path)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

    def verify(self) -> dict[str, int]:
        for entry in self.inventory["published_files"]:
            path = source_path(self.root, entry["path"])
            observed_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if observed_hash != entry["sha256"]:
                raise ValueError(f"Changed published artifact: {entry['path']}")

        records: dict[str, dict[str, Any]] = {}
        effective_paths: dict[str, str] = {}
        for entry in self.inventory["effective_inputs"]:
            input_records = self.read_records(entry["path"])
            if len(input_records) != entry["record_count"]:
                raise ValueError("Input record count mismatch")
            for record in input_records:
                records[record["question_id"]] = record
                effective_paths[record["question_id"]] = entry["path"]
        if (
            digest_value(list(records.values()))
            != self.inventory["effective_records_fingerprint_sha256"]
        ):
            raise ValueError("Effective collection fingerprint mismatch")

        bindings = self.read_records(self.inventory["record_bindings_path"])
        binding_ids = [entry["question_id"] for entry in bindings]
        if len(binding_ids) != len(set(binding_ids)) or set(binding_ids) != set(
            records
        ):
            raise ValueError("Record binding membership mismatch")
        for binding in bindings:
            record = records[binding["question_id"]]
            if (
                digest_value(record) != binding["record_sha256"]
                or record["draft_revision"] != binding["draft_revision"]
                or effective_paths[binding["question_id"]] != binding["effective_path"]
            ):
                raise ValueError("Record version binding mismatch")

        documents = {
            (entry["corpus_id"], entry["document_id"]): entry
            for entry in self.inventory["pdfs"]
        }
        if len(documents) != len(self.inventory["pdfs"]):
            raise ValueError("Duplicate reference document")
        per_document: Counter[tuple[str, str, bool]] = Counter()
        for record in records.values():
            identity = (record["corpus_id"], record["document_id"])
            if record["document_sha256"] != documents[identity]["sha256"]:
                raise ValueError("Question/document identity mismatch")
            per_document[(*identity, record["answerable"])] += 1
        expected_counts = self.inventory["counts"]
        for identity in documents:
            for answerable, label in ((True, "positive"), (False, "negative")):
                if (
                    per_document[(*identity, answerable)]
                    != expected_counts["per_pdf"][label]
                ):
                    raise ValueError("Per-document question count mismatch")
        observed_counts = {
            "records": len(records),
            "positive": sum(record["answerable"] for record in records.values()),
            "negative": sum(not record["answerable"] for record in records.values()),
            "pdfs": len(documents),
            "corpus_A_pdfs": sum(identity[0] == "A" for identity in documents),
            "corpus_B_pdfs": sum(identity[0] == "B" for identity in documents),
        }
        if any(expected_counts[key] != value for key, value in observed_counts.items()):
            raise ValueError("Collection count mismatch")
        core = self.inventory["audit"]["core_ids"]
        risk = self.inventory["audit"]["additional_risk_ids"]
        if len(core) != 100 or len(risk) != 20 or len(set(core + risk)) != 120:
            raise ValueError("Audit membership mismatch")
        if not set(core + risk).issubset(records):
            raise ValueError("Unknown audit question")
        return observed_counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[4]
    )
    arguments = parser.parse_args()
    inventory = read_json(
        arguments.root / "docs/evaluation/golden_set/release/publication.json"
    )
    counts = PublicationVerifier(arguments.root, inventory).verify()
    print(
        json.dumps(
            {"status": "passed", "counts": counts, "external_assets_checked": False}
        )
    )


if __name__ == "__main__":
    main()
