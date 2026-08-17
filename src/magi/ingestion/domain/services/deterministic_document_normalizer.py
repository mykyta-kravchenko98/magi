"""Deterministic normalization that retains document structure and provenance."""

import re
import unicodedata
from collections.abc import Set
from dataclasses import replace

from magi.ingestion.domain.errors import NoTextContentError
from magi.ingestion.domain.value_objects import (
    CodeBlock,
    ContentRole,
    DocumentNode,
    Heading,
    Paragraph,
    ParsedDocument,
)

_PROSE_WHITESPACE = re.compile(r"\s+")
_LETTER = r"[^\W\d_]"
_PDF_LINE_BREAK_HYPHEN = re.compile(
    rf"(?P<left>{_LETTER}+)-[^\S\r\n]*\r?\n[^\S\r\n]*(?P<right>{_LETTER}+)"
)
_HYPHENATED_WORD = re.compile(rf"(?<!{_LETTER}){_LETTER}+-{_LETTER}+(?!{_LETTER})")
_WORD = re.compile(rf"(?<!{_LETTER}){_LETTER}+(?!{_LETTER})")
_HYPHENATED_PARTICLES = frozenset({"ка", "либо", "нибудь", "таки", "то"})
_PRESERVED_HYPHEN_LEFT_PARTS = frozenset({"бизнес"})
_PDF_NODE_BOUNDARY_LEFT = re.compile(rf"(?P<left>{_LETTER}+)-\s*$")
_PDF_NODE_BOUNDARY_RIGHT = re.compile(rf"^\s*(?P<right>{_LETTER}+)")
_TRANSPARENT_PDF_ROLES = frozenset({ContentRole.FOOTNOTE, ContentRole.HEADER_FOOTER})


def _is_pdf_node(node: DocumentNode) -> bool:
    return node.source_location is not None and node.source_location.page_number is not None


def _pdf_unhyphenated_words(document: ParsedDocument) -> frozenset[str]:
    words: set[str] = set()
    for node in document.nodes:
        if isinstance(node, (Heading, Paragraph)) and _is_pdf_node(node):
            normalized = unicodedata.normalize("NFC", node.text)
            words.update(match.group(0).casefold() for match in _WORD.finditer(normalized))
    return frozenset(words)


def _known_hyphenated_words(
    document: ParsedDocument,
    unhyphenated_words: Set[str],
) -> frozenset[str]:
    words: set[str] = set()
    for node in document.nodes:
        if isinstance(node, (Heading, Paragraph)) and _is_pdf_node(node):
            normalized = unicodedata.normalize("NFC", node.text)
            for match in _HYPHENATED_WORD.finditer(normalized):
                hyphenated = match.group(0).casefold()
                if hyphenated.replace("-", "") not in unhyphenated_words:
                    words.add(hyphenated)
    return frozenset(words)


def _joined_pdf_word(left: str, right: str, known_words: Set[str]) -> str:
    hyphenated = f"{left}-{right}"
    if (
        hyphenated.casefold() in known_words
        or left.isupper()
        or left.casefold() in _PRESERVED_HYPHEN_LEFT_PARTS
        or right.casefold() in _HYPHENATED_PARTICLES
    ):
        return hyphenated
    return f"{left}{right}"


def _dehyphenate_pdf_line_breaks(text: str, known_words: Set[str]) -> str:
    def replace_line_break(match: re.Match[str]) -> str:
        return _joined_pdf_word(
            match.group("left"),
            match.group("right"),
            known_words,
        )

    return _PDF_LINE_BREAK_HYPHEN.sub(replace_line_break, text)


def _repair_confirmed_inline_pdf_splits(
    text: str,
    unhyphenated_words: Set[str],
) -> str:
    def replace_hyphenated(match: re.Match[str]) -> str:
        hyphenated = match.group(0)
        joined = hyphenated.replace("-", "")
        return joined if joined.casefold() in unhyphenated_words else hyphenated

    return _HYPHENATED_WORD.sub(replace_hyphenated, text)


def _is_pdf_paragraph(node: DocumentNode) -> bool:
    return (
        isinstance(node, Paragraph)
        and node.source_location is not None
        and node.source_location.page_number is not None
    )


