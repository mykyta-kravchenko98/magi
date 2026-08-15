from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from magi.bootstrap.composition import create_application_runtime
from magi.bootstrap.health import router as health_router
from magi.documents.infrastructure.http import (
    request_validation_problem,
)
from magi.documents.infrastructure.http import (
    router as documents_router,
)
from magi.shared.config import EmbeddingSettings, QdrantSettings, Settings, get_settings
from magi.shared.persistence import create_database_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        engine = create_database_engine(resolved_settings)
        app.state.db_engine = engine
        embedding_settings = EmbeddingSettings()  # pyright: ignore[reportCallIssue]
        qdrant_settings = QdrantSettings()  # pyright: ignore[reportCallIssue]
        runtime = create_application_runtime(
            settings=resolved_settings,
            embedding_settings=embedding_settings,
            qdrant_settings=qdrant_settings,
            engine=engine,
        )
        app.state.upload_document_handler = runtime.upload_document_handler
        app.state.document_addition_status_handler = runtime.document_addition_status_handler
        app.state.max_upload_bytes = resolved_settings.max_upload_bytes
        try:
            yield
        finally:
            await runtime.aclose()
            await engine.dispose()

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        docs_url="/docs" if resolved_settings.docs_enabled else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(documents_router)
    app.add_exception_handler(RequestValidationError, request_validation_problem)
    return app


app = create_app()
