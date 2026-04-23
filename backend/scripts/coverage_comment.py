from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def format_percent(value: float) -> str:
    return f"{value:.1f}%"


def load_coverage_report(input_path: Path) -> dict[str, Any]:
    with input_path.open("r", encoding="utf-8") as coverage_file:
        return json.load(coverage_file)


def build_file_rows(coverage_report: dict[str, Any]) -> list[str]:
    files = coverage_report.get("files", {})
    file_rows: list[tuple[float, str]] = []

    for file_name, file_data in files.items():
        summary = file_data.get("summary", {})
        statements = int(summary.get("num_statements", 0))
        missing_lines = int(summary.get("missing_lines", 0))
        percent_covered = float(summary.get("percent_covered", 0.0))

        row = (
            f"| `{file_name}` | {format_percent(percent_covered)} | "
            f"{statements} | {missing_lines} |"
        )
        file_rows.append((percent_covered, row))

    return [row for _, row in sorted(file_rows, key=lambda item: item[0])]


def build_markdown(coverage_report: dict[str, Any], minimum_coverage: int) -> str:
    totals = coverage_report.get("totals", {})
    total_percent_covered = float(totals.get("percent_covered", 0.0))
    total_statements = int(totals.get("num_statements", 0))
    total_missing_lines = int(totals.get("missing_lines", 0))

    lines = [
        "## Backend Coverage",
        "",
        f"Baseline gate: `{minimum_coverage}%`",
        f"Current total: `{format_percent(total_percent_covered)}`",
        "",
        "| Scope | Coverage | Statements | Missing Lines |",
        "|---|---:|---:|---:|",
        (
            f"| `TOTAL` | {format_percent(total_percent_covered)} | "
            f"{total_statements} | {total_missing_lines} |"
        ),
        "",
        "| File | Coverage | Statements | Missing Lines |",
        "|---|---:|---:|---:|",
    ]
    lines.extend(build_file_rows(coverage_report))
    lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Builds a Markdown coverage map from coverage.py JSON output."
    )
    parser.add_argument("--input", type=Path, default=Path("coverage.json"))
    parser.add_argument("--output", type=Path, default=Path("coverage-summary.md"))
    parser.add_argument("--minimum", type=int, default=79)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    coverage_report = load_coverage_report(args.input)
    markdown = build_markdown(coverage_report, args.minimum)
    args.output.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
