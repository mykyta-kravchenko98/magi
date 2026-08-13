# ADR 0002: Synchronous orchestration with an asynchronous evolution path

- Status: Accepted
- Date: 2026-08-13

## Context

The complete upload path includes several network calls and will eventually need durable asynchronous processing. RabbitMQ, outbox/inbox, workers, retries, and reconciliation are explicitly outside the first slice. An in-process background task would appear asynchronous without providing durable delivery.

## Decision

Execute the complete pipeline synchronously from a transport-neutral application use case in the first deployment. The FastAPI route invokes the use case and waits for its result.

Persist the addition before external processing and persist meaningful lifecycle checkpoints. The use case accepts identifiers and application DTOs, not FastAPI request objects. It receives repositories and external capabilities through ports.

Do not use FastAPI background tasks, an in-memory queue, a broker, or an outbox in this slice.

Preserve a future command boundary around “process accepted document addition”. A later worker can invoke that same application behavior using a persisted addition ID. Transport concerns, acknowledgement, redelivery, and integration-event mapping will remain outside the domain layer.

## Consequences

- The first upload request can be slow and is limited by its HTTP timeout.
- Failures are easier to observe and test end to end.
- The API and domain do not pretend to provide durable asynchronous guarantees.
- Adding a worker later changes bootstrap, inbound adapters, and delivery reliability components; it does not require rewriting aggregate rules.
- External writes are not atomic with PostgreSQL. Failed operations can leave stored objects or vector points; cleanup is deferred and status remains truthful.

## Rejected alternatives

- FastAPI `BackgroundTasks`: rejected because process loss can silently abandon accepted work.
- RabbitMQ plus outbox immediately: rejected as outside scope.
- A single database transaction around the pipeline: rejected because it cannot include MinIO, the embedding API, or Qdrant and would hold locks during slow network calls.

