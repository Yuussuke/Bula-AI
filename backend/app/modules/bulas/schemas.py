from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class BulaCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, description="O Nome do medicamento")
    description: Optional[str] = Field(None, description="Um resumo da bula")
    category: str = Field(..., description="Analgesico, Antibiotico, Antidepressivo, etc.")

class BulaResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BulaUploadResponse(BaseModel):
    filename: str
    pages: int
    characters: int
    chunks: int
    document_id: int