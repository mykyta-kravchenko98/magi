from collections.abc import Sequence
from types import TracebackType
from uuid import UUID

import pytest

from magi.documents.application import (
    GetDocumentAdditionStatusHandler,
    GetDocumentAdditionStatusQuery,
    InvalidUploadContentError,
    KnowledgeBaseNotFoundError,
    UploadDocumentCommand,
    UploadDocumentHandler,
)
from magi.documents.domain import (
    Document,
    DocumentAddition,
    DocumentAdditionStatus,
    DocumentVersion,
    DocumentVersionStatus,
    KnowledgeBase,
    ProcessingErrorCode,
)
from magi.ingestion.application import EmbeddingBatch, EmbeddingModelMetadata
from magi.ingestion.domain import ChunkContentType, DocumentChunk
from magi.retrieval.application import IndexChunk, IndexedDocumentVersion
from magi.retrieval.application.errors import VectorIndexUnavailableError

KNOWLEDGE_BASE_ID = UUID("10000000-0000-0000-0000-000000000001")


class Store:
    def __init__(self) -> None:
        self.knowledge_bases = {KNOWLEDGE_BASE_ID: KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Test")}
        self.additions: dict[UUID, DocumentAddition] = {}
        self.documents: dict[UUID, Document] = {}
        self.versions: dict[UUID, DocumentVersion] = {}
        self.commits = 0


class KnowledgeBases:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        return self._store.knowledge_bases.get(knowledge_base_id)


class Additions:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def add(self, addition: DocumentAddition) -> None:
        self._store.additions[addition.id] = addition

    async def get(self, addition_id: UUID) -> DocumentAddition | None:
        return self._store.additions.get(addition_id)

    async def save(self, addition: DocumentAddition) -> None:
        self._store.additions[addition.id] = addition


class Documents:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def add(self, document: Document) -> None:
        self._store.documents[document.id] = document


class Versions:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def add(self, version: DocumentVersion) -> None:
        self._store.versions[version.id] = version

    async def get(self, version_id: UUID) -> DocumentVersion | None:
        return self._store.versions.get(version_id)

    async def save(self, version: DocumentVersion) -> None:
        self._store.versions[version.id] = version


class FakeUnitOfWork:
    def __init__(self, store: Store) -> None:
        self._store = store
        self.knowledge_bases = KnowledgeBases(store)
        self.document_additions = Additions(store)
        self.documents = Documents(store)
        self.document_versions = Versions(store)

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback

    async def commit(self) -> None:
        self._store.commits += 1

    async def rollback(self) -> None:
        pass


class Storage:
    async def put(self, *, object_key: str, content: bytes, media_type: str) -> str:
        assert object_key.endswith("/source.md")
        assert content
        assert media_type == "text/markdown"
        return object_key


class Processor:
    def process(self, content: bytes, media_type: str) -> tuple[DocumentChunk, ...]:
        assert content
        assert media_type == "text/markdown"
        return (
            DocumentChunk(
                index=0,
                text="Deterministic walking skeleton.",
                heading_path=("Architecture",),
                content_type=ChunkContentType.TEXT,
            ),
        )


class Embedder:
    async def embed(self, chunks: Sequence[DocumentChunk]) -> EmbeddingBatch:
        assert len(chunks) == 1
        return EmbeddingBatch(
            vectors=((1.0, 2.0, 3.0),),
            model=EmbeddingModelMetadata(
                model_id="test",
                model_revision="v1",
                vector_dimension=3,
            ),
        )


class Indexer:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.received: tuple[IndexChunk, ...] = ()

    async def index(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
        document_version_id: UUID,
        chunks: Sequence[IndexChunk],
    ) -> IndexedDocumentVersion:
        del knowledge_base_id, document_id, document_version_id
        self.received = tuple(chunks)
        if self._fail:
            raise VectorIndexUnavailableError("unavailable")
        return IndexedDocumentVersion(
            projection_reference="chunks_v1",
            indexed_chunk_count=len(chunks),
        )


def handler(store: Store, indexer: Indexer | None = None) -> UploadDocumentHandler:
    status_query_handler = GetDocumentAdditionStatusHandler(lambda: FakeUnitOfWork(store))
    return UploadDocumentHandler(
        unit_of_work_factory=lambda: FakeUnitOfWork(store),
        object_storage=Storage(),
        content_pipeline=Processor(),
        document_embedder=Embedder(),
        document_version_indexer=indexer or Indexer(),
        status_query_handler=status_query_handler,
        max_upload_bytes=1_000,
    )


def command(**overrides: object) -> UploadDocumentCommand:
    values: dict[str, object] = {
        "knowledge_base_id": KNOWLEDGE_BASE_ID,
        "filename": "architecture.md",
        "media_type": "text/markdown; charset=utf-8",
        "content": b"# Architecture\n\nDeterministic walking skeleton.",
    }
    values.update(overrides)
    return UploadDocumentCommand(**values)  # pyright: ignore[reportArgumentType]


async def test_upload_completes_only_after_searchable_projection() -> None:
    store = Store()
    indexer = Indexer()

    result = await handler(store, indexer).handle(command())

    assert result.status is DocumentAdditionStatus.COMPLETED
    assert result.document_version_status is DocumentVersionStatus.SEARCHABLE
    assert result.indexed_chunk_count == 1
    assert result.failure is None
    assert indexer.received[0].heading_path == ("Architecture",)
    assert indexer.received[0].vector == (1.0, 2.0, 3.0)
    assert store.commits == 4
    assert (
        await GetDocumentAdditionStatusHandler(lambda: FakeUnitOfWork(store)).handle(
            GetDocumentAdditionStatusQuery(
                document_addition_id=result.document_addition_id,
            )
        )
        == result
    )


async def test_vector_failure_marks_addition_and_registered_version_failed() -> None:
    store = Store()

    result = await handler(store, Indexer(fail=True)).handle(command())

    assert result.status is DocumentAdditionStatus.FAILED
    assert result.document_version_status is None
    assert result.failure is not None
    assert result.failure.code is ProcessingErrorCode.VECTOR_INDEX_UNAVAILABLE
    assert len(store.versions) == 1
    version = next(iter(store.versions.values()))
    assert version.status is DocumentVersionStatus.FAILED
    assert version.failure == result.failure


async def test_invalid_utf8_is_rejected_before_acceptance() -> None:
    store = Store()

    with pytest.raises(InvalidUploadContentError, match="UTF-8"):
        await handler(store).handle(command(content=b"\xff"))

    assert store.additions == {}
    assert store.commits == 0


async def test_unknown_knowledge_base_is_rejected_before_acceptance() -> None:
    store = Store()

    with pytest.raises(KnowledgeBaseNotFoundError):
        await handler(store).handle(command(knowledge_base_id=UUID(int=99)))

    assert store.additions == {}
