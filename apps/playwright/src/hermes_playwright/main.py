from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from . import __version__

app = FastAPI(
    title="Hermes Playwright Service",
    version=__version__,
    description="Captura de peças do Bem-te-vi para o Hermes.",
)


class StartCaptureRequest(BaseModel):
    headless: bool = False


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "hermes-playwright"}


@app.post("/capture/start")
async def capture_start(_: StartCaptureRequest) -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Bem-te-vi capture lives in Phase 2.",
    )
