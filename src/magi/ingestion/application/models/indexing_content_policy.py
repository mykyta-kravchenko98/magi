"""Application policy selecting classified content for indexing."""

from dataclasses import dataclass, field

from magi.ingestion.domain import ContentRole, NoTextContentError, ParsedDocument


@dataclass(frozen=True, slots=True, kw_only=True)
class IndexingContentPolicy:
    included_roles: frozenset[ContentRole] = field(
        default_factory=lambda: frozenset({ContentRole.BODY, ContentRole.FRONT_MATTER})
    )

    def select(self, document: ParsedDocument) -> ParsedDocument:
        selected = tuple(
            node for node in document.nodes if node.content_role in self.included_roles
        )
        if not selected:
            raise NoTextContentError("document has no content eligible for indexing")
        return ParsedDocument(nodes=selected)
