from pydantic import BaseModel, Field


class TemaRepetitivoIn(BaseModel):
    numero: int = Field(..., gt=0)
    descricao: str = Field(..., min_length=1)
    situacao: str = Field(..., min_length=1, max_length=32)
    tese: str | None = None
    link: str | None = None


class TemaRepetitivoRead(BaseModel):
    numero: int
    descricao: str
    situacao: str
    tese: str | None = None
    link: str | None = None


class RepetitivoMatch(BaseModel):
    numero: int
    descricao: str
    situacao: str
    tese: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    kind: str  # "alta" | "media"
    justificativa: str | None = None
