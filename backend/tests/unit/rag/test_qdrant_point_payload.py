from uuid import UUID

from app.modules.bulas.models import Bula, BulaCorpus, BulaStatus
from app.modules.rag.qdrant_store import build_qdrant_point, make_point_id
from app.modules.rag.schemas import DocumentChunk


def test_make_point_id_is_deterministic() -> None:
    first_point_id = make_point_id("bula-123_chunk-0")
    second_point_id = make_point_id("bula-123_chunk-0")

    assert first_point_id == second_point_id


def test_build_qdrant_point_uses_bula_and_chunk_payload_fields() -> None:
    bula = Bula(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        user_id=1,
        drug_name="Losartana Potassica",
        manufacturer="Example Pharma",
        status=BulaStatus.READY,
        corpus=BulaCorpus.SHARED,
    )
    chunk = DocumentChunk(
        chunk_id="bula-123_chunk-0",
        doc_id="bula-123",
        index=0,
        text="Use conforme orientacao medica.",
        chunk_title="POSOLOGIA",
        section_title="POSOLOGIA",
        token_estimate=8,
        method="heuristic",
    )
    vector = [0.1, 0.2, 0.3]

    point = build_qdrant_point(
        bula=bula,
        chunk=chunk,
        vector=vector,
        embedding_profile="test-model;input=plain-v1",
    )

    assert point.id == make_point_id(chunk.chunk_id)
    assert point.vector == vector
    assert point.payload == {
        "bula_id": "11111111-1111-1111-1111-111111111111",
        "corpus": "shared",
        "drug_name": "Losartana Potassica",
        "manufacturer": "Example Pharma",
        "section_title": "POSOLOGIA",
        "chunk_text": "Use conforme orientacao medica.",
        "chunk_id": "bula-123_chunk-0",
        "chunk_index": 0,
        "embedding_profile": "test-model;input=plain-v1",
    }
