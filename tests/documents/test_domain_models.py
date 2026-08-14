from uuid import UUID, uuid4

import pytest

from magi.documents.domain import (
    Document,
    DocumentAddition,
    DocumentAdditionStatus,
    DocumentVersion,
    DocumentVersionStatus,
    DomainRuleViolation,
    InvalidStateTransition,
    KnowledgeBase,
    KnowledgeBaseStatus,
    ProcessingErrorCode,
    ProcessingFailure,
    SearchProjection,
    SourceFileMetadata,
)


def make_addition() -> DocumentAddition:
    return DocumentAddition(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        source_file=SourceFileMetadata(
            original_filename="architecture.md",
            media_type="text/markdown",
            size_bytes=128,
        ),
    )


def make_version() -> DocumentVersion:
    return DocumentVersion(
        id=uuid4(),
        document_id=uuid4(),
        created_from_addition_id=uuid4(),
    )


def test_knowledge_base_can_be_archived_once() -> None:
    knowledge_base = KnowledgeBase(id=uuid4(), name="Architecture")

    knowledge_base.archive()

    assert knowledge_base.status is KnowledgeBaseStatus.ARCHIVED
    with pytest.raises(InvalidStateTransition):
        knowledge_base.archive()
    with pytest.raises(DomainRuleViolation):
        knowledge_base.ensure_accepts_uploads()


@pytest.mark.parametrize("name", ["", "   "])
def test_knowledge_base_requires_a_name(name: str) -> None:
    with pytest.raises(DomainRuleViolation):
        KnowledgeBase(id=uuid4(), name=name)


def test_source_file_metadata_has_value_semantics() -> None:
    first = SourceFileMetadata(
        original_filename="book.pdf",
        media_type="application/pdf",
        size_bytes=1024,
    )
    second = SourceFileMetadata(
        original_filename="book.pdf",
        media_type="application/pdf",
        size_bytes=1024,
    )

    assert first == second


@pytest.mark.parametrize("size_bytes", [0, -1])
def test_source_file_metadata_requires_positive_size(size_bytes: int) -> None:
    with pytest.raises(DomainRuleViolation):
        SourceFileMetadata(
            original_filename="book.pdf",
            media_type="application/pdf",
            size_bytes=size_bytes,
        )


@pytest.mark.parametrize(
    ("original_filename", "media_type"),
    [("", "application/pdf"), ("book.pdf", " ")],
)
def test_source_file_metadata_requires_text_fields(original_filename: str, media_type: str) -> None:
    with pytest.raises(DomainRuleViolation):
        SourceFileMetadata(
            original_filename=original_filename,
            media_type=media_type,
            size_bytes=1,
        )


def test_addition_follows_happy_path() -> None:
    addition = make_addition()
    document_id = uuid4()
    version_id = uuid4()

    addition.start_processing("sources/immutable-object")
    addition.complete(document_id=document_id, document_version_id=version_id)

    assert addition.status is DocumentAdditionStatus.COMPLETED
    assert addition.source_object_reference == "sources/immutable-object"
    assert addition.document_id == document_id
    assert addition.document_version_id == version_id


@pytest.mark.parametrize(
    "initial_status",
    [DocumentAdditionStatus.ACCEPTED, DocumentAdditionStatus.PROCESSING],
)
def test_addition_can_fail_before_completion(initial_status: DocumentAdditionStatus) -> None:
    addition = make_addition()
    if initial_status is DocumentAdditionStatus.PROCESSING:
        addition.start_processing("sources/immutable-object")

    addition.fail(
        ProcessingFailure(
            code=ProcessingErrorCode.PARSING_FAILED,
            message="Document processing failed",
        )
    )

    assert addition.status is DocumentAdditionStatus.FAILED
    assert addition.failure is not None
    assert addition.failure.code is ProcessingErrorCode.PARSING_FAILED
    assert addition.failure.message == "Document processing failed"


