from app.modules.rag.deterministic_chunker import DeterministicMarkdownSplitter


class WordTokenEstimator:
    def estimate(self, text: str) -> int:
        return max(1, len(text.split()))


def build_splitter(
    *, target_tokens: int = 12, max_tokens: int = 18
) -> DeterministicMarkdownSplitter:
    return DeterministicMarkdownSplitter(
        token_estimator=WordTokenEstimator(),
        target_tokens=target_tokens,
        max_tokens=max_tokens,
        overlap_ratio=0,
    )


def test_small_dosage_table_remains_complete() -> None:
    source_text = (
        "## POSOLOGIA\n\n"
        "| Peso | Dose | Volume |\n"
        "| --- | --- | --- |\n"
        "| 10 kg | 100 mg | 2 mL |\n"
        "| 20 kg | 200 mg | 4 mL |"
    )

    chunks = build_splitter(max_tokens=40).split(
        source_text=source_text,
        section_title="POSOLOGIA",
    )

    assert len(chunks) == 1
    assert "| 10 kg | 100 mg | 2 mL |" in chunks[0].text
    assert "| 20 kg | 200 mg | 4 mL |" in chunks[0].text


def test_oversized_table_splits_only_between_rows_and_repeats_header() -> None:
    source_text = (
        "| Peso | Dose | Volume |\n"
        "| --- | --- | --- |\n"
        "| 10 kg | 100 mg | 2 mL |\n"
        "| 20 kg | 200 mg | 4 mL |\n"
        "| 30 kg | 300 mg | 6 mL |"
    )

    chunks = build_splitter(max_tokens=24).split(
        source_text=source_text,
        section_title="POSOLOGIA",
    )

    assert len(chunks) == 3
    assert all("| Peso | Dose | Volume |" in chunk.text for chunk in chunks)
    assert all("| --- | --- | --- |" in chunk.text for chunk in chunks)
    assert all(WordTokenEstimator().estimate(chunk.text) <= 24 for chunk in chunks)
    assert sum("| 10 kg | 100 mg | 2 mL |" in chunk.text for chunk in chunks) == 1
    assert sum("| 20 kg | 200 mg | 4 mL |" in chunk.text for chunk in chunks) == 1
    assert sum("| 30 kg | 300 mg | 6 mL |" in chunk.text for chunk in chunks) == 1


def test_bullet_items_and_continuation_lines_remain_together() -> None:
    source_text = (
        "- criancas de 10 kg: 2 mL por dose\n"
        "  sem exceder 8 mL ao dia\n"
        "- adultos: 10 mL por dose\n"
        "  sem exceder 40 mL ao dia"
    )

    chunks = build_splitter(max_tokens=16).split(
        source_text=source_text,
        section_title="POSOLOGIA",
    )

    assert len(chunks) == 2
    assert (
        "criancas de 10 kg: 2 mL por dose\n  sem exceder 8 mL ao dia" in chunks[0].text
    )
    assert "adultos: 10 mL por dose\n  sem exceder 40 mL ao dia" in chunks[1].text
    assert all(WordTokenEstimator().estimate(chunk.text) <= 16 for chunk in chunks)


def test_single_oversized_item_uses_hard_cap_without_truncation() -> None:
    source_text = "- " + " ".join(f"palavra{index}" for index in range(30))

    chunks = build_splitter(max_tokens=8).split(
        source_text=source_text,
        section_title="ADVERTENCIAS",
    )

    assert len(chunks) > 1
    assert all(WordTokenEstimator().estimate(chunk.text) <= 8 for chunk in chunks)
    reconstructed_tokens = [token for chunk in chunks for token in chunk.text.split()]
    assert reconstructed_tokens == source_text.split()
