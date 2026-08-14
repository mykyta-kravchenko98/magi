"""Deterministic, structure-aware character chunking."""

import re
from dataclasses import dataclass

from magi.ingestion.domain.errors import ContentBlockTooLargeError
from magi.ingestion.domain.value_objects import (
    CharacterChunkingConfig,
    ChunkContentType,
    CodeBlock,
    DocumentChunk,
    Heading,
    Paragraph,
    ParsedDocument,
    SourceLocation,
)

_SENTENCE_END = re.compile(r"[.!?\u3002\uff01\uff1f](?:[\"')\]]*)\s+")


@dataclass(frozen=True, slots=True)
class _Unit:
    text: str
    content_type: ChunkContentType
    location: SourceLocation | None


def _choose_break(text: str, start: int, limit: int) -> int:
    if limit >= len(text):
        return len(text)
    minimum = start + max(1, (limit - start) // 2)
    sentence_ends = [match.end() - 1 for match in _SENTENCE_END.finditer(text, start, limit + 1)]
    sentence_ends = [end for end in sentence_ends if end >= minimum]
    if sentence_ends:
        return sentence_ends[-1]
    whitespace = max(text.rfind(" ", minimum, limit + 1), text.rfind("\n", minimum, limit + 1))
    return whitespace if whitespace >= minimum else limit


def _overlap_prefix(text: str, cursor: int, size: int) -> str:
    if size == 0:
        return ""
    consumed = text[:cursor].rstrip()
    start = max(0, len(consumed) - max(0, size - 1))
    if start:
        boundary = consumed.find(" ", start)
        if boundary != -1:
            start = boundary + 1
    suffix = consumed[start:]
    return f"{suffix} " if suffix else ""


def _split_paragraph(text: str, config: CharacterChunkingConfig) -> tuple[str, ...]:
    pieces: list[str] = []
    cursor = 0
    while cursor < len(text):
        prefix = _overlap_prefix(text, cursor, config.overlap_chars) if pieces else ""
        limit = min(len(text), cursor + config.max_chars - len(prefix))
        end = _choose_break(text, cursor, limit)
        core = text[cursor:end].strip()
        if not core:
            end = min(len(text), max(cursor + 1, limit))
            core = text[cursor:end].strip()
        pieces.append(f"{prefix}{core}")
        cursor = end
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
    return tuple(pieces)


def _content_type(units: list[_Unit]) -> ChunkContentType:
    types = {unit.content_type for unit in units}
    return next(iter(types)) if len(types) == 1 else ChunkContentType.MIXED


def _source_span(units: list[_Unit]) -> tuple[int | None, int | None, int | None, int | None]:
    locations = [unit.location for unit in units if unit.location is not None]
    line_starts = [location.line_start for location in locations if location.line_start is not None]
    line_ends = [location.line_end for location in locations if location.line_end is not None]
    pages = [location.page_number for location in locations if location.page_number is not None]
    return (
        min(line_starts) if line_starts else None,
        max(line_ends) if line_ends else None,
        min(pages) if pages else None,
        max(pages) if pages else None,
    )


class StructureAwareCharacterChunker:
    """Pack normalized nodes without crossing heading boundaries."""

    def __init__(self, config: CharacterChunkingConfig | None = None) -> None:
        self._config = config or CharacterChunkingConfig()

    def chunk(self, document: ParsedDocument) -> tuple[DocumentChunk, ...]:
        chunks: list[DocumentChunk] = []
        heading_levels: list[tuple[int, str]] = []
        pending: list[_Unit] = []

        def heading_path() -> tuple[str, ...]:
            return tuple(text for _, text in heading_levels)

        def emit(units: list[_Unit]) -> None:
            if not units:
                return
            line_start, line_end, page_start, page_end = _source_span(units)
            chunks.append(
                DocumentChunk(
                    index=len(chunks),
                    text="\n\n".join(unit.text for unit in units),
                    heading_path=heading_path(),
                    content_type=_content_type(units),
                    source_line_start=line_start,
                    source_line_end=line_end,
                    page_start=page_start,
                    page_end=page_end,
                )
            )

        def flush() -> None:
            nonlocal pending
            emit(pending)
            pending = []

        for node in document.nodes:
            if isinstance(node, Heading):
                flush()
                heading_levels = [item for item in heading_levels if item[0] < node.level]
                heading_levels.append((node.level, node.text))
                continue

            content_type = (
                ChunkContentType.CODE if isinstance(node, CodeBlock) else ChunkContentType.TEXT
            )
            if isinstance(node, CodeBlock) and len(node.text) > self._config.max_chars:
                raise ContentBlockTooLargeError(
                    f"code block has {len(node.text)} characters; limit is {self._config.max_chars}"
                )
            if isinstance(node, Paragraph) and len(node.text) > self._config.max_chars:
                flush()
                for piece in _split_paragraph(node.text, self._config):
                    emit([_Unit(piece, content_type, node.source_location)])
                continue

            unit = _Unit(node.text, content_type, node.source_location)
            candidate_length = sum(len(item.text) for item in pending) + len(unit.text)
            if pending:
                candidate_length += 2 * len(pending)
            if pending and candidate_length > self._config.max_chars:
                flush()
            pending.append(unit)

        flush()
        return tuple(chunks)
