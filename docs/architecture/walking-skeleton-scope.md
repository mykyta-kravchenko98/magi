# Walking Skeleton: Data Upload Pipeline

- Status: Accepted
- Date: 2026-08-13
- Owners: backend team

## Goal

Deliver the smallest production-shaped vertical slice that proves a supported text file can travel through the complete ingestion path:

```text
HTTP upload
  -> MinIO
  -> parsing
  -> normalization
  -> chunking
  -> local embedding HTTP API
  -> Qdrant
  -> DocumentVersion.SEARCHABLE
```

The slice must preserve the intended modular-monolith and DDD boundaries. It is not a disposable script and it is not a reliability-complete ingestion platform.

## In scope

- Python 3.13 application managed with `uv`;
- FastAPI HTTP API and Pydantic 2 boundary models;
- PostgreSQL persistence through SQLAlchemy 2 and Alembic;
- one or more pre-created active knowledge bases;
- text-based PDF as the primary book format, plus UTF-8 plain text and Markdown uploads;
- configurable maximum upload size;
- durable storage of the original file in MinIO;
- deterministic parsing into a minimal document structure, normalization, and structure-aware chunking;
- `Qwen/Qwen3-Embedding-0.6B` served locally over HTTP by Hugging Face Text Embeddings Inference (TEI);
- embedding batching, request timeout, and vector-dimension validation;
- one Qdrant collection with deterministic point identifiers and idempotent upsert;
- persisted processing status exposed through HTTP;
- synchronous application orchestration for the first deployment;
- Docker Compose for PostgreSQL, MinIO, Qdrant, the application, and the selected embedding API;
- unit, integration, and end-to-end tests for the happy path and critical failure paths.

## Explicit non-goals

- RabbitMQ or another message broker;
- transactional outbox or inbox;
- Celery, Dramatiq, or a separate worker runtime;
- retries, leases, dead-letter queues, reconciliation, or scheduled cleanup;
- OCR and scanned/image-only PDF;
- formats other than text-based PDF, UTF-8 TXT, and UTF-8 Markdown;
- source/content deduplication or user-assisted duplicate resolution;
- multiple embedding models or live model migration;
- activation, retirement, or cleanup of vector projections;
- public retrieval, reranking, context assembly, LLM generation, or answers;
- authentication and authorization;
- Kubernetes.

## Modules and responsibilities

| Module | Owns | Does not own |
|---|---|---|
| `documents` | Knowledge bases, upload acceptance, document identity, versions, addition status, end-to-end application workflow | Text-processing algorithms or Qdrant details |
| `ingestion` | Parsing, normalization, chunking, embedding generation and validation | HTTP upload, document lifecycle, vector storage |
| `retrieval` | Qdrant projection and indexed-point metadata | User-facing retrieval or document lifecycle |
| `shared` | Configuration, persistence primitives, observability primitives | Business rules or a generic repository framework |
| `bootstrap` | Dependency construction, FastAPI assembly, process startup/shutdown | Business orchestration or domain rules |

The upload use case belongs to `documents.application`. It coordinates the public application contracts of `ingestion` and `retrieval`; those modules do not mutate document aggregates directly.

The cross-module application contracts are intentionally small:

| Contract | Input | Output |
|---|---|---|
| `PrepareDocumentContent` | Source bytes, supported media type, immutable processing profile | Parsed nodes with source locations, normalized ordered chunks with structural metadata and source spans, embeddings, and model metadata |
| `IndexDocumentVersion` | Knowledge-base/document/version IDs and ordered embedded chunks | Opaque projection reference and indexed chunk count |

These contracts use immutable application DTOs. They do not expose ORM entities, aggregate instances, or vendor SDK types.

## Dependency rules

```text
FastAPI route
  -> documents.application
       -> documents.domain
       -> ingestion.application public contract
            -> ingestion.domain / ingestion ports
       -> retrieval.application public contract
            -> retrieval.domain / retrieval ports

bootstrap -> every concrete adapter, only for composition
infrastructure -> application ports + external SDKs
domain -> Python standard library only
```

