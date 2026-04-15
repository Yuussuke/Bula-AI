from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.modules.bulas.models import BulaStatus

# What the user sends to the API 
class BulaCreate(BaseModel):
    drug_name: str = Field(..., json_schema_extra={"example": "Dipirona Monoidratada"})
    file_url: str = Field(..., json_schema_extra={"example": "https://storage.../bula.pdf"})
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
    file_url: str
    qdrant_collection: str | None
    status: BulaStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulaUploadResponse(BaseModel):
    filename: str
    pages: int
    characters: int
    chunks: int
    bula_id: UUID