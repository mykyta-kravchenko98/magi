"""Exact identity of the original source bytes."""

from dataclasses import dataclass
from re import fullmatch

from magi.documents.domain._validation import require_text
from magi.documents.domain.errors import DomainRuleViolation

SHA256_ALGORITHM = "sha256"
SHA256_HEX_DIGEST_LENGTH = 64


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceFingerprint:
    """A precomputed source digest; hashing belongs outside the domain."""

    algorithm: str
    digest: str

    def __post_init__(self) -> None:
        require_text(self.algorithm, "algorithm")
        require_text(self.digest, "digest")
        if self.algorithm != SHA256_ALGORITHM:
            raise DomainRuleViolation("source fingerprint algorithm must be sha256")
        if (
            len(self.digest) != SHA256_HEX_DIGEST_LENGTH
            or fullmatch(r"[0-9a-f]+", self.digest) is None
        ):
            raise DomainRuleViolation(
                "source fingerprint digest must be 64 lowercase hexadecimal characters"
            )
