"""Deterministic parser for the supported Markdown structure subset."""

import re

from magi.ingestion.domain import CodeBlock, DocumentNode, Heading, ParsedDocument
from magi.ingestion.infrastructure.parsers._text import (
    decode_utf8,
    paragraph,
    source_location,
)

_ATX_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?)|[ \t]*)$")
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_SETEXT_UNDERLINE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")


def _heading(line: str, line_index: int) -> Heading | None:
    match = _ATX_HEADING.match(line)
    if match is None:
        return None
    text = match.group(2) or ""
    text = re.sub(r"[ \t]+#+[ \t]*$", "", text)
    return Heading(
        level=len(match.group(1)),
        text=text,
        source_location=source_location(line_index, line_index),
    )


def _fence(line: str) -> re.Match[str] | None:
    match = _FENCE_OPEN.match(line)
    if match is not None and match.group(1).startswith("`") and "`" in match.group(2):
        return None
    return match


def _is_fence_close(line: str, marker: str) -> bool:
    pattern = rf" {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*"
    return re.fullmatch(pattern, line) is not None


class MarkdownParser:
    """Parse authoritative headings and fenced code without a Markdown dependency."""

    def parse(self, content: bytes) -> ParsedDocument:
        lines = decode_utf8(content).splitlines()
        nodes: list[DocumentNode] = []
        index = 0
        while index < len(lines):
            if not lines[index].strip():
                index += 1
                continue

            heading = _heading(lines[index], index)
            if heading is not None:
                nodes.append(heading)
                index += 1
                continue

            opening = _fence(lines[index])
            if opening is not None:
                index = self._append_code_block(lines, index, opening, nodes)
                continue

            index = self._append_paragraph_or_setext_heading(lines, index, nodes)

        return ParsedDocument(nodes=tuple(nodes))

    @staticmethod
    def _append_code_block(
        lines: list[str],
        index: int,
        opening: re.Match[str],
        nodes: list[DocumentNode],
    ) -> int:
        marker = opening.group(1)
        language_info = opening.group(2).strip()
        language = language_info.split(maxsplit=1)[0] if language_info else None
        start = index
        index += 1
        code_start = index
        while index < len(lines) and not _is_fence_close(lines[index], marker):
            index += 1
        code_end = index
        if index < len(lines):
            index += 1
        nodes.append(
            CodeBlock(
                text="\n".join(lines[code_start:code_end]),
                language=language,
                source_location=source_location(start, max(start, index - 1)),
            )
        )
        return index

    @staticmethod
    def _append_paragraph_or_setext_heading(
        lines: list[str],
        index: int,
        nodes: list[DocumentNode],
    ) -> int:
        start = index
        index += 1
        while index < len(lines) and lines[index].strip():
            if _heading(lines[index], index) is not None or _fence(lines[index]) is not None:
                break
            if _SETEXT_UNDERLINE.match(lines[index]) is not None:
                index += 1
                break
            index += 1
        setext = _SETEXT_UNDERLINE.match(lines[index - 1]) if index - start > 1 else None
        if setext is None:
            nodes.append(paragraph(lines, start, index))
        else:
            nodes.append(
                Heading(
                    level=1 if setext.group(1).startswith("=") else 2,
                    text="\n".join(lines[start : index - 1]),
                    source_location=source_location(start, index - 1),
                )
            )
        return index
