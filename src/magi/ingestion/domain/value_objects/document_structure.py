"""Immutable normalized document-structure values."""

from dataclasses import dataclass

from magi.ingestion.domain.value_objects.source_location import SourceLocation


@dataclass(frozen=True, slots=True, kw_only=True)
class Heading:
    level: int
    text: str
    source_location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.level <= 6:
            raise ValueError("heading level must be between 1 and 6")


@dataclass(frozen=True, slots=True, kw_only=True)
class Paragraph:
    text: str
    source_location: SourceLocation | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class CodeBlock:
    text: str
    language: str | None = None
    source_location: SourceLocation | None = None


type DocumentNode = Heading | Paragraph | CodeBlock


@dataclass(frozen=True, slots=True, kw_only=True)
class ParsedDocument:
    nodes: tuple[DocumentNode, ...]
