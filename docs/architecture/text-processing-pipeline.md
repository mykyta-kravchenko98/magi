# TXT/Markdown/PDF processing pipeline

The transport- and provider-independent ingestion pipeline is implemented in `magi.ingestion`:

```text
source bytes -> parse -> normalize -> enrich structure -> classify roles
             -> select indexable nodes -> character chunking -> DocumentChunk[]
```

Domain and application code deliberately have no imports from FastAPI, Pydantic, SQLAlchemy,
MinIO, an embedding provider, Qdrant, or a PDF SDK. The `pdfplumber` dependency is isolated in
`ingestion.infrastructure.parsers.pdf`. The public pipeline accepts the `DocumentParser` port, so
all format adapters are supplied at composition time. Individual stages remain public and
testable.

## Supported input

- `text/plain`: strict UTF-8 split into blank-line-delimited paragraphs;
- `text/markdown`: strict UTF-8 with ATX/Setext headings and backtick or tilde fenced code
  blocks preserved as structure;
- `application/pdf`: born-digital PDF with an embedded text layer; ordered layout words are
  classified conservatively as headings, paragraphs/list items, or code blocks;
- an optional UTF-8 byte-order mark is removed;
- an optional media-type parameter must be `charset=utf-8`.

Parsers return immutable `ParsedDocument` and node values (`Heading`, `Paragraph`, and
`CodeBlock`). Text formats carry inclusive source-line locations; PDF nodes carry one-based page
numbers. Invalid UTF-8, unsupported media types, malformed/encrypted PDFs, and PDFs without an
extractable text layer produce stable pipeline errors.

## PDF extraction profile

`PdfParser` uses `pdfplumber` word coordinates, font names, and font sizes. Its immutable
`PdfExtractionProfile` controls line tolerance, paragraph gaps, indentation, heading thresholds,
heading-line joining, page-furniture candidates, and recognized monospace font names.

- words are grouped into lines by vertical center and sorted left-to-right;
- bare page numbers, numbered running titles, short page ornaments, and repeated low-emphasis
  headers/footers are identified in configurable page-edge candidates and retained with the
  `header_footer` role;
- isolated small reference numbers and sufficiently separated trailing small-font blocks are
  retained with the `footnote` role;
- ordinary consecutive lines become paragraphs; visual gaps and new list markers create a new
  paragraph;
- a leading `(cid:2)` placeholder observed for list bullets in the representative PDF is emitted
  as `•`; other CID values and inline occurrences remain untouched;
- sufficiently large or bold short lines become headings, with levels derived from descending
  heading font sizes across the document;
- adjacent same-level heading lines on one page are merged when their visual gap is within the
  configured threshold;
- lines dominated by configured monospace fonts become atomic code blocks; relative x-offsets
  reconstruct leading indentation approximately;
- uncertain content remains a paragraph;
- pages without text are allowed, but a document with no embedded text fails explicitly;
- chunks may cross pages and retain inclusive `page_start`/`page_end` provenance.

The current reading-order heuristic targets ordinary single-column born-digital documents.
Multi-column layout, tables, rotated text, arbitrary page ornaments, and perfect code
reconstruction require representative fixtures before expanding the extraction profile.

## Normalization

Normalization is deterministic: Unicode is converted to NFC, prose whitespace is collapsed,
and empty nodes are removed. Before whitespace collapsing, PDF prose removes hyphens that occur
at physical line breaks between letters. A known hyphenated form found elsewhere in the document,
an uppercase abbreviation, a hyphenated particle, or the representative `бизнес-` compound prefix
preserves the hyphen. Words split across adjacent paragraph nodes or pages are also reconstructed
while looking through only `footnote` and `header_footer` nodes. This behavior applies only to
nodes carrying PDF page provenance; TXT, Markdown, and code are unaffected.

Code indentation and internal blank lines are retained; newline forms and trailing whitespace are
normalized. A document with no paragraph or non-empty code content is rejected with
`NoTextContentError`.

## Structure enrichment

After text normalization, a deterministic domain service composes split PDF book headings. An
exact numbered `Часть/Part` or `Глава/Chapter` label is joined with the immediately following
heading when both occur on the same page. The title heading's level is retained, producing paths
such as `ЧАСТЬ I — Стратегическое проектирование` / `ГЛАВА 1 — Анализ предметной области` without
guessing from table-of-contents page ranges. Nodes without PDF page provenance are unchanged.

