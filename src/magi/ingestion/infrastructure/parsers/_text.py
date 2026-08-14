"""Shared implementation details for dependency-free text parser adapters."""

from collections.abc import Sequence

from magi.ingestion.domain import InvalidTextEncodingError, Paragraph, SourceLocation


def decode_utf8(content: bytes) -> str:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InvalidTextEncodingError("text content must be valid UTF-8") from error
    return text.removeprefix("\ufeff")


def source_location(start_index: int, end_index: int) -> SourceLocation:
    return SourceLocation(line_start=start_index + 1, line_end=end_index + 1)


def paragraph(lines: Sequence[str], start: int, end: int) -> Paragraph:
    return Paragraph(
        text="\n".join(lines[start:end]),
        source_location=source_location(start, end - 1),
    )
