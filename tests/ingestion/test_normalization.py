import pytest

from magi.ingestion.domain import (
    CodeBlock,
    ContentRole,
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


def test_normalizer_dehyphenates_pdf_line_breaks_and_preserves_known_compounds() -> None:
    first_page = SourceLocation(page_number=1)
    second_page = SourceLocation(page_number=2)
    document = ParsedDocument(
        nodes=(
            Paragraph(
                text="Domain-driven design is a known compound.",
                source_location=first_page,
            ),
            Paragraph(
                text="A represen-\ntation remains Domain-\ndriven.",
                source_location=second_page,
            ),
            Paragraph(
                text="Бизнес-\nценности важны.",  # noqa: RUF001
                source_location=second_page,
            ),
        )
    )

    normalized = DeterministicDocumentNormalizer().normalize(document)

    assert normalized.nodes == (
        Paragraph(
            text="Domain-driven design is a known compound.",
            source_location=first_page,
        ),
        Paragraph(
            text="A representation remains Domain-driven.",
            source_location=second_page,
        ),
        Paragraph(
            text="Бизнес-ценности важны.",
            source_location=second_page,
        ),
    )


def test_normalizer_repairs_inline_pdf_split_when_joined_form_is_confirmed() -> None:
    first_page = SourceLocation(page_number=1)
    second_page = SourceLocation(page_number=2)
    document = ParsedDocument(
        nodes=(
            Paragraph(
                text="DDD пред-ставляет собой набор методов.",
                source_location=first_page,
            ),
            Paragraph(
                text="Автор представляет другой пример.",
                source_location=second_page,
            ),
            Paragraph(
                text="Client-server remains a real compound.",
                source_location=second_page,
            ),
        )
    )

    normalized = DeterministicDocumentNormalizer().normalize(document)

    assert normalized.nodes == (
        Paragraph(
            text="DDD представляет собой набор методов.",
            source_location=first_page,
        ),
        Paragraph(
            text="Автор представляет другой пример.",
            source_location=second_page,
        ),
        Paragraph(
            text="Client-server remains a real compound.",
            source_location=second_page,
        ),
    )


def test_normalizer_repairs_pdf_words_split_across_nodes_and_page_furniture() -> None:
    first_page = SourceLocation(page_number=1)
    second_page = SourceLocation(page_number=2)
    document = ParsedDocument(
        nodes=(
            Paragraph(text="Для этого было проведе-", source_location=first_page),
            Paragraph(
                text="2",
                source_location=first_page,
                content_role=ContentRole.FOOTNOTE,
            ),
            Paragraph(
                text="но множество исследований. Причина исследова-",
                source_location=first_page,
            ),
            Paragraph(
                text="Текст сноски.",
                source_location=first_page,
                content_role=ContentRole.FOOTNOTE,
            ),
            Paragraph(
                text="2 | Вступление",
                source_location=second_page,
                content_role=ContentRole.HEADER_FOOTER,
            ),
            Paragraph(text="телям известна.", source_location=second_page),
        )
    )

    normalized = DeterministicDocumentNormalizer().normalize(document)

    assert normalized.nodes == (
        Paragraph(text="Для этого было", source_location=first_page),
        Paragraph(
            text="2",
            source_location=first_page,
            content_role=ContentRole.FOOTNOTE,
        ),
        Paragraph(
            text="проведено множество исследований. Причина",
            source_location=first_page,
        ),
        Paragraph(
            text="Текст сноски.",
            source_location=first_page,
            content_role=ContentRole.FOOTNOTE,
        ),
        Paragraph(
            text="2 | Вступление",
            source_location=second_page,
            content_role=ContentRole.HEADER_FOOTER,
        ),
        Paragraph(text="исследователям известна.", source_location=second_page),
    )


def test_normalizer_does_not_dehyphenate_non_pdf_line_breaks() -> None:
    location = SourceLocation(line_start=1, line_end=2)
    document = ParsedDocument(
        nodes=(Paragraph(text="author-provided-\nbreak", source_location=location),)
    )

    normalized = DeterministicDocumentNormalizer().normalize(document)

    assert normalized.nodes == (Paragraph(text="author-provided- break", source_location=location),)


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
