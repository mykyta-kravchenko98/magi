"""Immutable token-aware chunking profile."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class TokenChunkingProfile:
    target_tokens: int = 600
    soft_max_tokens: int = 800
    hard_max_tokens: int = 1_000
    overlap_tokens: int = 80
    embedding_input_max_tokens: int = 2_048

    def __post_init__(self) -> None:
        if self.target_tokens < 1:
            raise ValueError("target_tokens must be positive")
        if not self.target_tokens <= self.soft_max_tokens:
            raise ValueError("soft_max_tokens must be at least target_tokens")
        if not self.soft_max_tokens <= self.hard_max_tokens:
            raise ValueError("hard_max_tokens must be at least soft_max_tokens")
        if not self.hard_max_tokens <= self.embedding_input_max_tokens:
            raise ValueError("embedding_input_max_tokens must be at least hard_max_tokens")
        if not 0 <= self.overlap_tokens < self.target_tokens:
            raise ValueError("overlap_tokens must be non-negative and smaller than target_tokens")
