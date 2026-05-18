import re

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from . import __version__
from .capture import Capturer, build_capturer
from .extract import extract_pieces
from .login_session import cancel_login, complete_login, list_sessions, start_login

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


class RenderRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=1000)
    wait_until: str = Field(default="networkidle", max_length=32)
    timeout_ms: int = Field(default=45000, ge=1000, le=120000)


class RenderResponse(BaseModel):
    url: str
    html: str
    status: int


@app.post("/render", response_model=RenderResponse)
async def render_page(payload: RenderRequest) -> RenderResponse:
    """Renderiza uma URL pública via Chromium headless e devolve o HTML
    pós-JS. Usado pra páginas JS-rendered como o portal Liferay do TST.

    Sem login, sem profile persistente — contexto efêmero.
    """
    from playwright.async_api import async_playwright

    if not (payload.url.startswith("http://") or payload.url.startswith("https://")):
        raise HTTPException(status_code=422, detail="URL deve começar com http(s)://")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                locale="pt-BR",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            response = await page.goto(
                payload.url,
                wait_until=payload.wait_until,  # type: ignore[arg-type]
                timeout=payload.timeout_ms,
            )
            status_code = response.status if response else 0
            html = await page.content()
        finally:
            await browser.close()
    return RenderResponse(url=payload.url, html=html, status=status_code)


class LoginCompleteRequest(BaseModel):
    session_id: str


@app.post("/login/start")
async def login_start() -> dict:
    try:
        return await start_login()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@app.post("/login/complete")
async def login_complete(payload: LoginCompleteRequest) -> dict:
    try:
        return await complete_login(payload.session_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"sessão {exc} não encontrada"
        ) from exc


@app.post("/login/cancel")
async def login_cancel(payload: LoginCompleteRequest) -> dict[str, str]:
    await cancel_login(payload.session_id)
    return {"status": "cancelled"}


@app.get("/login/status")
async def login_status() -> dict:
    return {"sessions": list_sessions()}
