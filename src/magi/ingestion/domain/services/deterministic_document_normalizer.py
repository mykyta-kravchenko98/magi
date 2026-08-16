"""Deterministic normalization that retains document structure and provenance."""

import re
import unicodedata
from collections.abc import Set

from magi.ingestion.domain.errors import NoTextContentError
from magi.ingestion.domain.value_objects import (
    CodeBlock,
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
_HYPHENATED_PARTICLES = frozenset({"ка", "либо", "нибудь", "таки", "то"})


def _known_hyphenated_words(document: ParsedDocument) -> frozenset[str]:
    words: set[str] = set()
    for node in document.nodes:
        if isinstance(node, (Heading, Paragraph)):
            normalized = unicodedata.normalize("NFC", node.text)
            words.update(
                match.group(0).casefold() for match in _HYPHENATED_WORD.finditer(normalized)
            )
    return frozenset(words)


def _dehyphenate_pdf_line_breaks(text: str, known_words: Set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        left = match.group("left")
        right = match.group("right")
        hyphenated = f"{left}-{right}"
        if (
            hyphenated.casefold() in known_words
            or left.isupper()
            or right.casefold() in _HYPHENATED_PARTICLES
        ):
            return hyphenated
        return f"{left}{right}"

    return _PDF_LINE_BREAK_HYPHEN.sub(replace, text)


def _normalize_prose(
    text: str,
    *,
    pdf_hyphenated_words: Set[str] | None = None,
) -> str:
    normalized = unicodedata.normalize("NFC", text)
    if pdf_hyphenated_words is not None:
        normalized = _dehyphenate_pdf_line_breaks(normalized, pdf_hyphenated_words)
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
        pdf_hyphenated_words = _known_hyphenated_words(document)
        for node in document.nodes:
            is_pdf_node = (
                node.source_location is not None and node.source_location.page_number is not None
            )
            known_words = pdf_hyphenated_words if is_pdf_node else None
            if isinstance(node, Heading):
                text = _normalize_prose(
                    node.text,
                    pdf_hyphenated_words=known_words,
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
