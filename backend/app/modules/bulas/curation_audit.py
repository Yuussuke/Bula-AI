"""Stable operation fingerprints and documentary snapshots; no HTTP or database access."""

from app.modules.bulas.models import Bula


def shared_bula_snapshot(bula: Bula) -> dict[str, object]:
    submission = bula.shared_submission
    if submission is None:
        raise ValueError("Shared document has no submission provenance.")
    return {
        "bula_id": str(bula.id),
        "sha256_checksum": submission.sha256_checksum,
        "content_size_bytes": submission.content_size_bytes,
        "source_url": submission.source_url,
        "source_description": submission.source_description,
        "product_name": bula.drug_name,
        "manufacturer": bula.manufacturer,
        "presentation": submission.presentation,
        "strength": submission.strength,
        "review_status": submission.review_status,
        "ingestion_status": bula.status.value,
        "error_message": bula.error_message,
        "qdrant_collection": bula.qdrant_collection,
        "version": submission.version,
        "ingestion_job_id": submission.ingestion_job_id,
        "ingestion_operation_id": str(submission.ingestion_operation_id)
        if submission.ingestion_operation_id
        else None,
        "supersedes_bula_id": str(submission.supersedes_bula_id)
        if submission.supersedes_bula_id
        else None,
    }
