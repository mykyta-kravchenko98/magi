"""FastAPI transport for document upload and status resources."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, File, Request, UploadFile, status
from fastapi.responses import JSONResponse

from magi.documents.application import (
    DocumentAdditionNotFoundError,
    EmptyUploadError,
    GetDocumentAdditionStatusHandler,
    GetDocumentAdditionStatusQuery,
    InvalidUploadContentError,
    KnowledgeBaseNotActiveError,
    KnowledgeBaseNotFoundError,
    UnsupportedUploadMediaTypeError,
    UploadDocumentCommand,
    UploadDocumentHandler,
    UploadTooLargeError,
)
from magi.documents.application.errors import DocumentApplicationError
from magi.documents.infrastructure.http.models import DocumentAdditionResponse, ProblemDetail

router = APIRouter(prefix="/api/v1", tags=["documents"])


async def request_validation_problem(
    request: Request,
    error: Exception,
) -> JSONResponse:
    del request, error
    body = ProblemDetail(
        title="Invalid request",
        status=status.HTTP_400_BAD_REQUEST,
        detail="Request validation failed",
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=body.model_dump(mode="json"),
        media_type="application/problem+json",
    )


def _problem(error: DocumentApplicationError) -> JSONResponse:
    if isinstance(error, (KnowledgeBaseNotFoundError, DocumentAdditionNotFoundError)):
        status_code = status.HTTP_404_NOT_FOUND
        title = "Resource not found"
    elif isinstance(error, KnowledgeBaseNotActiveError):
        status_code = status.HTTP_409_CONFLICT
        title = "Knowledge base does not accept uploads"
    elif isinstance(error, UploadTooLargeError):
        status_code = status.HTTP_413_CONTENT_TOO_LARGE
        title = "Upload is too large"
    elif isinstance(error, UnsupportedUploadMediaTypeError):
        status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        title = "Unsupported upload format"
    elif isinstance(error, (EmptyUploadError, InvalidUploadContentError)):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        title = "Invalid upload content"
    else:
        status_code = status.HTTP_400_BAD_REQUEST
        title = "Invalid request"
    body = ProblemDetail(
        title=title,
        status=status_code,
        detail=str(error),
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        media_type="application/problem+json",
    )


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentAdditionResponse,
)
async def upload_document(
    request: Request,
    knowledge_base_id: UUID,
    file: Annotated[UploadFile, File()],
) -> DocumentAdditionResponse | JSONResponse:
    handler = cast(UploadDocumentHandler, request.app.state.upload_document_handler)
    max_upload_bytes = cast(int, request.app.state.max_upload_bytes)
    content = await file.read(max_upload_bytes + 1)
    try:
        view = await handler.handle(
            UploadDocumentCommand(
                knowledge_base_id=knowledge_base_id,
                filename=file.filename or "",
                media_type=file.content_type or "",
                content=content,
            )
        )
    except DocumentApplicationError as error:
        return _problem(error)
    return DocumentAdditionResponse.from_view(view)


@router.get(
    "/document-additions/{document_addition_id}",
    response_model=DocumentAdditionResponse,
)
async def get_document_addition_status(
    request: Request,
    document_addition_id: UUID,
) -> DocumentAdditionResponse | JSONResponse:
    handler = cast(
        GetDocumentAdditionStatusHandler,
        request.app.state.document_addition_status_handler,
    )
    try:
        view = await handler.handle(
            GetDocumentAdditionStatusQuery(
                document_addition_id=document_addition_id,
            )
        )
    except DocumentApplicationError as error:
        return _problem(error)
    return DocumentAdditionResponse.from_view(view)
