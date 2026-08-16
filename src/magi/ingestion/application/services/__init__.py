"""Ingestion application services."""

from magi.ingestion.application.services.document_embedding import DocumentEmbeddingService
from magi.ingestion.application.services.text_document_pipeline import TextDocumentPipeline

__all__ = ["DocumentEmbeddingService", "TextDocumentPipeline"]