- Domain packages never import FastAPI, Pydantic, SQLAlchemy, MinIO, Qdrant, or HTTP clients.
- Infrastructure packages may depend inward; domain and application packages never depend on concrete adapters.
- Modules may call another module only through its public application contract. They do not import another module's infrastructure or persistence models.
- SQLAlchemy models do not cross module boundaries.
- `shared` must not become a home for cross-module business concepts.

## Minimal lifecycle

### KnowledgeBase

```text
ACTIVE -> ARCHIVED
```

Uploads are accepted only for an `ACTIVE` knowledge base. `ARCHIVED` is terminal in this slice.

### DocumentAddition

```text
ACCEPTED -> PROCESSING -> COMPLETED
    |             |
    +-----------> FAILED
```

- `COMPLETED` and `FAILED` are terminal.
- `PROCESSING` requires a stored source object reference.
- `COMPLETED` requires both `document_id` and `document_version_id`.
- `FAILED` requires a stable error code and may contain a sanitized diagnostic message.

### Document

```text
ACTIVE
```

Archiving and version replacement are outside this slice. A document is registered only after parsing and normalization succeed.

### DocumentVersion

```text
PROCESSING -> SEARCHABLE
     |
     +------> FAILED
```

- `SEARCHABLE` and `FAILED` are terminal.
- `SEARCHABLE` requires a Qdrant collection/projection reference and a positive indexed chunk count.
- A Qdrant error must never result in `SEARCHABLE`.
- If processing fails after version registration, both the version and its addition end in `FAILED`.

## Processing sequence

1. Validate knowledge-base state, media type, filename, size, and non-empty content.
2. Create a `DocumentAddition` in `ACCEPTED` and persist it.
3. Store the original bytes in MinIO under a generated immutable object key.
4. Move the addition to `PROCESSING`.
5. Extract ordered `DocumentNode` values. Preserve Markdown headings and fenced code blocks; preserve PDF page numbers and recognize structure only when it can be inferred reliably.
6. Normalize node text deterministically without discarding node type, heading hierarchy, or source provenance.
7. Register `Document` and `DocumentVersion(PROCESSING)`.
8. Produce deterministic, structure-aware ordered chunks with stable zero-based indexes, heading paths, content types, and source spans.
9. Request embeddings in bounded batches and validate count and dimension.
10. Upsert deterministic points into Qdrant.
11. Mark the version `SEARCHABLE`, then mark the addition `COMPLETED`.

External writes and PostgreSQL cannot be committed atomically in this slice. State changes are committed at meaningful checkpoints. A failure is recorded as `FAILED`; automatic compensation and cleanup are deferred.

## HTTP API

### Upload a document

```http
POST /api/v1/knowledge-bases/{knowledge_base_id}/documents
Content-Type: multipart/form-data

file=<PDF, TXT, or Markdown file>
```

The accepted media types are:

| Content type | Extensions | First-slice behavior |
|---|---|---|
| `application/pdf` | `.pdf` | Extract embedded text in page order and preserve 1-based page numbers |
| `text/plain` | `.txt` | Decode as strict UTF-8 |
| `text/markdown` | `.md`, `.markdown` | Decode as strict UTF-8; preserve headings, paragraphs, and fenced code blocks |

For text formats, an optional `charset` parameter must be `utf-8`. The server checks the declared media type, filename extension, and a minimal content signature where applicable. An extension alone cannot opt an arbitrary payload into processing.

PDF support means text-based PDFs with an extractable text layer. It does not include OCR. Encrypted, malformed, scanned/image-only PDFs, or PDFs whose extracted text normalizes to empty content end as a persisted processing failure with a stable code. The original file remains stored in MinIO for diagnosis and possible future reprocessing.

The first implementation executes processing synchronously but returns `202 Accepted` to keep the boundary compatible with a future queued worker. The response always reports the state observed when processing returns; it may therefore already be terminal.

```json
{
  "document_addition_id": "0198...",
  "status": "COMPLETED",
  "document_id": "0198...",
  "document_version_id": "0198...",
  "document_version_status": "SEARCHABLE",
  "indexed_chunk_count": 12
}
```

If an external stage fails after the addition has been accepted, the resource remains queryable and the response contains its terminal state:

```json
{
  "document_addition_id": "0198...",
  "status": "FAILED",
  "error": {
    "code": "EMBEDDING_PROVIDER_UNAVAILABLE",
    "message": "Document processing failed"
  }
}
```

