"""Concrete dependency composition for the walking skeleton."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from magi.documents.application import (
    GetDocumentAdditionStatusHandler,
    UploadDocumentHandler,
)
from magi.documents.infrastructure import MinioObjectStorage, create_minio_client
from magi.documents.infrastructure.persistence import SqlAlchemyUnitOfWork
from magi.ingestion.application import (
    DocumentEmbeddingService,
    IndexingContentPolicy,
    TextDocumentPipeline,
)
from magi.ingestion.domain import (
    CharacterChunkingConfig,
    DeterministicDocumentNormalizer,
    DeterministicDocumentRoleClassifier,
    StructureAwareCharacterChunker,
)
from magi.ingestion.infrastructure import (
    DocumentParserRegistry,
    MarkdownParser,
    PdfParser,
    TeiEmbeddingConfig,
    TeiEmbeddingProvider,
    TxtParser,
)
from magi.retrieval.application import DocumentVersionIndexingService
from magi.retrieval.infrastructure import QdrantVectorIndex, QdrantVectorIndexConfig
from magi.shared.config import EmbeddingSettings, QdrantSettings, Settings


@dataclass(frozen=True, slots=True)
class ApplicationRuntime:
    upload_document_handler: UploadDocumentHandler
    document_addition_status_handler: GetDocumentAdditionStatusHandler
    embedding_provider: TeiEmbeddingProvider
    vector_index: QdrantVectorIndex

    async def aclose(self) -> None:
        await self.embedding_provider.aclose()
        await self.vector_index.aclose()


def create_application_runtime(
    *,
    settings: Settings,
    embedding_settings: EmbeddingSettings,
    qdrant_settings: QdrantSettings,
    engine: AsyncEngine,
) -> ApplicationRuntime:
    if embedding_settings.vector_dimension != qdrant_settings.vector_dimension:
        raise ValueError("embedding and Qdrant vector dimensions must match")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    def unit_of_work_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    parser = DocumentParserRegistry(
        parsers={
            "application/pdf": PdfParser(),
            "text/markdown": MarkdownParser(),
            "text/plain": TxtParser(),
        }
    )
    content_pipeline = TextDocumentPipeline(
        parser=parser,
        normalizer=DeterministicDocumentNormalizer(),
        role_classifier=DeterministicDocumentRoleClassifier(),
        indexing_policy=IndexingContentPolicy(),
        chunker=StructureAwareCharacterChunker(
            CharacterChunkingConfig(
                max_chars=settings.chunk_max_chars,
                overlap_chars=settings.chunk_overlap_chars,
            )
        ),
    )
    embedding_provider = TeiEmbeddingProvider(
        TeiEmbeddingConfig(
            base_url=embedding_settings.base_url,
            model_id=embedding_settings.model_id,
            model_revision=embedding_settings.model_revision,
            vector_dimension=embedding_settings.vector_dimension,
            batch_size=embedding_settings.batch_size,
            timeout_seconds=embedding_settings.timeout_seconds,
            api_key=(
                embedding_settings.api_key.get_secret_value()
                if embedding_settings.api_key is not None
                else None
            ),
        )
    )
    vector_index = QdrantVectorIndex(
        QdrantVectorIndexConfig(
            base_url=qdrant_settings.url,
            collection_name=qdrant_settings.collection,
            vector_dimension=qdrant_settings.vector_dimension,
            batch_size=qdrant_settings.batch_size,
            timeout_seconds=qdrant_settings.timeout_seconds,
            api_key=(
                qdrant_settings.api_key.get_secret_value()
                if qdrant_settings.api_key is not None
                else None
            ),
        )
    )
    status_query_handler = GetDocumentAdditionStatusHandler(unit_of_work_factory)
    upload_handler = UploadDocumentHandler(
        unit_of_work_factory=unit_of_work_factory,
        object_storage=MinioObjectStorage(
            create_minio_client(settings),
            settings.object_storage_bucket,
        ),
        content_pipeline=content_pipeline,
        document_embedder=DocumentEmbeddingService(embedding_provider),
        document_version_indexer=DocumentVersionIndexingService(vector_index),
        status_query_handler=status_query_handler,
        max_upload_bytes=settings.max_upload_bytes,
    )
    return ApplicationRuntime(
        upload_document_handler=upload_handler,
        document_addition_status_handler=status_query_handler,
        embedding_provider=embedding_provider,
        vector_index=vector_index,
    )