## Content roles and indexing selection

Every node carries `body`, `front_matter`, `table_of_contents`, `header_footer`, or `footnote`. TXT and
Markdown nodes remain `body`. For PDF, the deterministic domain classifier recognizes explicit
Russian and English contents headings, common front-matter headings, and numbered part/chapter
headings. It does not depend on `pdfplumber` or layout DTOs.

The default application policy selects `body` and `front_matter` before chunking. Contents and
page furniture and footnotes remain available in the classified structure but do not reach the
embedding API or Qdrant. A document with no eligible nodes fails explicitly. Selected chunks carry `content_role`,
and Qdrant stores it for later filtering and diagnostics.

## Character chunking profile

`CharacterChunkingConfig` exposes `max_chars` and `overlap_chars`. The character profile is an
explicit interim profile and is not the token-aware `v1` profile described by ADR 0007.

- chunks never cross a heading boundary and carry the active heading hierarchy;
- paragraphs and atomic code blocks are packed up to `max_chars`;
- oversized prose is split at sentence, then word, then hard character boundaries;
- overlap is used only between pieces of the same oversized paragraph;
- code blocks are never split and raise `ContentBlockTooLargeError` above `max_chars`;
- chunk indexes, content types, content roles, source spans, and output order are deterministic;
- chunks never combine nodes with different content roles.

Tokenizer-aware sizing remains deferred. OCR is also deferred: image-only/scanned PDFs fail with
`PdfNoExtractableTextError`; Tesseract or another OCR engine belongs in a separate adapter and
processing profile rather than an implicit fallback in this parser.

The application-owned ports live in `ingestion.application.interfaces`:

- `DocumentFormatParser`: one concrete format, `bytes -> ParsedDocument`;
- `DocumentParser`: media-aware pipeline dependency,
  `bytes + media_type -> ParsedDocument`.

The infrastructure `DocumentParserRegistry` implements `DocumentParser`; `TxtParser`,
`MarkdownParser`, and `PdfParser` structurally implement `DocumentFormatParser`. The registry has
no implicit formats: bootstrap supplies the complete media-type mapping explicitly.

Parser responsibilities are split by format:

```text
ingestion/application/interfaces/document_parser.py   # parser ports
ingestion/application/services/text_document_pipeline.py # port-driven pipeline
ingestion/infrastructure/parsers/txt.py                # TXT adapter
ingestion/infrastructure/parsers/markdown.py           # Markdown adapter
ingestion/infrastructure/parsers/pdf.py                # pdfplumber adapter
ingestion/infrastructure/parsers/registry.py           # media-type resolution
ingestion/infrastructure/parsers/_text.py              # private UTF-8 helpers
```

The domain separates immutable values from stateless policies:

```text
ingestion/domain/value_objects/source_location.py      # source provenance
ingestion/domain/value_objects/document_structure.py   # parsed nodes/document
ingestion/domain/value_objects/content_role.py         # semantic node/chunk role
ingestion/domain/value_objects/document_chunk.py       # chunk output
ingestion/domain/value_objects/chunking_profile.py     # immutable limits
ingestion/domain/services/interfaces/document_normalizer.py # normalization contract
ingestion/domain/services/interfaces/document_structure_enricher.py # enrichment contract
ingestion/domain/services/interfaces/document_role_classifier.py # role contract
ingestion/domain/services/interfaces/document_chunker.py    # chunking contract
ingestion/domain/services/deterministic_document_normalizer.py # normalization policy
ingestion/domain/services/deterministic_document_structure_enricher.py # heading composition
ingestion/domain/services/deterministic_document_role_classifier.py # role policy
ingestion/domain/services/structure_aware_chunker.py   # chunking policy
```

These value objects are transient domain concepts; they do not require relational persistence or
ORM models. Domain services transform them deterministically without owning identity or state.
`TextDocumentPipeline` depends on protocols for normalization, structure enrichment, role
classification, and chunking, so bootstrap can replace any strategy without changing the
application workflow. The current implementations are deterministic domain services.

Run its focused checks with:

```shell
uv run pytest tests/ingestion
uv run ruff check src/magi/ingestion tests/ingestion
uv run ruff format --check src/magi/ingestion tests/ingestion
uv run pyright src/magi/ingestion tests/ingestion
```
