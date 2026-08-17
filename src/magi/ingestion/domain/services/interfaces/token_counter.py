"""Contract for the tokenizer pinned to the active embedding profile."""

from typing import Protocol


class TokenCounter(Protocol):
    """Count model tokens without exposing a tokenizer SDK to the domain."""

    def count_tokens(self, text: str) -> int: ...
