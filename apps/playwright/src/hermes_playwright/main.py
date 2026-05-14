import re
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from . import __version__

app = FastAPI(
    title="Hermes Playwright Service",
    version=__version__,
    description="Captura de peças do Bem-te-vi para o Hermes.",
)


PROCESSO_RE = re.compile(r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$")


class CaptureRequest(BaseModel):
    numero_processo: str = Field(..., min_length=20, max_length=64)


class CapturedDocument(BaseModel):
    titulo: str
    data: str | None = None


class CaptureResponse(BaseModel):
    numero_processo: str
    captured_at: datetime
    html: str
    documentos: list[CapturedDocument]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "hermes-playwright"}


@app.post("/capture", response_model=CaptureResponse)
async def capture(payload: CaptureRequest) -> CaptureResponse:
    if not PROCESSO_RE.match(payload.numero_processo):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="numero_processo inválido",
        )
    # TODO(fase-2): substituir pelo capture real do Bem-te-vi (Playwright + sessão).
    stub_html = (
        f"<html><body><h1>Processo {payload.numero_processo}</h1>"
        "<p>STUB — captura real será implementada na Fase 2.</p>"
        "</body></html>"
    )
    return CaptureResponse(
        numero_processo=payload.numero_processo,
        captured_at=datetime.now(timezone.utc),
        html=stub_html,
        documentos=[
            CapturedDocument(titulo="Petição inicial (stub)", data="2024-01-15"),
            CapturedDocument(titulo="Contestação (stub)", data="2024-02-10"),
        ],
    )
