"""Embedding provider errors owned by the ingestion application."""


class EmbeddingProviderError(Exception):
    """An embedding request could not be completed."""


class EmbeddingProviderUnavailableError(EmbeddingProviderError):
    """The embedding server was unavailable or returned a transport failure."""


class EmbeddingResponseInvalidError(EmbeddingProviderError):
    """The embedding server returned data incompatible with the configured profile."""
