from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from magi.bootstrap.app import create_app
from magi.shared.config import Settings


class FakeConnection:
    async def execute(self, statement: object) -> None:
        del statement


class FakeEngine:
    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[FakeConnection]:
        yield FakeConnection()

    async def dispose(self) -> None:
        pass


class UnavailableEngine(FakeEngine):
    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[FakeConnection]:
        if True:
            raise ConnectionError("database is unavailable")
        yield FakeConnection()


async def test_liveness_does_not_require_dependencies() -> None:
    app = create_app(Settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_checks_database() -> None:
    app = create_app(Settings())
    app.state.db_engine = cast(AsyncEngine, FakeEngine())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_is_unavailable_when_database_fails() -> None:
    app = create_app(Settings())
    app.state.db_engine = cast(AsyncEngine, UnavailableEngine())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
