"""Vector index errors owned by the retrieval application."""


class VectorIndexError(Exception):
    """A vector index operation could not be completed."""


class VectorIndexUnavailableError(VectorIndexError):
    """The vector database was unavailable or returned a transport failure."""


class VectorIndexConfigurationError(VectorIndexError):
    """The existing collection is incompatible with the configured projection."""


class VectorPointInvalidError(VectorIndexError):
    """A point is incompatible with the configured vector collection."""
