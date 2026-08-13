# ADR 0008: Temporary Qwen3-Embedding-0.6B embedding profile

- Status: Amended
- Date: 2026-08-13

## Context

The walking skeleton needs one locally hosted multilingual embedding model for technical books. The target workstation has an NVIDIA RTX 4080 with 16 GB VRAM. The originally selected Qwen3-Embedding-4B consumes too much of that shared GPU budget to comfortably co-reside with the assistant LLM. Supporting multiple active embedding models, dimension migrations, and runtime model selection would add lifecycle concerns outside this slice.

## Decision

Use the following immutable embedding profile for the first Qdrant projection:

```text
profile_id = qwen3-embedding-0.6b-v1
server = Hugging Face Text Embeddings Inference
model_id = Qwen/Qwen3-Embedding-0.6B
model_revision = to be pinned before durable indexing
tokenizer_revision = model_revision
vector_dimension = 1024
distance = Cosine
document_instruction = none
```

For the current implementation, use the 0.6B model's full 1024-dimensional output rather than Matryoshka truncation. This is a temporary GPU-capacity tradeoff, not a finding that 0.6B matches the retrieval quality of 4B. Pin the exact model revision in configuration before creating a durable projection and record the profile ID with that projection. The application talks to TEI through `EmbeddingProvider`; it does not import PyTorch, Transformers, CUDA, or model-specific runtime code.

For document embeddings, prefix non-empty `heading_path` values to the normalized chunk content but do not apply a query instruction. The future retrieval slice may define and version a fixed query instruction separately.

The adapter rejects a response with the wrong model identity or revision when exposed by the server, wrong item count, wrong dimension, non-finite values, or reordered/missing results. Qdrant uses a dedicated collection compatible with dimension 1024 and Cosine distance.

## Consequences

- The 0.6B model leaves substantially more of the 16 GB GPU budget available for the assistant LLM than the 4B model.
- A model, dimension, tokenizer, instruction, or distance change creates a new embedding profile and Qdrant projection; it is not an in-place configuration edit.
- The 1024-dimensional vectors require less Qdrant storage and memory than the 4B model's 2560-dimensional vectors.
- Moving to 4B later requires retrieval evaluation, a new 2560-dimensional collection/profile, and complete document re-embedding.
- TEI remains a replaceable adapter detail behind the existing port.

## References

- [Qwen3-Embedding-0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [Qwen3-Embedding-4B model card](https://huggingface.co/Qwen/Qwen3-Embedding-4B)
- [TEI supported models and hardware](https://huggingface.co/docs/text-embeddings-inference/en/supported_models)

## Rejected alternatives

- `Qwen/Qwen3-Embedding-4B`: deferred until retrieval evaluation justifies its higher quality and the deployment can allocate enough VRAM without crowding out the assistant LLM.
- Reduced vector dimensions: rejected until retrieval evaluation demonstrates an acceptable quality/storage tradeoff.
- Load the model inside the FastAPI process: rejected because it couples application deployment to CUDA and model runtime libraries.
- Select a model per request: rejected because the walking skeleton has one immutable projection profile.
