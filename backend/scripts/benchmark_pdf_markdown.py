"""Sequentially compare legacy and native PDF-to-Markdown parser paths."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Sequence
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Literal

import psutil
import pymupdf

from app.modules.rag.parsers.document_cleaner import (
    BulaDocumentCleaner,
    DocumentCleanupResult,
)
from app.modules.rag.parsers.handlers import (
    ExtractedPage,
    PdfplumberHandler,
    PyMuPDFHandler,
)
from app.modules.rag.parsers.pdf_parser import BulaParser


ParserVariant = Literal["legacy", "native"]
TOKEN_PATTERN = re.compile(r"[\wµ]+(?:[.,/-][\wµ]+)*", re.UNICODE)
DOSAGE_SIGNAL_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*(?:a|-|–)\s*\d+(?:[.,]\d+)?)?\s*"
    r"(?:mg|g|mcg|µg|mL|UI)(?:\s*/\s*(?:kg|mg|g|mL))?\b",
    re.IGNORECASE,
)
HEADING_PATTERN = re.compile(r"^#{1,6}\s+", re.MULTILINE)
PAGE_NUMBER_PATTERN = re.compile(r"^\s*\d{1,3}\s*$", re.MULTILINE)
DEFAULT_OUTPUT_PATH = Path("tmp/parser-benchmark/results.json")


class PassthroughDocumentCleaner(BulaDocumentCleaner):
    """Preserve the pre-#72 parser behavior for the benchmark baseline."""

    def clean(self, pages: list[ExtractedPage]) -> DocumentCleanupResult:
        extracted_lines = []
        for page in pages:
            extracted_lines.extend(page.lines)

        return DocumentCleanupResult(
            lines=extracted_lines,
            front_matter={},
            summary={"cleanup_mode": "disabled_for_legacy_baseline"},
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare legacy pdfplumber and native PyMuPDF4LLM parsing "
            "sequentially with bounded process-tree memory measurement."
        )
    )
    parser.add_argument(
        "pdfs",
        nargs="*",
        type=Path,
        help="Exactly five representative text-bearing PDF paths.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="JSON report path (default: tmp/parser-benchmark/results.json).",
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--variant",
        choices=("legacy", "native"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--pdf", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-output", type=Path, help=argparse.SUPPRESS)
    return parser


def build_legacy_parser() -> BulaParser:
    pdfplumber_handler = PdfplumberHandler()
    pdfplumber_handler.set_next(PyMuPDFHandler())
    return BulaParser(
        first_handler=pdfplumber_handler,
        document_cleaner=PassthroughDocumentCleaner(),
    )


async def run_worker(
    *,
    pdf_path: Path,
    variant: ParserVariant,
) -> dict[str, object]:
    pdf_bytes = pdf_path.read_bytes()
    parser = BulaParser() if variant == "native" else build_legacy_parser()
    source_text, page_count = extract_native_reference(pdf_bytes)

    started_at = time.perf_counter()
    parse_result = await parser.parse(pdf_bytes=pdf_bytes, filename=pdf_path.name)
    wall_time_seconds = time.perf_counter() - started_at
    if not parse_result.success:
        raise RuntimeError(
            f"{variant} parser failed for {pdf_path.name}: {parse_result.error}"
        )

    source_dosage_signals = extract_dosage_signals(source_text)
    output_dosage_signals = extract_dosage_signals(parse_result.markdown)
    section_metadata = parse_result.metadata.get("section_metadata", [])
    front_matter = parse_result.metadata.get("front_matter", {})

    return {
        "document": pdf_path.name,
        "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "size_bytes": len(pdf_bytes),
        "page_count": page_count,
        "variant": variant,
        "success": True,
        "extraction_tier": parse_result.extraction_tier,
        "parser_version": parse_result.parser_version,
        "converter_name": parse_result.converter_name,
        "converter_version": parse_result.converter_version,
        "extraction_decision": parse_result.extraction_decision,
        "wall_time_seconds": round(wall_time_seconds, 6),
        "source_character_count": len(source_text),
        "output_character_count": len(parse_result.markdown),
        "lexical_token_recall": round(
            multiset_token_recall(
                hypothesis=parse_result.markdown,
                reference=source_text,
            ),
            6,
        ),
        "heading_count": len(HEADING_PATTERN.findall(parse_result.markdown)),
        "detected_section_count": (
            len(section_metadata) if isinstance(section_metadata, list) else 0
        ),
        "front_matter_fields": (
            list(front_matter) if isinstance(front_matter, dict) else []
        ),
        "standalone_page_number_count": len(
            PAGE_NUMBER_PATTERN.findall(parse_result.markdown)
        ),
        "critical_dosage_signal_count": len(output_dosage_signals),
        "unique_critical_dosage_signal_count": len(set(output_dosage_signals)),
        "source_unique_critical_dosage_signal_count": len(set(source_dosage_signals)),
        "critical_dosage_signal_recall": round(
            set_recall(
                hypothesis=output_dosage_signals,
                reference=source_dosage_signals,
            ),
            6,
        ),
        "cleanup_summary": parse_result.cleanup_summary or {},
    }


def extract_native_reference(pdf_bytes: bytes) -> tuple[str, int]:
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        page_texts = [page.get_text("text") or "" for page in document]
        return "\n".join(page_texts), document.page_count
    finally:
        document.close()


def tokenize(value: str) -> list[str]:
    return [token.casefold() for token in TOKEN_PATTERN.findall(value)]


def multiset_token_recall(*, hypothesis: str, reference: str) -> float:
    return multiset_recall(
        hypothesis=tokenize(hypothesis),
        reference=tokenize(reference),
    )


def multiset_recall(*, hypothesis: list[str], reference: list[str]) -> float:
    if not reference:
        return 1.0

    hypothesis_counts = Counter(hypothesis)
    reference_counts = Counter(reference)
    overlap_count = sum(
        min(count, hypothesis_counts[value])
        for value, count in reference_counts.items()
    )
    return overlap_count / len(reference)


def set_recall(*, hypothesis: list[str], reference: list[str]) -> float:
    reference_values = set(reference)
    if not reference_values:
        return 1.0

    return len(reference_values.intersection(hypothesis)) / len(reference_values)


def extract_dosage_signals(value: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", match.group(0)).casefold()
        for match in DOSAGE_SIGNAL_PATTERN.finditer(value)
    ]


def run_measured_worker(
    *,
    pdf_path: Path,
    variant: ParserVariant,
    worker_output_path: Path,
) -> dict[str, object]:
    command = [
        sys.executable,
        "-m",
        "scripts.benchmark_pdf_markdown",
        "--worker",
        "--variant",
        variant,
        "--pdf",
        str(pdf_path.resolve()),
        "--worker-output",
        str(worker_output_path.resolve()),
    ]
    started_at = time.perf_counter()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    process_handle = psutil.Process(process.pid)
    peak_process_tree_rss_bytes = 0

    while process.poll() is None:
        peak_process_tree_rss_bytes = max(
            peak_process_tree_rss_bytes,
            get_process_tree_rss_bytes(process_handle),
        )
        time.sleep(0.05)

    stdout, stderr = process.communicate()
    controller_wall_time_seconds = time.perf_counter() - started_at
    if process.returncode != 0:
        raise RuntimeError(
            f"Benchmark worker failed for {pdf_path.name} ({variant}). "
            f"stdout={stdout.strip()!r} stderr={stderr.strip()!r}"
        )

    result = json.loads(worker_output_path.read_text(encoding="utf-8"))
    result["process_tree_peak_rss_bytes"] = peak_process_tree_rss_bytes
    result["controller_wall_time_seconds"] = round(
        controller_wall_time_seconds,
        6,
    )
    worker_output_path.unlink(missing_ok=True)
    return result


def get_process_tree_rss_bytes(process: psutil.Process) -> int:
    processes = [process]
    try:
        processes.extend(process.children(recursive=True))
    except psutil.NoSuchProcess, psutil.AccessDenied:
        pass

    total_rss_bytes = 0
    for current_process in processes:
        try:
            total_rss_bytes += current_process.memory_info().rss
        except psutil.NoSuchProcess, psutil.AccessDenied:
            continue
    return total_rss_bytes


def build_summary(results: list[dict[str, object]]) -> dict[str, object]:
    summary: dict[str, object] = {}
    for variant in ("legacy", "native"):
        variant_results = [result for result in results if result["variant"] == variant]
        summary[variant] = {
            "document_count": len(variant_results),
            "total_wall_time_seconds": round(
                sum(
                    float(result["controller_wall_time_seconds"])
                    for result in variant_results
                ),
                6,
            ),
            "peak_process_tree_rss_bytes": max(
                int(result["process_tree_peak_rss_bytes"]) for result in variant_results
            ),
            "mean_lexical_token_recall": round(
                sum(float(result["lexical_token_recall"]) for result in variant_results)
                / len(variant_results),
                6,
            ),
            "mean_critical_dosage_signal_recall": round(
                sum(
                    float(result["critical_dosage_signal_recall"])
                    for result in variant_results
                )
                / len(variant_results),
                6,
            ),
            "standalone_page_number_count": sum(
                int(result["standalone_page_number_count"])
                for result in variant_results
            ),
            "heading_count": sum(
                int(result["heading_count"]) for result in variant_results
            ),
        }
    return summary


def validate_pdf_paths(pdf_paths: list[Path]) -> list[Path]:
    if len(pdf_paths) != 5:
        raise ValueError(
            f"The benchmark requires exactly five PDFs; received {len(pdf_paths)}."
        )

    resolved_paths = [path.resolve() for path in pdf_paths]
    missing_paths = [path for path in resolved_paths if not path.is_file()]
    if missing_paths:
        raise FileNotFoundError(
            "Missing benchmark PDFs: " + ", ".join(str(path) for path in missing_paths)
        )

    checksums = [
        hashlib.sha256(path.read_bytes()).hexdigest() for path in resolved_paths
    ]
    if len(set(checksums)) != len(checksums):
        raise ValueError("The five benchmark PDFs must have distinct checksums.")

    return resolved_paths


def run_controller(*, pdf_paths: list[Path], output_path: Path) -> int:
    validated_paths = validate_pdf_paths(pdf_paths)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []

    for document_index, pdf_path in enumerate(validated_paths, start=1):
        for variant in ("legacy", "native"):
            worker_output_path = output_path.with_name(
                f".{output_path.stem}-{document_index}-{variant}-worker.json"
            )
            print(
                f"[{document_index}/5] {pdf_path.name}: {variant}",
                flush=True,
            )
            results.append(
                run_measured_worker(
                    pdf_path=pdf_path,
                    variant=variant,
                    worker_output_path=worker_output_path,
                )
            )

    report = {
        "schema_version": 1,
        "execution_mode": "sequential",
        "document_count": len(validated_paths),
        "variants": ["legacy", "native"],
        "results": results,
        "summary": build_summary(results),
    }
    output_path.write_text(
        f"{json.dumps(report, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Report: {output_path.resolve()}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.worker:
        if (
            arguments.variant is None
            or arguments.pdf is None
            or arguments.worker_output is None
        ):
            raise ValueError("Worker mode requires variant, pdf, and worker-output.")

        worker_result = asyncio.run(
            run_worker(
                pdf_path=arguments.pdf,
                variant=arguments.variant,
            )
        )
        arguments.worker_output.write_text(
            json.dumps(worker_result, ensure_ascii=False),
            encoding="utf-8",
        )
        return 0

    return run_controller(pdf_paths=arguments.pdfs, output_path=arguments.output)


if __name__ == "__main__":
    raise SystemExit(main())
