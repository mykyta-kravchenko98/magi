import re

import pytest

from magi.ingestion.domain import (
    ChunkContentType,
    CodeBlock,
    ContentBlockTooLargeError,
    ContentRole,
    DocumentChunker,
    Heading,
    Paragraph,
    ParsedDocument,
    SourceLocation,
    StructureAwareTokenChunker,
    TokenChunkingProfile,
    TokenCounter,
    compose_embedding_input,
)


class WordTokenCounter:
    def count_tokens(self, text: str) -> int:
        return len(re.findall(r"\S+", text))


class CharacterTokenCounter:
    def count_tokens(self, text: str) -> int:
        return len(text)


def chunk(
    *nodes: Heading | Paragraph | CodeBlock,
    target_tokens: int = 4,
    soft_max_tokens: int | None = None,
    hard_max_tokens: int | None = None,
    overlap_tokens: int = 0,
    embedding_input_max_tokens: int | None = None,
):
    soft = soft_max_tokens if soft_max_tokens is not None else target_tokens
    hard = hard_max_tokens if hard_max_tokens is not None else soft
    embedding_max = embedding_input_max_tokens if embedding_input_max_tokens is not None else hard
    return StructureAwareTokenChunker(
        WordTokenCounter(),
        TokenChunkingProfile(
            target_tokens=target_tokens,
            soft_max_tokens=soft,
            hard_max_tokens=hard,
            overlap_tokens=overlap_tokens,
            embedding_input_max_tokens=embedding_max,
        ),
    ).chunk(ParsedDocument(nodes=nodes))


@pytest.mark.parametrize(
    "overrides",
    [
        {"target_tokens": 0},
        {"target_tokens": 5, "soft_max_tokens": 4},
        {"soft_max_tokens": 6, "hard_max_tokens": 5},
        {"hard_max_tokens": 7, "embedding_input_max_tokens": 6},
        {"target_tokens": 5, "overlap_tokens": -1},
        {"target_tokens": 5, "overlap_tokens": 5},
    ],
)
def test_chunking_profile_rejects_invalid_limits(overrides: dict[str, int]) -> None:
    values = {
        "target_tokens": 4,
        "soft_max_tokens": 5,
        "hard_max_tokens": 6,
        "overlap_tokens": 1,
        "embedding_input_max_tokens": 7,
    }
    values.update(overrides)

    with pytest.raises(ValueError):
        TokenChunkingProfile(**values)


def test_chunker_keeps_a_coherent_section_within_soft_maximum() -> None:
    chunks = chunk(
        Paragraph(text="one two three"),
        Paragraph(text="four five"),
        target_tokens=4,
        soft_max_tokens=5,
        hard_max_tokens=6,
    )

    assert [item.text for item in chunks] == ["one two three\n\nfour five"]


def test_oversized_section_splits_at_paragraph_boundaries_around_target() -> None:
    chunks = chunk(
        Paragraph(text="one two three"),
        Paragraph(text="four five"),
        target_tokens=4,
        soft_max_tokens=4,
        hard_max_tokens=6,
    )

    assert [item.text for item in chunks] == ["one two three", "four five"]
    assert [item.index for item in chunks] == [0, 1]


def test_chunks_never_cross_heading_boundaries_and_heading_tokens_count() -> None:
    chunks = chunk(
        Heading(level=1, text="Chapter context"),
        Paragraph(text="one two three four"),
        Heading(level=2, text="Next"),
        Paragraph(text="ending"),
        target_tokens=4,
        soft_max_tokens=4,
        hard_max_tokens=5,
    )

    assert [item.text for item in chunks] == ["one two", "three four", "ending"]
    assert [item.heading_path for item in chunks] == [
        ("Chapter context",),
        ("Chapter context",),
        ("Chapter context", "Next"),
    ]
    assert all(
        WordTokenCounter().count_tokens(compose_embedding_input(item.heading_path, item.text)) <= 4
        for item in chunks
    )


def test_chunks_carry_role_and_never_mix_role_boundaries() -> None:
    chunks = chunk(
        Paragraph(text="preface", content_role=ContentRole.FRONT_MATTER),
        Paragraph(text="chapter", content_role=ContentRole.BODY),
        target_tokens=10,
        soft_max_tokens=10,
        hard_max_tokens=10,
    )

    assert [item.text for item in chunks] == ["preface", "chapter"]
    assert [item.content_role for item in chunks] == [
        ContentRole.FRONT_MATTER,
        ContentRole.BODY,
    ]


