"""pdfplumber parser adapter for deterministic, best-effort PDF structure extraction."""

import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from io import BytesIO
from statistics import median
from typing import Any, TypedDict, cast

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfplumber.page import Page
from pdfplumber.utils.exceptions import PdfminerException

from magi.ingestion.domain import (
    CodeBlock,
    DocumentNode,
    Heading,
    Paragraph,
    ParsedDocument,
    PdfEncryptedError,
    PdfNoExtractableTextError,
    PdfParsingError,
    SourceLocation,
)

_LIST_MARKER = re.compile(r"^(?:[\u2022\u25cf\u25aa\u25e6*+-]|\d+[.)])\s+")
_BOLD_FONT_MARKERS = ("bold", "black", "semibold", "demi")


class _RawWord(TypedDict):
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    fontname: str
    size: float


@dataclass(frozen=True, slots=True, kw_only=True)
class PdfExtractionProfile:
    """Immutable PDF-layout heuristic profile."""

    line_tolerance_ratio: float = 0.3
    paragraph_gap_ratio: float = 0.7
    indentation_ratio: float = 1.5
    heading_size_ratio: float = 1.2
    bold_heading_size_ratio: float = 1.08
    code_char_width_ratio: float = 0.6
    max_heading_chars: int = 200
    code_font_markers: tuple[str, ...] = (
        "courier",
        "consolas",
        "menlo",
        "monaco",
        "liberationmono",
        "dejavusansmono",
        "sourcecode",
        "monospace",
    )

    def __post_init__(self) -> None:
        positive_values = (
            self.line_tolerance_ratio,
            self.paragraph_gap_ratio,
            self.indentation_ratio,
            self.heading_size_ratio,
            self.bold_heading_size_ratio,
            self.code_char_width_ratio,
        )
        if any(value <= 0 for value in positive_values):
            raise ValueError("PDF extraction ratios must be positive")
        if self.max_heading_chars < 1:
            raise ValueError("max_heading_chars must be positive")
        if not self.code_font_markers:
            raise ValueError("code_font_markers must not be empty")


@dataclass(frozen=True, slots=True)
class _Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    fontname: str
    size: float


@dataclass(frozen=True, slots=True)
class _Line:
    page_number: int
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float
    max_size: float
    bold_ratio: float
    code_ratio: float

    @property
    def height(self) -> float:
        return self.bottom - self.top


def _float_field(word: Mapping[str, Any], field: str) -> float:
    value = word.get(field)
    if not isinstance(value, (int, float)):
        raise PdfParsingError(f"PDF word is missing numeric {field}")
    return float(value)


def _convert_word(raw: Mapping[str, Any]) -> _Word | None:
    text = raw.get("text")
    fontname = raw.get("fontname")
    if not isinstance(text, str) or not text.strip():
        return None
    if not isinstance(fontname, str):
        fontname = ""
    return _Word(
        text=text.strip(),
        x0=_float_field(raw, "x0"),
        x1=_float_field(raw, "x1"),
        top=_float_field(raw, "top"),
        bottom=_float_field(raw, "bottom"),
        fontname=fontname,
        size=_float_field(raw, "size"),
    )


def _weighted_ratio(words: Sequence[_Word], predicate: Callable[[_Word], bool]) -> float:
    total = sum(len(word.text) for word in words)
    if total == 0:
        return 0.0
    return sum(len(word.text) for word in words if predicate(word)) / total


def _is_bold(word: _Word) -> bool:
    name = word.fontname.lower().replace("-", "")
    return any(marker in name for marker in _BOLD_FONT_MARKERS)


def _is_code_font(word: _Word, markers: Sequence[str]) -> bool:
    name = word.fontname.lower().replace("-", "").replace("_", "")
    return any(marker in name for marker in markers)


