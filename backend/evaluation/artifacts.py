"""Stable identities and append-only artifacts for evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast


def digest_value(value: object) -> str:
    serialized = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("A JSON object is required")
    return cast(dict[str, Any], value)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_new_json(path: Path, value: object) -> None:
    """Exclusive creation: never replace an existing snapshot or history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def source_path(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Source path escapes the declared root")
    return path
