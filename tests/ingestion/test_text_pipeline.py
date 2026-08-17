import re

import pytest

from magi.ingestion.application import IndexingContentPolicy, TextDocumentPipeline
from magi.ingestion.domain import (
    ChunkContentType,
    DeterministicDocumentNormalizer,
    DeterministicDocumentRoleClassifier,
    DeterministicDocumentStructureEnricher,
    NoTextContentError,
    StructureAwareTokenChunker,
    TokenChunkingProfile,
)
from magi.ingestion.infrastructure import DocumentParserRegistry, MarkdownParser, TxtParser


def text_parser_registry() -> DocumentParserRegistry:
    return DocumentParserRegistry(
        parsers={
            "text/plain": TxtParser(),
            "text/markdown": MarkdownParser(),
        }
    )


class WordTokenCounter:
    def count_tokens(self, text: str) -> int:
        return len(re.findall(r"\S+", text))


def token_chunker(
    *, target_tokens: int = 600, overlap_tokens: int = 80
) -> StructureAwareTokenChunker:
    return StructureAwareTokenChunker(
        WordTokenCounter(),
        TokenChunkingProfile(
            target_tokens=target_tokens,
            soft_max_tokens=target_tokens,
            hard_max_tokens=target_tokens,
            overlap_tokens=overlap_tokens,
            embedding_input_max_tokens=target_tokens,
        ),
    )


def test_markdown_pipeline_runs_parse_normalize_chunk_end_to_end() -> None:
    pipeline = TextDocumentPipeline(
        parser=text_parser_registry(),
        normalizer=DeterministicDocumentNormalizer(),
        structure_enricher=DeterministicDocumentStructureEnricher(),
        role_classifier=DeterministicDocumentRoleClassifier(),
        indexing_policy=IndexingContentPolicy(),
        chunker=token_chunker(target_tokens=30, overlap_tokens=0),
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
        structure_enricher=DeterministicDocumentStructureEnricher(),
        role_classifier=DeterministicDocumentRoleClassifier(),
        indexing_policy=IndexingContentPolicy(),
        chunker=token_chunker(target_tokens=2, overlap_tokens=0),
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
            structure_enricher=DeterministicDocumentStructureEnricher(),
            role_classifier=DeterministicDocumentRoleClassifier(),
            indexing_policy=IndexingContentPolicy(),
            chunker=token_chunker(),
        ).process(content, media_type)
