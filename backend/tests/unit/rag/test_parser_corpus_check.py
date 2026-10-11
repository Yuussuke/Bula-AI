"""Offline comparison reports changes without replacing the baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from scripts.check_parser_corpus import compare_results, parse_documents


def write_result(directory: Path, *, checksum: str, markdown: str) -> None:
    directory.mkdir()
    (directory / "A-example.json").write_text(
        json.dumps(
            {
                "sha256": checksum,
                "success": True,
                "error": None,
                "markdown": markdown,
                "metadata": {"front_matter": "same source identity"},
            }
        ),
        encoding="utf-8",
    )


def test_comparison_reports_text_changes_without_rewriting_inputs(
    tmp_path: Path,
) -> None:
    before, after, output = (tmp_path / name for name in ("before", "after", "diff"))
    write_result(before, checksum="same", markdown="Header\nOld value\n")
    write_result(after, checksum="same", markdown="Header\nNew value\n")
    original = (before / "A-example.json").read_bytes()
    compare_results(argparse.Namespace(before=before, after=after, output=output))
    report = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
    assert report["changed_previous_successes"] == ["A-example"]
    assert report["records"][0]["lost_unique_words"] == ["old"]
    assert not report["records"][0]["front_matter_changed"]
    assert (before / "A-example.json").read_bytes() == original
    assert (output / "A-example.diff").exists()


def test_comparison_rejects_different_source_pdfs(tmp_path: Path) -> None:
    before, after, output = (tmp_path / name for name in ("before", "after", "diff"))
    write_result(before, checksum="original", markdown="value")
    write_result(after, checksum="different", markdown="value")
    with pytest.raises(ValueError, match="PDF identity differs"):
        compare_results(argparse.Namespace(before=before, after=after, output=output))


@pytest.mark.anyio
async def test_parser_check_rejects_unsafe_output_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The CLI's process-wide network guard must not leak into other tests.
    monkeypatch.setattr("socket.socket.connect", lambda *args: None)
    monkeypatch.setattr("socket.create_connection", lambda *args: None)
    configuration = tmp_path / "inputs.json"
    configuration.write_text(
        json.dumps(
            {"documents": [{"corpus_id": "../escape", "document_id": "example"}]}
        ),
        encoding="utf-8",
    )
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Unsafe corpus/document identity"):
        await parse_documents(
            argparse.Namespace(
                documents=[configuration], pdf_root=tmp_path, output=output
            )
        )
    assert not output.exists()
