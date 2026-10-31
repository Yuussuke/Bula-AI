from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from fastapi import UploadFile

from app.modules.bulas.models import Bula, BulaStatus, SharedReviewStatus


class SharedSourceInput(BaseModel):
    product_name: str = Field(min_length=2, max_length=255)
    manufacturer: str | None = Field(default=None, max_length=500)
    source_url: HttpUrl
    source_description: str = Field(min_length=3, max_length=1000)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("source_url")
    @classmethod
    def validate_source_link(cls, value: HttpUrl) -> HttpUrl:
        # A declared citation, never a URL to download on the server.
        if (
            value.scheme != "https"
            or value.username
            or value.password
            or len(str(value)) > 2048
        ):
            raise ValueError("Informe um endereço HTTPS sem credenciais.")
        return value


class CurationDecision(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=3000)
    product_name: str | None = Field(default=None, min_length=2, max_length=255)
    manufacturer: str | None = Field(default=None, max_length=500)
    presentation: str | None = Field(default=None, max_length=2000)
    strength: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class SharedUploadInput(SharedSourceInput):
    file: UploadFile


class SharedBulaResponse(BaseModel):
    id: UUID
    product_name: str
    manufacturer: str | None
    presentation: str | None
    strength: str | None
    source_url: str
    source_description: str
    review_status: SharedReviewStatus
    ingestion_status: BulaStatus
    is_available: bool
    version: int
    submitted_at: datetime
    sha256_checksum: str
    content_size_bytes: int
    error_message: str | None = None
    ingestion_job_id: int | None = None
    submitted_by_id: int
    supersedes_bula_id: UUID | None = None

    @classmethod
    def from_bula(
        cls, bula: Bula, *, is_available: bool = False
    ) -> "SharedBulaResponse":
        submission = bula.shared_submission
        if submission is None:
            raise ValueError("Shared bula has no submission provenance.")
        return cls(
            id=bula.id,
            product_name=bula.drug_name,
            manufacturer=bula.manufacturer,
            presentation=submission.presentation,
            strength=submission.strength,
            source_url=submission.source_url,
            source_description=submission.source_description,
            review_status=SharedReviewStatus(submission.review_status),
            ingestion_status=bula.status,
            is_available=is_available,
            version=submission.version,
            submitted_at=submission.created_at,
            sha256_checksum=submission.sha256_checksum,
            content_size_bytes=submission.content_size_bytes,
            error_message=bula.error_message,
            ingestion_job_id=submission.ingestion_job_id,
            submitted_by_id=bula.user_id,
            supersedes_bula_id=submission.supersedes_bula_id,
        )


class CurationMutationResponse(SharedBulaResponse):
    operation_id: UUID
    replayed: bool


class CurationEventResponse(BaseModel):
    id: UUID
    actor_id: int | None
    actor_role: str | None = None
    operation_id: UUID | None = None
    request_fingerprint: str | None = None
    before_state: dict[str, object] | None = None
    after_state: dict[str, object] | None = None
    action: str
    actor_name: str
    reason: str
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SharedBulaDetail(BaseModel):
    document: SharedBulaResponse
    events: list[CurationEventResponse]
    submitted_by_name: str | None = None


class SharedBulaPage(BaseModel):
    items: list[SharedBulaResponse]
    total: int
    limit: int
    offset: int


class CurationListQuery(BaseModel):
    view: Literal["public", "mine", "review"] = "public"
    status: SharedReviewStatus | None = None
    query: str = Field(default="", max_length=200)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
