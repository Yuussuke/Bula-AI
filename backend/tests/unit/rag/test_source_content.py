import pytest

from app.modules.rag.source_content import (
    ChunkContentRole,
    classify_chunk_content,
    without_front_matter,
)


@pytest.mark.parametrize(
    "envelope",
    [
        '---\nproduct: "Produto"\n---',
        '\ufeff \r\n---\r\nproduct: "Produto"\r\n...\r\n',
        '---\nproduct: "Produto"',
    ],
)
def test_metadata_envelope_is_not_answer_evidence(envelope: str) -> None:
    assert classify_chunk_content(envelope) == ChunkContentRole.DOCUMENT_METADATA
    assert without_front_matter(envelope).strip() == ""


def test_mixed_chunk_keeps_original_prose_and_is_evidence() -> None:
    text = '---\nproduct: "Produto"\n---\n\n## Armazenamento\nGuarde na embalagem original.'
    assert classify_chunk_content(text) == ChunkContentRole.EVIDENCE
    assert (
        without_front_matter(text)
        == "\n## Armazenamento\nGuarde na embalagem original."
    )


def test_role_does_not_depend_on_heading_or_drug_name() -> None:
    text = "## Documento\nO produto deve ser protegido da luz."
    assert classify_chunk_content(text) == ChunkContentRole.EVIDENCE
    assert without_front_matter(text) == text


def test_empty_front_matter_does_not_swallow_prose_or_horizontal_rules() -> None:
    text = "---\n---\n\nFonte original.\n\n---\nOutro parágrafo."
    assert classify_chunk_content(text) == ChunkContentRole.EVIDENCE
    assert without_front_matter(text) == "\nFonte original.\n\n---\nOutro parágrafo."
