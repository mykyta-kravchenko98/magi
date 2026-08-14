# Persistence adapter integration tests

The documents context keeps domain aggregates independent of SQLAlchemy and MinIO.
PostgreSQL repositories translate between aggregates and ORM rows through explicit
mappers. Value objects are flattened into their owning row and reconstructed on reads.
`SqlAlchemyUnitOfWork` owns one async session and explicit commit/rollback boundaries.

`MinioObjectStorage` runs the synchronous official MinIO SDK in worker threads, configures
explicit connect/read timeouts with retries disabled, creates the configured bucket when
needed, and refuses to replace an existing immutable object key.

The default test suite skips tests that require external services. Start PostgreSQL and
MinIO, apply migrations, and opt in explicitly from PowerShell:

```powershell
docker compose up -d postgres minio
uv run alembic -n documents upgrade head
$env:MAGI_RUN_INTEGRATION_TESTS = "true"
uv run pytest tests/integration
```

The tests use the normal `MAGI_DATABASE_URL` and `MAGI_OBJECT_STORAGE_*` settings. Object
keys and relational aggregate IDs are unique per run, and test-created records and
objects are removed afterward. The seeded `Technical Literature` knowledge base must be
present at revision `documents_0006`.

The adapter performs a pre-upload existence check because the MinIO Python SDK's
high-level `put_object` API does not expose a conditional create option. Application code
must continue to generate unique immutable object keys; the check prevents ordinary
accidental replacement but is not a distributed uniqueness lock.
