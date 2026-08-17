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
    ContentRole,
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
_CID_LIST_MARKER = "(cid:2)"
_CANONICAL_LIST_MARKER = "\u2022"
_PAGE_NUMBER = re.compile(r"^\d+$")
_NUMBERED_PAGE_FURNITURE = re.compile(r"^(?:\d+\s*\|\s*\S.*|\S.*\s*\|\s*\d+)$")
_DECORATIVE_PAGE_FURNITURE = re.compile(r"^[^\w]+$")
_FURNITURE_DIGITS = re.compile(r"\d+")
_FURNITURE_WHITESPACE = re.compile(r"\s+")
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
    heading_join_gap_ratio: float = 0.75
    footnote_size_ratio: float = 0.85
    footnote_gap_ratio: float = 1.0
    code_char_width_ratio: float = 0.6
    max_heading_chars: int = 200
    page_furniture_candidate_lines: int = 2
    page_furniture_min_repetitions: int = 2
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
            self.heading_join_gap_ratio,
            self.footnote_size_ratio,
            self.footnote_gap_ratio,
            self.code_char_width_ratio,
        )
        if any(value <= 0 for value in positive_values):
            raise ValueError("PDF extraction ratios must be positive")
        if self.max_heading_chars < 1:
            raise ValueError("max_heading_chars must be positive")
        if self.page_furniture_candidate_lines < 1:
            raise ValueError("page_furniture_candidate_lines must be positive")
        if self.page_furniture_min_repetitions < 2:
            raise ValueError("page_furniture_min_repetitions must be at least two")
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
    word_texts = [word.text for word in ordered]
    if len(word_texts) > 1 and word_texts[0] == _CID_LIST_MARKER:
        word_texts[0] = _CANONICAL_LIST_MARKER
    text = " ".join(word_texts)
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


def _page_furniture_indexes(line_count: int, candidate_lines: int) -> set[int]:
    boundary = min(line_count, candidate_lines)
    return {*range(boundary), *range(max(0, line_count - boundary), line_count)}


def _canonical_page_furniture(text: str) -> str:
    without_page_numbers = _FURNITURE_DIGITS.sub("#", text)
    return _FURNITURE_WHITESPACE.sub(" ", without_page_numbers).strip().casefold()


def _is_direct_page_furniture(line: _Line, line_index: int) -> bool:
    text = line.text.strip()
    page_number_match = _PAGE_NUMBER.fullmatch(text)
    if (
        page_number_match is not None and int(page_number_match.group(0)) == line.page_number
    ) or _NUMBERED_PAGE_FURNITURE.fullmatch(text):
        return True
    return (
        line_index == 0
        and len(text) <= 4
        and _DECORATIVE_PAGE_FURNITURE.fullmatch(text) is not None
    )


def _repeated_page_furniture(
    pages: Sequence[Sequence[_Line]],
    body_size: float,
    profile: PdfExtractionProfile,
) -> set[str]:
    occurrences: Counter[str] = Counter()
    maximum_furniture_size = body_size * profile.bold_heading_size_ratio
    for lines in pages:
        page_keys = {
            _canonical_page_furniture(lines[index].text)
            for index in _page_furniture_indexes(len(lines), profile.page_furniture_candidate_lines)
            if lines[index].max_size <= maximum_furniture_size
        }
        occurrences.update(key for key in page_keys if key)
    return {
        key for key, count in occurrences.items() if count >= profile.page_furniture_min_repetitions
    }


def _page_furniture_by_page(
    pages: Sequence[Sequence[_Line]],
    body_size: float,
    profile: PdfExtractionProfile,
) -> tuple[frozenset[int], ...]:
    repeated = _repeated_page_furniture(pages, body_size, profile)
    furniture_by_page: list[frozenset[int]] = []
    for lines in pages:
        candidates = _page_furniture_indexes(len(lines), profile.page_furniture_candidate_lines)
        furniture_by_page.append(
            frozenset(
                index
                for index, line in enumerate(lines)
                if index in candidates
                and (
                    _is_direct_page_furniture(line, index)
                    or _canonical_page_furniture(line.text) in repeated
                )
            )
        )
    return tuple(furniture_by_page)


