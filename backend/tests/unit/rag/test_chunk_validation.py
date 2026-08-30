import pytest

from app.modules.rag.chunk_validation import (
    SourceChunkValidationError,
    SourceChunkValidator,
    SourceHeadingResolver,
)


def test_complete_ordered_source_coverage_passes_and_reconstructs_whitespace() -> None:
    validator = SourceChunkValidator()
    source_text = "## POSOLOGIA\nDose de 10 mg.\n\nUse uma vez ao dia."

    spans = validator.validate_and_reconstruct(
        source_text=source_text,
        proposed_chunk_texts=[
            "## POSOLOGIA Dose de 10 mg.",
            "Use   uma vez\nao dia.",
        ],
        section_title="POSOLOGIA",
    )

    assert [span.text for span in spans] == [
        "## POSOLOGIA\nDose de 10 mg.",
        "Use uma vez ao dia.",
    ]
    assert " ".join(" ".join(span.text.split()) for span in spans) == " ".join(
        source_text.split()
    )


@pytest.mark.parametrize(
    ("proposals", "expected_reason"),
    [
        (
            ["## A primeiro", "## A primeiro", "segundo terceiro"],
            "duplicate_span",
        ),
        (["segundo terceiro", "## A primeiro"], "reordered_span"),
        (["## A primeiro", "terceiro"], "missing_source_text"),
        (["## A primeiro segundo", "segundo terceiro"], "overlapping_span"),
        (["## A primeiro", "texto inventado"], "non_source_text"),
    ],
)
def test_invalid_source_coverage_is_rejected(
    proposals: list[str],
    expected_reason: str,
) -> None:
    validator = SourceChunkValidator()

    with pytest.raises(SourceChunkValidationError) as exc_info:
        validator.validate_and_reconstruct(
            source_text="## A\nprimeiro segundo terceiro",
            proposed_chunk_texts=proposals,
            section_title="A",
        )

    assert exc_info.value.reason == expected_reason


def test_empty_proposal_is_rejected() -> None:
    validator = SourceChunkValidator()

    with pytest.raises(SourceChunkValidationError) as exc_info:
        validator.validate_and_reconstruct(
            source_text="## A\nTexto.",
            proposed_chunk_texts=["   \n"],
            section_title="A",
        )

    assert exc_info.value.reason == "empty_chunk"


def test_chunk_titles_follow_nested_source_headings() -> None:
    validator = SourceChunkValidator()
    source_text = (
        "## POSOLOGIA\nIntroducao.\n\n"
        "#### CRIANCAS\nDose infantil.\n\n"
        "### ADULTOS\nDose adulta."
    )

    spans = validator.validate_and_reconstruct(
        source_text=source_text,
        proposed_chunk_texts=[
            "## POSOLOGIA Introducao.",
            "#### CRIANCAS Dose infantil.",
            "### ADULTOS Dose adulta.",
        ],
        section_title="POSOLOGIA",
    )

    assert [span.chunk_title for span in spans] == [
        "POSOLOGIA",
        "CRIANCAS",
        "ADULTOS",
    ]


def test_heading_resolver_ignores_future_and_malformed_headings() -> None:
    resolver = SourceHeadingResolver()
    source_text = "Texto inicial.\n###Sem espaco\nTexto.\n### VALIDO\nFinal."

    initial_title = resolver.resolve_title(
        source_text=source_text,
        span_start=0,
        section_title="Secao conhecida",
    )
    final_title = resolver.resolve_title(
        source_text=source_text,
        span_start=source_text.index("Final"),
        section_title="Secao conhecida",
    )

    assert initial_title == "Secao conhecida"
    assert final_title == "VALIDO"


def test_heading_resolver_uses_document_when_no_title_is_available() -> None:
    resolver = SourceHeadingResolver()

    title = resolver.resolve_title(
        source_text="Texto sem heading.",
        span_start=0,
        section_title=" ",
    )

    assert title == "Documento"


def test_large_section_reconstructs_all_source_tokens() -> None:
    validator = SourceChunkValidator()
    source_tokens = [f"token-{token_index}" for token_index in range(20_000)]
    source_text = "## SECAO LONGA\n" + " ".join(source_tokens)
    proposed_chunk_texts = [
        "## SECAO LONGA " + " ".join(source_tokens[:10_000]),
        " ".join(source_tokens[10_000:]),
    ]

    spans = validator.validate_and_reconstruct(
        source_text=source_text,
        proposed_chunk_texts=proposed_chunk_texts,
        section_title="SECAO LONGA",
    )

    reconstructed_tokens = [token for span in spans for token in span.text.split()]
    assert reconstructed_tokens == source_text.split()
