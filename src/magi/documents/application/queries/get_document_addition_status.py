"""Read the persisted public status of a document addition."""

from dataclasses import dataclass
from uuid import UUID

from magi.documents.application.errors import DocumentAdditionNotFoundError
from magi.documents.application.interfaces import UnitOfWorkFactory
from magi.documents.application.models import DocumentAdditionView


@dataclass(frozen=True, slots=True, kw_only=True)
class GetDocumentAdditionStatusQuery:
    document_addition_id: UUID


class GetDocumentAdditionStatusHandler:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(
        self,
        query: GetDocumentAdditionStatusQuery,
    ) -> DocumentAdditionView:
        async with self._unit_of_work_factory() as unit_of_work:
            addition = await unit_of_work.document_additions.get(query.document_addition_id)
            if addition is None:
                raise DocumentAdditionNotFoundError("document addition not found")
            version = (
                await unit_of_work.document_versions.get(addition.document_version_id)
                if addition.document_version_id is not None
                else None
            )
            return DocumentAdditionView(
                document_addition_id=addition.id,
                status=addition.status,
                document_id=addition.document_id,
                document_version_id=addition.document_version_id,
                document_version_status=version.status if version is not None else None,
                indexed_chunk_count=(
                    version.projection.indexed_chunk_count
                    if version is not None and version.projection is not None
                    else None
                ),
                failure=addition.failure,
            )
