# Documents domain model

The `magi.documents.domain` package implements only the lifecycle required by the data
upload walking skeleton. It uses Python standard-library types and has no persistence,
web-framework, object-storage, embedding, or vector-database dependencies.

The aggregate state machines are:

```text
KnowledgeBase:     ACTIVE -> ARCHIVED

DocumentAddition: ACCEPTED -> PROCESSING -> COMPLETED
                      |            |
                      +----------> FAILED

Document:          ACTIVE

DocumentVersion:  PROCESSING -> SEARCHABLE
                       |
                       +------> FAILED
```

Each aggregate and its lifecycle enum live together in a dedicated module:

```text
documents/domain/
  __init__.py
  _validation.py
  errors.py
  knowledge_base.py
  document_addition.py
  document.py
  document_version.py
  value_objects/
    __init__.py
    processing_failure.py
    search_projection.py
    source_file_metadata.py
```

`documents.domain` re-exports the supported public names, so callers do not depend on
this internal file layout.

`DocumentAddition` owns immutable `SourceFileMetadata`, combining the original filename,
declared media type, and positive byte size. Equality of this metadata does not establish
content identity or deduplication. The addition can enter `PROCESSING` only after receiving
an opaque stored-source reference. Completion requires both a document ID and a
document-version ID. A failed addition stores an immutable `ProcessingFailure` with a
stable error code and never an SDK exception.

`DocumentVersion` becomes `SEARCHABLE` only with an immutable `SearchProjection`. The
value object combines a non-blank projection reference with a positive indexed chunk
count, so incomplete projection states cannot be represented. `COMPLETED`, `SEARCHABLE`,
and all `FAILED` states are terminal. Constructors enforce the same invariants as
transition methods so invalid persistent state cannot be silently rehydrated.

Infrastructure-facing contracts live in `magi.documents.application.interfaces`. They are
structural `typing.Protocol` definitions owned by the consuming application layer:
repositories for complete aggregates, an explicit unit of work, and immutable object
storage. Concrete SQLAlchemy and MinIO adapters depend on these ports, not the reverse.
`Document` and `DocumentVersion` are separate aggregate roots and therefore have separate
repository interfaces and adapters. The unit of work can still persist both through one
database session and transaction.

SQLAlchemy rows live separately in `magi.documents.infrastructure.persistence.models`.
Each aggregate has its own `*Row` mapping. Value objects are flattened into columns of
their owning aggregate table; they do not receive separate tables or identities. The ORM
models contain scalar aggregate references and no relationships. Alembic imports the
models package so all four tables are present in the documents-owned metadata during
autogeneration.

Explicit infrastructure mappers translate domain aggregates to and from ORM rows.
PostgreSQL repositories contain persistence operations only; lifecycle transitions remain
on aggregates. `SqlAlchemyUnitOfWork` supplies all documents repositories from one async
session and exposes explicit commit and rollback checkpoints.

Persistence code is grouped by aggregate and responsibility:

```text
persistence/
  models/       # one SQLAlchemy row module per aggregate
  mappers/      # one domain-to-ORM mapping module per aggregate
  repositories/ # one adapter module per application repository interface
  unit_of_work.py
```

Migration `documents_0006` seeds the active `Technical Literature` knowledge base with
stable ID `c87d83a0-eac5-4a2c-9b7d-31fbdce39f51`. This supplies the pre-created knowledge
base required by the walking skeleton without introducing a management API.

The model intentionally excludes deduplication, user decisions, domain-event dispatch,
retry state, outbox/inbox, workers, and asynchronous messaging.
