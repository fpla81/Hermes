import re

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from . import __version__
from .capture import Capturer, build_capturer
from .extract import extract_pieces

app = FastAPI(
    title="Hermes Playwright Service",
    version=__version__,
    description="Captura de peças do Bem-te-vi para o Hermes.",
)


PROCESSO_RE = re.compile(r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$")


class CaptureRequest(BaseModel):
    numero_processo: str = Field(..., min_length=20, max_length=64)


class CapturedDocumentOut(BaseModel):
    titulo: str
    data: str | None = None


class CaptureResponse(BaseModel):
    numero_processo: str
    captured_at: str
    html: str
    documentos: list[CapturedDocumentOut]
    pieces: list[dict] = Field(default_factory=list)


def get_capturer() -> Capturer:
    """Override via dependency_overrides em testes."""
    return build_capturer()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "hermes-playwright"}


@app.post("/capture", response_model=CaptureResponse)
async def capture(
    payload: CaptureRequest,
    capturer: Capturer = Depends(get_capturer),
) -> CaptureResponse:
    if not PROCESSO_RE.match(payload.numero_processo):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="numero_processo inválido",
        )
    data = await capturer.capture(payload.numero_processo)
    pieces = extract_pieces(data.html)
    return CaptureResponse(
        numero_processo=data.numero_processo,
        captured_at=data.captured_at.isoformat(),
        html=data.html,
        documentos=[
            CapturedDocumentOut(titulo=d.titulo, data=d.data) for d in data.documentos
        ],
        pieces=pieces,
    )
