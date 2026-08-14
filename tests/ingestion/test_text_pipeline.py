import pytest

from magi.ingestion.application import TextDocumentPipeline
from magi.ingestion.domain import (
    CharacterChunkingConfig,
    ChunkContentType,
    DeterministicDocumentNormalizer,
    NoTextContentError,
    StructureAwareCharacterChunker,
)
from magi.ingestion.infrastructure import DocumentParserRegistry, MarkdownParser, TxtParser


def text_parser_registry() -> DocumentParserRegistry:
    return DocumentParserRegistry(
        parsers={
            "text/plain": TxtParser(),
            "text/markdown": MarkdownParser(),
        }
    )


def character_chunker(
    *, max_chars: int = 2_000, overlap_chars: int = 200
) -> StructureAwareCharacterChunker:
    return StructureAwareCharacterChunker(
        CharacterChunkingConfig(max_chars=max_chars, overlap_chars=overlap_chars)
    )


def test_markdown_pipeline_runs_parse_normalize_chunk_end_to_end() -> None:
    pipeline = TextDocumentPipeline(
        parser=text_parser_registry(),
        normalizer=DeterministicDocumentNormalizer(),
        chunker=character_chunker(max_chars=30, overlap_chars=0),
    )

    chunks = pipeline.process(
        "# Héading\r\n\r\n  prose\tvalue  \r\n\r\n```py\r\nprint(1)  \r\n```".encode(),
        "text/markdown; charset=utf-8",
    )

    assert [item.text for item in chunks] == ["prose value\n\nprint(1)"]
    assert chunks[0].heading_path == ("Héading",)
    assert chunks[0].content_type is ChunkContentType.MIXED


def test_txt_pipeline_uses_supplied_chunking_configuration() -> None:
    pipeline = TextDocumentPipeline(
        parser=text_parser_registry(),
        normalizer=DeterministicDocumentNormalizer(),
        chunker=character_chunker(max_chars=8, overlap_chars=0),
    )

    chunks = pipeline.process(b"one two three", "text/plain")

    assert [item.text for item in chunks] == ["one two", "three"]


@pytest.mark.parametrize("content", [b"", b" \n\t", b"# heading only"])
def test_pipeline_rejects_empty_normalized_documents(content: bytes) -> None:
    media_type = "text/markdown" if content.startswith(b"#") else "text/plain"

    with pytest.raises(NoTextContentError):
        TextDocumentPipeline(
            parser=text_parser_registry(),
            normalizer=DeterministicDocumentNormalizer(),
            chunker=character_chunker(),
        ).process(content, media_type)
