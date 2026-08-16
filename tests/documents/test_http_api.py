from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from magi.bootstrap.app import create_app
from magi.documents.application import (
    DocumentAdditionNotFoundError,
    DocumentAdditionView,
    GetDocumentAdditionStatusQuery,
    UploadDocumentCommand,
)
from magi.documents.domain import DocumentAdditionStatus, DocumentVersionStatus
from magi.shared.config import Settings

KNOWLEDGE_BASE_ID = UUID("10000000-0000-0000-0000-000000000001")


class UploadHandler:
    def __init__(self, view: DocumentAdditionView) -> None:
        self._view = view
        self.command: UploadDocumentCommand | None = None

    async def handle(self, command: UploadDocumentCommand) -> DocumentAdditionView:
        self.command = command
        return self._view


class StatusQueryHandler:
    def __init__(self, view: DocumentAdditionView | None) -> None:
        self._view = view

    async def handle(self, query: GetDocumentAdditionStatusQuery) -> DocumentAdditionView:
        if self._view is None or query.document_addition_id != self._view.document_addition_id:
            raise DocumentAdditionNotFoundError("document addition not found")
        return self._view


def completed_view() -> DocumentAdditionView:
    return DocumentAdditionView(
        document_addition_id=uuid4(),
        status=DocumentAdditionStatus.COMPLETED,
        document_id=uuid4(),
        document_version_id=uuid4(),
        document_version_status=DocumentVersionStatus.SEARCHABLE,
        indexed_chunk_count=2,
        failure=None,
    )


async def test_upload_endpoint_delegates_to_application_handler() -> None:
    view = completed_view()
    handler = UploadHandler(view)
    app = create_app(Settings())
    app.state.upload_document_handler = handler
    app.state.document_addition_status_handler = StatusQueryHandler(view)
    app.state.max_upload_bytes = 1_000

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/knowledge-bases/{KNOWLEDGE_BASE_ID}/documents",
            files={"file": ("architecture.md", b"# Architecture", "text/markdown")},
        )

    assert response.status_code == 202
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["document_version_status"] == "SEARCHABLE"
    assert handler.command == UploadDocumentCommand(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        filename="architecture.md",
        media_type="text/markdown",
        content=b"# Architecture",
    )


async def test_status_endpoint_returns_application_view_and_problem_details() -> None:
    view = completed_view()
    app = create_app(Settings())
    app.state.upload_document_handler = UploadHandler(view)
    app.state.document_addition_status_handler = StatusQueryHandler(view)
    app.state.max_upload_bytes = 1_000

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/document-additions/{view.document_addition_id}")
        missing = await client.get(f"/api/v1/document-additions/{uuid4()}")

    assert response.status_code == 200
    assert response.json()["indexed_chunk_count"] == 2
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/problem+json")
    assert missing.json()["status"] == 404


async def test_malformed_identifier_returns_sanitized_problem_details() -> None:
    app = create_app(Settings())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/document-additions/not-a-uuid")

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "about:blank",
        "title": "Invalid request",
        "status": 400,
        "detail": "Request validation failed",
    }
