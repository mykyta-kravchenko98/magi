import pytest

from magi.ingestion.application import IndexingContentPolicy
from magi.ingestion.domain import (
    ContentRole,
    DeterministicDocumentRoleClassifier,
    DeterministicDocumentStructureEnricher,
    Heading,
    NoTextContentError,
    Paragraph,
    ParsedDocument,
    SourceLocation,
)


def pdf_location(page: int) -> SourceLocation:
    return SourceLocation(page_number=page)


def test_pdf_roles_follow_toc_and_book_section_boundaries() -> None:
    document = ParsedDocument(
        nodes=(
            Paragraph(text="Copyright", source_location=pdf_location(1)),
            Heading(level=1, text="Оглавление", source_location=pdf_location(2)),
            Paragraph(text="Глава 1 ........ 10", source_location=pdf_location(2)),
            Paragraph(
                text="Sample Book | 3",
                source_location=pdf_location(3),
                content_role=ContentRole.HEADER_FOOTER,
            ),
            Heading(
                level=1,
                text="Предисловие редакторской группы",
                source_location=pdf_location(4),
            ),
            Paragraph(text="Book overview", source_location=pdf_location(4)),
            Heading(level=1, text="Глава 1. Основы", source_location=pdf_location(8)),
            Paragraph(text="Основной текст", source_location=pdf_location(8)),
        )
    )

    classified = DeterministicDocumentRoleClassifier().classify(document)

    assert [node.content_role for node in classified.nodes] == [
        ContentRole.FRONT_MATTER,
        ContentRole.TABLE_OF_CONTENTS,
        ContentRole.TABLE_OF_CONTENTS,
        ContentRole.HEADER_FOOTER,
        ContentRole.FRONT_MATTER,
        ContentRole.FRONT_MATTER,
        ContentRole.BODY,
        ContentRole.BODY,
    ]


def test_classifier_leaves_non_pdf_documents_unchanged() -> None:
    document = ParsedDocument(
        nodes=(
            Heading(level=1, text="Contents"),
            Paragraph(text="This is ordinary Markdown content."),
        )
    )

    assert DeterministicDocumentRoleClassifier().classify(document) is document


def test_pdf_structure_enricher_composes_numbered_part_and_chapter_titles() -> None:
    document = ParsedDocument(
        nodes=(
            Heading(level=3, text="ЧАСТЬ I", source_location=pdf_location(31)),
            Heading(
                level=1,
                text="Стратегическое проектирование",
                source_location=pdf_location(31),
            ),
            Paragraph(text="Введение в часть", source_location=pdf_location(31)),
            Heading(level=3, text="ГЛАВА 1", source_location=pdf_location(33)),
            Heading(
                level=2,
                text="Анализ предметной области",
                source_location=pdf_location(33),
            ),
        )
    )

    enriched = DeterministicDocumentStructureEnricher().enrich(document)

    assert [(node.level, node.text) for node in enriched.nodes if isinstance(node, Heading)] == [
        (1, "ЧАСТЬ I — Стратегическое проектирование"),
        (2, "ГЛАВА 1 — Анализ предметной области"),
    ]


def test_structure_enricher_does_not_compose_across_pages_or_without_pdf_provenance() -> None:
    document = ParsedDocument(
        nodes=(
            Heading(level=1, text="Part I"),
            Heading(level=1, text="Architecture"),
            Heading(level=1, text="Chapter 1", source_location=pdf_location(2)),
            Heading(level=1, text="Domain model", source_location=pdf_location(3)),
        )
    )

    assert DeterministicDocumentStructureEnricher().enrich(document) is document


@pytest.mark.parametrize("heading", ["Часть I", "Часть 1", "Part IV", "Part 4"])
def test_numbered_part_heading_starts_pdf_body(heading: str) -> None:
    document = ParsedDocument(
        nodes=(
            Heading(level=1, text="Оглавление", source_location=pdf_location(2)),
            Paragraph(text="Содержание", source_location=pdf_location(2)),
            Heading(level=1, text=heading, source_location=pdf_location(10)),
            Paragraph(text="Основной текст", source_location=pdf_location(10)),
        )
    )

    classified = DeterministicDocumentRoleClassifier().classify(document)

    assert [node.content_role for node in classified.nodes] == [
        ContentRole.TABLE_OF_CONTENTS,
        ContentRole.TABLE_OF_CONTENTS,
        ContentRole.BODY,
        ContentRole.BODY,
    ]


def test_default_indexing_policy_keeps_body_and_front_matter_only() -> None:
    document = ParsedDocument(
        nodes=tuple(Paragraph(text=role.value, content_role=role) for role in ContentRole)
    )

    selected = IndexingContentPolicy().select(document)

    assert [node.content_role for node in selected.nodes] == [
        ContentRole.BODY,
        ContentRole.FRONT_MATTER,
    ]


def test_indexing_policy_rejects_document_with_no_indexable_content() -> None:
    document = ParsedDocument(
        nodes=(Paragraph(text="Contents", content_role=ContentRole.TABLE_OF_CONTENTS),)
    )

    with pytest.raises(NoTextContentError, match="eligible for indexing"):
        IndexingContentPolicy().select(document)
