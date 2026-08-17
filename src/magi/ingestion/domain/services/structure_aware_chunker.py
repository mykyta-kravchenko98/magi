"""Deterministic, structure-aware token chunking."""

from dataclasses import dataclass

from magi.ingestion.domain.errors import ContentBlockTooLargeError
from magi.ingestion.domain.services._token_aware_prose_splitter import TokenAwareProseSplitter
from magi.ingestion.domain.services.interfaces.token_counter import TokenCounter
from magi.ingestion.domain.value_objects import (
    ChunkContentType,
    CodeBlock,
    ContentRole,
    DocumentChunk,
    Heading,
    ParsedDocument,
    SourceLocation,
    TokenChunkingProfile,
    compose_embedding_input,
)


@dataclass(frozen=True, slots=True)
class _Unit:
    text: str
    content_type: ChunkContentType
    location: SourceLocation | None
    content_role: ContentRole


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


class StructureAwareTokenChunker:
    """Chunk document sections using the tokenizer pinned to the embedding profile."""

    def __init__(
        self,
        token_counter: TokenCounter,
        profile: TokenChunkingProfile | None = None,
    ) -> None:
        self._token_counter = token_counter
        self._profile = profile or TokenChunkingProfile()
        self._prose_splitter = TokenAwareProseSplitter(token_counter, self._profile)

    def chunk(self, document: ParsedDocument) -> tuple[DocumentChunk, ...]:
        chunks: list[DocumentChunk] = []
        heading_levels: list[tuple[int, str]] = []
        section: list[_Unit] = []
        active_role = ContentRole.BODY

        def heading_path() -> tuple[str, ...]:
            return tuple(text for _, text in heading_levels)

        def flush_section() -> None:
            nonlocal section
            chunks.extend(self._chunk_section(section, heading_path(), len(chunks)))
            section = []

        for node in document.nodes:
            if isinstance(node, Heading):
                flush_section()
                active_role = node.content_role
                heading_levels = [item for item in heading_levels if item[0] < node.level]
                heading_levels.append((node.level, node.text))
                continue

            if section and node.content_role is not active_role:
                flush_section()
            active_role = node.content_role
            section.append(
                _Unit(
                    text=node.text,
                    content_type=(
                        ChunkContentType.CODE
                        if isinstance(node, CodeBlock)
                        else ChunkContentType.TEXT
                    ),
                    location=node.source_location,
                    content_role=active_role,
                )
            )

        flush_section()
        return tuple(chunks)

    def _chunk_section(
        self,
        units: list[_Unit],
        heading_path: tuple[str, ...],
        first_index: int,
    ) -> list[DocumentChunk]:
        if not units:
            return []

        for unit in units:
            if unit.content_type is ChunkContentType.CODE:
                self._validate_code_block(unit, heading_path)

        if self._count_units(heading_path, units) <= self._profile.soft_max_tokens:
            return [self._make_chunk(first_index, heading_path, units)]

        chunks: list[DocumentChunk] = []
        pending: list[_Unit] = []

        def emit(items: list[_Unit]) -> None:
            if items:
                chunks.append(self._make_chunk(first_index + len(chunks), heading_path, items))

        def flush() -> None:
            nonlocal pending
            emit(pending)
            pending = []

        for unit in units:
            unit_tokens = self._count_units(heading_path, [unit])
            if unit.content_type is ChunkContentType.CODE and (
                unit_tokens > self._profile.hard_max_tokens
            ):
                flush()
                emit([unit])
                continue
            if unit.content_type is ChunkContentType.TEXT and (
                unit_tokens > self._profile.soft_max_tokens
            ):
                flush()
                for text in self._prose_splitter.split(unit.text, heading_path):
                    emit(
                        [
                            _Unit(
                                text=text,
                                content_type=unit.content_type,
                                location=unit.location,
                                content_role=unit.content_role,
                            )
                        ]
                    )
                continue

            candidate = [*pending, unit]
            if pending and self._count_units(heading_path, candidate) > self._profile.target_tokens:
                flush()
            pending.append(unit)

        flush()
        return chunks

    def _validate_code_block(self, unit: _Unit, heading_path: tuple[str, ...]) -> None:
        token_count = self._count_units(heading_path, [unit])
        if token_count > self._profile.embedding_input_max_tokens:
            raise ContentBlockTooLargeError(
                f"code block embedding input has {token_count} tokens; "
                f"safety limit is {self._profile.embedding_input_max_tokens}"
            )

    def _count_units(self, heading_path: tuple[str, ...], units: list[_Unit]) -> int:
        return self._count_text(heading_path, "\n\n".join(unit.text for unit in units))

    def _count_text(self, heading_path: tuple[str, ...], text: str) -> int:
        return self._token_counter.count_tokens(compose_embedding_input(heading_path, text))

    @staticmethod
    def _make_chunk(
        index: int,
        heading_path: tuple[str, ...],
        units: list[_Unit],
    ) -> DocumentChunk:
        line_start, line_end, page_start, page_end = _source_span(units)
        return DocumentChunk(
            index=index,
            text="\n\n".join(unit.text for unit in units),
            heading_path=heading_path,
            content_type=_content_type(units),
            content_role=units[0].content_role,
            source_line_start=line_start,
            source_line_end=line_end,
            page_start=page_start,
            page_end=page_end,
        )
