import pytest

from magi.ingestion.domain import (
    CodeBlock,
    Heading,
    InvalidTextEncodingError,
    Paragraph,
    UnsupportedMediaTypeError,
)
from magi.ingestion.infrastructure import DocumentParserRegistry, MarkdownParser, TxtParser


def text_parser_registry() -> DocumentParserRegistry:
    return DocumentParserRegistry(
        parsers={
            "text/plain": TxtParser(),
            "text/markdown": MarkdownParser(),
        }
    )


def test_txt_parser_preserves_paragraph_order_and_source_lines() -> None:
    document = TxtParser().parse(b"first line\ncontinued\n\n\nsecond")

    assert document.nodes == (
        Paragraph(
            text="first line\ncontinued",
            source_location=document.nodes[0].source_location,
        ),
        Paragraph(text="second", source_location=document.nodes[1].source_location),
    )
    assert document.nodes[0].source_location is not None
    assert document.nodes[0].source_location.line_start == 1
    assert document.nodes[0].source_location.line_end == 2
    assert document.nodes[1].source_location is not None
    assert document.nodes[1].source_location.line_start == 5


def test_txt_parser_treats_whitespace_only_lines_as_boundaries() -> None:
    document = TxtParser().parse(b"alpha\n \t\nbeta\n")

    assert [node.text for node in document.nodes] == ["alpha", "beta"]


def test_text_parser_ignores_an_optional_utf8_byte_order_mark() -> None:
    document = TxtParser().parse(b"\xef\xbb\xbfalpha")

    assert document.nodes[0].text == "alpha"


def test_markdown_parser_recognizes_headings_paragraphs_and_fenced_code() -> None:
    source = b"""# API #
intro
wrap

### Client
```python extra-metadata
def call():
    return 1
```
tail
"""

    document = MarkdownParser().parse(source)

    assert [type(node) for node in document.nodes] == [
        Heading,
        Paragraph,
        Heading,
        CodeBlock,
        Paragraph,
    ]
    assert document.nodes[0] == Heading(
        level=1,
        text="API",
        source_location=document.nodes[0].source_location,
    )
    code = document.nodes[3]
    assert isinstance(code, CodeBlock)
    assert code.language == "python"
    assert code.text == "def call():\n    return 1"
    assert code.source_location is not None
    assert (code.source_location.line_start, code.source_location.line_end) == (6, 9)


def test_markdown_parser_accepts_tilde_fences_and_longer_closing_fence() -> None:
    document = MarkdownParser().parse(b"~~~ js\nconst x = 1;\n~~~~\n")

    assert document.nodes == (
        CodeBlock(
            text="const x = 1;",
            language="js",
            source_location=document.nodes[0].source_location,
        ),
    )


def test_markdown_parser_recognizes_setext_headings() -> None:
    document = MarkdownParser().parse(b"Main title\n==========\n\nSubtitle\n---\nbody")

    assert [type(node) for node in document.nodes] == [Heading, Heading, Paragraph]
    first, second = document.nodes[:2]
    assert isinstance(first, Heading)
    assert isinstance(second, Heading)
    assert first.level == 1
    assert first.text == "Main title"
    assert second.level == 2


def test_markdown_parser_treats_an_unclosed_fence_as_code_to_end_of_file() -> None:
    document = MarkdownParser().parse(b"```text\nvalue\n")

    assert isinstance(document.nodes[0], CodeBlock)
    assert document.nodes[0].text == "value"


@pytest.mark.parametrize("line", [b"####### not-heading", b"#not-heading", b"text # value"])
def test_markdown_parser_does_not_guess_non_headings(line: bytes) -> None:
    document = MarkdownParser().parse(line)

    assert isinstance(document.nodes[0], Paragraph)


def test_text_parser_accepts_case_insensitive_utf8_charset() -> None:
    document = text_parser_registry().parse(b"hello", "Text/Plain; Charset=UTF-8")

    assert len(document.nodes) == 1


def test_parser_registry_rejects_duplicate_or_malformed_media_types() -> None:
    parser = TxtParser()

    with pytest.raises(ValueError, match="already registered"):
        DocumentParserRegistry(parsers={"text/plain": parser, "TEXT/PLAIN": parser})
    with pytest.raises(ValueError, match="invalid parser media type"):
        DocumentParserRegistry(parsers={"pdf": parser})
    with pytest.raises(ValueError, match="at least one"):
        DocumentParserRegistry(parsers={})


@pytest.mark.parametrize(
    "media_type",
    ["application/pdf", "text/html", "text/plain; charset=latin1"],
)
def test_text_parser_rejects_unsupported_media_types(media_type: str) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        text_parser_registry().parse(b"content", media_type)


@pytest.mark.parametrize("parser", [TxtParser(), MarkdownParser()])
def test_text_parsers_reject_invalid_utf8(parser: TxtParser | MarkdownParser) -> None:
    with pytest.raises(InvalidTextEncodingError) as raised:
        parser.parse(b"\xff")

    assert str(raised.value) == "text content must be valid UTF-8"
