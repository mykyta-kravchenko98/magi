# TXT/Markdown/PDF processing pipeline

The transport- and provider-independent ingestion pipeline is implemented in `magi.ingestion`:

```text
source bytes -> parse -> normalize -> character chunking -> DocumentChunk[]
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
and recognized monospace font names.

- words are grouped into lines by vertical center and sorted left-to-right;
- ordinary consecutive lines become paragraphs; visual gaps and new list markers create a new
  paragraph;
- sufficiently large or bold short lines become headings, with levels derived from descending
  heading font sizes across the document;
- lines dominated by configured monospace fonts become atomic code blocks; relative x-offsets
  reconstruct leading indentation approximately;
- uncertain content remains a paragraph;
- pages without text are allowed, but a document with no embedded text fails explicitly;
- chunks may cross pages and retain inclusive `page_start`/`page_end` provenance.

The current reading-order heuristic targets ordinary single-column born-digital documents.
Multi-column layout, tables, repeated header/footer removal, rotated text, and perfect code
reconstruction require representative fixtures before expanding the extraction profile.

## Normalization

Normalization is deterministic: Unicode is converted to NFC, prose whitespace is collapsed,
and empty nodes are removed. Code indentation and internal blank lines are retained; newline
forms and trailing whitespace are normalized. A document with no paragraph or non-empty code
content is rejected with `NoTextContentError`.

## Character chunking profile

`CharacterChunkingConfig` exposes `max_chars` and `overlap_chars`. The character profile is an
explicit interim profile and is not the token-aware `v1` profile described by ADR 0007.

- chunks never cross a heading boundary and carry the active heading hierarchy;
- paragraphs and atomic code blocks are packed up to `max_chars`;
- oversized prose is split at sentence, then word, then hard character boundaries;
- overlap is used only between pieces of the same oversized paragraph;
- code blocks are never split and raise `ContentBlockTooLargeError` above `max_chars`;
- chunk indexes, content types, source spans, and output order are deterministic.

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
ingestion/application/text_pipeline.py                # port-driven pipeline
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
ingestion/domain/value_objects/document_chunk.py       # chunk output
ingestion/domain/value_objects/chunking_profile.py     # immutable limits
ingestion/domain/services/interfaces/document_normalizer.py # normalization contract
ingestion/domain/services/interfaces/document_chunker.py    # chunking contract
ingestion/domain/services/deterministic_document_normalizer.py # normalization policy
ingestion/domain/services/structure_aware_chunker.py   # chunking policy
```

These value objects are transient domain concepts; they do not require relational persistence or
ORM models. Domain services transform them deterministically without owning identity or state.
`TextDocumentPipeline` depends on the `DocumentNormalizer` and `DocumentChunker` protocols, so
bootstrap can replace either strategy without changing the application workflow. The current
implementations are `DeterministicDocumentNormalizer` and `StructureAwareCharacterChunker`.

Run its focused checks with:

```shell
uv run pytest tests/ingestion
uv run ruff check src/magi/ingestion tests/ingestion
uv run ruff format --check src/magi/ingestion tests/ingestion
uv run pyright src/magi/ingestion tests/ingestion
```