Validation performed before acceptance uses an RFC 9457-style problem response and does not create an addition:

| Condition | Status |
|---|---:|
| Invalid identifier or malformed multipart request | 400 |
| Knowledge base not found | 404 |
| Knowledge base archived | 409 |
| Empty file | 422 |
| Invalid UTF-8 text upload | 422 |
| Unsupported media type | 415 |
| Upload too large | 413 |

### Read addition status

```http
GET /api/v1/document-additions/{document_addition_id}
```

```json
{
  "document_addition_id": "0198...",
  "status": "PROCESSING",
  "document_id": null,
  "document_version_id": null,
  "document_version_status": null,
  "indexed_chunk_count": null,
  "error": null
}
```

Unknown additions return `404`. Enum values are uppercase stable API values. Internal exception text, object-storage credentials, and external response bodies are never exposed.

The initial processing error taxonomy is deliberately small:

- `OBJECT_STORAGE_UNAVAILABLE`;
- `PARSING_FAILED`;
- `PDF_ENCRYPTED`;
- `NO_EXTRACTABLE_TEXT`;
- `CONTENT_BLOCK_TOO_LARGE`;
- `EMBEDDING_PROVIDER_UNAVAILABLE`;
- `EMBEDDING_RESPONSE_INVALID`;
- `VECTOR_INDEX_UNAVAILABLE`;
- `PROCESSING_FAILED` as a safe fallback.

Invalid client content is rejected before acceptance and therefore uses problem details rather than a persisted processing error.

## Infrastructure ports

Ports are narrow, typed contracts owned by the application module that consumes them.

| Port | Required operations and guarantees |
|---|---|
| `KnowledgeBaseRepository` | Load a knowledge base by ID within a unit of work |
| `DocumentAdditionRepository` | Add and load an addition; persist lifecycle changes |
| `DocumentRepository` | Add a document |
| `DocumentVersionRepository` | Add and load a version; persist version lifecycle changes |
| `UnitOfWork` | Explicit begin/commit/rollback around PostgreSQL checkpoints |
| `ObjectStorage` | Put immutable bytes with media type; return an opaque object reference |
| `DocumentParser` | Convert supported bytes to an ordered `ParsedDocument` of `DocumentNode` values and source locations, or return a typed parsing failure |
| `EmbeddingProvider` | Embed an ordered batch; return model metadata and vectors in the same order |
| `VectorIndex` | Ensure the configured collection and idempotently upsert ordered vector points |

Normalization and chunking are deterministic in-process services, not infrastructure adapters. The minimal node types are `Heading`, `Paragraph`, and `CodeBlock`. Nodes carry text and optional source locations; headings carry a level and code blocks may carry a language. A chunk carries its active `heading_path`, content type, and the inclusive page range covering its source text when that information exists. External DTOs from the PDF library, MinIO, TEI, and Qdrant are translated at adapter boundaries.

Every outbound network adapter has an explicit timeout. The embedding adapter verifies the pinned model revision, vector count, finite numeric values, and dimension `1024`. The Qdrant adapter uses a deterministic point ID derived from `document_version_id` and `chunk_index`.

## Chunking profile v1

`StructureAwareChunker` consumes `DocumentNode[]`; it does not parse PDF or Markdown itself.

```text
target_tokens: 600
soft_max_tokens: 800
hard_max_tokens: 1000
overlap_tokens: 80
embedding_input_max_tokens: 2048
```

- Natural heading boundaries take precedence over target size.
- Nodes are grouped within the active chapter/section/subsection hierarchy.
- A complete section may be smaller than the target; chunks are not padded to uniform size.
- A section over the soft maximum is split on paragraph boundaries, then sentence boundaries as fallback.
- Overlap is added only between pieces of the same oversized prose section, not across natural section boundaries.
- A `CodeBlock` is atomic when it fits within the hard maximum and is never copied into overlap.
- A code block larger than the hard maximum becomes one explicitly oversized chunk up to the 2048-token embedding-input safety limit, including its heading prefix. Exceeding that limit produces `CONTENT_BLOCK_TOO_LARGE`; the first slice does not silently split code mid-block.
- Markdown structure is authoritative. PDF heading and code recognition is best effort; uncertain PDF content becomes `Paragraph` nodes and follows the paragraph-aware fallback.
- Token counts use the tokenizer revision pinned with the embedding model.

