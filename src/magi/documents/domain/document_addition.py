"""Document addition aggregate."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from magi.documents.domain._validation import require_text
from magi.documents.domain.errors import DomainRuleViolation, InvalidStateTransition
from magi.documents.domain.value_objects import (
    ProcessingFailure,
    RejectionOutcome,
    SourceFileMetadata,
    SourceFingerprint,
)


class DocumentAdditionStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


@dataclass(slots=True, kw_only=True)
class DocumentAddition:
    id: UUID
    knowledge_base_id: UUID
    source_file: SourceFileMetadata
    source_fingerprint: SourceFingerprint | None = None
    status: DocumentAdditionStatus = DocumentAdditionStatus.ACCEPTED
    source_object_reference: str | None = None
    document_id: UUID | None = None
    document_version_id: UUID | None = None
    failure: ProcessingFailure | None = None
    rejection: RejectionOutcome | None = None

    def __post_init__(self) -> None:
        self._validate_state()

    def start_processing(self, source_object_reference: str) -> None:
        if self.status is not DocumentAdditionStatus.ACCEPTED:
            raise InvalidStateTransition("only an accepted addition can start processing")
        require_text(source_object_reference, "source_object_reference")
        self.source_object_reference = source_object_reference
        self.status = DocumentAdditionStatus.PROCESSING

    def complete(self, *, document_id: UUID, document_version_id: UUID) -> None:
        if self.status is not DocumentAdditionStatus.PROCESSING:
            raise InvalidStateTransition("only a processing addition can be completed")
        self.document_id = document_id
        self.document_version_id = document_version_id
        self.status = DocumentAdditionStatus.COMPLETED

    def fail(self, failure: ProcessingFailure) -> None:
        if self.status not in {
            DocumentAdditionStatus.ACCEPTED,
            DocumentAdditionStatus.PROCESSING,
        }:
            raise InvalidStateTransition("a terminal addition cannot fail")
        self.failure = failure
        self.status = DocumentAdditionStatus.FAILED

    def reject(self, rejection: RejectionOutcome) -> None:
        if self.status is not DocumentAdditionStatus.ACCEPTED:
            raise InvalidStateTransition("only an accepted addition can be rejected")
        if self.source_fingerprint is None:
            raise DomainRuleViolation(
                "an exact-source duplicate rejection requires a source fingerprint"
            )
        self.rejection = rejection
        self.status = DocumentAdditionStatus.REJECTED

    def _validate_state(self) -> None:
        has_result = self.document_id is not None or self.document_version_id is not None
        has_failure = self.failure is not None
        has_rejection = self.rejection is not None

        if self.status is DocumentAdditionStatus.ACCEPTED:
            if (
                self.source_object_reference is not None
                or has_result
                or has_failure
                or has_rejection
            ):
                raise DomainRuleViolation("an accepted addition cannot contain processing results")
            return

        if self.status is DocumentAdditionStatus.PROCESSING:
            if not self.source_object_reference or has_result or has_failure or has_rejection:
                raise DomainRuleViolation(
                    "a processing addition requires only a source object reference"
                )
            return

        if self.status is DocumentAdditionStatus.COMPLETED:
            if (
                not self.source_object_reference
                or self.document_id is None
                or self.document_version_id is None
                or has_failure
                or has_rejection
            ):
                raise DomainRuleViolation(
                    "a completed addition requires source, document, and version references"
                )
            return

        if self.status is DocumentAdditionStatus.FAILED:
            if self.failure is None or has_result or has_rejection:
                raise DomainRuleViolation(
                    "a failed addition requires a failure and cannot contain a result or rejection"
                )
            return

        if (
            self.rejection is None
            or self.source_fingerprint is None
            or self.source_object_reference is not None
            or has_result
            or has_failure
        ):
            raise DomainRuleViolation(
                "a rejected addition requires a rejection and cannot contain processing results"
            )
