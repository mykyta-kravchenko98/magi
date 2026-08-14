import pytest

from magi.ingestion.domain import (
    CodeBlock,
    DeterministicDocumentNormalizer,
    DocumentNormalizer,
    Heading,
    NoTextContentError,
    Paragraph,
    ParsedDocument,
    SourceLocation,
)


def test_normalizer_collapses_prose_whitespace_and_composes_unicode() -> None:
    location = SourceLocation(line_start=1, line_end=2)
    document = ParsedDocument(
        nodes=(
            Heading(level=1, text="  Cafe\u0301\t guide ", source_location=location),
            Paragraph(text=" one\n\t two\u00a0three ", source_location=location),
        )
    )

    normalized = DeterministicDocumentNormalizer().normalize(document)

    assert normalized.nodes == (
        Heading(level=1, text="Caf\u00e9 guide", source_location=location),
        Paragraph(text="one two three", source_location=location),
    )


def test_normalizer_preserves_code_indentation_and_internal_blank_lines() -> None:
    document = ParsedDocument(
        nodes=(CodeBlock(text="\n\tcall()  \r\n\r\n  next()\t\n", language=" py "),)
    )

    normalized = DeterministicDocumentNormalizer().normalize(document)

    assert normalized.nodes == (CodeBlock(text="\tcall()\n\n  next()", language="py"),)


def test_normalizer_removes_empty_nodes_but_retains_nonempty_content() -> None:
    document = ParsedDocument(
        nodes=(Heading(level=1, text="  "), Paragraph(text=""), Paragraph(text="kept"))
    )

    assert DeterministicDocumentNormalizer().normalize(document).nodes == (Paragraph(text="kept"),)


@pytest.mark.parametrize(
    "nodes",
    [(), (Heading(level=1, text="Only a title"),), (Paragraph(text=" \n\t "),)],
)
def test_normalizer_rejects_documents_without_meaningful_body_text(
    nodes: tuple[Heading | Paragraph, ...],
) -> None:
    with pytest.raises(NoTextContentError):
        DeterministicDocumentNormalizer().normalize(ParsedDocument(nodes=nodes))


def test_deterministic_normalizer_satisfies_domain_service_interface() -> None:
    normalizer: DocumentNormalizer = DeterministicDocumentNormalizer()

    assert normalizer is not None
