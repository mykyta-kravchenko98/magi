"""Command handler for the synchronous document-upload walking skeleton."""

import asyncio
from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from magi.documents.application.errors import (
    KnowledgeBaseNotActiveError,
    KnowledgeBaseNotFoundError,
)
from magi.documents.application.interfaces import ObjectStorage, UnitOfWorkFactory
from magi.documents.application.models import DocumentAdditionView
from magi.documents.application.queries import (
    GetDocumentAdditionStatusHandler,
    GetDocumentAdditionStatusQuery,
)
from magi.documents.application.services import UploadValidator, processing_failure_from
from magi.documents.domain import (
    Document,
    DocumentAddition,
    DocumentVersion,
    DomainRuleViolation,
    ProcessingFailure,
    SearchProjection,
    SourceFileMetadata,
)
from magi.ingestion.application import (
    DocumentContentProcessor,
    DocumentEmbedder,
    EmbeddingResponseInvalidError,
)
from magi.retrieval.application import DocumentVersionIndexer, IndexChunk


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadDocumentCommand:
    knowledge_base_id: UUID
    filename: str
    media_type: str
    content: bytes


class UploadDocumentHandler:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        object_storage: ObjectStorage,
        content_pipeline: DocumentContentProcessor,
        document_embedder: DocumentEmbedder,
        document_version_indexer: DocumentVersionIndexer,
        status_query_handler: GetDocumentAdditionStatusHandler,
        max_upload_bytes: int,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._object_storage = object_storage
        self._content_pipeline = content_pipeline
        self._document_embedder = document_embedder
        self._document_version_indexer = document_version_indexer
        self._status_query_handler = status_query_handler
        self._upload_validator = UploadValidator(max_upload_bytes)

    async def handle(self, command: UploadDocumentCommand) -> DocumentAdditionView:
        upload = self._upload_validator.validate(command)
        addition_id = uuid4()
        await self._accept_addition(
            addition_id=addition_id,
            command=command,
            filename=upload.filename,
            media_type=upload.media_type,
        )

        version_id: UUID | None = None
        try:
            source_reference = await self._object_storage.put(
                object_key=self._object_key(
                    command.knowledge_base_id,
                    addition_id,
                    upload.filename,
                ),
                content=command.content,
                media_type=upload.media_type,
            )
            await self._start_processing(addition_id, source_reference)
            chunks = await asyncio.to_thread(
                self._content_pipeline.process,
                command.content,
                upload.media_type,
            )
            document_id = uuid4()
            version_id = uuid4()
            await self._register_document(
                addition_id=addition_id,
                knowledge_base_id=command.knowledge_base_id,
                document_id=document_id,
                version_id=version_id,
                display_name=upload.filename,
            )
            embeddings = await self._document_embedder.embed(chunks)
            if len(embeddings.vectors) != len(chunks):
                raise EmbeddingResponseInvalidError("embedding count does not match chunks")
            indexed = await self._document_version_indexer.index(
                knowledge_base_id=command.knowledge_base_id,
                document_id=document_id,
                document_version_id=version_id,
                chunks=tuple(
                    IndexChunk(
                        index=chunk.index,
                        content_type=chunk.content_type.value,
                        content_role=chunk.content_role.value,
                        heading_path=chunk.heading_path,
                        text=chunk.text,
                        vector=vector,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                    )
                    for chunk, vector in zip(chunks, embeddings.vectors, strict=True)
                ),
            )
            await self._complete(
                addition_id=addition_id,
                document_id=document_id,
                version_id=version_id,
                projection=SearchProjection(
                    reference=indexed.projection_reference,
                    indexed_chunk_count=indexed.indexed_chunk_count,
                ),
            )
        except Exception as error:  # Persist a sanitized terminal state after acceptance.
            await self._fail(addition_id, version_id, processing_failure_from(error))

        return await self._status_query_handler.handle(
            GetDocumentAdditionStatusQuery(document_addition_id=addition_id)
        )

    async def _accept_addition(
        self,
        *,
        addition_id: UUID,
        command: UploadDocumentCommand,
        filename: str,
        media_type: str,
    ) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            knowledge_base = await unit_of_work.knowledge_bases.get(command.knowledge_base_id)
            if knowledge_base is None:
                raise KnowledgeBaseNotFoundError("knowledge base not found")
            try:
                knowledge_base.ensure_accepts_uploads()
            except DomainRuleViolation as error:
                raise KnowledgeBaseNotActiveError(
                    "knowledge base does not accept uploads"
                ) from error
            await unit_of_work.document_additions.add(
                DocumentAddition(
                    id=addition_id,
                    knowledge_base_id=command.knowledge_base_id,
                    source_file=SourceFileMetadata(
                        original_filename=filename,
                        media_type=media_type,
                        size_bytes=len(command.content),
                    ),
                )
            )
            await unit_of_work.commit()

    async def _start_processing(self, addition_id: UUID, source_reference: str) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            addition = await unit_of_work.document_additions.get(addition_id)
            if addition is None:
                raise RuntimeError("accepted document addition disappeared")
            addition.start_processing(source_reference)
            await unit_of_work.document_additions.save(addition)
            await unit_of_work.commit()

    async def _register_document(
        self,
        *,
        addition_id: UUID,
        knowledge_base_id: UUID,
        document_id: UUID,
        version_id: UUID,
        display_name: str,
    ) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            await unit_of_work.documents.add(
                Document(
                    id=document_id,
                    knowledge_base_id=knowledge_base_id,
                    created_from_addition_id=addition_id,
                    display_name=display_name,
                )
            )
            await unit_of_work.document_versions.add(
                DocumentVersion(
                    id=version_id,
                    document_id=document_id,
                    created_from_addition_id=addition_id,
                )
            )
            await unit_of_work.commit()

    async def _complete(
        self,
        *,
        addition_id: UUID,
        document_id: UUID,
        version_id: UUID,
        projection: SearchProjection,
    ) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            addition = await unit_of_work.document_additions.get(addition_id)
            version = await unit_of_work.document_versions.get(version_id)
            if addition is None or version is None:
                raise RuntimeError("registered document workflow state disappeared")
            version.mark_searchable(projection)
            addition.complete(document_id=document_id, document_version_id=version_id)
            await unit_of_work.document_versions.save(version)
            await unit_of_work.document_additions.save(addition)
            await unit_of_work.commit()

    async def _fail(
        self,
        addition_id: UUID,
        version_id: UUID | None,
        failure: ProcessingFailure,
    ) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            addition = await unit_of_work.document_additions.get(addition_id)
            if addition is None:
                raise RuntimeError("accepted document addition disappeared")
            addition.fail(failure)
            await unit_of_work.document_additions.save(addition)
            if version_id is not None:
                version = await unit_of_work.document_versions.get(version_id)
                if version is not None:
                    version.fail(failure)
                    await unit_of_work.document_versions.save(version)
            await unit_of_work.commit()

    @staticmethod
    def _object_key(knowledge_base_id: UUID, addition_id: UUID, filename: str) -> str:
        suffix = PurePosixPath(filename).suffix.lower()
        return f"knowledge-bases/{knowledge_base_id}/additions/{addition_id}/source{suffix}"
