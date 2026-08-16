from collections.abc import Callable
from io import BytesIO

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.pdfgen.canvas import Canvas

from magi.ingestion.application import (
    DocumentFormatParser,
    DocumentParser,
    IndexingContentPolicy,
    TextDocumentPipeline,
)
from magi.ingestion.domain import (
    CharacterChunkingConfig,
    CodeBlock,
    ContentRole,
    DeterministicDocumentNormalizer,
    DeterministicDocumentRoleClassifier,
    Heading,
    Paragraph,
    PdfEncryptedError,
    PdfNoExtractableTextError,
    PdfParsingError,
    StructureAwareCharacterChunker,
    UnsupportedMediaTypeError,
)
from magi.ingestion.infrastructure import (
    DocumentParserRegistry,
    PdfExtractionProfile,
    PdfParser,
)


def make_structured_pdf(*, encrypted: bool = False) -> bytes:
    output = BytesIO()
    encryption = StandardEncryption("secret") if encrypted else None
    pdf = Canvas(output, pagesize=letter, encrypt=encryption)

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(72, 740, "Distributed Systems")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 700, "A distributed system consists of multiple nodes that")
    pdf.drawString(72, 686, "communicate over a network and coordinate their work.")
    pdf.drawString(72, 655, "Failures are expected and must be handled explicitly.")
    pdf.drawString(72, 625, "- First capability continues on")
    pdf.drawString(84, 611, "the following visual line.")
    pdf.drawString(72, 580, "- Second capability is independent.")
    pdf.setFont("Courier", 10)
    pdf.drawString(72, 535, "def consume(event):")
    pdf.drawString(72, 522, "    return event.id")

    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, 740, "Implementation Details")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 700, "The second page retains one-based page provenance.")
    pdf.save()
    return output.getvalue()


def make_plain_pages_pdf() -> bytes:
    output = BytesIO()
    pdf = Canvas(output, pagesize=letter)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 700, "End of the first page.")
    pdf.showPage()
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 700, "Start of the second page.")
    pdf.save()
    return output.getvalue()


def make_blank_pdf() -> bytes:
    output = BytesIO()
    pdf = Canvas(output, pagesize=letter)
    pdf.rect(72, 700, 100, 20)
    pdf.showPage()
    pdf.save()
    return output.getvalue()


def make_pdf_with_empty_middle_page() -> bytes:
    output = BytesIO()
    pdf = Canvas(output, pagesize=letter)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 700, "First page text.")
    pdf.showPage()
    pdf.showPage()
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 700, "Third page text.")
    pdf.save()
    return output.getvalue()


def make_pdf_requiring_normalization() -> bytes:
    output = BytesIO()
    pdf = Canvas(output, pagesize=letter)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(72, 770, "16 | Sample Book")
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(72, 720, "Normalization for")
    pdf.drawString(72, 696, "Technical Books")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 650, "A represen-")
    pdf.drawString(72, 636, "tation should be reconstructed.")
    pdf.drawString(72, 610, "Domain-driven design is a known compound.")
    pdf.drawString(72, 30, "2024")

    pdf.showPage()
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(540, 770, "Sample Book | 17")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, 700, "Domain-")
    pdf.drawString(72, 686, "driven design keeps its lexical hyphen.")
    pdf.save()
    return output.getvalue()


def make_pdf_with_repeated_page_furniture() -> bytes:
    output = BytesIO()
    pdf = Canvas(output, pagesize=letter)
    for page_number in range(1, 3):
        pdf.setFont("Helvetica", 9)
        pdf.drawString(72, 770, "Technical Books")
        pdf.drawString(72, 30, "Confidential")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(72, 700, f"Unique body on page {page_number}.")
        pdf.showPage()
    pdf.save()
    return output.getvalue()


def test_pdf_parser_extracts_all_node_types_and_page_provenance() -> None:
    document = PdfParser().parse(make_structured_pdf())

    assert [type(node) for node in document.nodes] == [
        Heading,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        CodeBlock,
        Heading,
        Paragraph,
    ]
    first_heading = document.nodes[0]
    code = document.nodes[5]
    second_heading = document.nodes[6]
    assert isinstance(first_heading, Heading)
    assert isinstance(code, CodeBlock)
    assert isinstance(second_heading, Heading)
    assert first_heading.level == 1
    assert second_heading.level == 2
    assert code.text == "def consume(event):\n    return event.id"
    assert first_heading.source_location is not None
    assert first_heading.source_location.page_number == 1
    assert second_heading.source_location is not None
    assert second_heading.source_location.page_number == 2


def test_pdf_parser_joins_wrapped_lines_but_splits_list_items() -> None:
    document = PdfParser().parse(make_structured_pdf())
    paragraphs = [node for node in document.nodes if isinstance(node, Paragraph)]

    assert paragraphs[0].text.endswith("coordinate their work.")
    assert paragraphs[2].text == "- First capability continues on\nthe following visual line."
    assert paragraphs[3].text == "- Second capability is independent."