The text sent for document embedding is the chunk text prefixed by its non-empty heading path. The stored payload keeps the original normalized chunk text and headings separate.

## Embedding profile v1

```text
server: Hugging Face Text Embeddings Inference
model_id: Qwen/Qwen3-Embedding-0.6B
model_revision: pinned immutable revision
tokenizer_revision: same pinned model revision
vector_dimension: 1024
distance: Cosine
document_instruction: none
```

The full 1024-dimensional output is used in the walking skeleton. The 0.6B model preserves GPU capacity for a co-resident assistant LLM; moving to the 4B model is a future quality upgrade that requires retrieval evaluation, a new embedding profile, and complete reindexing. Dimension reduction, other alternate models, and live model migration are deferred. A future retrieval query may use a fixed retrieval instruction, but indexed document chunks do not receive a query instruction.

## Qdrant point contract

Each point contains one embedding and a payload sufficient to prove indexability:

```json
{
  "knowledge_base_id": "uuid",
  "document_id": "uuid",
  "document_version_id": "uuid",
  "chunk_index": 0,
  "content_type": "text",
  "heading_path": [
    "Chapter 5 — Replication",
    "Leader-based replication"
  ],
  "page_start": 12,
  "page_end": 13,
  "text": "normalized chunk text"
}
```

`content_type` is `text`, `code`, or `mixed`. `page_start` and `page_end` are present for PDF chunks and absent for text formats. Preserving structure and provenance now enables later citations and filtering without changing the indexed chunk identity.

The Qdrant collection uses 1024-dimensional vectors and Cosine distance. The collection name and immutable embedding/chunking profile identifiers are fixed in configuration.

## Definition of Done

The walking skeleton is done when all of the following are true:

1. A documented `uv` command starts the API locally and Docker Compose starts all required dependencies.
2. Health endpoints distinguish process liveness from dependency readiness.
3. Alembic can create the PostgreSQL schema from an empty database.
4. A text-based PDF book can be uploaded to an active knowledge base; UTF-8 TXT and Markdown remain supported secondary formats.
5. The original bytes and media type are present in MinIO after upload.
6. PDF parsing preserves page order and page provenance; Markdown parsing preserves headings and fenced code blocks.
7. Structure-aware chunking is deterministic, respects natural boundaries, applies overlap only to split prose, and does not split an in-limit code block.
8. Embeddings are produced by pinned `Qwen/Qwen3-Embedding-0.6B` through local TEI and validated as 1024-dimensional finite vectors before indexing.
9. All expected chunks are present in a Cosine Qdrant collection with deterministic IDs and the documented payload.
10. The version becomes `SEARCHABLE` only after the complete Qdrant upsert succeeds.
11. The addition status endpoint exposes `COMPLETED` or a persisted, sanitized `FAILED` result.
12. Empty, oversized, invalid UTF-8, unsupported, malformed, encrypted, and image-only PDF uploads have automated tests.
13. Oversized prose, code blocks, heading paths, page spans, and chunking determinism have automated tests.
14. Embedding and Qdrant failures have automated tests proving that `SEARCHABLE` is not set.
15. Repository integration tests run against PostgreSQL; adapter integration tests run against real MinIO and Qdrant.
16. An end-to-end test uploads a document, observes `COMPLETED`/`SEARCHABLE`, and confirms a technical similarity search finds its content.
17. Restarting the Compose stack does not lose completed PostgreSQL, MinIO, or Qdrant data.
18. Ruff, Pyright, unit tests, relevant integration tests, and the end-to-end test pass using documented commands.

## Deferred evolution to asynchronous processing

The future worker will invoke the same transport-neutral upload-processing application use case. The HTTP route will stop after durable acceptance and return `ACCEPTED`; a message consumer will continue from the persisted addition ID. Aggregate methods, state invariants, and infrastructure ports remain unchanged.

Reliable delivery, idempotent consumers, retries, and outbox/inbox are separate future decisions. This document deliberately does not simulate those guarantees with in-process background tasks.
