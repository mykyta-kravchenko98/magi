# magi

Python backend for a modular-monolith RAG system.

## Development

Prerequisites: [uv](https://docs.astral.sh/uv/) and Python 3.13.

```shell
uv sync --locked
uv run magi-migrate
uv run uvicorn magi.bootstrap.app:app --reload
```

Database migrations are independently owned by each bounded context. Run one history
directly when needed:

```shell
uv run alembic -n documents upgrade head
uv run alembic -n ingestion upgrade head
uv run alembic -n retrieval upgrade head
```

`docker compose up` runs the three histories through a one-shot `migrations` service
before starting the API.

The documents migration history seeds one active knowledge base for the walking skeleton:

```text
Name: Technical Literature
ID:   c87d83a0-eac5-4a2c-9b7d-31fbdce39f51
```

It is deployment seed data, not a content-deduplication or knowledge-base management API.

Configuration uses `MAGI_`-prefixed environment variables; copy `.env.example` to
`.env` for local overrides. The default database URL targets PostgreSQL on
`localhost:5432`.

- `GET /health/live` reports process liveness and performs no external I/O.
- `GET /health/ready` checks that PostgreSQL accepts a query.
- Interactive API documentation is available at `/docs` unless
  `MAGI_DOCS_ENABLED=false`.

Run the same checks as CI with:

```shell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
uv build --no-sources
docker build -t magi:local .
```

The source tree follows the bounded contexts documented below. Each business module
has explicit `domain`, `application`, and `infrastructure` packages; concrete
dependencies are assembled only in `magi.bootstrap`.

The current architectural target is the data-upload walking skeleton. See:

- [Walking skeleton scope](docs/architecture/walking-skeleton-scope.md)
- [Documents domain model](docs/architecture/documents-domain-model.md)
- [Architecture Decision Records](docs/architecture/adr/README.md)
- [Local embedding server on RTX 4080](docs/development/embedding-server.md)
