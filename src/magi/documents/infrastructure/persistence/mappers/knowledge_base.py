"""Knowledge base domain-to-ORM mappings."""

from magi.documents.domain import KnowledgeBase
from magi.documents.infrastructure.persistence.models import KnowledgeBaseRow


def knowledge_base_to_row(knowledge_base: KnowledgeBase) -> KnowledgeBaseRow:
    return KnowledgeBaseRow(
        id=knowledge_base.id,
        name=knowledge_base.name,
        status=knowledge_base.status,
    )


def knowledge_base_from_row(row: KnowledgeBaseRow) -> KnowledgeBase:
    return KnowledgeBase(id=row.id, name=row.name, status=row.status)
