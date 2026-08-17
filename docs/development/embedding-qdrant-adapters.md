# Embedding and Qdrant adapters

The walking-skeleton infrastructure has two independent asynchronous adapters:

- `TeiEmbeddingProvider` implements the ingestion-owned `EmbeddingProvider` port over
  TEI's `/info` and `/embed` endpoints;
- `QdrantVectorIndex` implements the retrieval-owned `VectorIndex` port over Qdrant's
  REST API.

Neither application port depends on HTTPX, TEI, or Qdrant. The adapters translate
transport and protocol failures to application-owned exceptions.

Application DTOs live separately from ports under `application/models`, application
services under `application/services`, and application-owned failure types under
`application/errors`. Immutable TEI and Qdrant configuration records remain next to
their infrastructure adapters in dedicated `config.py` modules: they have value semantics,
but are neither domain value objects nor application DTOs.

## Runtime guarantees

The TEI adapter:

- splits inputs into ordered, configurable request batches;
- applies one configurable HTTP timeout;
- verifies the loaded model ID and pinned revision through `/info` once per adapter;
- rejects a changed vector count, dimension, non-numeric value, `NaN`, or infinity.

The Qdrant adapter:

- creates an unnamed dense-vector collection when it is absent;
- rejects an existing collection with a different dimension or distance;
- validates every vector before network I/O and writes points in configurable batches;
- derives the point UUID with UUIDv5 from `(document_version_id, chunk_index)`;
- uses Qdrant upsert with `wait=true`, so retrying the same immutable chunk identity
  updates the same point and waits until the operation is applied.

Changing the embedding dimension, distance, tokenizer, or chunking profile requires a new
collection and a full reindex. Do not mix points produced by incompatible processing profiles.
Token-aware profile v1 uses `magi_knowledge_chunks_qwen3_06b_1024_token_v1`; the previous
character-profile collection remains available for baseline comparison until it is explicitly
retired.

## Local integration test

Start Qdrant and the pinned GPU embedding server:

```shell
docker compose up --detach qdrant
docker compose --profile gpu up --detach --wait tei
```

Then opt in to the test that calls both real services, embeds three texts, performs the
same upsert twice, and verifies that Qdrant still contains exactly three points:

```shell
MAGI_RUN_INTEGRATION_TESTS=true uv run pytest \
  tests/integration/test_embedding_qdrant_pipeline.py
```

On PowerShell, set the variable for the current process first:

```powershell
$env:MAGI_RUN_INTEGRATION_TESTS = "true"
uv run pytest tests/integration/test_embedding_qdrant_pipeline.py
```

The test creates a uniquely named collection and removes it in `finally`. Service URLs,
timeouts, batch sizes, vector dimensions, collection name, and optional Qdrant API key
are configured with the `MAGI_EMBEDDING_*` and `MAGI_QDRANT_*` variables listed in
`.env.example`. These adapter settings are required environment input and have no
fallback values in Python; copying `.env.example` provides the local development
profile.
