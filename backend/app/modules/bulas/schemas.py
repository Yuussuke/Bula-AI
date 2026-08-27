from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.modules.bulas.models import BulaCorpus, BulaStatus


# What the user sends to the API
class BulaCreate(BaseModel):
    drug_name: str = Field(..., json_schema_extra={"example": "Dipirona Monoidratada"})
    file_url: str = Field(
        ..., json_schema_extra={"example": "https://storage.../bula.pdf"}
    )
    manufacturer: str | None = Field(
        default=None,
        json_schema_extra={"example": "Medley"},
    )


# What the API returns to the user
class BulaResponse(BaseModel):
    id: UUID
    user_id: int
    drug_name: str
    manufacturer: str | None
    file_url: str | None
    file_address: str | None
    qdrant_collection: str | None
    status: BulaStatus
    error_message: str | None
    corpus: BulaCorpus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulaUploadResponse(BaseModel):
    filename: str
    pages: int
    characters: int
    chunks: int
    bula_id: UUID


class BulaStatusResponse(BaseModel):
    id: UUID
    status: BulaStatus
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class SystemBulaManifestReview(BaseModel):
    status: Literal["pending", "approved"] = "pending"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_approval_metadata(self) -> "SystemBulaManifestReview":
        if self.status == "approved" and (
            self.reviewed_by is None or self.reviewed_at is None
        ):
            raise ValueError(
                "Approved manifest entries require reviewed_by and reviewed_at."
            )
        if self.status == "pending" and (
            self.reviewed_by is not None or self.reviewed_at is not None
        ):
            raise ValueError(
                "Pending manifest entries cannot contain approval metadata."
            )
        return self

    model_config = ConfigDict(str_strip_whitespace=True)


class SystemBulaManifestEntry(BaseModel):
    target_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    active_ingredient: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    strength: str = Field(min_length=1)
    pharmaceutical_form: str = Field(min_length=1)
    presentation: str = Field(min_length=1)
    audience: Literal["patient", "professional"]
    manufacturer: str = Field(min_length=1)
    company_tax_id: str = Field(min_length=1)
    anvisa_product_id: int = Field(gt=0)
    registration_number: str = Field(min_length=1)
    process_number: str = Field(min_length=1)
    expedition_number: str = Field(min_length=1)
    transaction_number: str = Field(min_length=1)
    source_record_id: str = Field(pattern=r"^[0-9]+$")
    canonical_source_url: AnyHttpUrl
    source_published_at: datetime
    source_updated_at: datetime | None = None
    search_query: str = Field(min_length=1)
    downloader_version: str = Field(min_length=1)
    downloaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    filename: str
    sha256_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_size_bytes: int = Field(gt=0)
    review: SystemBulaManifestReview = Field(default_factory=SystemBulaManifestReview)

    @field_validator("filename")
    @classmethod
    def validate_pdf_filename(cls, value: str) -> str:
        clean_filename = value.strip()
        has_directory_component = (
            PurePosixPath(clean_filename).name != clean_filename
            or PureWindowsPath(clean_filename).name != clean_filename
        )
        if has_directory_component or not clean_filename.lower().endswith(".pdf"):
            raise ValueError("Manifest filename must be a local PDF filename.")
        return clean_filename

    model_config = ConfigDict(str_strip_whitespace=True)


class SystemBulaManifest(BaseModel):
    schema_version: Literal[2] = 2
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    documents: list[SystemBulaManifestEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_document_identities(self) -> "SystemBulaManifest":
        filenames = [document.filename.casefold() for document in self.documents]
        if len(filenames) != len(set(filenames)):
            raise ValueError("Manifest contains duplicate PDF filenames.")

        target_ids = [document.target_id for document in self.documents]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("Manifest contains duplicate target IDs.")

        source_identities = [
            (document.source_record_id, document.audience)
            for document in self.documents
        ]
        if len(source_identities) != len(set(source_identities)):
            raise ValueError("Manifest contains duplicate source identities.")

        return self


class SystemBulaSeedCandidate(BaseModel):
    manifest_entry: SystemBulaManifestEntry
    content: bytes = Field(repr=False)


class SystemBulaSeedFailure(BaseModel):
    filename: str
    reason: str


class SystemBulaSeedSummary(BaseModel):
    planned: int = 0
    inserted: int = 0
    skipped: int = 0
    queued: int = 0
    failed: int = 0
    failures: list[SystemBulaSeedFailure] = Field(default_factory=list)
