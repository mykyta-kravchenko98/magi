"""Internal sentence/word/character fallback for oversized prose."""

import re
from collections.abc import Callable

from magi.ingestion.domain.errors import ContentBlockTooLargeError
from magi.ingestion.domain.services.interfaces.token_counter import TokenCounter
from magi.ingestion.domain.value_objects import TokenChunkingProfile, compose_embedding_input

_SENTENCE_BOUNDARY = re.compile(r"[.!?\u2026\u3002\uff01\uff1f](?:[\"')\]]*)(?=\s|$)")
_WORD_BOUNDARY = re.compile(r"\S+(?:\s+|$)")


class TokenAwareProseSplitter:
    def __init__(self, token_counter: TokenCounter, profile: TokenChunkingProfile) -> None:
        self._token_counter = token_counter
        self._profile = profile

    def split(self, text: str, heading_path: tuple[str, ...]) -> tuple[str, ...]:
        pieces: list[str] = []
        cursor = 0
        previous_core = ""
        while cursor < len(text):
            overlap = self._overlap_suffix(previous_core)
            end = self._choose_end(text, cursor, overlap, heading_path)
            core = text[cursor:end].strip()
            if not core:
                raise ContentBlockTooLargeError("prose cannot make progress within token limit")
            pieces.append(f"{overlap} {core}" if overlap else core)
            previous_core = core
            cursor = end
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
        return tuple(pieces)

    def _choose_end(
        self,
        text: str,
        cursor: int,
        overlap: str,
        heading_path: tuple[str, ...],
    ) -> int:
        def fits(end: int) -> bool:
            core = text[cursor:end].strip()
            piece = f"{overlap} {core}" if overlap else core
            return self._count(heading_path, piece) <= self._profile.target_tokens

        if fits(len(text)):
            return len(text)

        sentence_ends = [
            match.end()
            for match in _SENTENCE_BOUNDARY.finditer(text, cursor)
            if match.end() > cursor
        ]
        sentence_end = self._last_fitting(sentence_ends, fits)
        if sentence_end is not None:
            return sentence_end

        word_ends = [
            match.end() for match in _WORD_BOUNDARY.finditer(text, cursor) if match.end() > cursor
        ]
        word_end = self._last_fitting(word_ends, fits)
        if word_end is not None:
            return word_end

        low = cursor + 1
        high = len(text)
        best: int | None = None
        while low <= high:
            middle = (low + high) // 2
            if fits(middle):
                best = middle
                low = middle + 1
            else:
                high = middle - 1
        if best is not None:
            return best

        token_count = self._count(heading_path, text[cursor : cursor + 1])
        raise ContentBlockTooLargeError(
            "heading path leaves no room for prose: "
            f"minimum input has {token_count} tokens; "
            f"target is {self._profile.target_tokens}"
        )

    @staticmethod
    def _last_fitting(boundaries: list[int], fits: Callable[[int], bool]) -> int | None:
        best: int | None = None
        for boundary in boundaries:
            if fits(boundary):
                best = boundary
        return best

    def _overlap_suffix(self, text: str) -> str:
        if not text or self._profile.overlap_tokens == 0:
            return ""
        starts = [match.start() for match in re.finditer(r"\S+", text)]
        best = ""
        for start in reversed(starts):
            suffix = text[start:].strip()
            if self._token_counter.count_tokens(suffix) > self._profile.overlap_tokens:
                break
            best = suffix
        return best

    def _count(self, heading_path: tuple[str, ...], text: str) -> int:
        return self._token_counter.count_tokens(compose_embedding_input(heading_path, text))
