"""Deterministic enrichment of normalized document structure."""

import re
from dataclasses import replace

from magi.ingestion.domain.value_objects import (
    ContentRole,
    DocumentNode,
    Heading,
    ParsedDocument,
)

_NUMBERED_CONTAINER_HEADING = re.compile(
    r"^(?:часть|part|глава|chapter)\s+(?:\d+|[ivxlcdm]+)$",
    re.IGNORECASE,
)


def _pdf_page(node: DocumentNode) -> int | None:
    if node.source_location is None:
        return None
    return node.source_location.page_number


class DeterministicDocumentStructureEnricher:
    """Compose split PDF section labels without depending on a PDF library."""

    def enrich(self, document: ParsedDocument) -> ParsedDocument:
        enriched: list[DocumentNode] = []
        index = 0

        while index < len(document.nodes):
            node = document.nodes[index]
            next_node = document.nodes[index + 1] if index + 1 < len(document.nodes) else None

            if self._can_compose(node, next_node):
                assert isinstance(node, Heading)
                assert isinstance(next_node, Heading)
                enriched.append(
                    replace(
                        node,
                        level=next_node.level,
                        text=f"{node.text.strip()} — {next_node.text.strip()}",
                    )
                )
                index += 2
                continue

            enriched.append(node)
            index += 1

        if tuple(enriched) == document.nodes:
            return document
        return ParsedDocument(nodes=tuple(enriched))

    @staticmethod
    def _can_compose(node: DocumentNode, next_node: DocumentNode | None) -> bool:
        if not isinstance(node, Heading) or not isinstance(next_node, Heading):
            return False
        if (
            node.content_role is ContentRole.HEADER_FOOTER
            or next_node.content_role is ContentRole.HEADER_FOOTER
        ):
            return False
        page_number = _pdf_page(node)
        return (
            page_number is not None
            and page_number == _pdf_page(next_node)
            and _NUMBERED_CONTAINER_HEADING.fullmatch(node.text.strip()) is not None
            and _NUMBERED_CONTAINER_HEADING.fullmatch(next_node.text.strip()) is None
        )
