from uuid import uuid4

from magi.documents.domain import (
    DocumentAddition,
    DocumentAdditionStatus,
    DocumentVersion,
    ProcessingErrorCode,
    ProcessingFailure,
    RejectionCode,
    RejectionOutcome,
    SearchProjection,
    SourceFileMetadata,
    SourceFingerprint,
)
from magi.documents.infrastructure.persistence.mappers import (
    document_addition_from_row,
    document_addition_to_row,
    document_version_from_row,
    document_version_to_row,
)


def test_failed_addition_mapper_round_trip() -> None:
    addition = DocumentAddition(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        source_file=SourceFileMetadata(
            original_filename="broken.pdf",
            media_type="application/pdf",
            size_bytes=128,
        ),
        source_fingerprint=SourceFingerprint(algorithm="sha256", digest="a" * 64),
    )
    addition.fail(
        ProcessingFailure(
            code=ProcessingErrorCode.PARSING_FAILED,
            message="Document processing failed",
        )
    )

    restored = document_addition_from_row(document_addition_to_row(addition))

    assert restored == addition


def test_rejected_addition_mapper_round_trip() -> None:
    addition = DocumentAddition(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        source_file=SourceFileMetadata(
            original_filename="duplicate.pdf",
            media_type="application/pdf",
            size_bytes=128,
        ),
        source_fingerprint=SourceFingerprint(algorithm="sha256", digest="b" * 64),
    )
    addition.reject(RejectionOutcome(code=RejectionCode.EXACT_SOURCE_DUPLICATE))

    restored = document_addition_from_row(document_addition_to_row(addition))

    assert restored == addition
    assert restored.status is DocumentAdditionStatus.REJECTED


def test_searchable_version_mapper_round_trip() -> None:
    version = DocumentVersion(
        id=uuid4(),
        document_id=uuid4(),
        created_from_addition_id=uuid4(),
    )
    version.mark_searchable(
        SearchProjection(reference="magi-document-chunks", indexed_chunk_count=12)
    )

    restored = document_version_from_row(document_version_to_row(version))

    assert restored == version
