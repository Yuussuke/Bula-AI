"""Read-only corpus parsing and comparison; no chunking, providers or indexes.

External input JSON contains a ``documents`` list with corpus_id, document_id,
path and sha256. PDF paths are relative to --pdf-root. Outputs must be new.
Run each parser revision in its own worktree and compare the resulting folders.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import asdict
import difflib
import hashlib
import importlib
import json
from pathlib import Path
import re
import socket
import sys
from typing import Any
from unittest.mock import patch


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def reject_network(*args: object, **kwargs: object) -> None:
    raise RuntimeError("Network access is forbidden in the offline parser check")


def source_fingerprint() -> dict[str, str]:
    parser_directory = Path(__file__).resolve().parents[1] / "app/modules/rag/parsers"
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(parser_directory.glob("*.py"))
    }


async def parse_documents(options: argparse.Namespace) -> None:
    # Fail locally instead of accidentally contacting a provider or database.
    with (
        patch.object(socket.socket, "connect", side_effect=reject_network),
        patch.object(socket, "create_connection", side_effect=reject_network),
    ):
        await _parse_documents(options)


async def _parse_documents(options: argparse.Namespace) -> None:
    from app.modules.rag.parsers.pdf_parser import BulaParser
    import pymupdf

    pymupdf4llm = importlib.import_module("pymupdf4llm")

    documents = [
        document
        for configuration in options.documents
        for document in read_json(configuration)["documents"]
    ]
    identities = [
        (document["corpus_id"], document["document_id"]) for document in documents
    ]
    if any(
        not re.fullmatch(r"[A-Za-z0-9_-]+", identifier)
        for identity in identities
        for identifier in identity
    ):
        raise ValueError("Unsafe corpus/document identity")
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate corpus/document identity")
    fingerprint = source_fingerprint()
    options.output.mkdir(parents=True, exist_ok=False)
    write_json(
        options.output / "run.json",
        {
            "source_files": fingerprint,
            "python": sys.version,
            "pymupdf": pymupdf.__version__,
            "pymupdf4llm": pymupdf4llm.__version__,
            "documents": documents,
        },
    )
    for document in documents:
        path = (options.pdf_root / document["path"]).resolve()
        if not path.is_relative_to(options.pdf_root.resolve()):
            raise ValueError("PDF path escapes the declared input root")
        source = path.read_bytes()
        if hashlib.sha256(source).hexdigest() != document["sha256"]:
            raise ValueError("PDF identity changed")
        parsed = await BulaParser().parse(source, path.name)
        identity = f"{document['corpus_id']}-{document['document_id']}"
        write_json(
            options.output / f"{identity}.json",
            {
                "identity": identity,
                "sha256": document["sha256"],
                **asdict(parsed),
            },
        )
        with (options.output / f"{identity}.md").open("x", encoding="utf-8") as stream:
            stream.write(parsed.markdown)
        if hashlib.sha256(path.read_bytes()).hexdigest() != document["sha256"]:
            raise ValueError("PDF changed during parsing")
        print(f"{identity}: success={parsed.success}; error={parsed.error}", flush=True)
    if source_fingerprint() != fingerprint:
        raise ValueError(
            "Parser source changed during the run; results are not canonical"
        )


def word_counts(text: str) -> Counter[str]:
    return Counter(re.findall(r"\w+", text.casefold()))


def compare_results(options: argparse.Namespace) -> None:
    before_paths = {
        path.stem: path for path in options.before.glob("*.json") if path.stem != "run"
    }
    after_paths = {
        path.stem: path for path in options.after.glob("*.json") if path.stem != "run"
    }
    if before_paths.keys() != after_paths.keys():
        raise ValueError("Comparison requires exactly the same document identities")
    options.output.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, object]] = []
    for identity in sorted(before_paths):
        before = read_json(before_paths[identity])
        after = read_json(after_paths[identity])
        if before["sha256"] != after["sha256"]:
            raise ValueError("Comparison PDF identity differs")
        old_markdown, new_markdown = before["markdown"], after["markdown"]
        is_changed = old_markdown != new_markdown
        old_words, new_words = word_counts(old_markdown), word_counts(new_markdown)
        old_tables = (before.get("cleanup_summary") or {}).get("table_extraction", {})
        new_tables = (after.get("cleanup_summary") or {}).get("table_extraction", {})
        record = {
            "identity": identity,
            "sha256": before["sha256"],
            "before_success": before["success"],
            "after_success": after["success"],
            "after_error": after["error"],
            "markdown_changed": is_changed,
            "before_markdown_sha256": hashlib.sha256(old_markdown.encode()).hexdigest(),
            "after_markdown_sha256": hashlib.sha256(new_markdown.encode()).hexdigest(),
            "removed_word_occurrences": dict(old_words - new_words),
            "added_word_occurrences": dict(new_words - old_words),
            "lost_unique_words": sorted(old_words.keys() - new_words.keys()),
            "front_matter_changed": before["metadata"].get("front_matter")
            != after["metadata"].get("front_matter"),
            "before_tables": old_tables,
            "after_tables": new_tables,
        }
        records.append(record)
        if is_changed:
            with (options.output / f"{identity}.diff").open(
                "x", encoding="utf-8"
            ) as stream:
                stream.writelines(
                    difflib.unified_diff(
                        old_markdown.splitlines(keepends=True),
                        new_markdown.splitlines(keepends=True),
                        fromfile="before",
                        tofile="after",
                    )
                )
    summary = {
        "documents": len(records),
        "previous_successes": sum(bool(record["before_success"]) for record in records),
        "current_successes": sum(bool(record["after_success"]) for record in records),
        "new_failures": [
            record["identity"]
            for record in records
            if record["before_success"] and not record["after_success"]
        ],
        "changed_previous_successes": [
            record["identity"]
            for record in records
            if record["before_success"] and record["markdown_changed"]
        ],
        "records": records,
    }
    write_json(options.output / "comparison.json", summary)
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key != "records"},
            ensure_ascii=False,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    parse_command = commands.add_parser("parse")
    parse_command.add_argument("--documents", type=Path, nargs="+", required=True)
    parse_command.add_argument("--pdf-root", type=Path, required=True)
    parse_command.add_argument("--output", type=Path, required=True)
    compare_command = commands.add_parser("compare")
    compare_command.add_argument("--before", type=Path, required=True)
    compare_command.add_argument("--after", type=Path, required=True)
    compare_command.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    if options.command == "parse":
        asyncio.run(parse_documents(options))
    else:
        compare_results(options)


if __name__ == "__main__":
    main()
