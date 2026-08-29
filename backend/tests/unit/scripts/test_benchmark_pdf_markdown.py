from __future__ import annotations

from pathlib import Path
import sys

import pytest

from scripts.benchmark_pdf_markdown import (
    extract_dosage_signals,
    multiset_token_recall,
    run_process_with_rss_measurement,
    set_recall,
    validate_pdf_paths,
)


def test_lexical_recall_ignores_layout_whitespace_without_losing_tokens() -> None:
    reference = "O início de\nação ocorre entre 30 e 60 minutos."
    hypothesis = "O início de ação ocorre entre 30 e 60 minutos."

    recall = multiset_token_recall(hypothesis=hypothesis, reference=reference)

    assert recall == 1.0


def test_dosage_signals_preserve_decimal_comma_ranges_and_units() -> None:
    text = "Dose de 1,25 a 2,5 mL, 13,2-22,3 mg/kg e máximo diário de 500 mg."

    signals = extract_dosage_signals(text)

    assert signals == ["1,25 a 2,5 ml", "13,2-22,3 mg/kg", "500 mg"]


def test_benchmark_requires_exactly_five_distinct_pdfs() -> None:
    with pytest.raises(ValueError, match="exactly five PDFs"):
        validate_pdf_paths([Path("one.pdf")])


def test_dosage_recall_does_not_penalize_removed_page_duplicates() -> None:
    recall = set_recall(
        hypothesis=["500 mg"],
        reference=["500 mg", "500 mg"],
    )

    assert recall == 1.0


def test_worker_measurement_drains_large_stdout_and_stderr_without_hanging() -> None:
    output_size_bytes = 2 * 1024 * 1024
    command = [
        sys.executable,
        "-c",
        (
            "import sys; "
            f"sys.stdout.write('o' * {output_size_bytes}); "
            f"sys.stderr.write('e' * {output_size_bytes})"
        ),
    ]

    result = run_process_with_rss_measurement(command)

    assert result.return_code == 0
    assert len(result.stdout) == output_size_bytes
    assert len(result.stderr) == output_size_bytes
    assert result.wall_time_seconds >= 0
