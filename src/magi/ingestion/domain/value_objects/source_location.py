"""Source-provenance value object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceLocation:
    """Inclusive source location for text lines or one PDF page."""

    line_start: int | None = None
    line_end: int | None = None
    page_number: int | None = None

    def __post_init__(self) -> None:
        if (self.line_start is None) != (self.line_end is None):
            raise ValueError("line_start and line_end must be provided together")
        if self.line_start is not None:
            if self.line_start < 1 or self.line_end is None or self.line_end < self.line_start:
                raise ValueError("source lines must be positive and ordered")
        if self.page_number is not None and self.page_number < 1:
            raise ValueError("page_number must be positive")