def test_in_limit_code_is_atomic_and_can_form_a_mixed_chunk() -> None:
    chunks = chunk(
        Paragraph(text="intro"),
        CodeBlock(text="x = 1"),
        target_tokens=4,
        soft_max_tokens=4,
        hard_max_tokens=5,
    )

    assert len(chunks) == 1
    assert chunks[0].text == "intro\n\nx = 1"
    assert chunks[0].content_type is ChunkContentType.MIXED


def test_code_above_hard_maximum_remains_atomic_up_to_embedding_limit() -> None:
    chunks = chunk(
        CodeBlock(text="one two three four five"),
        target_tokens=3,
        soft_max_tokens=3,
        hard_max_tokens=4,
        embedding_input_max_tokens=5,
    )

    assert [item.text for item in chunks] == ["one two three four five"]
    assert chunks[0].content_type is ChunkContentType.CODE

    with pytest.raises(ContentBlockTooLargeError, match="6 tokens; safety limit is 5"):
        chunk(
            CodeBlock(text="one two three four five six"),
            target_tokens=3,
            soft_max_tokens=3,
            hard_max_tokens=4,
            embedding_input_max_tokens=5,
        )


def test_oversized_prose_prefers_sentence_then_word_boundaries() -> None:
    chunks = chunk(
        Paragraph(text="First sentence. Second sentence has several words."),
        target_tokens=4,
        soft_max_tokens=4,
        hard_max_tokens=5,
    )

    assert [item.text for item in chunks] == [
        "First sentence.",
        "Second sentence has several",
        "words.",
    ]


def test_oversized_unbroken_prose_uses_hard_character_fallback() -> None:
    chunks = StructureAwareTokenChunker(
        CharacterTokenCounter(),
        TokenChunkingProfile(
            target_tokens=4,
            soft_max_tokens=4,
            hard_max_tokens=5,
            overlap_tokens=0,
            embedding_input_max_tokens=6,
        ),
    ).chunk(ParsedDocument(nodes=(Paragraph(text="abcdefgh"),)))

    assert [item.text for item in chunks] == ["abcd", "efgh"]


def test_overlap_is_applied_only_to_pieces_of_one_oversized_paragraph() -> None:
    chunks = chunk(
        Paragraph(text="alpha bravo charlie delta echo foxtrot golf"),
        Paragraph(text="next"),
        target_tokens=4,
        soft_max_tokens=4,
        hard_max_tokens=5,
        overlap_tokens=1,
    )

    copied_word = chunks[0].text.split()[-1]
    assert chunks[1].text.startswith(f"{copied_word} ")
    assert chunks[-1].text == "next"
    assert all(WordTokenCounter().count_tokens(item.text) <= 4 for item in chunks)


def test_chunk_source_span_covers_all_packed_nodes() -> None:
    chunks = chunk(
        Paragraph(text="first", source_location=SourceLocation(line_start=2, line_end=3)),
        Paragraph(text="second", source_location=SourceLocation(line_start=7, line_end=8)),
        target_tokens=10,
        soft_max_tokens=10,
        hard_max_tokens=10,
    )

    assert (chunks[0].source_line_start, chunks[0].source_line_end) == (2, 8)


def test_chunking_is_deterministic_and_does_not_mutate_input() -> None:
    document = ParsedDocument(
        nodes=(Heading(level=1, text="Title"), Paragraph(text="one two three four five"))
    )
    chunker = StructureAwareTokenChunker(
        WordTokenCounter(),
        TokenChunkingProfile(
            target_tokens=4,
            soft_max_tokens=4,
            hard_max_tokens=5,
            overlap_tokens=1,
            embedding_input_max_tokens=6,
        ),
    )

    first = chunker.chunk(document)
    second = chunker.chunk(document)

    assert first == second
    assert document.nodes[1].text == "one two three four five"


def test_token_chunker_and_counter_satisfy_domain_interfaces() -> None:
    counter: TokenCounter = WordTokenCounter()
    chunker: DocumentChunker = StructureAwareTokenChunker(counter)

    assert chunker is not None