def test_pdf_parser_marks_page_furniture_and_merges_wrapped_headings() -> None:
    parsed = PdfParser().parse(make_pdf_requiring_normalization())

    headings = [node for node in parsed.nodes if isinstance(node, Heading)]
    paragraphs = [node for node in parsed.nodes if isinstance(node, Paragraph)]

    assert [heading.text for heading in headings] == ["Normalization for Technical Books"]
    furniture = [node for node in parsed.nodes if node.content_role is ContentRole.HEADER_FOOTER]
    assert [node.text for node in furniture] == ["16 | Sample Book", "Sample Book | 17"]
    assert any("represen-\ntation" in paragraph.text for paragraph in paragraphs)
    assert any(paragraph.text == "2024" for paragraph in paragraphs)

    normalized = DeterministicDocumentNormalizer().normalize(parsed)

    normalized_text = "\n".join(node.text for node in normalized.nodes)
    assert "representation should be reconstructed" in normalized_text
    assert "Domain-driven design keeps its lexical hyphen" in normalized_text
    assert [
        node.text for node in normalized.nodes if node.content_role is ContentRole.HEADER_FOOTER
    ] == ["16 | Sample Book", "Sample Book | 17"]


def test_pdf_parser_marks_repeated_unnumbered_headers_and_footers() -> None:
    parsed = PdfParser().parse(make_pdf_with_repeated_page_furniture())

    assert [node.text for node in parsed.nodes] == [
        "Technical Books",
        "Unique body on page 1.",
        "Confidential",
        "Technical Books",
        "Unique body on page 2.",
        "Confidential",
    ]
    assert [node.content_role for node in parsed.nodes] == [
        ContentRole.HEADER_FOOTER,
        ContentRole.BODY,
        ContentRole.HEADER_FOOTER,
        ContentRole.HEADER_FOOTER,
        ContentRole.BODY,
        ContentRole.HEADER_FOOTER,
    ]


def test_pdf_parser_is_deterministic() -> None:
    content = make_structured_pdf()
    parser = PdfParser()

    assert parser.parse(content) == parser.parse(content)


def test_pdf_parser_and_registry_satisfy_application_ports() -> None:
    format_parser: DocumentFormatParser = PdfParser()
    parser: DocumentParser = DocumentParserRegistry(parsers={"application/pdf": format_parser})

    assert parser is not None


def test_pdf_parser_preserves_order_across_empty_pages() -> None:
    document = PdfParser().parse(make_pdf_with_empty_middle_page())

    assert [node.text for node in document.nodes] == ["First page text.", "Third page text."]
    assert [
        node.source_location.page_number
        for node in document.nodes
        if node.source_location is not None
    ] == [1, 3]


def test_pdf_pipeline_can_be_composed_without_application_importing_pdfplumber() -> None:
    parser = DocumentParserRegistry(parsers={"application/pdf": PdfParser()})
    pipeline = TextDocumentPipeline(
        parser=parser,
        normalizer=DeterministicDocumentNormalizer(),
        role_classifier=DeterministicDocumentRoleClassifier(),
        indexing_policy=IndexingContentPolicy(),
        chunker=StructureAwareCharacterChunker(
            CharacterChunkingConfig(max_chars=100, overlap_chars=0)
        ),
    )

    chunks = pipeline.process(make_plain_pages_pdf(), "application/pdf")

    assert len(chunks) == 1
    assert chunks[0].text == "End of the first page.\n\nStart of the second page."
    assert (chunks[0].page_start, chunks[0].page_end) == (1, 2)


def test_pdf_media_type_does_not_accept_text_charset_parameters() -> None:
    parser = DocumentParserRegistry(parsers={"application/pdf": PdfParser()})

    with pytest.raises(UnsupportedMediaTypeError):
        parser.parse(b"not reached", "application/pdf; charset=utf-8")


def test_pdf_parser_rejects_missing_signature() -> None:
    with pytest.raises(PdfParsingError, match="signature"):
        PdfParser().parse(b"not a PDF")


def test_pdf_parser_sanitizes_malformed_pdf_errors() -> None:
    with pytest.raises(PdfParsingError, match="PDF parsing failed") as raised:
        PdfParser().parse(b"%PDF-1.7\nnot a valid container")

    assert raised.value.__cause__ is not None


def test_pdf_parser_rejects_encrypted_pdf() -> None:
    with pytest.raises(PdfEncryptedError, match="encrypted PDF"):
        PdfParser().parse(make_structured_pdf(encrypted=True))


def test_pdf_parser_rejects_image_only_or_blank_pdf() -> None:
    with pytest.raises(PdfNoExtractableTextError, match="no extractable text layer"):
        PdfParser().parse(make_blank_pdf())


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PdfExtractionProfile(line_tolerance_ratio=0),
        lambda: PdfExtractionProfile(paragraph_gap_ratio=-1),
        lambda: PdfExtractionProfile(heading_join_gap_ratio=0),
        lambda: PdfExtractionProfile(code_char_width_ratio=0),
        lambda: PdfExtractionProfile(max_heading_chars=0),
        lambda: PdfExtractionProfile(page_furniture_candidate_lines=0),
        lambda: PdfExtractionProfile(page_furniture_min_repetitions=1),
        lambda: PdfExtractionProfile(code_font_markers=()),
    ],
)
def test_pdf_profile_rejects_invalid_configuration(
    factory: Callable[[], PdfExtractionProfile],
) -> None:
    with pytest.raises(ValueError):
        factory()
