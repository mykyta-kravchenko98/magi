"""UTF-8 plain-text parser."""

from magi.ingestion.domain import DocumentNode, ParsedDocument
from magi.ingestion.infrastructure.parsers._text import decode_utf8, paragraph


class TxtParser:
    """Represent blank-line-delimited UTF-8 text as paragraphs."""

    def parse(self, content: bytes) -> ParsedDocument:
        lines = decode_utf8(content).splitlines()
        nodes: list[DocumentNode] = []
        start: int | None = None
        for index in range(len(lines) + 1):
            is_boundary = index == len(lines) or not lines[index].strip()
            if is_boundary:
                if start is not None:
                    nodes.append(paragraph(lines, start, index))
                    start = None
            elif start is None:
                start = index
        return ParsedDocument(nodes=tuple(nodes))