def _make_line(
    page_number: int,
    words: Sequence[_Word],
    profile: PdfExtractionProfile,
) -> _Line:
    ordered = sorted(words, key=lambda word: word.x0)
    text = " ".join(word.text for word in ordered)
    weights = [len(word.text) for word in ordered]
    weighted_size = sum(word.size * weight for word, weight in zip(ordered, weights, strict=True))
    return _Line(
        page_number=page_number,
        text=text,
        x0=min(word.x0 for word in ordered),
        x1=max(word.x1 for word in ordered),
        top=min(word.top for word in ordered),
        bottom=max(word.bottom for word in ordered),
        size=weighted_size / sum(weights),
        max_size=max(word.size for word in ordered),
        bold_ratio=_weighted_ratio(ordered, _is_bold),
        code_ratio=_weighted_ratio(
            ordered,
            lambda word: _is_code_font(word, profile.code_font_markers),
        ),
    )


def _group_lines(
    page_number: int,
    words: Sequence[_Word],
    profile: PdfExtractionProfile,
) -> tuple[_Line, ...]:
    ordered = sorted(words, key=lambda word: (word.top, word.x0))
    groups: list[list[_Word]] = []
    for word in ordered:
        if not groups:
            groups.append([word])
            continue
        current = groups[-1]
        current_center = median((item.top + item.bottom) / 2 for item in current)
        word_center = (word.top + word.bottom) / 2
        tolerance = (
            max(word.size, median(item.size for item in current)) * profile.line_tolerance_ratio
        )
        if abs(word_center - current_center) <= tolerance:
            current.append(word)
        else:
            groups.append([word])
    return tuple(_make_line(page_number, group, profile) for group in groups)


def _body_font_size(lines: Iterable[_Line]) -> float:
    frequency: Counter[float] = Counter()
    for line in lines:
        frequency[round(line.size * 2) / 2] += len(line.text)
    if not frequency:
        return 0.0
    return frequency.most_common(1)[0][0]


def _is_heading(line: _Line, body_size: float, profile: PdfExtractionProfile) -> bool:
    if _LIST_MARKER.match(line.text) or len(line.text) > profile.max_heading_chars:
        return False
    large = line.max_size >= body_size * profile.heading_size_ratio
    bold_and_larger = (
        line.bold_ratio >= 0.7 and line.max_size >= body_size * profile.bold_heading_size_ratio
    )
    return large or bold_and_larger


def _heading_sizes(
    lines: Iterable[_Line],
    body_size: float,
    profile: PdfExtractionProfile,
) -> tuple[float, ...]:
    sizes = {round(line.max_size, 1) for line in lines if _is_heading(line, body_size, profile)}
    return tuple(sorted(sizes, reverse=True)[:6])


def _heading_level(line: _Line, sizes: Sequence[float]) -> int:
    rounded = round(line.max_size, 1)
    return sizes.index(rounded) + 1 if rounded in sizes else min(6, len(sizes) + 1)


def _starts_new_paragraph(
    previous: _Line,
    current: _Line,
    paragraph_lines: Sequence[_Line],
    body_size: float,
    profile: PdfExtractionProfile,
) -> bool:
    if _LIST_MARKER.match(current.text):
        return True
    gap = current.top - previous.bottom
    if gap > max(body_size, previous.height) * profile.paragraph_gap_ratio:
        return True
    paragraph_is_list_item = bool(_LIST_MARKER.match(paragraph_lines[0].text))
    indentation_changed = abs(current.x0 - paragraph_lines[0].x0) > (
        body_size * profile.indentation_ratio
    )
    return indentation_changed and not paragraph_is_list_item


def _paragraph(lines: Sequence[_Line]) -> Paragraph:
    return Paragraph(
        text=" ".join(line.text for line in lines),
        source_location=SourceLocation(page_number=lines[0].page_number),
    )


