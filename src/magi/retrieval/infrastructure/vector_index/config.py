"""Immutable Qdrant adapter configuration."""

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

type QdrantDistance = Literal["Cosine", "Dot", "Euclid", "Manhattan"]

_COLLECTION_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True, slots=True, kw_only=True)
class QdrantVectorIndexConfig:
    base_url: str
    collection_name: str
    vector_dimension: int = 1_024
    distance: QdrantDistance = "Cosine"
    batch_size: int = 64
    timeout_seconds: float = 10.0
    api_key: str | None = None

    def __post_init__(self) -> None:
        parsed_url = urlsplit(self.base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if not _COLLECTION_NAME_PATTERN.fullmatch(self.collection_name):
            raise ValueError(
                "collection_name may contain only letters, digits, dot, underscore, and dash"
            )
        if self.vector_dimension < 1:
            raise ValueError("vector_dimension must be positive")
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
