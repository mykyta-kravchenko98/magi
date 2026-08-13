# ADR 0004: Ports and adapters for external systems

- Status: Accepted
- Date: 2026-08-13

## Context

The pipeline depends on PostgreSQL, MinIO, a local embedding HTTP API, and Qdrant. Direct SDK use in application or domain code would make the workflow difficult to test and would bind business state to infrastructure-specific types.

## Decision

Define narrow typed ports owned by their consuming application module:

- repositories and `UnitOfWork` for PostgreSQL;
- `ObjectStorage` for immutable source upload;
- `DocumentParser` for conversion to ordered text segments with optional source locations;
- `EmbeddingProvider` for ordered batch embedding plus model metadata;
- `VectorIndex` for collection validation and idempotent point upsert.

Keep normalization and chunking as deterministic in-process services. Their inputs and outputs are application/domain value types, not Pydantic or vendor DTOs. The parser contract returns a `ParsedDocument`; its segments carry extracted text and an optional 1-based PDF page number. Normalized chunks preserve the inclusive source-page range when available.

Adapters translate vendor failures into a small application error taxonomy. Network ports enforce explicit timeouts. The embedding adapter validates model identity, result count, finite values, and configured vector dimension. Qdrant point IDs are deterministically derived from document-version ID and chunk index.

No port exposes PDF-library, MinIO, HTTP-client, or Qdrant response classes. No application contract accepts untyped `object` payloads.

## Consequences

- Unit tests can replace every external boundary with small fakes.
- Integration tests can verify each real adapter independently.
- Switching embedding-server protocol or SDK affects one adapter and composition.
- Port evolution must remain use-case-driven; a generic storage or repository framework is not introduced.

## Rejected alternatives

- Import vendor clients in handlers: rejected because it reverses dependencies and leaks vendor models.
- One universal `Storage` abstraction: rejected because object, relational, and vector stores have different semantics.
- Put parsing, normalization, and chunking behind remote-service abstractions: rejected because the first implementations are deterministic local behavior.