def _repair_pdf_node_boundary_hyphenation(
    document: ParsedDocument,
    known_words: Set[str],
) -> ParsedDocument:
    nodes = list(document.nodes)
    previous_index: int | None = None

    for index, current in enumerate(nodes):
        if current.content_role in _TRANSPARENT_PDF_ROLES:
            continue
        if not _is_pdf_paragraph(current):
            previous_index = None
            continue
        if previous_index is not None:
            previous = nodes[previous_index]
            assert isinstance(previous, Paragraph)
            assert previous.source_location is not None
            assert current.source_location is not None
            previous_page = previous.source_location.page_number
            current_page = current.source_location.page_number
            assert previous_page is not None
            assert current_page is not None
            left_match = _PDF_NODE_BOUNDARY_LEFT.search(previous.text)
            right_match = _PDF_NODE_BOUNDARY_RIGHT.match(current.text)
            if (
                current.content_role is previous.content_role
                and current_page in {previous_page, previous_page + 1}
                and left_match is not None
                and right_match is not None
            ):
                joined_word = _joined_pdf_word(
                    left_match.group("left"),
                    right_match.group("right"),
                    known_words,
                )
                nodes[previous_index] = replace(
                    previous,
                    text=previous.text[: left_match.start()].rstrip(),
                )
                current = replace(
                    current,
                    text=f"{joined_word}{current.text[right_match.end() :]}",
                )
                nodes[index] = current
        previous_index = index

    return ParsedDocument(nodes=tuple(nodes))


def _normalize_prose(
    text: str,
    *,
    pdf_hyphenated_words: Set[str] | None = None,
    pdf_unhyphenated_words: Set[str] | None = None,
) -> str:
    normalized = unicodedata.normalize("NFC", text)
    if pdf_hyphenated_words is not None:
        normalized = _dehyphenate_pdf_line_breaks(normalized, pdf_hyphenated_words)
    if pdf_unhyphenated_words is not None:
        normalized = _repair_confirmed_inline_pdf_splits(normalized, pdf_unhyphenated_words)
    return _PROSE_WHITESPACE.sub(" ", normalized).strip()


def _normalize_code(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


class DeterministicDocumentNormalizer:
    def normalize(self, document: ParsedDocument) -> ParsedDocument:
        nodes: list[DocumentNode] = []
        pdf_unhyphenated_words = _pdf_unhyphenated_words(document)
        pdf_hyphenated_words = _known_hyphenated_words(document, pdf_unhyphenated_words)
        repaired = _repair_pdf_node_boundary_hyphenation(
            document,
            pdf_hyphenated_words,
        )
        for node in repaired.nodes:
            is_pdf = _is_pdf_node(node)
            known_words = pdf_hyphenated_words if is_pdf else None
            unhyphenated_words = pdf_unhyphenated_words if is_pdf else None
            if isinstance(node, Heading):
                text = _normalize_prose(
                    node.text,
                    pdf_hyphenated_words=known_words,
                    pdf_unhyphenated_words=unhyphenated_words,
                )
                if text:
                    nodes.append(
                        Heading(
                            level=node.level,
                            text=text,
                            source_location=node.source_location,
                            content_role=node.content_role,
                        )
                    )
            elif isinstance(node, Paragraph):
                text = _normalize_prose(
                    node.text,
                    pdf_hyphenated_words=known_words,
                    pdf_unhyphenated_words=unhyphenated_words,
                )
                if text:
                    nodes.append(
                        Paragraph(
                            text=text,
                            source_location=node.source_location,
                            content_role=node.content_role,
                        )
                    )
            else:
                text = _normalize_code(node.text)
                if text:
                    language = _normalize_prose(node.language) if node.language else None
                    nodes.append(
                        CodeBlock(
                            text=text,
                            language=language or None,
                            source_location=node.source_location,
                            content_role=node.content_role,
                        )
                    )
        if not any(isinstance(node, (Paragraph, CodeBlock)) for node in nodes):
            raise NoTextContentError("document contains no meaningful text")
        return ParsedDocument(nodes=tuple(nodes))
