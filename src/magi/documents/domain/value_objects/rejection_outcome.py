"""Business rejection outcome for a document addition."""

from dataclasses import dataclass
from enum import StrEnum


class RejectionCode(StrEnum):
    EXACT_SOURCE_DUPLICATE = "EXACT_SOURCE_DUPLICATE"


@dataclass(frozen=True, slots=True, kw_only=True)
class RejectionOutcome:
    code: RejectionCode
