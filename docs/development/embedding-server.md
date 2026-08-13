# Local embedding server on RTX 4080

This setup runs Hugging Face Text Embeddings Inference (TEI) in Docker Desktop through
its WSL2 backend. It is intentionally isolated behind the Compose `gpu` profile and does
not start with a plain `docker compose up`.

## Pinned runtime profile

| Setting | Value |
|---|---|
| TEI image | `ghcr.io/huggingface/text-embeddings-inference:cuda-1.9.3` |
| CUDA target | compute capability 8.9 (Ada Lovelace / RTX 4000) |
| Model | `Qwen/Qwen3-Embedding-0.6B` |
| Model revision | `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` |
| Data type | `float16` |
| Embedding dimension | `1024` |
| Host endpoint | `http://127.0.0.1:8081` |

The initial runtime uses the 0.6B model to preserve enough of the RTX 4080's 16 GB VRAM
for an assistant LLM. The 4B model remains a future quality upgrade after retrieval
evaluation and GPU-budget testing. Moving between these models requires a new embedding
profile and a complete reindex because their default vector dimensions differ.

The TEI patch release and model revision are pinned so container recreation does not
silently change the embedding profile. The `tei-model-cache` named volume stores
downloaded model artifacts across container recreation.

## Host preparation (Windows and WSL2)

1. Install a current NVIDIA Windows driver that supports CUDA in WSL2. Do not install a
   Linux NVIDIA display driver inside WSL; the Windows driver is exposed to WSL2.
2. Install or update WSL2 from an elevated PowerShell:

   ```powershell
   wsl.exe --install
   wsl.exe --update
   wsl.exe --list --verbose
   ```

3. Install Docker Desktop, enable its WSL2 engine and enable integration for the Linux
   distribution that contains the repository.
4. Use Linux containers and run the remaining commands from that WSL2 distribution.

The CUDA toolkit is not required in the WSL distribution merely to run the prebuilt TEI
container. The container carries its CUDA runtime; the host still needs a compatible
Windows NVIDIA driver.

The local RTX 4080 setup was verified with the NVIDIA 596 driver branch. The 610 branch
caused TEI compatibility problems on that machine and was rolled back. Treat this as a
tested local baseline, not as a universal upper bound; re-run the GPU and embedding smoke
tests before adopting a different driver branch.

## Verify GPU passthrough

Check the host and WSL view first:

```powershell
nvidia-smi
wsl.exe nvidia-smi
```

Then verify that Docker can reserve the GPU. The diagnostic image is version-pinned and
matches the CUDA runtime family used by TEI:

```bash
docker run --rm --gpus all nvidia/cuda:12.9.1-base-ubuntu24.04 nvidia-smi
```

The output must list the RTX 4080. Fix WSL2, Docker Desktop integration, or the Windows
driver before starting TEI if this command fails.

## Validate and start TEI

From the repository root in WSL2:

```bash
docker compose --profile gpu config --quiet
docker compose --profile gpu pull tei
docker compose --profile gpu up --detach --wait tei
docker compose --profile gpu ps
```

The first start downloads the model artifacts and can take several minutes.
The Compose healthcheck has a long startup allowance for that initial download and calls
TEI's inference-aware `/health` endpoint. Follow startup progress with:

```bash
docker compose --profile gpu logs --follow tei
```

Only loopback port `8081` is published, so the unauthenticated development endpoint is not
exposed to the local network.

## Verify the HTTP endpoints

Check readiness and the loaded-model metadata:

```bash
curl --fail --silent --show-error http://127.0.0.1:8081/health
curl --fail --silent --show-error http://127.0.0.1:8081/info
```

Run the checked-in smoke test:

```bash
bash scripts/smoke-embedding.sh
```

The script sends a real `/embed` request, requires exactly one 1024-dimensional vector,
and rejects non-numeric values such as `NaN` or infinity. A successful run prints:

```text
Smoke test passed: endpoint=http://127.0.0.1:8081/embed dimension=1024
```

For diagnostics, a raw request is:

```bash
curl --fail-with-body --silent --show-error \
  --header 'Content-Type: application/json' \
  --data '{"inputs":"Magi embedding endpoint check"}' \
  http://127.0.0.1:8081/embed
```

## Stop and preserve the model cache

```bash
docker compose --profile gpu down
```

This preserves `magi_tei-model-cache`. Do not add `--volumes` unless the cached model
download should be deleted deliberately.

## References

- [TEI supported models and GPU images](https://github.com/huggingface/text-embeddings-inference#docker-images)
- [Qwen3-Embedding-0.6B model](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [Qwen3-Embedding-4B model (deferred upgrade)](https://huggingface.co/Qwen/Qwen3-Embedding-4B)
- [Docker Compose GPU reservations](https://docs.docker.com/compose/how-tos/gpu-support/)
- [NVIDIA CUDA on WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/)

