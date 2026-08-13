# ADR 0006: Text-based PDF support and source provenance

- Status: Accepted
- Date: 2026-08-13

## Context

Books are the primary knowledge source, so limiting the walking skeleton to TXT and Markdown would not test the main product input. PDF parsing also differs from plain-text decoding: page order matters, extraction may fail despite a valid container, and later answers need page-level citations.

Supporting OCR in the same slice would add image rendering, language/model selection, GPU or external processing, confidence handling, and substantially different failure modes.

## Decision

Support text-based PDF (`application/pdf`, `.pdf`) as the primary input format. Extract the embedded text layer in document page order and attach the 1-based page number to every parsed segment.

Define the parser boundary in terms of application-owned values:

```text
ParsedDocument
  nodes[]
    Heading(level, text, source_location?)
    Paragraph(text, source_location?)
    CodeBlock(text, language?, source_location?)
```

Normalization operates on ordered nodes and retains their type and source locations. PDF structure recognition is best effort: uncertain content is emitted as paragraphs rather than guessed headings or code. Chunking may cross a page boundary; every resulting PDF chunk stores the inclusive `page_start` and `page_end`. Qdrant payloads preserve these fields so future retrieval can produce book citations without reparsing the source.

PDF-library objects and layout-specific details remain inside the parser adapter. A concrete PDF library will be selected during implementation based on extraction quality, Python 3.13 support, licensing, and deterministic behavior.

Do not perform OCR in the walking skeleton. Encrypted PDFs, malformed PDFs, image-only/scanned PDFs, and documents with no meaningful text after normalization fail with stable error codes. Their original bytes remain in MinIO.

## Consequences

- The end-to-end test must use a representative multi-page text-based PDF, not only a synthetic TXT file.
- Parser tests cover page order, page provenance, empty pages, malformed and encrypted inputs, and an image-only PDF.
- Complex layouts, tables, headers/footers, hyphenation, and reading order may expose extraction limitations; representative fixtures make these visible early.
- OCR can later be added as another parsing strategy without changing document aggregates, chunk identity, embedding, or vector-index ports.
- Exact page-level provenance is available for future citations, while bounding boxes and character offsets remain outside this slice.

## Rejected alternatives

- Defer all PDF support: rejected because it would validate the pipeline against a secondary source format.
- Include OCR now: rejected because it materially expands infrastructure and failure semantics beyond the walking skeleton.
- Flatten PDF to one unlocated string: rejected because it discards page provenance required by the likely retrieval experience.
