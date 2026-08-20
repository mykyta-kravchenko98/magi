"""Shared reconstruction of flattened domain value objects."""

from magi.documents.domain import (
    ProcessingErrorCode,
    ProcessingFailure,
    RejectionCode,
    RejectionOutcome,
    SearchProjection,
    SourceFingerprint,
)


class PersistenceMappingError(ValueError):
    """A database row cannot be reconstructed as a valid aggregate."""


def failure_from_columns(
    code: ProcessingErrorCode | None,
    message: str | None,
) -> ProcessingFailure | None:
    if code is None:
        if message is not None:
            raise PersistenceMappingError("failure_message exists without failure_code")
        return None
    return ProcessingFailure(code=code, message=message)


def source_fingerprint_from_columns(
    algorithm: str | None,
    digest: str | None,
) -> SourceFingerprint | None:
    if algorithm is None and digest is None:
        return None
    if algorithm is None or digest is None:
        raise PersistenceMappingError("source fingerprint columns are incomplete")
    return SourceFingerprint(algorithm=algorithm, digest=digest)


def rejection_from_column(code: RejectionCode | None) -> RejectionOutcome | None:
    return RejectionOutcome(code=code) if code is not None else None


def projection_from_columns(
    reference: str | None,
    indexed_chunk_count: int | None,
) -> SearchProjection | None:
    if reference is None and indexed_chunk_count is None:
        return None
    if reference is None or indexed_chunk_count is None:
        raise PersistenceMappingError("search projection columns are incomplete")
    return SearchProjection(reference=reference, indexed_chunk_count=indexed_chunk_count)
