from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from magi.bootstrap.health import router as health_router
from magi.shared.config import Settings, get_settings
from magi.shared.persistence import create_database_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        engine = create_database_engine(resolved_settings)
        app.state.db_engine = engine
        yield
        await engine.dispose()

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        docs_url="/docs" if resolved_settings.docs_enabled else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    return app


app = create_app()
