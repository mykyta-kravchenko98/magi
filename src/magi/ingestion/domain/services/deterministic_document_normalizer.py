"""Deterministic normalization that retains document structure and provenance."""

import re
import unicodedata

from magi.ingestion.domain.errors import NoTextContentError
from magi.ingestion.domain.value_objects import (
    CodeBlock,
    DocumentNode,
    Heading,
    Paragraph,
    ParsedDocument,
)

_PROSE_WHITESPACE = re.compile(r"\s+")


def _normalize_prose(text: str) -> str:
    return _PROSE_WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


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
        for node in document.nodes:
            if isinstance(node, Heading):
                text = _normalize_prose(node.text)
                if text:
                    nodes.append(
                        Heading(
                            level=node.level,
                            text=text,
                            source_location=node.source_location,
                        )
                    )
            elif isinstance(node, Paragraph):
                text = _normalize_prose(node.text)
                if text:
                    nodes.append(Paragraph(text=text, source_location=node.source_location))
            else:
                text = _normalize_code(node.text)
                if text:
                    language = _normalize_prose(node.language) if node.language else None
                    nodes.append(
                        CodeBlock(
                            text=text,
                            language=language or None,
                            source_location=node.source_location,
                        )
                    )
        if not any(isinstance(node, (Paragraph, CodeBlock)) for node in nodes):
            raise NoTextContentError("document contains no meaningful text")
        return ParsedDocument(nodes=tuple(nodes))