def _footnote_indexes(
    lines: Sequence[_Line],
    furniture_indexes: frozenset[int],
    body_size: float,
    profile: PdfExtractionProfile,
) -> frozenset[int]:
    maximum_size = body_size * profile.footnote_size_ratio
    references = {
        index
        for index, line in enumerate(lines)
        if index not in furniture_indexes
        and line.max_size <= maximum_size
        and _PAGE_NUMBER.fullmatch(line.text.strip()) is not None
    }
    content_indexes = [index for index in range(len(lines)) if index not in furniture_indexes]
    trailing: set[int] = set()
    for index in reversed(content_indexes):
        if lines[index].max_size > maximum_size:
            break
        trailing.add(index)
    if trailing:
        first_index = min(trailing)
        previous_indexes = [index for index in content_indexes if index < first_index]
        previous_index = previous_indexes[-1] if previous_indexes else None
        gap = (
            lines[first_index].top - lines[previous_index].bottom
            if previous_index is not None
            else float("inf")
        )
        has_prose = any(
            _PAGE_NUMBER.fullmatch(lines[index].text.strip()) is None for index in trailing
        )
        if not has_prose or gap <= body_size * profile.footnote_gap_ratio:
            trailing.clear()
    return frozenset(references | trailing)


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


def _paragraph(
    lines: Sequence[_Line],
    *,
    content_role: ContentRole = ContentRole.BODY,
) -> Paragraph:
    return Paragraph(
        text="\n".join(line.text for line in lines),
        source_location=SourceLocation(page_number=lines[0].page_number),
        content_role=content_role,
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
    furniture_indexes: frozenset[int],
    footnote_indexes: frozenset[int],
    body_size: float,
    heading_sizes: Sequence[float],
    profile: PdfExtractionProfile,
) -> tuple[DocumentNode, ...]:
    nodes: list[DocumentNode] = []
    paragraph_lines: list[_Line] = []
    code_lines: list[_Line] = []
    footnote_lines: list[_Line] = []
    previous_heading_line: _Line | None = None

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

    def flush_footnote() -> None:
        nonlocal footnote_lines
        if footnote_lines:
            nodes.append(_paragraph(footnote_lines, content_role=ContentRole.FOOTNOTE))
            footnote_lines = []

    for line_index, line in enumerate(lines):
        if line_index in furniture_indexes:
            flush_paragraph()
            flush_code()
            flush_footnote()
            nodes.append(
                Paragraph(
                    text=line.text,
                    source_location=SourceLocation(page_number=line.page_number),
                    content_role=ContentRole.HEADER_FOOTER,
                )
            )
            previous_heading_line = None
            continue
        if line_index in footnote_indexes:
            flush_paragraph()
            flush_code()
            footnote_lines.append(line)
            previous_heading_line = None
            continue
        flush_footnote()
        if _is_heading(line, body_size, profile):
            flush_paragraph()
            flush_code()
            level = _heading_level(line, heading_sizes)
            previous_node = nodes[-1] if nodes else None
            gap = (
                line.top - previous_heading_line.bottom
                if previous_heading_line is not None
                else float("inf")
            )
            maximum_gap = (
                max(body_size, previous_heading_line.height, line.height)
                * profile.heading_join_gap_ratio
                if previous_heading_line is not None
                else 0.0
            )
            if (
                previous_heading_line is not None
                and isinstance(previous_node, Heading)
                and previous_node.level == level
                and gap <= maximum_gap
                and len(previous_node.text) + len(line.text) + 1 <= profile.max_heading_chars
            ):
                nodes[-1] = Heading(
                    level=level,
                    text=f"{previous_node.text} {line.text}",
                    source_location=previous_node.source_location,
                )
            else:
                nodes.append(
                    Heading(
                        level=level,
                        text=line.text,
                        source_location=SourceLocation(page_number=line.page_number),
                    )
                )
            previous_heading_line = line
            continue
        previous_heading_line = None
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
    flush_footnote()
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
        furniture_by_page = _page_furniture_by_page(pages, body_size, self._profile)
        meaningful_lines = tuple(
            line
            for page_lines, furniture_indexes in zip(pages, furniture_by_page, strict=True)
            for index, line in enumerate(page_lines)
            if index not in furniture_indexes
        )
        if not meaningful_lines:
            raise PdfNoExtractableTextError("PDF has no meaningful text")
        body_size = _body_font_size(meaningful_lines)
        heading_sizes = _heading_sizes(meaningful_lines, body_size, self._profile)
        footnotes_by_page = tuple(
            _footnote_indexes(page_lines, furniture_indexes, body_size, self._profile)
            for page_lines, furniture_indexes in zip(pages, furniture_by_page, strict=True)
        )
        nodes = tuple(
            node
            for page_lines, furniture_indexes, footnote_indexes in zip(
                pages, furniture_by_page, footnotes_by_page, strict=True
            )
            for node in _classify_page(
                page_lines,
                furniture_indexes,
                footnote_indexes,
                body_size,
                heading_sizes,
                self._profile,
            )
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
