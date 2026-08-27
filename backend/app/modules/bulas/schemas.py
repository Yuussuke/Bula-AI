from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

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


class SystemBulaManifestEntry(BaseModel):
    drug_name: str = Field(min_length=1)
    manufacturer: str | None = None
    source_url: AnyHttpUrl
    filename: str
    sha256_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_size_bytes: int = Field(gt=0)

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
    schema_version: Literal[1] = 1
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    documents: list[SystemBulaManifestEntry] = Field(default_factory=list)


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
