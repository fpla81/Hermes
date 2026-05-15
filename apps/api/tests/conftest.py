from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from hermes_api.db import Base, get_db
from hermes_api.main import app
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class FakeStorage:
    """Stub in-memory de S3Storage para os testes."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get_bytes(self, key: str) -> bytes:
        return self.objects[key]

    def list_keys(self, prefix: str) -> list[str]:
        return sorted(k for k in self.objects if k.startswith(prefix))

    def delete_key(self, key: str) -> None:
        self.objects.pop(key, None)


@pytest_asyncio.fixture
async def engine() -> AsyncIterator:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def client(session_factory, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("HERMES_INTERNAL_SECRET", "test-secret")
    # reset cached settings
    from hermes_api.config import get_settings

    get_settings.cache_clear()

    async def _get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def fake_storage(monkeypatch) -> FakeStorage:
    """Substitui get_storage() pelo FakeStorage em todos os módulos que o importam."""
    storage = FakeStorage()
    from hermes_api import storage as storage_module
    from hermes_api.routes import cases as cases_module

    monkeypatch.setattr(storage_module, "get_storage", lambda: storage)
    monkeypatch.setattr(cases_module, "get_storage", lambda: storage)
    return storage
