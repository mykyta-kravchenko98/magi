# ADR 0012: PDF content roles and default indexing policy

- Status: Accepted
- Date: 2026-08-16

## Context

The representative technical-book PDF contains front matter, a multi-page table of contents,
running page titles, and ordinary book content. Embedding all extracted text makes the table of
contents dominate the vector projection and duplicates running titles without adding useful
retrieval context.

Removing those regions inside the PDF adapter would lose information before later processing
profiles can make a different decision. Applying the rule inside the Qdrant adapter would couple
a content decision to one storage technology.

## Decision

Assign every `DocumentNode` one of four technology-independent roles:

- `body`;
- `front_matter`;
- `table_of_contents`;
- `header_footer`.

All parsers produce `body` by default. The PDF adapter identifies page furniture from layout and
retains it as `header_footer`. After normalization, a deterministic domain classifier recognizes
Russian and English table-of-contents headings, common front-matter headings, and numbered
chapter headings. It uses only normalized nodes and page provenance; it does not import a PDF
library.

The application-owned indexing policy selects `body` and `front_matter` before chunking. It keeps
`table_of_contents` and `header_footer` in the classified source structure but does not send them
to the embedding provider or Qdrant. The policy is explicit and replaceable at composition time.

`DocumentChunk`, the retrieval application DTOs, and the Qdrant payload carry `content_role`.
Chunks never combine nodes with different roles.

## Consequences

- The immutable source file in MinIO and the classified in-memory structure retain all extracted
  text; exclusion is a projection policy, not destructive parsing.
- TXT and Markdown behavior is unchanged because their nodes remain `body`.
- Content-role heuristics are deterministic, independently testable, and can evolve without
  changing the PDF adapter, embedding provider, or Qdrant adapter.
- A PDF containing only excluded roles fails with `NoTextContentError` rather than becoming a
  searchable version with zero points.
- Reprocessing changes chunk indexes and point IDs for a new document version. Existing searchable
  versions remain immutable.
- Heuristics can miss unusual localized headings. Representative-corpus evaluation is required
  before adding broad fuzzy or page-range inference.

## Rejected alternatives

- Delete the table of contents and page furniture in the parser: rejected because parsing should
  preserve extracted source information for later policies and diagnostics.
- Filter payloads in the Qdrant adapter: rejected because content eligibility is an application
  decision, independent of vector storage.
- Infer table-of-contents page ranges from page numbers printed in its entries: deferred because
  the first useful rule only needs section boundaries; range reconciliation belongs to a later
  structure-enrichment profile.
- Use an LLM classifier: rejected because the walking skeleton requires deterministic local
  processing without another model dependency.