def _code_block(lines: Sequence[_Line], profile: PdfExtractionProfile) -> CodeBlock:
    left_edge = min(line.x0 for line in lines)
    rendered_lines: list[str] = []
    for line in lines:
        approximate_char_width = line.size * profile.code_char_width_ratio
        indentation = round((line.x0 - left_edge) / approximate_char_width)
        rendered_lines.append(f"{' ' * indentation}{line.text}")
    return CodeBlock(
        text="\n".join(rendered_lines),
        language=None,
        source_location=SourceLocation(page_number=lines[0].page_number),
    )


def _classify_page(
    lines: Sequence[_Line],
    body_size: float,
    heading_sizes: Sequence[float],
    profile: PdfExtractionProfile,
) -> tuple[DocumentNode, ...]:
    nodes: list[DocumentNode] = []
    paragraph_lines: list[_Line] = []
    code_lines: list[_Line] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            nodes.append(_paragraph(paragraph_lines))
            paragraph_lines = []

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            nodes.append(_code_block(code_lines, profile))
            code_lines = []

    for line in lines:
        if _is_heading(line, body_size, profile):
            flush_paragraph()
            flush_code()
            nodes.append(
                Heading(
                    level=_heading_level(line, heading_sizes),
                    text=line.text,
                    source_location=SourceLocation(page_number=line.page_number),
                )
            )
            continue
        if line.code_ratio >= 0.8:
            flush_paragraph()
            if code_lines:
                gap = line.top - code_lines[-1].bottom
                if gap > max(body_size, code_lines[-1].height) * profile.paragraph_gap_ratio:
                    flush_code()
            code_lines.append(line)
            continue
        flush_code()
        if paragraph_lines and _starts_new_paragraph(
            paragraph_lines[-1], line, paragraph_lines, body_size, profile
        ):
            flush_paragraph()
        paragraph_lines.append(line)

    flush_paragraph()
    flush_code()
    return tuple(nodes)


class PdfParser:
    """Parse born-digital PDFs into application-owned structural nodes."""

    def __init__(self, profile: PdfExtractionProfile | None = None) -> None:
        self._profile = profile or PdfExtractionProfile()

    def parse(self, content: bytes) -> ParsedDocument:
        if not content.startswith(b"%PDF-"):
            raise PdfParsingError("content does not have a PDF signature")
        try:
            with pdfplumber.open(BytesIO(content), unicode_norm="NFC") as pdf:
                pages = tuple(
                    self._extract_page(page, index) for index, page in enumerate(pdf.pages, 1)
                )
        except PDFPasswordIncorrect as error:
            raise PdfEncryptedError("encrypted PDF is not supported") from error
        except PdfminerException as error:
            if error.args and isinstance(error.args[0], PDFPasswordIncorrect):
                raise PdfEncryptedError("encrypted PDF is not supported") from error
            raise PdfParsingError("PDF parsing failed") from error
        except PdfParsingError:
            raise
        except Exception as error:
            raise PdfParsingError("PDF parsing failed") from error

        all_lines = tuple(line for page in pages for line in page)
        if not all_lines:
            raise PdfNoExtractableTextError("PDF has no extractable text layer")
        body_size = _body_font_size(all_lines)
        heading_sizes = _heading_sizes(all_lines, body_size, self._profile)
        nodes = tuple(
            node
            for page_lines in pages
            for node in _classify_page(page_lines, body_size, heading_sizes, self._profile)
        )
        if not nodes:
            raise PdfNoExtractableTextError("PDF has no meaningful text")
        return ParsedDocument(nodes=nodes)

    def _extract_page(self, page: Page, page_number: int) -> tuple[_Line, ...]:
        raw_words = cast(
            "list[_RawWord]",
            page.dedupe_chars().extract_words(
                x_tolerance_ratio=0.15,
                y_tolerance=3,
                extra_attrs=["fontname", "size"],
            ),
        )
        words = tuple(word for raw in raw_words if (word := _convert_word(raw)) is not None)
        return _group_lines(page_number, words, self._profile)
