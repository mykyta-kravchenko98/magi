# ADR 0003: Minimal aggregate lifecycles and consistency boundaries

- Status: Accepted
- Date: 2026-08-13

## Context

The Event Storming model contains richer lifecycles for duplicate resolution, retries, ingestion stages, and projection activation. Implementing those states now would create rules for behavior that the walking skeleton does not support. Too little state, however, could falsely report a partially indexed document as searchable.

## Decision

Use four minimal aggregates or aggregate roots owned by the `documents` module:

- `KnowledgeBase`: `ACTIVE -> ARCHIVED`;
- `DocumentAddition`: `ACCEPTED -> PROCESSING -> COMPLETED | FAILED`, also allowing `ACCEPTED -> FAILED`;
- `Document`: `ACTIVE` only in this slice;
- `DocumentVersion`: `PROCESSING -> SEARCHABLE | FAILED`.

Terminal states cannot transition. `DocumentAddition.COMPLETED` requires document and version IDs. `DocumentVersion.SEARCHABLE` requires a vector collection/projection reference and a positive indexed chunk count. External failures are represented by stable application error codes; domain state does not store SDK exceptions.

Use separate short PostgreSQL transactions at lifecycle checkpoints. Never hold a transaction open while calling MinIO, the embedding API, or Qdrant. Repositories load and save complete aggregates; ORM entities are persistence details.

The application workflow is responsible for coordinated failure: if a registered version cannot be fully indexed, mark the version `FAILED` and its addition `FAILED`. Only a successful complete Qdrant upsert permits `SEARCHABLE`.

## Consequences

- Persisted status is truthful but deliberately coarse-grained.
- Stage-level progress, retry counters, leases, and attempt history require a later model extension.
- There is no distributed transaction. Partial external artifacts are possible after failure.
- The domain layer remains independent of whether the workflow is invoked by HTTP or a future message consumer.

## Rejected alternatives

- Reproduce every Event Storming state now: rejected because most transitions have no implementation in this slice.
- Store only a boolean `searchable`: rejected because it cannot distinguish active processing from failure.
- Let Qdrant success implicitly define searchability: rejected because PostgreSQL owns the business-visible lifecycle.

