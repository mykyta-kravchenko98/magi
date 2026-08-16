# PDF normalization similarity baseline

Capture a retrieval baseline before changing PDF normalization. This is development-only
evaluation tooling: it calls the configured TEI and Qdrant services directly and does not add a
retrieval endpoint or production application behavior.

The checked-in suite at `evaluation/pdf-normalization/queries.json` contains semantic body
queries plus diagnostics for table-of-contents competition, line-break hyphenation, and repeated
page furniture. Keep the suite and `top-k` unchanged when comparing pipeline revisions.

## Capture the current baseline

Start the complete GPU stack and make sure document version
`bbf15cac-8a40-4831-bc81-732bd958ff24` is still present in the configured Qdrant collection. From
the repository root run:

```powershell
uv run python -m scripts.capture_similarity_baseline `
  --suite evaluation/pdf-normalization/queries.json `
  --document-version-id bbf15cac-8a40-4831-bc81-732bd958ff24 `
  --top-k 5 `
  --output evaluation/pdf-normalization/baseline-before-normalization.json
```

The command uses the `MAGI_EMBEDDING_*` and `MAGI_QDRANT_*` settings from `.env`. It fails on a
TEI model identity/revision mismatch and restricts every Qdrant query to the supplied immutable
document version. It records:

- capture time and Git revision;
- suite, document version, collection, and `top-k`;
- embedding model, revision, dimension, and the absence of a query instruction;
- Qdrant collection configuration;
- ranked point IDs, cosine scores, and complete payloads for every query.

Query vectors are intentionally omitted from the artifact. Review and commit the resulting JSON
before normalization changes so it remains an immutable comparison input.

## Compare after normalization

Upload the same PDF after the normalization changes, then run the same command with the new
`document_version_id` and a different output file:

```powershell
uv run python -m scripts.capture_similarity_baseline `
  --suite evaluation/pdf-normalization/queries.json `
  --document-version-id <new-document-version-id> `
  --top-k 5 `
  --output evaluation/pdf-normalization/baseline-after-normalization.json
```

Do not compare a mixed collection without the document-version filter. Chunk identities and
scores may change after normalization; compare relevance, content role, text quality, and noisy
result frequency rather than expecting identical point IDs.
