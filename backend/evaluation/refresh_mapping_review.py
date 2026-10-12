"""Refresh presentation only, preserving mapping data and old review compatibility."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from evaluation.artifacts import (
    digest_file,
    digest_value,
    read_json,
    source_path,
    write_new_json,
)
from evaluation.mapping_review import HumanMappingLedger
from evaluation.prepare_mapping import MappingPackageBuilder


class MappingReviewRefresher:
    def refresh(self, root: Path, original: Path, output: Path) -> dict[str, Any]:
        root, original, output = root.resolve(), original.resolve(), output.resolve()
        if output.exists():
            raise ValueError(
                "Review presentations are immutable; use a fresh directory"
            )
        if original.parent != output.parent:
            raise ValueError(
                "Keep the same artifact parent to preserve relative PDF links"
            )
        manifest = read_json(original / "manifest.json")
        body = dict(manifest)
        if body.pop("fingerprint_sha256") != digest_value(body):
            raise ValueError("Parent manifest fingerprint changed")
        for name, expected in manifest["artifacts"].items():
            if digest_file(source_path(original, name)) != expected:
                raise ValueError("Parent artifact changed")
        for name, expected in manifest["input_files"].items():
            if digest_file(source_path(root, name)) != expected:
                raise ValueError("Frozen mapping source changed")
        package = read_json(original / "review-package.json")
        if package["package_sha256"] != manifest["package_sha256"]:
            raise ValueError("Parent package binding changed")
        ledger = HumanMappingLedger(package)
        for case in package["cases"]:
            pdf = (original / unquote(case["pdf_link"])).resolve()
            # PDF links intentionally leave the artifact directory for the verified
            # corpus. Resolve against its parent, then enforce the repository root.
            if not pdf.is_relative_to(root) or digest_file(pdf) != case["pdf_sha256"]:
                raise ValueError("Original PDF identity changed")
        output.mkdir(parents=True)
        write_new_json(output / "review-package.json", package)
        if digest_file(output / "review-package.json") != digest_file(
            original / "review-package.json"
        ):
            raise ValueError("Presentation refresh must preserve exact package bytes")
        MappingPackageBuilder._render(output, package)
        counts = {
            "priority": sum(
                case["mapping"]["status"] != "complete" for case in package["cases"]
            ),
            "quick": sum(
                case["mapping"]["status"] == "complete" for case in package["cases"]
            ),
        }
        report = """# Prioritized mapping review — presentation v4

The view shows absent, partial and ambiguous cases first, then complete lexical
correspondences. Candidate discovery, golds, records and package identity are
unchanged. Prioritized does not mean a confirmed source error.

Quick review shows both question variants, indispensable information,
qualifiers, source-page links and original indexed chunks beside each quote.
The per-record approval button explicitly attests all displayed review criteria
together, selects only the displayed unique full-text proposal, records a human
event and advances. It is not bulk approval, inferred semantic support or an
attestation of full-PDF reading. Tables/fallbacks remain visible warnings.

Loading, navigating or inspecting a proposal creates no decision. Priority
cases require detailed review. Existing decisions and dirty detailed edits
disable quick approval; the detailed form can append a new decision without
overwriting history. Prior partial/tangential candidates remain inspectable.

Export before closing. Existing exports from the unchanged parent package can
be imported; no human decisions are imported during this preparation. This is
a presentation change, not another mapping generation or an experiment.
"""
        with (output / "report.md").open("x", encoding="utf-8") as stream:
            stream.write(report)
        result = {
            "presentation_version": 4,
            "status": "pending_explicit_human_mapping_review",
            "parent_manifest_sha256": digest_file(original / "manifest.json"),
            "package_sha256": package["package_sha256"],
            "data_unchanged": True,
            "review_modes": counts,
            "initial_human_summary": ledger.summary(),
            "ingestion_snapshot_fingerprint": package["ingestion_snapshot_fingerprint"],
            "derived_release_fingerprint": package["derived_release_fingerprint"],
            "input_files": manifest["input_files"],
            "tool_files": {
                name: digest_file(Path(__file__).parent / name)
                for name in (
                    "refresh_mapping_review.py",
                    "mapping_ui/review.js",
                    "mapping_ui/template.html",
                )
            },
            "artifacts": {
                path.name: digest_file(path)
                for path in output.iterdir()
                if path.is_file()
            },
        }
        result["fingerprint_sha256"] = digest_value(result)
        write_new_json(output / "manifest.json", result)
        return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    print(
        MappingReviewRefresher().refresh(options.root, options.original, options.output)
    )


if __name__ == "__main__":
    main()
