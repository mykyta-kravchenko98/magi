import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from magi.documents.domain import (
    Document,
    DocumentAddition,
    DocumentAdditionStatus,
    DocumentVersion,
    DocumentVersionStatus,
    SearchProjection,
    SourceFileMetadata,
)
from magi.documents.infrastructure.persistence.models import (
    DocumentAdditionRow,
    DocumentRow,
    DocumentVersionRow,
)
from magi.documents.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from magi.shared.config import Settings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("MAGI_RUN_INTEGRATION_TESTS", "").lower() != "true",
        reason="set MAGI_RUN_INTEGRATION_TESTS=true to use external services",
    ),
]

KNOWLEDGE_BASE_ID = UUID("c87d83a0-eac5-4a2c-9b7d-31fbdce39f51")


async def test_documents_repository_round_trip() -> None:
    engine = create_async_engine(Settings().database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    addition_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()

    try:
        async with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
            knowledge_base = await unit_of_work.knowledge_bases.get(KNOWLEDGE_BASE_ID)
            assert knowledge_base is not None

            addition = DocumentAddition(
                id=addition_id,
                knowledge_base_id=knowledge_base.id,
                source_file=SourceFileMetadata(
                    original_filename="architecture.md",
                    media_type="text/markdown",
                    size_bytes=256,
                ),
            )
            await unit_of_work.document_additions.add(addition)
            await unit_of_work.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
            addition = await unit_of_work.document_additions.get(addition_id)
            assert addition is not None
            addition.start_processing("sources/integration/architecture.md")
            await unit_of_work.document_additions.save(addition)
            await unit_of_work.documents.add(
                Document(
                    id=document_id,
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    created_from_addition_id=addition_id,
                    display_name="Architecture",
                )
            )
            await unit_of_work.document_versions.add(
                DocumentVersion(
                    id=version_id,
                    document_id=document_id,
                    created_from_addition_id=addition_id,
                )
            )
            await unit_of_work.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
            addition = await unit_of_work.document_additions.get(addition_id)
            version = await unit_of_work.document_versions.get(version_id)
            assert addition is not None
            assert version is not None
            version.mark_searchable(
                SearchProjection(reference="magi-document-chunks", indexed_chunk_count=3)
            )
            addition.complete(document_id=document_id, document_version_id=version_id)
            await unit_of_work.document_versions.save(version)
            await unit_of_work.document_additions.save(addition)
            await unit_of_work.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
            restored_addition = await unit_of_work.document_additions.get(addition_id)
            restored_version = await unit_of_work.document_versions.get(version_id)

        assert restored_addition is not None
        assert restored_addition.status is DocumentAdditionStatus.COMPLETED
        assert restored_addition.document_id == document_id
        assert restored_version is not None
        assert restored_version.status is DocumentVersionStatus.SEARCHABLE
        assert restored_version.projection == SearchProjection(
            reference="magi-document-chunks",
            indexed_chunk_count=3,
        )
    finally:
        async with session_factory() as session:
            await session.execute(
                delete(DocumentVersionRow).where(DocumentVersionRow.id == version_id)
            )
            await session.execute(delete(DocumentRow).where(DocumentRow.id == document_id))
            await session.execute(
                delete(DocumentAdditionRow).where(DocumentAdditionRow.id == addition_id)
            )
            await session.commit()
        await engine.dispose()
