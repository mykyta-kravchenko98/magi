# ADR 0007: Minimal document structure and structure-aware chunking

- Status: Accepted
- Date: 2026-08-13

## Context

Fixed-size splitting can cut a technical explanation or code block in the middle and discard the chapter context needed to interpret a chunk. Full semantic segmentation or robust reconstruction of arbitrary PDF layouts would make the walking skeleton substantially larger.

## Decision

Parsers return an ordered `ParsedDocument` containing application-owned `DocumentNode` values. The minimal node types are:

- `Heading(level, text, source_location?)`;
- `Paragraph(text, source_location?)`;
- `CodeBlock(text, language?, source_location?)`.

Markdown headings and fenced code blocks are authoritative. The PDF adapter recognizes structure only when extraction metadata makes it sufficiently reliable; otherwise it emits page-located paragraphs. TXT is represented as paragraphs.

Use a custom deterministic `StructureAwareChunker` with profile `v1`:

```text
target_tokens = 600
soft_max_tokens = 800
hard_max_tokens = 1000
overlap_tokens = 80
embedding_input_max_tokens = 2048
```

The target and soft maximum are guidance, not invariants. Preserve a coherent section even when it produces a smaller chunk. Split an oversized section by paragraphs, then sentences. Apply overlap only to consecutive pieces produced from the same oversized prose section.

Track the active heading hierarchy as `heading_path`. Store it separately in chunk metadata and prefix it to the text sent for document embedding. Preserve inclusive PDF page spans.

Treat an in-limit code block atomically and never copy it into overlap. A code block above the hard maximum may remain one oversized chunk up to the 2048-token embedding-input safety limit, including the heading prefix. Content beyond that safety limit fails explicitly with `CONTENT_BLOCK_TOO_LARGE`; the first slice does not silently cut code mid-block.

Token counting uses the tokenizer revision pinned to the embedding profile. `RecursiveCharacterTextSplitter` or equivalent behavior may be used only as an internal final fallback after structural and prose boundaries, not as the architecture-facing contract.

## Consequences

- Technical sections and code retain substantially more context than fixed-width chunks.
- Chunk sizes vary; this is intentional.
- The same source and immutable profiles produce the same node order, chunks, indexes, and point IDs.
- PDF results depend on extraction quality but degrade to paragraph-aware chunking rather than blocking the complete pipeline.
- Changing node recognition, tokenizer, or chunking parameters creates a new versioned processing profile and requires reindexing; existing chunk identities are not silently reinterpreted.

## Rejected alternatives

- Uniform fixed-size chunks: rejected because numerical regularity is less important than semantic integrity for technical books.
- LLM-based semantic chunking: rejected because it adds cost, nondeterminism, and another model dependency to the walking skeleton.
- Require perfect PDF heading and code reconstruction: rejected because layout recovery is a separate product problem.
- Split every code block at the hard limit: rejected because arbitrary cuts can destroy the unit a reader is trying to retrieve.
