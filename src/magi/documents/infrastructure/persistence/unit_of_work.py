"""SQLAlchemy unit of work for the documents context."""

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from magi.documents.infrastructure.persistence.repositories import (
    SqlAlchemyDocumentAdditionRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentVersionRepository,
    SqlAlchemyKnowledgeBaseRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._knowledge_bases: SqlAlchemyKnowledgeBaseRepository | None = None
        self._document_additions: SqlAlchemyDocumentAdditionRepository | None = None
        self._documents: SqlAlchemyDocumentRepository | None = None
        self._document_versions: SqlAlchemyDocumentVersionRepository | None = None

    @property
    def knowledge_bases(self) -> SqlAlchemyKnowledgeBaseRepository:
        if self._knowledge_bases is None:
            raise RuntimeError("unit of work has not been entered")
        return self._knowledge_bases

    @property
    def document_additions(self) -> SqlAlchemyDocumentAdditionRepository:
        if self._document_additions is None:
            raise RuntimeError("unit of work has not been entered")
        return self._document_additions

    @property
    def documents(self) -> SqlAlchemyDocumentRepository:
        if self._documents is None:
            raise RuntimeError("unit of work has not been entered")
        return self._documents

    @property
    def document_versions(self) -> SqlAlchemyDocumentVersionRepository:
        if self._document_versions is None:
            raise RuntimeError("unit of work has not been entered")
        return self._document_versions

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        if self._session is not None:
            raise RuntimeError("unit of work cannot be entered twice")
        self._session = self._session_factory()
        self._knowledge_bases = SqlAlchemyKnowledgeBaseRepository(self._session)
        self._document_additions = SqlAlchemyDocumentAdditionRepository(self._session)
        self._documents = SqlAlchemyDocumentRepository(self._session)
        self._document_versions = SqlAlchemyDocumentVersionRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        del exc_value, traceback
        session = self._require_session()
        try:
            if exc_type is not None:
                await session.rollback()
        finally:
            await session.close()
            self._session = None
            self._knowledge_bases = None
            self._document_additions = None
            self._documents = None
            self._document_versions = None
        return None

    async def commit(self) -> None:
        await self._require_session().commit()

    async def rollback(self) -> None:
        await self._require_session().rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("unit of work has not been entered")
        return self._session
