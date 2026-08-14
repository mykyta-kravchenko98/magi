"""Immutable configuration for character-based chunking."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class CharacterChunkingConfig:
    max_chars: int = 2_000
    overlap_chars: int = 200

    def __post_init__(self) -> None:
        if self.max_chars < 1:
            raise ValueError("max_chars must be positive")
        if not 0 <= self.overlap_chars < self.max_chars:
            raise ValueError("overlap_chars must be non-negative and smaller than max_chars")
