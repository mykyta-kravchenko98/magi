"""Document domain-to-ORM mappings."""

from magi.documents.domain import Document
from magi.documents.infrastructure.persistence.models import DocumentRow


def document_to_row(document: Document) -> DocumentRow:
    return DocumentRow(
        id=document.id,
        knowledge_base_id=document.knowledge_base_id,
        created_from_addition_id=document.created_from_addition_id,
        display_name=document.display_name,
        status=document.status,
    )


def document_from_row(row: DocumentRow) -> Document:
    return Document(
        id=row.id,
        knowledge_base_id=row.knowledge_base_id,
        created_from_addition_id=row.created_from_addition_id,
        display_name=row.display_name,
        status=row.status,
    )