def test_addition_terminal_states_cannot_transition() -> None:
    completed = make_addition()
    completed.start_processing("sources/completed")
    completed.complete(document_id=uuid4(), document_version_id=uuid4())
    failed = make_addition()
    failed.fail(ProcessingFailure(code=ProcessingErrorCode.OBJECT_STORAGE_UNAVAILABLE))

    with pytest.raises(InvalidStateTransition):
        completed.fail(ProcessingFailure(code=ProcessingErrorCode.PROCESSING_FAILED))
    with pytest.raises(InvalidStateTransition):
        failed.start_processing("sources/late")


def test_processing_addition_requires_stored_source_reference() -> None:
    with pytest.raises(DomainRuleViolation):
        DocumentAddition(
            id=uuid4(),
            knowledge_base_id=uuid4(),
            source_file=SourceFileMetadata(
                original_filename="book.txt",
                media_type="text/plain",
                size_bytes=10,
            ),
            status=DocumentAdditionStatus.PROCESSING,
        )


def test_completed_addition_requires_both_result_ids() -> None:
    with pytest.raises(DomainRuleViolation):
        DocumentAddition(
            id=uuid4(),
            knowledge_base_id=uuid4(),
            source_file=SourceFileMetadata(
                original_filename="book.txt",
                media_type="text/plain",
                size_bytes=10,
            ),
            status=DocumentAdditionStatus.COMPLETED,
            source_object_reference="sources/book",
            document_id=uuid4(),
        )


def test_document_is_an_immutable_active_identity() -> None:
    document = Document(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        created_from_addition_id=uuid4(),
        display_name="Designing Data-Intensive Applications",
    )

    assert document.status.value == "ACTIVE"
    with pytest.raises(AttributeError):
        document.display_name = "Changed"  # type: ignore[misc]


def test_version_becomes_searchable_only_with_complete_projection() -> None:
    version = make_version()
    projection = SearchProjection(reference="magi_chunks/v1", indexed_chunk_count=12)

    version.mark_searchable(projection)

    assert version.status is DocumentVersionStatus.SEARCHABLE
    assert version.projection == projection


@pytest.mark.parametrize(
    ("projection_reference", "indexed_chunk_count"),
    [("", 1), ("magi_chunks/v1", 0), ("magi_chunks/v1", -1)],
)
def test_version_rejects_incomplete_projection(
    projection_reference: str, indexed_chunk_count: int
) -> None:
    with pytest.raises(DomainRuleViolation):
        SearchProjection(
            reference=projection_reference,
            indexed_chunk_count=indexed_chunk_count,
        )


def test_version_can_fail_and_then_is_terminal() -> None:
    version = make_version()
    failure = ProcessingFailure(code=ProcessingErrorCode.VECTOR_INDEX_UNAVAILABLE)

    version.fail(failure)

    assert version.status is DocumentVersionStatus.FAILED
    assert version.failure == failure
    with pytest.raises(InvalidStateTransition):
        version.mark_searchable(SearchProjection(reference="late", indexed_chunk_count=1))


def test_searchable_version_invariant_is_checked_when_rehydrated() -> None:
    with pytest.raises(DomainRuleViolation):
        DocumentVersion(
            id=uuid4(),
            document_id=uuid4(),
            created_from_addition_id=uuid4(),
            status=DocumentVersionStatus.SEARCHABLE,
        )


@pytest.mark.parametrize("message", ["", "   "])
def test_processing_failure_rejects_blank_message(message: str) -> None:
    with pytest.raises(DomainRuleViolation):
        ProcessingFailure(code=ProcessingErrorCode.PROCESSING_FAILED, message=message)


def test_aggregate_identifiers_are_uuids() -> None:
    known_id = UUID("0198f000-0000-7000-8000-000000000001")

    addition = DocumentAddition(
        id=known_id,
        knowledge_base_id=uuid4(),
        source_file=SourceFileMetadata(
            original_filename="book.pdf",
            media_type="application/pdf",
            size_bytes=1,
        ),
    )

    assert addition.id == known_id
