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

### Complete walking skeleton

Copy the local environment profile and start PostgreSQL, MinIO, Qdrant, the GPU-backed
TEI embedding server, migrations, and the API:

```powershell
Copy-Item .env.example .env
# Replace every replace-with-* placeholder in .env with a different random value.
docker compose --profile gpu up --build --detach --wait
docker compose --profile gpu ps
```

The first TEI start downloads the pinned embedding model and can take several minutes. The API
also downloads and caches `tokenizer.json` from the same pinned revision for token-aware chunking;
it does not load model weights. The container cache is stored under the app-owned
`/app/.cache/huggingface` directory.
The API is available at `http://127.0.0.1:8000`. Upload a Markdown document to the seeded
knowledge base with:

```powershell
curl.exe --fail-with-body `
  -F "file=@README.md;type=text/markdown" `
  http://127.0.0.1:8000/api/v1/knowledge-bases/c87d83a0-eac5-4a2c-9b7d-31fbdce39f51/documents
```

The synchronous first slice returns `202 Accepted` after processing and includes the
current addition status. The same resource can be read later at:

```text
GET /api/v1/document-additions/{document_addition_id}
```

Run the real end-to-end Markdown test against the running stack:

```powershell
$env:MAGI_RUN_E2E_TESTS = "true"
uv run pytest tests/e2e/test_markdown_upload.py -v
```

The test uploads `tests/e2e/fixtures/walking_skeleton.md`, polls until `COMPLETED`,
requires `DocumentVersion.SEARCHABLE`, and verifies the version's points directly in
Qdrant. Stop the stack without removing persisted volumes with:

```powershell
docker compose --profile gpu down
```

The documents migration history seeds one active knowledge base for the walking skeleton:

```text
Name: Technical Literature
ID:   c87d83a0-eac5-4a2c-9b7d-31fbdce39f51
```

It is deployment seed data, not a content-deduplication or knowledge-base management API.

Configuration uses `MAGI_`-prefixed environment variables; copy `.env.example` to
`.env` for local overrides. The default database URL targets PostgreSQL on
`localhost:5432`.

The token-aware v1 projection writes to
`magi_knowledge_chunks_qwen3_06b_1024_token_v1`. Documents indexed by the retired character
profile remain in their previous collection and must be uploaded again to create token-profile
points; the application does not silently migrate existing vectors. Existing local `.env` files
must be updated from `.env.example`, especially the `MAGI_CHUNK_*`,
`MAGI_EMBEDDING_INPUT_MAX_TOKENS`, and `MAGI_QDRANT_COLLECTION` values, before rebuilding Compose.

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

Production images are published to ECR only after the `main` CI gate passes. The workflow
records the immutable ECR digest for local, reproducible Compose deployment; it performs no
automatic deployment. See [AWS ECR publishing and local deployment](docs/deployment/aws-ecr.md).

The source tree follows the bounded contexts documented below. Each business module
has explicit `domain`, `application`, and `infrastructure` packages; concrete
dependencies are assembled only in `magi.bootstrap`.

The current architectural target is the data-upload walking skeleton. See:

- [Walking skeleton scope](docs/architecture/walking-skeleton-scope.md)
- [TXT/Markdown/PDF processing pipeline](docs/architecture/text-processing-pipeline.md)
- [Documents domain model](docs/architecture/documents-domain-model.md)
- [Architecture Decision Records](docs/architecture/adr/README.md)
- [Local embedding server on RTX 4080](docs/development/embedding-server.md)
- [Embedding and Qdrant adapters](docs/development/embedding-qdrant-adapters.md)
- [PDF normalization similarity baseline](docs/development/similarity-baseline.md)
- [Persistence adapter integration tests](docs/development/persistence-integration-tests.md)
