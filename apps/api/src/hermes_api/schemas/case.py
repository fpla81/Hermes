import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.case import CaseStatus

PROCESSO_RE = re.compile(r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$")


class CaseCreate(BaseModel):
    numero_processo: str = Field(..., min_length=20, max_length=64)
    titulo: str | None = Field(default=None, max_length=255)

    @field_validator("numero_processo")
    @classmethod
    def validar_numero(cls, v: str) -> str:
        v = v.strip()
        if not PROCESSO_RE.match(v):
            raise ValueError("numero_processo deve seguir NNNNNNN-DD.AAAA.J.TR.OOOO")
        return v


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero_processo: str
    titulo: str | None
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
