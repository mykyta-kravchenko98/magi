# Walking Skeleton

The upload pipeline stores this Markdown source, parses its structure, normalizes the
content, creates deterministic chunks, generates embeddings, and indexes them in Qdrant.

## Idempotent projection

Each chunk belongs to an immutable document version and receives a deterministic point
identifier. The document becomes searchable only after every point is written.

```python
status = "SEARCHABLE"
assert status == "SEARCHABLE"
```
