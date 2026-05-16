import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FundamentoCreate(BaseModel):
    tema: str = Field(..., min_length=1, max_length=255)
    titulo: str = Field(..., min_length=1, max_length=255)
    corpo_md: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    resumo: str | None = None
    source_case_id: uuid.UUID | None = None


class FundamentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tema: str
    titulo: str
    corpo_md: str
    tags: list[str] | None = None
    resumo: str | None = None
    source_case_id: uuid.UUID | None = None
    usage_count: int
    created_at: datetime


class LearnResult(BaseModel):
    learned: int
    fundamentos: list[FundamentoRead]


class FundamentoUpdate(BaseModel):
    tema: str | None = Field(default=None, max_length=255)
    titulo: str | None = Field(default=None, max_length=255)
    corpo_md: str | None = None
    tags: list[str] | None = None
    resumo: str | None = None
