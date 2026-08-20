# ADR 0013: Exact-source identity within a knowledge base

- Status: Proposed
- Date: 2026-08-20

## Context

The Event Storming model places `Calculate File Hash`, `Find Exact Source Duplicate`, and
an atomic `check + reserve` before parsing and semantic identity analysis. It distinguishes
an exact source duplicate from an exact normalized-content duplicate and from a potential
semantic duplicate.

The current synchronous upload handler validates the request, creates a new
`DocumentAddition`, stores the source, and runs the complete ingestion pipeline for every
request. `SourceFileMetadata` deliberately does not define identity. Consequently, two
requests containing the same bytes can create two documents, and a read followed by an
insert would still allow that outcome under concurrency.

`DocumentAddition` is also the observable upload attempt. Its `COMPLETED` and `FAILED`
states are terminal, so recovery from a failed attempt cannot mutate that attempt back to
`ACCEPTED` or `PROCESSING`.

## Decision

Define **exact-source identity** as the SHA-256 digest of the original, unmodified upload
bytes:

```text
ExactSourceIdentity = (knowledge_base_id, algorithm = "sha256", digest)
digest = SHA-256(command.content)
```

Hash the validated bytes before any object-storage write, decoding, parsing,
normalization, or format-specific transformation. Filename, declared media type, upload
time, and uploader do not participate in identity. The same bytes are distinct identities
when uploaded to different knowledge bases. Store the algorithm explicitly and the digest
in a canonical fixed representation; do not use a language or database hash function.

PostgreSQL owns a source-identity registry with a unique key on
`(knowledge_base_id, algorithm, digest)`. A registry entry points to the current owning
`DocumentAddition` and records whether the claim is `IN_PROGRESS`, `COMPLETED`, or
`RETRYABLE`. The registry is a consistency mechanism, not another document aggregate.
The referenced addition remains the business-visible lifecycle and result.

The knowledge-base eligibility check, insertion of a new `DocumentAddition`, and
acquisition or transfer of the source-identity claim occur in one short PostgreSQL
transaction. The operation must be implemented as a single atomic repository operation
backed by the unique key and row locking or an equivalent compare-and-set operation. An
application-level `find` followed by `add` is not sufficient. No transaction remains open
while hashing, writing to object storage, parsing, embedding, or indexing.

The atomic claim operation has exactly these outcomes:

| Existing claim/result | Atomic outcome | Upload response behavior |
|---|---|---|
| No claim | Create a new addition and acquire `IN_PROGRESS` for it | Process the new addition |
| `COMPLETED` | Return the owning completed addition; create nothing | Return the existing completed result |
| `IN_PROGRESS` | Return the owning in-progress addition; create nothing | Join that operation by returning its current status; do not start another pipeline |
| `RETRYABLE` after its owning addition failed | Create a new addition and atomically transfer the claim to it as `IN_PROGRESS` | Process the new attempt |

Thus concurrent requests for the same identity have one winner. After the winner commits,
losers observe its claim and return the same `document_addition_id`; they do not upload a
second source object or create a second document/version. A completed claim is permanent
for the life of the knowledge base and always resolves to the same completed document and
version.

Failure handling marks the owning `DocumentAddition` (and a registered
`DocumentVersion`, when present) `FAILED` and changes its registry claim to `RETRYABLE`
in the same PostgreSQL transaction. A later upload of the same bytes creates a fresh addition
with a fresh ID and transfers ownership from the failed attempt. The failed addition
remains queryable as immutable history. If several retries arrive concurrently, only one
can transfer the claim; the others return that new in-progress addition.

Only a persisted `FAILED` state permits transfer. A slow or crashed operation that still
appears `IN_PROGRESS` is not silently stolen by another HTTP request. Leases, watchdogs,
abandoned-attempt detection, and operator recovery are separate decisions.

Keep the existing `202 Accepted` response shape from ADR 0005. The returned resource may
therefore be a newly accepted addition, the current in-progress owner, or the already
completed owner. This decision does not introduce a separate duplicate error response or
expose the digest as a public identifier.

## Atomicity and failure boundaries

- Digest computation and request validation happen before acceptance; failure there
  creates neither an addition nor a claim.
- Claim acquisition and addition creation commit together. A claim cannot point to an
  addition that was not durably accepted.
- Completion of the addition and transition of its claim to `COMPLETED` commit together.
- Persisting processing failure and making the claim retryable commit together.
- Object storage and downstream indexing remain outside PostgreSQL transactions, as in
  ADR 0003. Orphaned external artifacts are possible, but they cannot grant source
  identity ownership.
- Repeated completion/failure delivery must be conditional on the claim still belonging
  to that addition, preventing an old attempt from changing a claim transferred to a
  retry.

## Consequences

- Exact byte-for-byte repeats within one knowledge base converge on one successful
  document/version, including under concurrent upload.
- Retries after a recorded failure preserve audit history while allowing progress.
- Filename or media-type changes do not bypass exact-source identity when bytes are
  unchanged.
- SHA-256 collision risk is accepted as negligible for this identity mechanism. Changing
  algorithms requires an explicit migration or dual-hash decision because the algorithm
  is part of the key.
- The registry adds transactional persistence and repository behavior but does not require
  changes to the existing aggregate state machines.
- Existing rows need a separately planned backfill and collision-resolution migration
  before enforcing the unique registry invariant in a populated environment.

## Out of scope

- Normalized-content identity, exact-content identity after parsing, perceptual hashes,
  embeddings, similarity thresholds, and other semantic duplicate detection.
- User-driven duplicate resolution such as registering the source as a separate document
  or as a new version.
- Automatic recovery or takeover of stale `IN_PROGRESS` claims.
- Production code, schema migrations, API implementation, and backfill implementation.

## Rejected alternatives

- Use filename, media type, or size as identity: metadata can differ for identical bytes
  and can match for different bytes.
- Hash normalized or parsed content: that defines content or semantic identity, not exact
  source identity, and depends on processing versions.
- Query for a digest and then insert an addition: concurrent transactions can both observe
  absence and start duplicate pipelines.
- Keep one permanently unique digest on `DocumentAddition`: terminal failed additions
  would prevent a fresh retry, while weakening the constraint would lose concurrency
  safety.
- Restart the failed addition: terminal-state history would be overwritten and would
  contradict the current aggregate invariants.
