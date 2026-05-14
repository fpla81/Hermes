import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.case import CaseStatus

PROCESSO_RE = re.compile(r"^(\d{6,7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$")


class CaseCreate(BaseModel):
    numero_processo: str = Field(..., min_length=19, max_length=64)
    titulo: str | None = Field(default=None, max_length=255)

    @field_validator("numero_processo")
    @classmethod
    def validar_numero(cls, v: str) -> str:
        v = v.strip()
        m = PROCESSO_RE.match(v)
        if not m:
            raise ValueError("numero_processo deve seguir NNNNNNN-DD.AAAA.J.TR.OOOO")
        seq, dv, ano, justica, tribunal, origem = m.groups()
        return f"{seq.zfill(7)}-{dv}.{ano}.{justica}.{tribunal}.{origem}"


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero_processo: str
    titulo: str | None
    status: CaseStatus
    last_error: str | None = None
    captured_at: datetime | None = None
    analyzed_at: datetime | None = None
    analysis_result: str | None = None
    created_at: datetime
    updated_at: datetime
