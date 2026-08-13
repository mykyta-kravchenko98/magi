# ADR 0005: Upload and status API contract

- Status: Accepted
- Date: 2026-08-13

## Context

Clients need a stable identifier and truthful processing status. The first implementation runs synchronously, while a later implementation should be able to return after durable acceptance and continue in a worker without redesigning the resource model.

## Decision

Expose two versioned endpoints:

```http
POST /api/v1/knowledge-bases/{knowledge_base_id}/documents
GET  /api/v1/document-additions/{document_addition_id}
```

The upload is multipart with one `file` part. The primary book format is text-based PDF (`application/pdf`, `.pdf`). UTF-8 TXT (`text/plain`, `.txt`) and Markdown (`text/markdown`, `.md`/`.markdown`) are also supported. The server validates configured size, non-empty bytes, the declared media type, matching extension, and a minimal content signature where applicable; filename extension alone is not authoritative.

PDF processing extracts the existing text layer in page order and preserves 1-based page provenance. OCR is not part of this slice. Encrypted, malformed, scanned/image-only PDFs, and PDFs with no meaningful extractable text become persisted processing failures after acceptance; the status endpoint exposes a stable sanitized error code.

Return `202 Accepted` after a valid upload has created an addition, even though the first implementation completes processing before responding. The representation reports the latest persisted status and may already be `COMPLETED` or `FAILED`. This preserves the same response shape when orchestration later moves to a worker.

Return pre-acceptance validation failures as RFC 9457-style problem details. Once an addition exists, processing failures are persisted and represented by its status and stable error code. Status lookup is always available by addition ID.

Use uppercase enum strings as stable wire values. Do not expose internal stack traces, vendor response bodies, credentials, bucket names, or raw object keys.

## Consequences

- Clients are expected to understand that `202` can contain a terminal current state and can always use the status endpoint.
- Moving processing to a worker does not change endpoint paths or response schemas.
- The initial request may still take a long time; operational request limits must reflect that temporary constraint.
- A future API revision may add polling hints such as `Retry-After` without changing domain state.

## Rejected alternatives

- Return only `201 Created` after full indexing: rejected because moving to asynchronous processing would change the interaction contract.
- Return `200` with an unpersisted transient result: rejected because status must survive process restart.
- Expose detailed pipeline-stage enums now: rejected because stage-level lifecycle and retry semantics are outside scope.
