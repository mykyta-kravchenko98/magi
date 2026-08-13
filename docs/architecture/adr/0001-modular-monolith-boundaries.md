# ADR 0001: Modular monolith and dependency boundaries

- Status: Accepted
- Date: 2026-08-13

## Context

The first vertical slice crosses document intake, text ingestion, and vector indexing. Splitting these concerns into deployable services would add distribution and delivery problems before the domain boundaries are proven. Putting everything into technical layers would make later ownership and extraction difficult.

## Decision

Build one deployable application as a modular monolith with three business modules:

- `documents`: knowledge bases, additions, documents, versions, and the upload workflow;
- `ingestion`: parsing, normalization, chunking, and embedding generation;
- `retrieval`: Qdrant projection and indexing.

Each module contains `domain`, `application`, and `infrastructure` packages. HTTP routes are module-owned inbound adapters. `bootstrap` constructs dependencies; `shared` contains only technical primitives with no business ownership.

Dependencies point inward. Domain code uses only the standard library. Application code depends on domain types and ports. Infrastructure implements ports and owns external SDK usage.

The `documents` upload workflow may call the public application contracts of `ingestion` and `retrieval`. Modules must not import another module's infrastructure, ORM mappings, or private domain objects.

## Consequences

- There is one image, one database deployment, and one composition root.
- Domain rules can be tested without external services.
- Module boundaries are explicit enough to extract later if operational evidence justifies it.
- Cross-module calls are currently in-process and do not claim network or delivery semantics.
- Some workflow coordination lives in `documents.application`; this is intentional because document lifecycle owns the user-visible outcome.

## Rejected alternatives

- Microservices now: rejected because it introduces broker, delivery, observability, and distributed consistency work outside the walking-skeleton goal.
- One package per technical layer: rejected because it obscures business ownership and encourages shared persistence models.
- A generic shared domain: rejected because it couples bounded contexts through ambiguous abstractions.

