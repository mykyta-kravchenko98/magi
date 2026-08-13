# ADR 0008: Qwen3-Embedding-4B embedding profile

- Status: Accepted
- Date: 2026-08-13

## Context

The walking skeleton needs one locally hosted multilingual embedding model for technical books. The target workstation has an NVIDIA RTX 4080 with 16 GB VRAM. Supporting multiple models, dimension migrations, and runtime model selection would add lifecycle concerns outside this slice.

## Decision

Use the following immutable embedding profile for the first Qdrant projection:

```text
profile_id = qwen3-embedding-4b-v1
server = Hugging Face Text Embeddings Inference
model_id = Qwen/Qwen3-Embedding-4B
model_revision = pinned immutable revision
tokenizer_revision = model_revision
vector_dimension = 2560
distance = Cosine
document_instruction = none
```

Use the model's full 2560-dimensional output rather than Matryoshka truncation. Pin the exact model revision in configuration and record the profile ID with the projection. The application talks to TEI through `EmbeddingProvider`; it does not import PyTorch, Transformers, CUDA, or model-specific runtime code.

For document embeddings, prefix non-empty `heading_path` values to the normalized chunk content but do not apply a query instruction. The future retrieval slice may define and version a fixed query instruction separately.

The adapter rejects a response with the wrong model identity or revision when exposed by the server, wrong item count, wrong dimension, non-finite values, or reordered/missing results. Qdrant uses a dedicated collection compatible with dimension 2560 and Cosine distance.

## Consequences

- The model and tokenizer consume a meaningful portion of the 16 GB GPU budget; the infrastructure spike must verify startup, batch size, latency, and peak VRAM on the actual RTX 4080 before implementation is considered complete.
- A model, dimension, tokenizer, instruction, or distance change creates a new embedding profile and Qdrant projection; it is not an in-place configuration edit.
- The 2560-dimensional vectors require more Qdrant storage and memory than the 0.6B model's 1024-dimensional vectors.
- TEI remains a replaceable adapter detail behind the existing port.

## References

- [Qwen3-Embedding-4B model card](https://huggingface.co/Qwen/Qwen3-Embedding-4B)
- [TEI supported models and hardware](https://huggingface.co/docs/text-embeddings-inference/en/supported_models)

## Rejected alternatives

- `Qwen/Qwen3-Embedding-0.6B`: rejected for the initial profile in favor of the selected 4B quality/capacity tradeoff.
- Reduced vector dimensions: rejected until retrieval evaluation demonstrates an acceptable quality/storage tradeoff.
- Load the model inside the FastAPI process: rejected because it couples application deployment to CUDA and model runtime libraries.
- Select a model per request: rejected because the walking skeleton has one immutable projection profile.
