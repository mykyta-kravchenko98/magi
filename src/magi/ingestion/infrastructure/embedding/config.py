"""Immutable TEI adapter configuration."""

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True, kw_only=True)
class TeiEmbeddingConfig:
    base_url: str
    model_id: str
    model_revision: str
    vector_dimension: int = 1_024
    batch_size: int = 16
    timeout_seconds: float = 30.0
    api_key: str | None = None

    def __post_init__(self) -> None:
        parsed_url = urlsplit(self.base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if not self.model_id.strip() or not self.model_revision.strip():
            raise ValueError("model_id and model_revision must not be blank")
        if self.vector_dimension < 1:
            raise ValueError("vector_dimension must be positive")
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
