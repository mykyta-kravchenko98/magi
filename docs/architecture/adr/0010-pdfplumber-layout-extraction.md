# ADR 0010: pdfplumber for conservative PDF layout extraction

- Status: Accepted
- Date: 2026-08-14

## Context

ADR 0006 requires text-based PDF support with one-based page provenance while keeping PDF-library
types inside an infrastructure adapter. ADR 0007 defines `Heading`, `Paragraph`, and `CodeBlock`
as the common structure. Plain page text is insufficient to recognize those types because it
discards positions and font evidence.

The first adapter must support Python 3.13, have a compatible license, expose word/character
coordinates and font metadata, and produce deterministic results with a pinned version. OCR is
outside this processing profile.

## Decision

Use [`pdfplumber`](https://pypi.org/project/pdfplumber/) `0.11.x`, pinned by `uv.lock`, inside
`ingestion.infrastructure.parsers.pdf`. It is MIT-licensed, declares Python 3.13 support, and
exposes word/character bounding boxes, font names, and font sizes.

The adapter reconstructs lines from positioned words and applies an immutable, configurable
`PdfExtractionProfile`:

- large or sufficiently bold short lines are headings;
- lines dominated by known monospace fonts are code;
- list markers, visual gaps, and indentation separate paragraphs;
- the representative book's leading `(cid:2)` placeholder is canonicalized to `•` before list
  boundary detection; arbitrary CID values and inline occurrences are preserved;
- uncertain content is a paragraph;
- every node retains its one-based page number.

Malformed, encrypted, and no-text/image-only PDFs produce application-owned stable errors.
Vendor exceptions and objects do not cross the adapter boundary. PDF parsing is registered with
the application parser registry by the composition root.

## Consequences

- Layout behavior is explicit, deterministic, configurable, and covered by rendered PDF fixtures.
- Heading and code recognition are best effort rather than claims about authorial structure.
- Relative code indentation is reconstructed approximately from x-coordinates.
- Current reading order is suitable for ordinary single-column PDFs; columns, tables, rotated
  text, repeated headers/footers, and OCR require separately tested profile evolution.
- CID identifiers are font-local. The accepted mapping is deliberately limited to the observed
  leading `(cid:2)` list marker and must not become a global `(cid:N)` substitution table.
- Changing the library version or extraction thresholds changes parsing semantics and requires a
  new processing profile plus reindexing.

## Rejected alternatives

- Plain page-level text extraction: rejected because it discards evidence needed for structure.
- PyMuPDF for the first adapter: rejected because pdfplumber's MIT license and direct layout/debug
  metadata are a better fit for this implementation; performance can be reevaluated with corpus
  benchmarks.
- Implicit Tesseract fallback: rejected because OCR has different resource, language, confidence,
  and failure semantics and remains outside the current scope.
