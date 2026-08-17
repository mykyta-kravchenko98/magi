"""Deterministic content-role classification for normalized documents."""

import re
from dataclasses import replace

from magi.ingestion.domain.value_objects import (
    ContentRole,
    DocumentNode,
    Heading,
    ParsedDocument,
)

_TOC_HEADING = re.compile(
    r"^(?:оглавление|содержание|contents|table\s+of\s+contents)$",
    re.IGNORECASE,
)
_FRONT_MATTER_HEADING = re.compile(
    r"^(?:предисловие(?:\s+.+)?|об\s+авторе|благодарности|посвящение|"  # noqa: RUF001
    r"от\s+издательства|foreword|preface|acknowledg(?:e)?ments|about\s+the\s+author)$",
    re.IGNORECASE,
)
_BODY_HEADING = re.compile(
    r"^(?:часть|part|глава|chapter)\s+(?:\d+|[ivxlcdm]+)(?:\b|\s|[.:\u2013\u2014-])",
    re.IGNORECASE,
)


def _is_pdf_node(node: DocumentNode) -> bool:
    return node.source_location is not None and node.source_location.page_number is not None


class DeterministicDocumentRoleClassifier:
    """Classify PDF regions without depending on a PDF extraction library."""

    def classify(self, document: ParsedDocument) -> ParsedDocument:
        if not any(_is_pdf_node(node) for node in document.nodes):
            return document

        has_toc = any(
            isinstance(node, Heading) and _TOC_HEADING.fullmatch(node.text.strip())
            for node in document.nodes
        )
        active_role = ContentRole.FRONT_MATTER if has_toc else ContentRole.BODY
        classified: list[DocumentNode] = []

        for node in document.nodes:
            if node.content_role in {ContentRole.HEADER_FOOTER, ContentRole.FOOTNOTE}:
                classified.append(node)
                continue
            if not _is_pdf_node(node):
                classified.append(node)
                continue
            if isinstance(node, Heading):
                heading = node.text.strip()
                if _TOC_HEADING.fullmatch(heading):
                    active_role = ContentRole.TABLE_OF_CONTENTS
                elif _FRONT_MATTER_HEADING.fullmatch(heading):
                    active_role = ContentRole.FRONT_MATTER
                elif _BODY_HEADING.match(heading):
                    active_role = ContentRole.BODY
            classified.append(replace(node, content_role=active_role))

        return ParsedDocument(nodes=tuple(classified))
