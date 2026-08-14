"""Document version aggregate."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from magi.documents.domain.errors import DomainRuleViolation, InvalidStateTransition
from magi.documents.domain.value_objects import ProcessingFailure, SearchProjection


class DocumentVersionStatus(StrEnum):
    PROCESSING = "PROCESSING"
    SEARCHABLE = "SEARCHABLE"
    FAILED = "FAILED"


@dataclass(slots=True, kw_only=True)
class DocumentVersion:
    id: UUID
    document_id: UUID
    created_from_addition_id: UUID
    status: DocumentVersionStatus = DocumentVersionStatus.PROCESSING
    projection: SearchProjection | None = None
    failure: ProcessingFailure | None = None

    def __post_init__(self) -> None:
        self._validate_state()

    def mark_searchable(self, projection: SearchProjection) -> None:
        if self.status is not DocumentVersionStatus.PROCESSING:
            raise InvalidStateTransition("only a processing version can become searchable")
        self.projection = projection
        self.status = DocumentVersionStatus.SEARCHABLE

    def fail(self, failure: ProcessingFailure) -> None:
        if self.status is not DocumentVersionStatus.PROCESSING:
            raise InvalidStateTransition("a terminal document version cannot fail")
        self.failure = failure
        self.status = DocumentVersionStatus.FAILED

    def _validate_state(self) -> None:
        if self.status is DocumentVersionStatus.PROCESSING:
            if self.projection is not None or self.failure is not None:
                raise DomainRuleViolation("a processing version cannot contain a result or failure")
            return

        if self.status is DocumentVersionStatus.SEARCHABLE:
            if self.projection is None or self.failure is not None:
                raise DomainRuleViolation(
                    "a searchable version requires a projection and positive chunk count"
                )
            return

        if self.failure is None or self.projection is not None:
            raise DomainRuleViolation("a failed version requires a code and cannot be projected")
