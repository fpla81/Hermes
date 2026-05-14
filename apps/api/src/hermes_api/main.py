from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .routes import health

settings = get_settings()

app = FastAPI(
    title="Hermes API",
    version=__version__,
    description="Backend for the Hermes TST processo analyzer.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "hermes-api", "version": __version__}
