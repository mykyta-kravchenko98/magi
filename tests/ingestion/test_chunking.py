import pytest

from magi.ingestion.domain import (
    CharacterChunkingConfig,
    ChunkContentType,
    CodeBlock,
    ContentBlockTooLargeError,
    DocumentChunker,
    Heading,
    Paragraph,
    ParsedDocument,
    SourceLocation,
    StructureAwareCharacterChunker,
)


def chunk(
    *nodes: Heading | Paragraph | CodeBlock,
    max_chars: int = 20,
    overlap_chars: int = 0,
):
    return StructureAwareCharacterChunker(
        CharacterChunkingConfig(max_chars=max_chars, overlap_chars=overlap_chars)
    ).chunk(ParsedDocument(nodes=nodes))


@pytest.mark.parametrize(
    ("max_chars", "overlap_chars"),
    [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)],
)
def test_chunking_config_rejects_invalid_limits(max_chars: int, overlap_chars: int) -> None:
    with pytest.raises(ValueError):
        CharacterChunkingConfig(max_chars=max_chars, overlap_chars=overlap_chars)


def test_chunker_packs_paragraphs_up_to_the_exact_limit() -> None:
    chunks = chunk(Paragraph(text="12345"), Paragraph(text="678"), max_chars=10)

    assert [item.text for item in chunks] == ["12345\n\n678"]
    assert chunks[0].content_type is ChunkContentType.TEXT


def test_chunker_splits_at_paragraph_boundary_before_exceeding_limit() -> None:
    chunks = chunk(Paragraph(text="12345"), Paragraph(text="6789"), max_chars=10)

    assert [item.text for item in chunks] == ["12345", "6789"]
    assert [item.index for item in chunks] == [0, 1]


def test_chunks_never_cross_heading_boundaries_and_track_hierarchy() -> None:
    chunks = chunk(
        Heading(level=1, text="Chapter"),
        Paragraph(text="intro"),
        Heading(level=3, text="Deep"),
        Paragraph(text="details"),
        Heading(level=2, text="Next"),
        Paragraph(text="ending"),
        max_chars=100,
    )

    assert [item.text for item in chunks] == ["intro", "details", "ending"]
    assert [item.heading_path for item in chunks] == [
        ("Chapter",),
        ("Chapter", "Deep"),
        ("Chapter", "Next"),
    ]


def test_code_is_atomic_and_can_form_a_mixed_chunk() -> None:
    chunks = chunk(Paragraph(text="intro"), CodeBlock(text="x = 1"), max_chars=20)

    assert len(chunks) == 1
    assert chunks[0].text == "intro\n\nx = 1"
    assert chunks[0].content_type is ChunkContentType.MIXED


def test_code_at_exact_limit_is_allowed_but_oversized_code_fails() -> None:
    assert chunk(CodeBlock(text="x" * 10), max_chars=10)[0].content_type is ChunkContentType.CODE

    with pytest.raises(ContentBlockTooLargeError, match="11 characters; limit is 10"):
        chunk(CodeBlock(text="x" * 11), max_chars=10)


def test_oversized_prose_prefers_sentence_then_word_boundaries() -> None:
    chunks = chunk(
        Paragraph(text="First sentence. Second sentence has several words."),
        max_chars=30,
    )

    assert [item.text for item in chunks] == [
        "First sentence.",
        "Second sentence has several",
        "words.",
    ]
    assert all(len(item.text) <= 30 for item in chunks)


def test_overlap_is_applied_only_to_pieces_of_one_oversized_paragraph() -> None:
    chunks = chunk(
        Paragraph(text="alpha bravo charlie delta echo foxtrot"),
        Paragraph(text="next"),
        max_chars=20,
        overlap_chars=8,
    )

    copied_word = chunks[0].text.split()[-1]
    assert chunks[1].text.startswith(f"{copied_word} ")
    assert chunks[-1].text == "next"
    assert all(len(item.text) <= 20 for item in chunks)


def test_chunk_source_span_covers_all_packed_nodes() -> None:
    chunks = chunk(
        Paragraph(
            text="first",
            source_location=SourceLocation(line_start=2, line_end=3),
        ),
        Paragraph(
            text="second",
            source_location=SourceLocation(line_start=7, line_end=8),
        ),
        max_chars=100,
    )

    assert (chunks[0].source_line_start, chunks[0].source_line_end) == (2, 8)


def test_chunking_is_deterministic_and_does_not_mutate_input() -> None:
    document = ParsedDocument(
        nodes=(Heading(level=1, text="Title"), Paragraph(text="one two three four five"))
    )
    chunker = StructureAwareCharacterChunker(CharacterChunkingConfig(max_chars=12, overlap_chars=3))

    first = chunker.chunk(document)
    second = chunker.chunk(document)

    assert first == second
    assert document.nodes[1].text == "one two three four five"


def test_character_chunker_satisfies_domain_service_interface() -> None:
    chunker: DocumentChunker = StructureAwareCharacterChunker()

    assert chunker is not None
